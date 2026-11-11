#!/usr/bin/env python3
"""Historical price-year inputs for model v3: heating years 2016-17 .. 2024-25 (1 Nov - 31 Oct, UTC keys).

For each start year Y writes data/model/gb/years/<Y>/ in the formats of the current-year files:
  prices_year.json  {"agile_X": {"YYYY-MM-DDTHH:MMZ": p}, "cosy_X": {...}}  Agile REBUILT from Elexon MID with today's
                    (AGILE-24-10-01) per-region fit; Cosy = the 2025-26 actual Cosy shape x the year's cap ratio
  agile_actual.json {"agile_X": {...}}   actual Octopus Agile where it exists (validation only)
  carbon_year.json  {"X": {"...Z": gCO2/kWh}}  NESO regional forecast from 10 May 2018; before that NESO national x
                    the region's mean ratio to national over the first 12 months of regional data
  base_demand.json  NESO ND, via gb_base_demand.read()
  tariffs.json      SVR, gas, standing charges, IOG and the Cosy ratio from the Ofgem cap (EPG Oct 2022-Jun 2023)
plus years/meta.json (sources, product codes, fit table, gaps, flags) and years/feedback_beta.json (MID on ND).

Every download is cached under data/model/gb/sources/; a rerun fetches only what is missing. <=2 requests/s.
    .venv/bin/python scripts/spark/gb_v3_prices.py
"""
import csv
import datetime as dt
import json
import re
import sys
import threading
import time
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[2]
G = ROOT / "data" / "model" / "gb"
SRC = G / "sources"
OUT = G / "years"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gb_base_demand import read as nd_read  # noqa: E402  (NESO ND, settlement periods -> UTC)

UTC, LON = dt.timezone.utc, ZoneInfo("Europe/London")
YEARS = range(2016, 2025)
REGIONS = json.load(open(G / "towns.json"))["regions"]          # letter -> carbon API region id
UA = {"User-Agent": "lds-gb-model-v3/1.0 (research; contact via ldsconsultancy.net)"}
ELEXON = "https://data.elexon.co.uk/bmrs/api/v1/datasets/MID/stream"
OCTO = "https://api.octopus.energy/v1/products/"
CI = "https://api.carbonintensity.org.uk/regional/intensity/{a}/{b}"
NESO_DEMAND = "https://api.neso.energy/api/3/action/package_show?id=historic-demand-data"
NESO_MIX = ("https://api.neso.energy/dataset/88313ae5-94e4-4ddc-a790-593554d8c6b9/resource/"
            "f93d1835-75bc-43e5-84ad-12472b180a98/download/df_fuel_ckan.csv")
OFGEM_XLSX = "https://www.ofgem.gov.uk/sites/default/files/2026-08/Default-tariff-cap-level-v1.31.xlsx"
QEP = {"table_224.xlsx": "https://assets.publishing.service.gov.uk/media/6a4245b97ac6fd9c6a94aae2/table_224__1_.xlsx",
       "table_234.xlsx": "https://assets.publishing.service.gov.uk/media/6a424620b9f58f0eb4c13f1b/table_234__1_.xlsx"}
EPG_URL = "https://www.gov.uk/government/publications/energy-bills-support/energy-price-guarantee-up-until-30-june-2023"
REF_PRODUCT = "AGILE-24-10-01"
META = {"flags": [], "gaps": {}}
_lock, _last = threading.Lock(), [0.0]


def get(url, **kw):
    """Throttled GET: at most 2 requests/s across all threads, 3 retries."""
    for k in range(4):
        with _lock:
            wait = _last[0] + 0.5 - time.time()
            if wait > 0:
                time.sleep(wait)
            _last[0] = time.time()
        try:
            r = requests.get(url, headers=UA, timeout=120, **kw)
            if r.status_code == 200:
                return r
            print(f"  HTTP {r.status_code} {url[:120]}", flush=True)
        except requests.RequestException as e:
            print(f"  {e} {url[:120]}", flush=True)
        time.sleep(3 * (k + 1))
    raise RuntimeError(f"failed: {url}")


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    json.dump(obj, open(tmp, "w"), separators=(",", ":"))
    tmp.replace(path)


