#!/usr/bin/env python3
"""Model v3 housing stock: an empirical dwelling distribution per town (79 towns), calibrated to metered gas.

Method (docs/article/lit/methods_v3.md section 3; plan "Model v3" item 3):
  1. Canet et al. (UKERC EDC, doi:10.5286/ukerc.edc.000944, CC-BY 4.0, latest = version 2 of 14 Oct 2021):
     per 2011 LSOA, number of gas-boiler dwellings and their mean EPC space-heating demand for 4 forms
     (detached, semi, terraced, flat). EPC HEATING_COST_CURRENT -> kWh, i.e. SPACE heat only, at SAP
     standard occupancy and climate. The file has NO floor area.
  2. LSOAs whose ONS 2011 population-weighted centroid is within R of the town (R = 10 km, widened in 2 km
     steps until >= 5,000 dwellings of all heating types).
  3. HTC = space heat / degree-hours (base 15.5 C, ERA5 1991-2020 hourly from history.npz).
  4. Halloran-style calibration: one factor per town so that mean modelled gas per gas dwelling
     (space heat / 0.89 + hot water / 0.89) equals DESNZ 2024 mean domestic gas per GAS-HEATED HOME
     (= mean per meter / h, h = 0.86 heated homes per meter, 0.813 / 0.913 / 1.0 as sensitivities) over the
     MSOAs (2021 PWC) inside the same R. The factor bundles EPC over-prediction AND the SAP-climate vs
     local-climate difference, because EPC demand is not at local weather.
  5. Floor area and within-cell spread from NEED anonymised 2026 (50k, OGL): for gas-heated homes of the
     same form and ONS region, the floor-area band mix, and each band's mean space-heat gas relative to the
     form x region mean (mean-preserving). So HTC and floor area co-vary as they do in metered homes.
  6. Scotland (regions N, P): no Canet. Form mix, floor area and band ratios from NEED North East
     (E12000001) gas homes, scaled to the Scottish Intermediate Zone metered gas in R. Flagged as proxy.
  7. C = 250 kJ/m2K x floor area (SAP "medium"; SAP 2012 Table 1f indicative TMP: low 100, medium 250,
     high 450 kJ/m2K; RdSAP uses 250). tau = C / HTC.

Few et al. (2023) band deflation is NOT applied: Canet gives no EPC band per LSOA, and the per-town gas
factor already removes the mean EPC bias. Downloaded files are data only; nothing in them is executed.
Run:  .venv/bin/python scripts/spark/gb_v3_stock.py [--refresh] [--n 20000] [--seed 7112026]
"""
import csv, json, math, sys
from pathlib import Path
import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[2]
G = ROOT / "data/model/gb"
SRC = G / "sources"
ARGS = sys.argv[1:]
REFRESH = "--refresh" in ARGS
N = int(ARGS[ARGS.index("--n") + 1]) if "--n" in ARGS else 20000
SEED = int(ARGS[ARGS.index("--seed") + 1]) if "--seed" in ARGS else 7112026
R0_KM, R_STEP_KM, MIN_DW = 10.0, 2.0, 5000
ETA = 0.89                       # boiler seasonal efficiency (Halloran 2024 calibration convention)
DHW_HEAT = 5.0 * 365             # kWh/yr useful hot water: the mean of homes.py U(2, 8) kWh/day
# gas-heated homes per domestic gas METER (census 2021 E&W TS046 / DESNZ meters, region_weights.json):
# 0.813 mains-gas-only, 0.913 incl. multi-fuel homes; central = midpoint; per_meter = uncorrected sensitivity
H_PER_METER = {"central": 0.86, "low": 0.813, "high": 0.913, "per_meter": 1.0}
BASE_C, YEARS = 15.5, (1991, 2020)
TMP = {"low": 100, "medium": 250, "high": 450}   # kJ/m2K, SAP 2012 (9.92) Table 1f
FORMS = ["detached", "semi-detached", "terraced", "flat"]
NEED_FORM = {"Detached": 0, "Bungalow": 0, "Semi detached": 1, "Mid terrace": 2, "End terrace": 2, "Flat": 3}
BAND_M2 = {1: (30, 50), 2: (51, 100), 3: (101, 150), 4: (151, 200), 5: (201, 300)}  # 1 and 5 bounds assumed
NE = "E12000001"
REGION_TOWNS = {
    "E12000001": "Berwick Newcastle Durham Middlesbrough",
    "E12000002": "Carlisle Kendal Lancaster Blackpool Preston Manchester Liverpool Chester",
    "E12000003": "Scarborough Harrogate York Leeds Hull Sheffield",
    "E12000004": "Buxton Lincoln Nottingham Derby Leicester Northampton",
    "E12000005": "Stoke Shrewsbury Birmingham Coventry Hereford",
    "E12000006": "King's_Lynn Norwich Peterborough Cambridge Ipswich Chelmsford",
    "E12000007": "London",
    "E12000008": "Oxford Reading Southampton Portsmouth Maidstone Canterbury Dover Hastings Brighton",
    "E12000009": "Bristol Taunton Barnstaple Exeter Plymouth Truro Penzance Swindon Chippenham Salisbury Poole",
    "W92000004": "Bangor Wrexham Aberystwyth Brecon Carmarthen Swansea Cardiff",
}
ONS_REGION = {t.replace("_", " "): r for r, s in REGION_TOWNS.items() for t in s.split()}