def key(t):
    return t.strftime("%Y-%m-%dT%H:%MZ")


def hh(a, b):
    t = a
    while t < b:
        yield t
        t += dt.timedelta(minutes=30)


def ystart(y):
    return dt.datetime(y, 11, 1, tzinfo=UTC)


def iso(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(UTC)


# ---------------------------------------------------------------- 1. Elexon market index (MID), APXMIDP
def mid():
    d = SRC / "elexon_mid"
    d.mkdir(parents=True, exist_ok=True)
    out, zero = {}, 0
    q = dt.datetime(2016, 10, 1, tzinfo=UTC)
    while q < dt.datetime(2026, 11, 1, tzinfo=UTC):
        e = dt.datetime(q.year + (q.month + 3 > 12), (q.month + 2) % 12 + 1, 1, tzinfo=UTC)
        f = d / f"MID_APXMIDP_{q:%Y-%m}.json"
        if not f.exists():
            # stream endpoint, one quarter per call; 'to' is inclusive so stop 30 min short
            rows = get(ELEXON, params={"from": key(q), "to": key(e - dt.timedelta(minutes=30)),
                                       "dataProviders": "APXMIDP"}).json()
            save(f, rows)
            print(f"MID {q:%Y-%m}: {len(rows)} rows", flush=True)
        for r in json.load(open(f)):
            if r.get("dataProvider") != "APXMIDP":
                continue
            if not r.get("volume") and not r.get("price"):         # APX reports 0 price at 0 volume: not a price
                zero += 1
                continue
            out[key(iso(r["startTime"]))] = float(r["price"])
        q = e
    # linear interpolation over gaps (zero-volume or absent periods)
    t0, t1 = dt.datetime(2016, 10, 1, tzinfo=UTC), dt.datetime(2026, 11, 1, tzinfo=UTC)
    ks = [key(t) for t in hh(t0, t1)]
    have = np.array([k in out for k in ks])
    v = np.array([out.get(k, np.nan) for k in ks])
    idx = np.arange(len(ks))
    v[~have] = np.interp(idx[~have], idx[have], v[have])
    META["mid"] = {"endpoint": ELEXON, "params": "from, to (inclusive), dataProviders=APXMIDP",
                   "provider_choice": "APXMIDP (EPEX/APX): N2EXMIDP is zero-volume for most periods",
                   "first": ks[int(np.argmax(have))], "zero_price_zero_volume_dropped": zero,
                   "half_hours_interpolated": int((~have).sum()), "unit": "GBP/MWh",
                   "licence": "Elexon BMRS open data licence (attribution)"}
    return dict(zip(ks, v.tolist()))


# ---------------------------------------------------------------- 2. Octopus Agile: products, rates, fit
def agile_products():
    f = SRC / "octopus_agile" / "products.json"
    if f.exists():
        return json.load(open(f))
    seen = {}
    m = dt.date(2018, 3, 1)
    while m <= dt.date(2026, 11, 1):                                  # monthly available_at scan finds retired codes
        for p in get(OCTO, params={"available_at": f"{m}T00:00Z", "page_size": 1500}).json()["results"]:
            c = p["code"]
            if c.startswith("AGILE-") and "OUTGOING" not in c and "-BB-" not in c:
                seen[c] = {"code": c, "available_from": p["available_from"], "available_to": p["available_to"]}
        m = (m.replace(day=28) + dt.timedelta(days=5)).replace(day=1)
    prods = sorted(seen.values(), key=lambda p: p["available_from"])
    for p in prods:
        j = get(OCTO + p["code"] + "/").json()
        p["full_name"], p["description"] = j.get("full_name"), j.get("description")
        cap = re.search(r"capped at (\d+(?:\.\d+)?)p", j.get("description") or "")
        p["cap_inc_vat_stated"] = float(cap.group(1)) if cap else None
    # each product's window = from its launch to the next launch (the Oct-Nov 2022 pause stays on AGILE-22-08-31)
    for i, p in enumerate(prods):
        p["window"] = [max(p["available_from"][:10], "2018-02-21"),
                       prods[i + 1]["available_from"][:10] if i + 1 < len(prods) else "2026-11-01"]
    save(f, prods)
    return prods


def agile_rates(code, reg, a, b):
    f = SRC / "octopus_agile" / f"{code}_{reg}.json"
    if f.exists():
        return json.load(open(f))
    out = {}
    url = f"{OCTO}{code}/electricity-tariffs/E-1R-{code}-{reg}/standard-unit-rates/"
    params = {"period_from": f"{a}T00:00Z", "period_to": f"{b}T00:00Z", "page_size": 1500}
    A, B = iso(f"{a}T00:00Z"), iso(f"{b}T00:00Z")
    while url:
        j = get(url, params=params).json()
        params = None
        for x in j["results"]:
            s = iso(x["valid_from"])
            e = iso(x["valid_to"]) if x.get("valid_to") else s + dt.timedelta(minutes=30)
            for t in hh(max(s, A), min(e, B)):
                out[key(t)] = [x["value_exc_vat"], x["value_inc_vat"]]
        url = j.get("next")
    save(f, out)
    print(f"agile {code} {reg}: {len(out)} half-hours", flush=True)
    return out


def peak(k):
    """16:00-19:00 UK local time."""
    h = iso(k).astimezone(LON)
    return 16 <= h.hour < 19


def fit_agile(prods, W):
    """Per product x region: ex-VAT Agile = min(D*W + P*peak [+ c], cap), W = MID in p/kWh. Capped points excluded."""
    jobs = [(p, r) for p in prods for r in REGIONS]
    with ThreadPoolExecutor(2) as ex:
        rates = dict(zip([(p["code"], r) for p, r in jobs],
                         ex.map(lambda pr: agile_rates(pr[0]["code"], pr[1], *pr[0]["window"]), jobs)))
    table, actual = [], {}
    for p in prods:
        for r in REGIONS:
            R = rates[(p["code"], r)]
            ks = [k for k in sorted(R) if k in W]
            if not ks:
                continue
            for k in ks:
                actual.setdefault(r, {})[k] = R[k][1]
            y = np.array([R[k][0] for k in ks])
            w = np.array([W[k] / 10 for k in ks])
            pk = np.array([peak(k) for k in ks], float)
            cap = (p["cap_inc_vat_stated"] / 1.05) if p["cap_inc_vat_stated"] else float(y.max())
            ok = y < cap - 0.01
            row = {"product": p["code"], "region": r, "window": p["window"], "n": len(ks),
                   "n_capped": int((~ok).sum()), "cap_exc_vat": round(cap, 3)}
            for name, X in (("no_intercept", np.c_[w, pk]), ("intercept", np.c_[w, pk, np.ones_like(w)])):
                b = np.linalg.lstsq(X[ok], y[ok], rcond=None)[0]
                pred = np.minimum(X @ b, cap)
                row[name] = {"D": round(b[0], 4), "P": round(b[1], 3), **({"c": round(b[2], 3)} if len(b) > 2 else {}),
                             "rmse_p": round(float(np.sqrt(np.mean((pred - y) ** 2))), 3),
                             "r2": round(float(1 - np.var(pred - y) / np.var(y)), 4)}
            table.append(row)
    return table, actual


# ---------------------------------------------------------------- 3. Ofgem cap, EPG, DESNZ QEP
_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def xlsx_sheet(path, name):
    """Minimal stdlib xlsx reader: {row: {col: value}} (no openpyxl in .venv)."""
    z = zipfile.ZipFile(path)
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rel = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    rid = [s.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
           for s in wb.iter(_NS + "sheet") if s.get("name") == name][0]
    ss = ["".join(t.text or "" for t in si.iter(_NS + "t"))
          for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(_NS + "si")]
    rows = {}
    for _, el in ET.iterparse(z.open("xl/" + rel[rid].lstrip("/").replace("xl/", ""))):
        if el.tag == _NS + "c" and el.find(_NS + "v") is not None:
            v, t = el.find(_NS + "v").text, el.get("t")
            v = ss[int(v)] if t == "s" else (v if t in ("str", "b", "e") else float(v))
            m = re.match(r"([A-Z]+)(\d+)", el.get("r"))
            rows.setdefault(int(m.group(2)), {})[m.group(1)] = v
            el.clear()
    return rows


def download(url, path):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(get(url).content)
    return path


MON = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}