CANET = {"dir": "canet2021", "file": "Annual_heat_demand_LSOA.csv",
         "url": "https://dap.ceda.ac.uk/edc/d1/94510b6f-f8d5-4257-a0d9-e1c0ca7f929e/data/version_0/"
                "Annual_heat_demand_LSOA.csv?download=1",
         "title": "Spatio-temporal heat demand for LSOAs in England and Wales (Annual_heat_demand_LSOA.csv)",
         "publisher": "Canet, Cardiff University / UKERC Energy Data Centre (CEDA archive)",
         "doi": "10.5286/ukerc.edc.000944", "licence": "CC-BY 4.0",
         "version": "version 2, 14 Oct 2021 (folder 'version_0' holds the latest per README_FIRST.txt)"}
LSOA_PWC = {"dir": "lsoa2011_pwc", "file": "lsoa11_pwc_27700.json",
            "url": "https://services1.arcgis.com/ESMARspQHYMw9BZ9/ArcGIS/rest/services/"
                   "LSOA_Dec_2011_PWC_in_England_and_Wales_2022/FeatureServer/0/query",
            "title": "LSOA (Dec 2011) population weighted centroids in England and Wales",
            "publisher": "ONS Open Geography Portal", "licence": "OGL v3", "version": "2022 release, EPSG:27700"}
NEED = {"dir": "need2026", "file": "anon2026_50k.csv",
        "url": "https://assets.publishing.service.gov.uk/media/6a282ad83b15d05a7ce31fb1/anon2026_50k.csv",
        "title": "Anonymised NEED data 2026: 50,000 row sample", "publisher": "DESNZ",
        "licence": "OGL v3", "version": "published 11 Jun 2026; gas 2024, weather corrected"}
NEED_META = dict(NEED, file="NEED-2026-anonymised-dataset-metadata.ods",
                 url="https://assets.publishing.service.gov.uk/media/6a282d2be371d9d2c0052b39/"
                     "NEED-2026-anonymised-dataset-metadata.ods", title="NEED 2026 anonymised data: metadata")
SAP12 = {"dir": "sap", "file": "SAP-2012_9-92.pdf", "url": "https://files.bregroup.com/SAP/SAP-2012_9-92.pdf",
         "title": "SAP 2012 version 9.92 (Oct 2013), Table 1f indicative TMP", "publisher": "BRE for DESNZ",
         "licence": "Crown copyright", "version": "9.92"}
SAP102 = dict(SAP12, file="SAP_10.2_-_11-04-2023.pdf",
              url="https://files.bregroup.com/SAP/SAP%2010.2%20-%2011-04-2023.pdf",
              title="SAP 10.2 (11-04-2023), Tables 1e/1f (k values; TMP definition)", version="10.2")