def cap_periods():
    """GB-average direct-debit cap per period from Ofgem 1b Historical level tables (inc VAT):
    unit p/kWh = (typical - nil) / benchmark kWh; standing p/day = nil / 365."""
    f = download(OFGEM_XLSX, SRC / "ofgem_cap" / "Default-tariff-cap-level-v1.31.xlsx")
    R = xlsx_sheet(f, "1b Historical level tables")
    hdr = R[12]
    groups = {"elec": ("C", "AE"), "gas": ("BM", "CO")}               # single-rate electricity, gas; Other (DD)

    def ci(c):
        return sum((ord(ch) - 64) * 26 ** i for i, ch in enumerate(reversed(c)))
    out = []
    for col in sorted(hdr, key=ci):
        if not (ci(groups["elec"][0]) <= ci(col) <= ci(groups["elec"][1])):
            continue
        lab = hdr[col]
        m = re.match(r"(\w{3})\w* (\d{4}) - (\w{3})\w* (\d{4})", lab)
        a = dt.date(int(m.group(2)), MON[m.group(1)], 1)
        b = dt.date(int(m.group(4)), MON[m.group(3)], 1)
        b = (b.replace(day=28) + dt.timedelta(days=5)).replace(day=1)
        bench = (3100, 12000) if a < dt.date(2026, 1, 1) else (2700, 11500) if a < dt.date(2026, 7, 1) else (2500, 9500)
        gcol = [c for c in hdr if hdr[c] == lab and ci(groups["gas"][0]) <= ci(c) <= ci(groups["gas"][1])][0]
        e_nil, e_typ, g_nil, g_typ = R[28][col], R[46][col], R[28][gcol], R[46][gcol]
        out.append({"label": lab, "from": a.isoformat(), "to": b.isoformat(), "benchmark_kwh": bench,
                    "elec_p": round(100 * (e_typ - e_nil) / bench[0], 3), "elec_sc_p_day": round(100 * e_nil / 365, 3),
                    "gas_p": round(100 * (g_typ - g_nil) / bench[1], 3), "gas_sc_p_day": round(100 * g_nil / 365, 3),
                    "basis": "Ofgem cap" if a >= dt.date(2019, 1, 1) else "Ofgem illustrative (pre-cap)"})
    # Energy Price Guarantee, 1 Oct 2022 - 30 Jun 2023: GB-average DD unit rates 34.0p and 10.3p inc VAT (gov.uk)
    for p in out:
        if dt.date(2022, 10, 1) <= dt.date.fromisoformat(p["from"]) < dt.date(2023, 7, 1):
            p.update(elec_p_cap=p["elec_p"], gas_p_cap=p["gas_p"], elec_p=34.0, gas_p=10.3, basis="EPG (gov.uk)")
    # Nov 2016 - Mar 2017: no Ofgem figure; Apr-Sep 2017 x DESNZ QEP direct-debit 2016/2017 calendar-year ratio
    q = {}
    for name, sheet in (("table_224.xlsx", "2.2.4"), ("table_234.xlsx", "2.3.4")):
        T = xlsx_sheet(download(QEP[name], SRC / "desnz_qep" / name), sheet)
        for r in T.values():
            if r.get("B") == "United Kingdom" and isinstance(r.get("A"), float):
                q.setdefault(name[:9], {})[int(r["A"])] = {"unit_p": 100 * r["F"], "fixed_gbp_yr": r["G"]}
    first = out[0]
    re_, rg = (q["table_224"][2016]["unit_p"] / q["table_224"][2017]["unit_p"],
               q["table_234"][2016]["unit_p"] / q["table_234"][2017]["unit_p"])
    out.insert(0, {"label": "Nov 2016 - Mar 2017 (back-cast)", "from": "2016-10-01", "to": "2017-04-01",
                   "elec_p": round(first["elec_p"] * re_, 3), "elec_sc_p_day": first["elec_sc_p_day"],
                   "gas_p": round(first["gas_p"] * rg, 3), "gas_sc_p_day": first["gas_sc_p_day"],
                   "basis": f"Ofgem illustrative Apr-Sep 2017 x DESNZ QEP DD 2016/2017 (elec {re_:.3f}, gas {rg:.3f})"})
    META["retail_sources"] = {"ofgem": OFGEM_XLSX, "ofgem_sheet": "1b Historical level tables, Other payment method "
                              "(direct debit), GB average, Total inc VAT, nil and benchmark consumption",
                              "epg": EPG_URL, "qep": QEP, "qep_uk_direct_debit": q}
    return out


def cap_at(periods, t):
    d = t.astimezone(LON).date()
    for p in periods:
        if p["from"] <= d.isoformat() < p["to"]:
            return p
    raise KeyError(d)


# ---------------------------------------------------------------- 4/5. NESO demand and carbon
def demand():
    files = {}
    res = get(NESO_DEMAND).json()["result"]["resources"]
    for y in list(YEARS) + [2025]:
        f = SRC / "neso_demand" / f"demanddata_{y}.csv"
        if not f.exists():
            url = [r["url"] for r in res if r["url"].endswith(f"demanddata_{y}.csv")][0]
            download(url, f)
        files[y] = f
    out = {}
    for y, f in sorted(files.items()):
        out.update(nd_read(iso_dates(f)))
    out.update(nd_read(SRC / "neso_demand" / "demanddataupdate_2026.csv"))
    return out


def iso_dates(f):
    """Older NESO files write SETTLEMENT_DATE as 01-JAN-2016; read() expects ISO. Write an ISO copy (cached) and use it."""
    with open(f) as fh:
        rows = list(csv.DictReader(fh))
    if re.match(r"\d{4}-\d{2}-\d{2}", rows[0]["SETTLEMENT_DATE"].strip('"')):
        return f
    g = f.parent / "iso" / f.name
    if g.exists() and sum(1 for _ in open(g)) < 1000:                 # a half-written cache from a failed run
        g.unlink()
    if not g.exists():
        g.parent.mkdir(exist_ok=True)
        with open(g, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            for r in rows:
                d = r["SETTLEMENT_DATE"].strip('"').title()            # 01-Jan-2016, or 01-Jan-23 in the 2023 file
                r["SETTLEMENT_DATE"] = dt.datetime.strptime(d, "%d-%b-%Y" if len(d.split("-")[-1]) == 4 else "%d-%b-%y").date().isoformat()
                w.writerow(r)
    return g


def carbon_national():
    f = download(NESO_MIX, SRC / "neso_genmix" / "df_fuel_ckan.csv")
    out = {}
    for r in csv.DictReader(open(f)):
        t = dt.datetime.fromisoformat(r["DATETIME"][:19]).replace(tzinfo=UTC)
        if t.year >= 2016 and r["CARBON_INTENSITY"] not in ("", None):
            out[key(t)] = float(r["CARBON_INTENSITY"])
    return out


def carbon_regional():
    d = SRC / "carbon_regional"
    d.mkdir(parents=True, exist_ok=True)
    a, stop = dt.datetime(2018, 5, 10, 23, 30, tzinfo=UTC), dt.datetime(2025, 11, 1, tzinfo=UTC)
    chunks = []
    while a < stop:
        b = min(a + dt.timedelta(days=13), stop)
        chunks.append((a, b))
        a = b

    def one(ab):
        a, b = ab
        f = d / f"{a:%Y%m%dT%H%M}.json"
        if not f.exists():
            save(f, get(CI.format(a=key(a), b=key(b))).json())
        return json.load(open(f))
    out = {}
    with ThreadPoolExecutor(2) as ex:
        for j in ex.map(one, chunks):
            for x in j.get("data", []):
                for r in x["regions"]:
                    if r["intensity"].get("forecast") is not None:
                        out.setdefault(int(r["regionid"]), {})[x["from"][:16] + "Z"] = r["intensity"]["forecast"]
    return out


# ---------------------------------------------------------------- 6. beta: MID on ND
def ols(x, y, lags=48):
    X = np.c_[np.ones_like(x), x]
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    e = y - X @ b
    XtXi = np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(XtXi) * e.var(ddof=2))
    S = (X * e[:, None]).T @ (X * e[:, None])                         # Newey-West HAC, Bartlett kernel
    for L in range(1, lags + 1):
        G_ = (X[L:] * e[L:, None]).T @ (X[:-L] * e[:-L, None])
        S += (1 - L / (lags + 1)) * (G_ + G_.T)
    nw = np.sqrt(np.diag(XtXi @ S @ XtXi))
    return {"beta_gbp_mwh_per_gw": round(b[1], 3), "se_ols": round(se[1], 3), "se_newey_west_48": round(nw[1], 3),
            "intercept": round(b[0], 2), "r2": round(float(1 - e.var() / y.var()), 4), "n": int(len(y))}