GAS = {"file": "gas_domestic_MSOA_stacked_2010-2024.csv", "year": "2024", "publisher": "DESNZ", "licence": "OGL v3",
       "title": "Domestic gas by MSOA / Scottish IZ, 2010-2024 (already fetched by gb_national_scale.py)"}


def fetch(spec):
    d = SRC / spec["dir"]
    path = d / spec["file"]
    if path.exists() and path.stat().st_size > 0 and not REFRESH:
        return path
    d.mkdir(parents=True, exist_ok=True)
    if spec is LSOA_PWC:                              # ArcGIS pages of 2000
        pts, off = {}, 0
        while True:
            r = requests.get(spec["url"], timeout=120, params={
                "where": "1=1", "outFields": "lsoa11cd", "outSR": "27700", "f": "json",
                "resultOffset": off, "resultRecordCount": 2000, "orderByFields": "OBJECTID"})
            r.raise_for_status()
            page = r.json().get("features", [])
            for f in page:
                pts[f["attributes"]["lsoa11cd"]] = [round(f["geometry"]["x"], 1), round(f["geometry"]["y"], 1)]
            if len(page) < 2000:
                break
            off += len(page)
        path.write_text(json.dumps(pts))
    else:
        r = requests.get(spec["url"], timeout=600)
        r.raise_for_status()
        path.write_bytes(r.content)
    return path


def osgb(lat, lon):
    """WGS84 lat/lon -> OS National Grid E, N (Airy 1830 TM; no datum shift, ~100 m error, fine for a 10 km radius)."""
    a, b, F0 = 6377563.396, 6356256.909, 0.9996012717
    phi0, lam0, N0, E0 = math.radians(49), math.radians(-2), -100000, 400000
    phi, lam = math.radians(lat), math.radians(lon)
    e2, n = 1 - b * b / (a * a), (a - b) / (a + b)
    s, c, t = math.sin(phi), math.cos(phi), math.tan(phi)
    nu = a * F0 / math.sqrt(1 - e2 * s * s)
    rho = a * F0 * (1 - e2) / (1 - e2 * s * s) ** 1.5
    eta2 = nu / rho - 1
    dp, sp = phi - phi0, phi + phi0
    M = b * F0 * ((1 + n + 1.25 * n * n + 1.25 * n ** 3) * dp - (3 * n + 3 * n * n + 2.625 * n ** 3) * math.sin(dp) * math.cos(sp)
                  + (1.875 * n * n + 1.875 * n ** 3) * math.sin(2 * dp) * math.cos(2 * sp)
                  - 35 / 24 * n ** 3 * math.sin(3 * dp) * math.cos(3 * sp))
    I, II = M + N0, nu / 2 * s * c
    III = nu / 24 * s * c ** 3 * (5 - t * t + 9 * eta2)
    IIIA = nu / 720 * s * c ** 5 * (61 - 58 * t * t + t ** 4)
    IV, V = nu * c, nu / 6 * c ** 3 * (nu / rho - t * t)
    VI = nu / 120 * c ** 5 * (5 - 18 * t * t + t ** 4 + 14 * eta2 - 58 * t * t * eta2)
    dl = lam - lam0
    return E0 + IV * dl + V * dl ** 3 + VI * dl ** 5, I + II * dl ** 2 + III * dl ** 4 + IIIA * dl ** 6


def degree_hours(names):
    h = np.load(G / "history.npz")
    assert list(h["towns"]) == names, "history.npz town order differs from towns.json"
    t0 = np.datetime64(str(h["start"]), "h")
    i0 = int((np.datetime64(f"{YEARS[0]}-01-01T00", "h") - t0).astype(int))
    i1 = int((np.datetime64(f"{YEARS[1] + 1}-01-01T00", "h") - t0).astype(int))
    T = h["t"][:, i0:i1].astype(np.float32) / 10.0
    return np.maximum(BASE_C - T, 0).sum(1) / (YEARS[1] - YEARS[0] + 1)       # K h per year