def beta(W, ND):
    res = {"per_year": {}, "method": "OLS of Elexon MID (GBP/MWh, APXMIDP) on NESO ND (GW), half-hourly; winter = "
           "Nov-Mar local. SEs: OLS and Newey-West (48 half-hour lags). 'fe' pools all years with year-season means "
           "removed (within estimator) so the 2021-23 gas-price level shift does not load onto demand."}
    pool = {"winter": ([], []), "non_winter": ([], [])}
    for y in list(YEARS) + [2025]:
        for s in ("winter", "non_winter"):
            ks = [key(t) for t in hh(ystart(y), ystart(y + 1)) if (t.astimezone(LON).month in (11, 12, 1, 2, 3)) ==
                  (s == "winter") and key(t) in ND and key(t) in W]
            x, v = np.array([ND[k] / 1000 for k in ks]), np.array([W[k] for k in ks])
            res["per_year"].setdefault(f"{y}-{(y + 1) % 100:02d}", {})[s] = ols(x, v)
            pool[s][0].append(x)
            pool[s][1].append(v)
    for s, (xs, vs) in pool.items():
        res[f"pooled_{s}"] = ols(np.concatenate(xs), np.concatenate(vs))
        res[f"fe_{s}"] = ols(np.concatenate([x - x.mean() for x in xs]), np.concatenate([v - v.mean() for v in vs]))
    res["recommended"] = {"winter": res["fe_winter"]["beta_gbp_mwh_per_gw"],
                          "non_winter": res["fe_non_winter"]["beta_gbp_mwh_per_gw"],
                          "note": "within-year slope; per-year values show it varies with the gas price (2022 high)"}
    return res