def load_canet(path):
    codes, cnt, dem, alln = [], [], [], []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            num = lambda k: float(r[k]) if r[k] not in ("", "nan", "NaN") else 0.0
            codes.append(r["LSOA11CD"])
            cnt.append([num(f"Number of {f} gas boiler in 2018") for f in FORMS])
            dem.append([num(f"Average heat demand before energy efficiency measures for {f} gas boiler (kWh)")
                        for f in FORMS])
            alln.append(sum(num(f"Number of {f} {h} in 2018") for f in FORMS
                            for h in ("gas boiler", "oil boiler", "biomass boiler", "resistance heating")))
    return codes, np.array(cnt), np.array(dem), np.array(alln)


def load_need(path):
    """Gas-heated NEED homes with a valid 2024 reading: (region, form, floor band, space-heat-equivalent kWh)."""
    out = []
    with open(path, encoding="latin-1", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["MAIN_HEAT_FUEL"] != "1" or r["GasValFlag2024"] != "V" or not r["Gcons2024"]:
                continue
            if r["PROP_TYPE"] not in NEED_FORM or r["FLOOR_AREA_BAND"] not in "12345":
                continue
            sh = max(float(r["Gcons2024"]) * ETA - DHW_HEAT, 0.0)
            out.append((r["REGION"], NEED_FORM[r["PROP_TYPE"]], int(r["FLOOR_AREA_BAND"]), sh))
    return out


def need_tables(need):
    """Per (region, form): band probabilities (5,) and band space-heat ratio to the region-form mean (5,).
    Cells with < 30 homes, or bands with < 10, fall back to all of England & Wales for that form."""
    reg = sorted({x[0] for x in need})
    tab = {}
    for f in range(4):
        nat = np.array([(b, s) for r, ff, b, s in need if ff == f])
        for rg in reg + ["EW"]:
            sub = nat if rg == "EW" else np.array([(b, s) for r, ff, b, s in need if ff == f and r == rg])
            if len(sub) < 30:
                sub = nat
            p, ratio, m = np.zeros(5), np.ones(5), sub[:, 1].mean()
            for b in range(1, 6):
                sel = sub[sub[:, 0] == b]
                p[b - 1] = len(sel)
                src = sel if len(sel) >= 10 else nat[nat[:, 0] == b]
                ratio[b - 1] = src[:, 1].mean() / m if len(src) else 1.0
            p /= p.sum()
            ratio /= (p * ratio).sum()                                      # exactly mean-preserving
            tab[(rg, f)] = (p, ratio, len(sub), m)
    return tab


def load_gas():
    rows = {}
    with open(SRC / GAS["file"], encoding="latin-1", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["Year"] == GAS["year"] and r["Meters"] and r["Consumption_kWh"]:
                rows[r["MSOA_code"].strip()] = (float(r["Meters"]), float(r["Consumption_kWh"]))
    pts = {}
    for f in json.loads((SRC / "msoa_dec2021_ew_pwc_v2.json").read_text())["features"]:
        pts[f["attributes"]["MSOA21CD"]] = (f["geometry"]["x"], f["geometry"]["y"])
    for f in json.loads((SRC / "iz2022_centroids_scotland.geojson").read_text())["features"]:
        p = f["properties"]
        pts[p["IZCode"]] = (float(p["Easting"]), float(p["Northing"]))
    codes = [c for c in rows if c in pts]
    xy = np.array([pts[c] for c in codes])
    mc = np.array([rows[c] for c in codes])
    scot = np.array([c.startswith("S") for c in codes])
    return xy, mc, scot, len(rows) - len(codes)


def band_area(rng, bands):
    lo = np.array([BAND_M2[b][0] for b in range(1, 6)])[bands]
    hi = np.array([BAND_M2[b][1] for b in range(1, 6)])[bands]
    return rng.uniform(lo, hi)


def main():
    tj = json.loads((G / "towns.json").read_text())
    towns = tj["towns"]
    names = [t[0] for t in towns]
    for spec in (CANET, LSOA_PWC, NEED, NEED_META, SAP12, SAP102):
        fetch(spec)
    dh = degree_hours(names)
    codes, cnt, dem, alln = load_canet(SRC / CANET["dir"] / CANET["file"])
    pwc = json.loads((SRC / LSOA_PWC["dir"] / LSOA_PWC["file"]).read_text())
    have = np.array([c in pwc for c in codes])
    lxy = np.array([pwc.get(c, (np.nan, np.nan)) for c in codes])
    tab = need_tables(load_need(SRC / NEED["dir"] / NEED["file"]))
    gxy, gmc, gscot, gas_unplaced = load_gas()
    ne_n = np.array([tab[(NE, f)][2] for f in range(4)], float)
    ne_form_p = ne_n / ne_n.sum()
    ne_sh = sum(ne_form_p[f] * tab[(NE, f)][3] for f in range(4))
    rng = np.random.default_rng(SEED)
    T = len(towns)
    out = {k: np.zeros((T, N), np.float32) for k in ("floor_area", "htc_w_k", "htc_low", "htc_high", "c_kwh_k", "c_low", "c_high", "heat_kwh_yr")}
    out["form_code"] = np.zeros((T, N), np.int8)
    diag = []
    for i, (name, lat, lon, letter) in enumerate(towns):
        x, y = osgb(lat, lon)
        scot = letter in ("N", "P")
        dg = np.hypot(gxy[:, 0] - x, gxy[:, 1] - y) / 1000
        dl = np.hypot(lxy[:, 0] - x, lxy[:, 1] - y) / 1000
        r = R0_KM
        while True:
            gsel = (dg <= r) & (gscot == scot)
            if scot:
                ok = gmc[gsel, 0].sum() >= MIN_DW
            else:
                lsel = have & (dl <= r)
                ok = alln[lsel].sum() >= MIN_DW and gsel.any()
            if ok or r >= 60:
                break
            r += R_STEP_KM
        meters, cons = gmc[gsel, 0].sum(), gmc[gsel, 1].sum()
        g_meter = cons / meters
        sh_v = {v: g_meter / h * ETA - DHW_HEAT for v, h in H_PER_METER.items()}   # space heat per gas-heated home
        sh_target = sh_v["central"]
        mult = {v: sh_v[v] / sh_target for v in H_PER_METER}
        if scot:
            region, proxy = NE, True
            factor = sh_target / ne_sh
            forms = rng.choice(4, N, p=ne_form_p)
            base = np.array([tab[(NE, f)][3] for f in range(4)])[forms]
            n_lsoa, dwell, epc_mean = 0, int(meters), float("nan")
        else:
            region, proxy = ONS_REGION[name], False
            idx = np.nonzero(lsel)[0]
            w = cnt[idx]
            d = np.where(w > 0, dem[idx], 0.0)
            epc_mean = float((w * d).sum() / w.sum())
            factor = sh_target / epc_mean
            flat = w.ravel() / w.sum()
            pick = rng.choice(flat.size, N, p=flat)
            forms = (pick % 4).astype(np.int64)
            base = d.ravel()[pick]
            n_lsoa, dwell = int(len(idx)), int(alln[idx].sum())
        bands = np.empty(N, np.int64)
        ratio = np.empty(N)
        for f in range(4):
            m = forms == f
            p, rt, _, _ = tab[(region, f)] if (region, f) in tab else tab[("EW", f)]
            bands[m] = rng.choice(5, m.sum(), p=p)
            ratio[m] = rt[bands[m]]
        heat = factor * base * ratio                                   # kWh/yr space heat, long-term weather
        htc = heat * 1000.0 / dh[i]
        area = band_area(rng, bands)
        c = TMP["medium"] * area / 3600.0                              # kWh/K
        tau = c * 1000.0 / np.maximum(htc, 1e-6)
        for k, v in (("floor_area", area), ("htc_w_k", htc), ("htc_low", htc * mult["low"]), ("htc_high", htc * mult["high"]),
                     ("c_kwh_k", c), ("c_low", c * TMP["low"] / TMP["medium"]), ("c_high", c * TMP["high"] / TMP["medium"]),
                     ("heat_kwh_yr", heat), ("form_code", forms)):
            out[k][i] = v
        pos = htc > 0
        diag.append({"town": name, "region_letter": letter, "need_region": region, "scottish_proxy": proxy, "h_basis": "E&W ratio applied" if proxy else "census 2021 E&W",
                     "radius_km": r, "n_lsoa": n_lsoa, "dwellings": dwell, "gas_areas": int(gsel.sum()),
                     "gas_meters": int(meters), "gas_mean_kwh_per_meter_2024": round(g_meter),
                     "epc_mean_space_heat_kwh": None if proxy else round(epc_mean),
                     "gas_factor": round(float(factor), 3), "degree_hours_kh": round(float(dh[i]) / 1000, 2),
                     "median_htc_w_k": round(float(np.median(htc)), 1),
                     "p10_p90_htc": [round(float(v), 1) for v in np.percentile(htc, [10, 90])],
                     "median_tau_h": round(float(np.median(tau[pos])), 1),
                     "htc_mult": {v: round(float(m), 4) for v, m in mult.items()},
                     "median_htc_by_h": {v: round(float(np.median(htc) * m), 1) for v, m in mult.items()},
                     "median_tau_by_h": {v: round(float(np.median(tau[pos]) / m), 1) for v, m in mult.items()},
                     "median_floor_m2": round(float(np.median(area)), 1),
                     "form_share": [round(float((forms == f).mean()), 3) for f in range(4)],
                     "zero_heat_share": round(float((~pos).mean()), 4)})
    meta = {
        "built_by": "scripts/spark/gb_v3_stock.py", "seed": SEED, "n_per_town": N,
        "fields": {"floor_area": "m2", "form_code": "int, see form_codes", "htc_w_k": "heat transfer coefficient W/K, central h = 0.86 gas-heated homes per meter",
                   "htc_low": "HTC with h_low = 0.813 (higher HTC)", "htc_high": "HTC with h_high = 0.913",
                   "c_low": "C at SAP low 100 kJ/m2K", "c_high": "C at SAP high 450 kJ/m2K",
                   "htc_mult": "per town and variant (central/low/high/per_meter): HTC multiplier vs htc_w_k",
                   "c_kwh_k": "effective heat capacity kWh/K (SAP medium 250 kJ/m2K x floor area)",
                   "heat_kwh_yr": "annual SPACE heat, useful kWh, at 1991-2020 mean weather (excludes hot water)",
                   "gas_factor": "per town: metered space heat / EPC (Canet) or NEED-NE (Scotland) mean space heat"},
        "form_codes": {"0": {"form": "detached (NEED bungalows folded in)", "sap_tmp_kj_m2k": TMP},
                       "1": {"form": "semi-detached", "sap_tmp_kj_m2k": TMP},
                       "2": {"form": "terraced (mid + end)", "sap_tmp_kj_m2k": TMP},
                       "3": {"form": "flat (incl. maisonette)", "sap_tmp_kj_m2k": TMP}},
        "thermal_mass": ("C uses SAP 'medium' 250 kJ/m2K for every form (RdSAP default). SAP 2012 v9.92 Table 1f "
                         "indicative TMP: low 100, medium 250, high 450 kJ/m2K; SAP 10.2 Table 1e lists k per "
                         "construction and 1f defines TMP = sum(k A)/TFA. Low/high scale c_kwh_k by 0.4 / 1.8."),
        "constants": {"boiler_eta": ETA, "dhw_heat_kwh_yr": DHW_HEAT, "base_temp_c": BASE_C,
                      "weather_years": YEARS, "radius_km": R0_KM, "radius_step_km": R_STEP_KM,
                      "min_dwellings": MIN_DW, "h_heated_homes_per_meter": H_PER_METER, "floor_band_m2": BAND_M2},
        "method": __doc__.split("Run:")[0].strip(),
        "sources": [CANET, LSOA_PWC, NEED, NEED_META, SAP12, SAP102, GAS,
                    {"title": "ONS MSOA Dec 2021 PWC; Scottish Government IZ 2022 centroids (already fetched)",
                     "file": "msoa_dec2021_ew_pwc_v2.json, iz2022_centroids_scotland.geojson"},
                    {"title": "ERA5 hourly 2 m temperature via Open-Meteo", "file": "data/model/gb/history.npz"}],
        "caveats": [
            "Per-meter bias corrected: gas per gas-heated home = gas per meter / h, h = 0.86 (midpoint of census 2021 "
            "E&W 0.813 mains-gas-only and 0.913 incl. multi-fuel homes per DESNZ meter); per_meter (h = 1) kept as the "
            "uncorrected sensitivity. Scotland: E&W ratio applied (no Scottish census ratio used).",
            "Cooking gas is ignored; hot water is fixed at the model's own mean (5 kWh/day useful).",
            "Within-cell spread is floor-area driven only (NEED band means); occupant behaviour is not in the HTC, "
            "so the within-town HTC spread is a lower bound.",
            "Floor-area bands are uniform within band; band 1 taken as 30-50 m2 and band 5 as 201-300 m2.",
            "Canet is gas-boiler dwellings only here; oil/electric/biomass homes are counted toward the 5,000 "
            "dwelling radius rule but are not in the records.",
            "Scottish towns: NEED North East form mix, floor area and band ratios (Scotland is not in NEED or Canet), "
            "scaled to Intermediate Zone metered gas. scottish_proxy = true.",
            "Few et al. (2023) band deflation not applied: no EPC band in Canet; the gas factor removes the mean bias.",
            f"{gas_unplaced} DESNZ gas areas had no centroid (unallocated / old codes) and are not used."],
        "towns": diag,
    }
    np.savez_compressed(G / "stock_v3.npz", towns=np.array(names),
                        gas_factor=np.array([d["gas_factor"] for d in diag], np.float32),
                        scottish_proxy=np.array([d["scottish_proxy"] for d in diag]),
                        degree_hours=dh.astype(np.float32), h_variants=np.array(list(H_PER_METER)),
                        htc_mult=np.array([[d["htc_mult"][v] for v in H_PER_METER] for d in diag], np.float32), **out)
    (G / "stock_v3_meta.json").write_text(json.dumps(meta, indent=1, default=str))
    print(f"{'town':14s} {'dwell':>8s} {'R km':>5s} {'gas/m':>6s} {'HTC':>6s} {'tau h':>6s} {'factor':>6s}")
    for d in diag:
        print(f"{d['town']:14s} {d['dwellings']:8d} {d['radius_km']:5.0f} {d['gas_mean_kwh_per_meter_2024']:6d} "
              f"{d['median_htc_w_k']:6.1f} {d['median_tau_h']:6.1f} {d['gas_factor']:6.3f}{'  proxy' if d['scottish_proxy'] else ''}")
    h = np.array([d["median_htc_w_k"] for d in diag])
    t = np.array([d["median_tau_h"] for d in diag])
    f = np.array([d["gas_factor"] for d in diag])
    ew = ~np.array([d["scottish_proxy"] for d in diag])
    print(f"across towns: median HTC {np.median(h):.0f} W/K (range {h.min():.0f}-{h.max():.0f}); median tau "
          f"{np.median(t):.1f} h (range {t.min():.1f}-{t.max():.1f}); gas factor E&W {f[ew].min():.2f}-{f[ew].max():.2f} "
          f"(median {np.median(f[ew]):.2f}), Scotland {f[~ew].min():.2f}-{f[~ew].max():.2f}")
    for v in H_PER_METER:
        hv = np.array([d["median_htc_by_h"][v] for d in diag]); tv = np.array([d["median_tau_by_h"][v] for d in diag])
        print(f"h={H_PER_METER[v]:.3f} ({v}): median town HTC {np.median(hv):.0f} W/K, median town tau {np.median(tv):.1f} h")
    allh, allt = out["htc_w_k"].ravel(), (out["c_kwh_k"] * 1000 / np.maximum(out["htc_w_k"], 1e-6)).ravel()
    print(f"pooled records: median HTC {np.median(allh):.0f} W/K, median tau {np.median(allt[allh > 0]):.1f} h "
          f"(acceptance window 23-44 h, Halloran 30.6 h; reported, not tuned)")


if __name__ == "__main__":
    main()