# ---------------------------------------------------------------- assemble per year
def shift_local(t, y_src0):
    """The 2025-26 instant with the same UK local month-day and clock time as t (29 Feb -> 28 Feb)."""
    lt = t.astimezone(LON)
    day = 28 if (lt.month, lt.day) == (2, 29) else lt.day
    yy = y_src0 if lt.month >= 11 else y_src0 + 1
    return dt.datetime(yy, lt.month, day, lt.hour, lt.minute, fold=lt.fold, tzinfo=LON).astimezone(UTC)


def build():
    W = mid()
    prods = agile_products()
    META["agile_products"] = [{k: p[k] for k in ("code", "full_name", "available_from", "available_to", "window",
                                                 "cap_inc_vat_stated")} for p in prods]
    table, actual = fit_agile(prods, W)
    META["agile_fit"] = table
    ref = {r["region"]: r for r in table if r["product"] == REF_PRODUCT}
    caps = cap_periods()
    META["cap_periods"] = caps
    cur = json.load(open(G / "prices_year.json"))
    ND = demand()
    CN, CR = carbon_national(), carbon_regional()
    # regional / national ratio over the first 12 months of regional data
    r0, r1 = dt.datetime(2018, 5, 11, tzinfo=UTC), dt.datetime(2019, 5, 11, tzinfo=UTC)
    kk = [key(t) for t in hh(r0, r1) if key(t) in CN]
    ratio = {reg: float(np.mean([CR[rid][k] for k in kk if k in CR[rid]]) / np.mean([CN[k] for k in kk]))
             for reg, rid in REGIONS.items()}
    gb = [k for k in kk if k in CR.get(18, {})]
    lagc = {L: float(np.corrcoef([CN[k] for k in gb[2:-2]], [CR[18][gb[i + L]] for i in range(2, len(gb) - 2)])[0, 1])
            for L in (-2, -1, 0, 1, 2)}
    META["carbon"] = {"regional": "api.carbonintensity.org.uk /regional/intensity/{from}/{to} (forecast), from "
                      "2018-05-10T23:30Z", "national": NESO_MIX + " (CARBON_INTENSITY, UTC)",
                      "pre_regional_method": "NESO national x region ratio (mean regional / mean national, "
                      "11 May 2018 - 10 May 2019)", "ratio": {k: round(v, 3) for k, v in ratio.items()},
                      "national_vs_api_GB_correlation_by_lag": lagc}
    ref_cap = {key(t): cap_at(caps, t) for t in hh(ystart(2025), ystart(2026))}
    ref_mean = float(np.mean([p["elec_p"] for p in ref_cap.values()]))
    ref_gas = float(np.mean([p["gas_p"] for p in ref_cap.values()]))
    META["reference_2025_26"] = {"svr_p": round(ref_mean, 3), "gas_p": round(ref_gas, 3),
                                 "note": "time-weighted cap-derived values for 1 Nov 2025 - 31 Oct 2026; cfg.py uses "
                                 "SVR_P 26.47, GAS_P 8.17, IOG (6.6, 35.61)"}
    for y in YEARS:
        d = OUT / str(y)
        ts = list(hh(ystart(y), ystart(y + 1)))
        P, A, C, gaps = {}, {}, {}, {}
        caps_y = [cap_at(caps, t) for t in ts]
        for reg in REGIONS:
            f = ref[reg]["no_intercept"]
            cap = ref[reg]["cap_exc_vat"]
            P[f"agile_{reg}"] = {key(t): round(1.05 * min(f["D"] * W[key(t)] / 10 + f["P"] * peak(key(t)), cap), 2)
                                 for t in ts}
            cz = cur[f"cosy_{reg}"]
            cs, miss = {}, 0
            for t, cp in zip(ts, caps_y):
                s = shift_local(t, 2025)
                ks = key(s)
                if ks not in cz:
                    ks = key(s - dt.timedelta(minutes=30))
                    miss += 1
                src = cap_at(caps, iso(ks))
                cs[key(t)] = round(cz[ks] * cp["elec_p"] / src["elec_p"], 4)
            P[f"cosy_{reg}"] = cs
            gaps[f"cosy_{reg}_slot_borrowed"] = miss
            act = {key(t): actual.get(reg, {}).get(key(t)) for t in ts}
            act = {k: v for k, v in act.items() if v is not None}
            if act:
                A[f"agile_{reg}"] = act
            rid = REGIONS[reg]
            ser, nat, fill = {}, 0, 0
            for t in ts:
                k = key(t)
                if k in CR.get(rid, {}):
                    ser[k] = CR[rid][k]
                elif t < dt.datetime(2018, 5, 10, 23, 30, tzinfo=UTC) and k in CN:
                    ser[k] = round(CN[k] * ratio[reg], 1)
                    nat += 1
                else:
                    ser[k] = None
            m = float(np.mean([v for v in ser.values() if v is not None]))
            for k, v in ser.items():
                if v is None:
                    ser[k] = round(m, 1)
                    fill += 1
            C[reg] = ser
            gaps[f"carbon_{reg}_national_scaled"], gaps[f"carbon_{reg}_filled_region_mean"] = nat, fill
        bd, nd_fill = {}, []
        for t in ts:
            k = key(t)
            if k not in ND:
                k2 = key(t - dt.timedelta(days=7))
                nd_fill.append(k)
                bd[key(t)] = ND[k2]
            else:
                bd[k] = ND[k]
        v = list(bd.values())
        e = np.array([p["elec_p"] for p in caps_y])
        tar = {"year": f"{y}-{(y + 1) % 100:02d}", "svr_p": round(float(e.mean()), 3),
               "svr_p_nov_mar": round(float(np.mean([p["elec_p"] for t, p in zip(ts, caps_y)
                                                    if t.astimezone(LON).month in (11, 12, 1, 2, 3)])), 3),
               "gas_p": round(float(np.mean([p["gas_p"] for p in caps_y])), 3),
               "gas_sc_p_day": round(float(np.mean([p["gas_sc_p_day"] for p in caps_y])), 3),
               "elec_sc_p_day": round(float(np.mean([p["elec_sc_p_day"] for p in caps_y])), 3),
               "elec_ratio_to_2025_26": round(float(e.mean()) / ref_mean, 4),
               "gas_ratio_to_2025_26": round(float(np.mean([p["gas_p"] for p in caps_y])) / ref_gas, 4)}
        tar["iog"] = [round(6.6 * tar["elec_ratio_to_2025_26"], 3), round(35.61 * tar["elec_ratio_to_2025_26"], 3)]
        tar["cosy_mean_p"] = {r: round(float(np.mean(list(P[f"cosy_{r}"].values()))), 3) for r in REGIONS}
        tar["agile_mean_p"] = {r: round(float(np.mean(list(P[f"agile_{r}"].values()))), 3) for r in REGIONS}
        tar["periods"] = sorted({(p["label"], p["elec_p"], p["gas_p"], p["basis"]) for p in caps_y},
                                key=lambda x: x[0])
        tar["notes"] = ("Unit rates and standing charges inc VAT, GB-average direct debit. svr/gas are time-weighted "
                        "over the year. IOG = cfg.IOG (6.6, 35.61) x elec_ratio. Cosy series = 2025-26 actual Cosy "
                        "at the same local clock time x (cap unit rate this period / cap unit rate 2025-26 period).")
        tar["flags"] = [p for p in {c["basis"] for c in caps_y} if p != "Ofgem cap"]
        save(d / "prices_year.json", P)
        save(d / "agile_actual.json", A)
        save(d / "carbon_year.json", C)
        save(d / "base_demand.json", {"series": bd, "filled_from_prior_year": sorted({k[:10] for k in nd_fill}),
                                      "fill_rule": "a missing half-hour takes the same UTC slot 7 days earlier",
                                      "unit": "MW", "column": "ND",
                                      "source": f"NESO Historic Demand Data {y} and {y + 1} via gb_base_demand.read()",
                                      "stats": {"max_mw": max(v), "min_mw": min(v), "mean_mw": sum(v) / len(v)}})
        save(d / "tariffs.json", tar)
        # validation: reconstruction vs actual
        val = {}
        for reg in REGIONS:
            ks = [k for k in A.get(f"agile_{reg}", {})]
            if ks:
                a_ = np.array([A[f"agile_{reg}"][k] for k in ks])
                r_ = np.array([P[f"agile_{reg}"][k] for k in ks])
                val[reg] = {"n": len(ks), "rmse_p": round(float(np.sqrt(np.mean((a_ - r_) ** 2))), 3),
                            "mean_actual": round(float(a_.mean()), 3), "mean_recon": round(float(r_.mean()), 3)}
        META["gaps"][str(y)] = {"base_demand_half_hours_filled": len(nd_fill), **gaps}
        META.setdefault("validation_recon_vs_actual", {})[str(y)] = val
        print(f"{y}: svr {tar['svr_p']} gas {tar['gas_p']} ratio {tar['elec_ratio_to_2025_26']} "
              f"agile(A) {tar['agile_mean_p']['A']} val(A) {val.get('A')}", flush=True)
    b = beta(W, ND)
    save(OUT / "feedback_beta.json", b)
    META["beta"] = {k: b[k] for k in b if k != "per_year"}
    META["agile_reconstruction"] = {"product": REF_PRODUCT, "form": "inc VAT = 1.05 x min(D*W + P*[16:00-19:00 "
                                    "local], cap_exc_vat), W = MID GBP/MWh / 10, per-region D, P from the "
                                    "no-intercept fit of value_exc_vat", "coefficients": {r: {**ref[r]["no_intercept"],
                                    "cap_exc_vat": ref[r]["cap_exc_vat"]} for r in REGIONS}}
    META["generated"] = dt.datetime.now(UTC).isoformat(timespec="seconds")
    META["script"] = "scripts/spark/gb_v3_prices.py"
    save(OUT / "meta.json", META)


if __name__ == "__main__":
    build()
