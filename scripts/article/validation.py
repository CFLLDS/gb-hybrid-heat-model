"""Rerunnable validation of the GB hybrid-heating model's heat pump COP against heatpumpmonitor.org (HPM).

Writes docs/article/validation.json with five sections, each carrying its inputs and a 'generated' timestamp:
  out_of_sample_share  5-fold cross-validation BY SYSTEM of the stock Carnot-share curve (55 fit systems)
  temporal_holdout     fit on winter 2024-25, predict 2025-26 for the same systems
  litmus               the 6 Nov litmus test (12 towns, 25 km, 3 per town) rerun and saved, HOUSE and STOCK curves
  house_454            the case-study Poole Daikin: measured space COP vs the HOUSE curve over the latest year
  fleet_context        GB air-source fleet median SPF from the public last365 stats, with documented filters

Model: COP = clip(share(out) x (flow + 273.15) / max(flow - out, 5), 1.3, 7), share linearly interpolated over band
nodes and flat beyond the ends (jnp.interp). Curves are read from scripts/spark/gbmodel/physics.py (no jax needed).
Daily data are cached in logs/hpm_cache/<id>_<start>.csv (same files as scripts/oneoff/hpm_shares_20261106.py);
anything missing is fetched 1 s apart with User-Agent lds-gb-validation/1.0. Read-only towards HPM.
    .venv/bin/python scripts/article/validation.py
"""
import ast
import csv
import io
import json
import math
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
API = "https://heatpumpmonitor.org"
UA = {"User-Agent": "lds-gb-validation/1.0"}
CACHE = ROOT / "logs" / "hpm_cache"
OUT = ROOT / "docs" / "article" / "validation.json"
WINTERS = [("2024-11-01", "2025-04-01"), ("2025-11-01", "2026-04-01")]
BANDS = [(-10, 0), (0, 3), (3, 6), (6, 9), (9, 12), (12, 16)]
GB_BOX = dict(lat=(49.8, 61.0), lon=(-8.5, 2.0))
# The 55 systems behind logs/hpm_shares_20261106.json. The shares script did not save its ids and its latitude-spread
# selection ran on the 6 Nov public list, which has since changed, so they were recovered from the cache: the 52
# systems whose 0-6 C share matches 'cold_share_per_system' exactly, plus the 3 cached systems with <10 cold days.
# main() refits them and checks every band share and day count against the logged fit ('reproduces_logged_fit').
FIT_IDS = [3, 32, 71, 104, 111, 113, 115, 140, 147, 163, 219, 240, 346, 354, 357, 373, 386, 405, 416, 427, 456, 508,
           517, 547, 549, 575, 597, 631, 632, 654, 674, 685, 696, 703, 725, 726, 738, 739, 756, 802, 803, 829, 830,
           872, 873, 876, 877, 889, 912, 924, 934, 940, 966, 1018, 1025]
SHARES_FILTER = "space split only; heat>=2 kWh, elec>0, 20<flow<60, -15<out<18, 1<COP<8, flow-out>8; system needs >=40 days"
LITMUS_FILTER = "space if split else combined; heat>=2 kWh, elec>0, 15<flow<65, -15<out<20, 1<COP<8; system needs >=20 days"
_last = [0.0]


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get(url):
    time.sleep(max(0.0, 1.0 - (time.time() - _last[0])))
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
            return r.read().decode()
    finally:
        _last[0] = time.time()


def curves():
    """HOUSE_SHARE_T/HOUSE_SHARE/STOCK_SHARE_T/STOCK_SHARE straight from physics.py."""
    out = {}
    for node in ast.parse((ROOT / "scripts/spark/gbmodel/physics.py").read_text()).body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Call):
            name = node.targets[0].id
            if name in ("HOUSE_SHARE_T", "HOUSE_SHARE", "STOCK_SHARE_T", "STOCK_SHARE"):
                out[name] = [float(x) for x in ast.literal_eval(node.value.args[0])]
    return out


def cop(share_t, share_v, out, flow):
    s = float(np.interp(out, share_t, share_v))
    return min(max(s * (flow + 273.15) / max(flow - out, 5.0), 1.3), 7.0)


def daily(sid, a, b, tag=None):
    f = CACHE / f"{sid}_{tag or a}.csv"
    if f.exists():
        return f.read_text()
    ua, ub = (int(datetime.fromisoformat(x).replace(tzinfo=timezone.utc).timestamp()) for x in (a, b))
    txt = get(f"{API}/system/stats/daily?id={sid}&start={ua}&end={ub}")
    if txt.startswith("id,"):
        f.write_text(txt)
    return txt


def rows(sid, a, b, mode, tag=None):
    """Daily (date, heat, elec, out, flow) after the shares ('shares') or litmus ('litmus') day filter."""
    days = []
    for r in csv.DictReader(io.StringIO(daily(sid, a, b, tag))):
        pre = "space" if r.get("space_heat_kwh") else ("combined" if mode == "litmus" else None)
        if pre is None:
            continue
        try:
            h, e, o, f = (float(r[f"{pre}_{k}"]) for k in ("heat_kwh", "elec_kwh", "outsideT_mean", "flowT_mean"))
        except (KeyError, ValueError):
            continue
        ok = (h >= 2 and e > 0 and 20 < f < 60 and -15 < o < 18 and 1 < h / e < 8 and f - o > 8) if mode == "shares" \
            else (h >= 2 and e > 0 and 15 < f < 65 and -15 < o < 20 and 1 < h / e < 8)
        if ok:
            days.append((int(r["timestamp"]), h, e, o, f, pre))
    return days


def band_of(o):
    return next((b for b in BANDS if b[0] <= o < b[1]), None)


def bkey(b):
    return f"{b[0]}..{b[1]}"


def fit_shares(days):
    """Per-band heat-weighted Carnot share: sum(heat) / sum(elec x Carnot), as the shares script."""
    acc = {b: [0.0, 0.0, 0] for b in BANDS}
    for _, h, e, o, f, _ in days:
        b = band_of(o)
        if b:
            acc[b][0] += h
            acc[b][1] += e * (f + 273.15) / max(f - o, 5.0)
            acc[b][2] += 1
    return {b: (h / ec if ec else None, n) for b, (h, ec, n) in acc.items()}


def as_curve(fit, t_nodes):
    pts = [(t, fit[b][0]) for t, b in zip(t_nodes, BANDS) if fit[b][0] is not None]
    return [p[0] for p in pts], [p[1] for p in pts]


def score(per_sys, curve_t, curve_v, min_band_days=5):
    """per_sys: {id: days}. Heat-weighted measured vs predicted COP per band and overall, bias %, and the median
    absolute % error across systems (per band: systems with >= min_band_days days in that band)."""
    def agg(days):
        H = sum(d[1] for d in days)
        E = sum(d[2] for d in days)
        P = sum(d[1] / cop(curve_t, curve_v, d[3], d[4]) for d in days)
        return H / E, H / P
    out = {}
    for b in BANDS + [None]:
        pooled, errs = [], []
        for days in per_sys.values():
            sel = [d for d in days if b is None or band_of(d[3]) == b]
            pooled += sel
            if sel and (b is None or len(sel) >= min_band_days):
                m, p = agg(sel)
                errs.append(abs(100 * (p / m - 1)))
        if not pooled:
            continue
        m, p = agg(pooled)
        out["overall" if b is None else bkey(b)] = dict(
            days=len(pooled), systems=len(errs), measured_cop=round(m, 3), predicted_cop=round(p, 3),
            bias_pct=round(100 * (p / m - 1), 2), median_abs_pct_err=round(float(np.median(errs)), 2) if errs else None)
    return out


def out_of_sample(fit_days, C, logged):
    folds = {sid: i % 5 for i, sid in enumerate(sorted(fit_days))}
    pred, fold_shares = {}, []
    for k in range(5):
        train = [d for sid, ds in fit_days.items() if folds[sid] != k for d in ds]
        fit = fit_shares(train)
        t, v = as_curve(fit, C["STOCK_SHARE_T"])
        fold_shares.append({bkey(b): round(s, 4) for b, (s, _) in fit.items() if s})
        held = {sid: ds for sid, ds in fit_days.items() if folds[sid] == k}
        pred.update({sid: (ds, t, v) for sid, ds in held.items()})
    oos = {}                                    # score each held-out system with its own fold's curve, then pool
    for b in BANDS + [None]:
        H = E = P = 0.0
        n, errs = 0, []
        for ds, t, v in pred.values():
            sel = [d for d in ds if b is None or band_of(d[3]) == b]
            if not sel:
                continue
            h, e = sum(d[1] for d in sel), sum(d[2] for d in sel)
            p = sum(d[1] / cop(t, v, d[3], d[4]) for d in sel)
            H, E, P, n = H + h, E + e, P + p, n + len(sel)
            if b is None or len(sel) >= 5:
                errs.append(abs(100 * ((h / p) / (h / e) - 1)))
        oos["overall" if b is None else bkey(b)] = dict(
            days=n, systems=len(errs), measured_cop=round(H / E, 3), predicted_cop=round(H / P, 3),
            bias_pct=round(100 * ((H / P) / (H / E) - 1), 2), median_abs_pct_err=round(float(np.median(errs)), 2))
    full = fit_shares([d for ds in fit_days.values() for d in ds])
    repro = all(abs(round(full[b][0], 4) - logged["bands"][bkey(b)]["share"]) < 1e-9
                and full[b][1] == logged["bands"][bkey(b)]["days"] for b in BANDS)
    return dict(
        generated=now(), method="5-fold CV by system: fold = position in sorted id list mod 5; per-band share refit on "
        "4 folds, curve nodes at STOCK_SHARE_T, held-out systems predicted from their own daily flow and outside temp, "
        "level x1.0", day_filter=SHARES_FILTER, winters=WINTERS, system_ids=sorted(fit_days),
        folds={str(k): [s for s in sorted(fit_days) if folds[s] == k] for k in range(5)},
        reproduces_logged_fit=repro, physics_stock_share=dict(t=C["STOCK_SHARE_T"], share=C["STOCK_SHARE"]),
        fold_shares=fold_shares, out_of_sample=oos,
        in_sample=score(fit_days, C["STOCK_SHARE_T"], C["STOCK_SHARE"]),
        note="system-level error per band counts systems with >=5 days in the band")


def temporal(fit_days, C):
    w2 = int(datetime.fromisoformat(WINTERS[1][0]).replace(tzinfo=timezone.utc).timestamp())
    early = [d for ds in fit_days.values() for d in ds if d[0] < w2]
    late = {sid: [d for d in ds if d[0] >= w2] for sid, ds in fit_days.items()}
    late = {k: v for k, v in late.items() if v}
    fit = fit_shares(early)
    t, v = as_curve(fit, C["STOCK_SHARE_T"])
    return dict(generated=now(), fit_winter=WINTERS[0], test_winter=WINTERS[1], day_filter=SHARES_FILTER,
                system_ids=sorted(late), fit_shares={bkey(b): round(s, 4) for b, (s, _) in fit.items() if s},
                holdout=score(late, t, v), in_sample_full_curve_on_test=score(late, C["STOCK_SHARE_T"], C["STOCK_SHARE"]))


def km(a, b, c, d):
    p = math.pi / 180
    h = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


def eligible(s):
    return (s.get("published") and s.get("latitude") and s.get("longitude") and s.get("id") != 454
            and str(s.get("data_flag")) != "1" and str(s.get("hp_hybrid")) != "1" and s.get("hp_type") == "Air Source")


def litmus(public, C):
    towns = {r["town"]: dict(lat=float(r["lat"]), lon=float(r["lon"]), out=float(r["out_mean_c"]), cop=float(r["cop_space"]))
             for r in csv.DictReader(open(ROOT / "data/model/results/town_summary.csv")) if r["tariff"] == "agile"}
    systems = [s for s in public if eligible(s)]
    near = {}
    for name, t in towns.items():
        c = sorted(((km(t["lat"], t["lon"], float(s["latitude"]), float(s["longitude"])), s) for s in systems),
                   key=lambda x: x[0])
        c = [x for x in c if x[0] <= 25]
        if c:
            near[name] = c[:3]
    ranked = sorted(near, key=lambda n: towns[n]["out"])
    pick = list(dict.fromkeys(ranked[round(i * (len(ranked) - 1) / 11)] for i in range(min(12, len(ranked)))))
    res, per_sys = [], {}
    for name in pick:
        for d, s in near[name]:
            days = [x for a, b in WINTERS for x in rows(s["id"], a, b, "litmus")]
            row = dict(town=name, town_winter_out_c=towns[name]["out"], map_town_cop=towns[name]["cop"], id=s["id"],
                       km=round(d, 1), model=f"{s.get('hp_manufacturer') or ''} {s.get('hp_model') or ''}".strip(),
                       days=len(days), in_fit_set=s["id"] in FIT_IDS)
            if len(days) < 20:
                res.append(dict(row, skipped="fewer than 20 winter days"))
                continue
            H, E = sum(x[1] for x in days), sum(x[2] for x in days)
            ph = H / sum(x[1] / cop(C["HOUSE_SHARE_T"], C["HOUSE_SHARE"], x[3], x[4]) for x in days)
            ps = H / sum(x[1] / cop(C["STOCK_SHARE_T"], C["STOCK_SHARE"], x[3], x[4]) for x in days)
            row.update(basis="space" if all(x[5] == "space" for x in days) else "combined (incl. hot water)",
                       mean_out_c=round(sum(x[1] * x[3] for x in days) / H, 2),
                       mean_flow_c=round(sum(x[1] * x[4] for x in days) / H, 2), measured_cop=round(H / E, 3),
                       house_cop=round(ph, 3), house_err_pct=round(100 * (ph / (H / E) - 1), 1),
                       stock_cop=round(ps, 3), stock_err_pct=round(100 * (ps / (H / E) - 1), 1))
            res.append(row)
            per_sys[s["id"]] = days
    fresh = {k: v for k, v in per_sys.items() if k not in FIT_IDS}
    summ = lambda ps: dict(house=score(ps, C["HOUSE_SHARE_T"], C["HOUSE_SHARE"]),       # noqa: E731
                           stock_x1=score(ps, C["STOCK_SHARE_T"], C["STOCK_SHARE"]))
    return dict(generated=now(), towns=pick, radius_km=25, per_town=3, n_towns=len(pick),
                n_systems=len(per_sys), n_systems_not_in_fit_set=len(fresh), winters=WINTERS,
                exclusions="unpublished, no lat/lon, system 454, data_flag=1, hp_hybrid=1, not Air Source",
                day_filter=LITMUS_FILTER, public_list_size=len(public), eligible_systems=len(systems),
                house_curve=dict(t=C["HOUSE_SHARE_T"], share=C["HOUSE_SHARE"]),
                note="town/system selection uses the live public list, so it can drift between runs; the original "
                     "litmus used a 4-node HOUSE curve (no 14 C node), this uses physics.py's current one",
                systems=res, overlap_with_fit_set=sorted(set(per_sys) & set(FIT_IDS)),
                pooled_all=summ(per_sys), pooled_not_in_fit_set=summ(fresh) if fresh else None)


def house_454(C, stats):
    a, b = "2025-11-01", "2026-11-01"
    txt = daily(454, a, b, tag=f"{a}_to_{b}")
    raw = list(csv.DictReader(io.StringIO(txt)))
    out = dict(generated=now(), system=454, period=[a, b], rows_returned=len(raw),
               last_day=datetime.fromtimestamp(int(raw[-1]["timestamp"]), timezone.utc).date().isoformat() if raw else None,
               house_curve=dict(t=C["HOUSE_SHARE_T"], share=C["HOUSE_SHARE"]), variants={})
    filters = {"space_split_days_heat_gt_0": lambda h, e, o, f: h > 0 and e > 0,
               "space_split_days_heat_ge_2kWh": lambda h, e, o, f: h >= 2 and e > 0,
               "shares_filter": lambda h, e, o, f: h >= 2 and e > 0 and 20 < f < 60 and -15 < o < 18 and 1 < h / e < 8 and f - o > 8}
    for name, ok in filters.items():
        days = []
        for r in raw:
            if not r.get("space_heat_kwh"):
                continue
            try:
                h, e, o, f = (float(r[f"space_{k}"]) for k in ("heat_kwh", "elec_kwh", "outsideT_mean", "flowT_mean"))
            except ValueError:
                continue
            if ok(h, e, o, f):
                days.append((h, e, o, f))
        if days:
            H, E = sum(d[0] for d in days), sum(d[1] for d in days)
            P = H / sum(d[0] / cop(C["HOUSE_SHARE_T"], C["HOUSE_SHARE"], d[2], d[3]) for d in days)
            out["variants"][name] = dict(days=len(days), heat_kwh=round(H, 1), elec_kwh=round(E, 1),
                                         measured_space_cop=round(H / E, 3), model_space_cop=round(P, 3),
                                         err_pct=round(100 * (P / (H / E) - 1), 2))
    head = out["variants"].get("shares_filter", {})          # headline = the stock fit's own day filter
    out.update(headline_variant="shares_filter", measured_space_cop=head.get("measured_space_cop"),
               model_space_cop=head.get("model_space_cop"), days=head.get("days"))
    s = stats.get("454") or {}
    out["public_last365"] = dict(combined_spf=s.get("combined_cop"), space_spf=s.get("space_cop"),
                                 combined_heat_kwh=s.get("combined_heat_kwh"), combined_elec_kwh=s.get("combined_elec_kwh"),
                                 combined_days=round((s.get("combined_data_length") or 0) / 86400, 1))
    out["excluded_corrupt"] = dict(from_energy_feeds_heat_kwh=s.get("from_energy_feeds_heat_kwh"),
                                   from_energy_feeds_cop=s.get("from_energy_feeds_cop"),
                                   note="from_energy_feeds annual figures are corrupt (earlier read: 90,266 kWh heat, COP 12.98; live values above); not used")
    return out


def fleet(public, stats):
    meta = {s["id"]: s for s in public}
    base = []
    for k, v in stats.items():
        s = meta.get(int(k))
        if not s or s.get("hp_type") != "Air Source" or str(s.get("hp_hybrid")) == "1" or not s.get("latitude"):
            continue
        if not (GB_BOX["lat"][0] < float(s["latitude"]) < GB_BOX["lat"][1] and GB_BOX["lon"][0] < float(s["longitude"]) < GB_BOX["lon"][1]):
            continue
        if v.get("combined_cop") and (v.get("combined_heat_kwh") or 0) > 0:
            base.append((int(k), float(v["combined_cop"]), (v.get("combined_data_length") or 0) / 86400, str(s.get("data_flag")) == "1"))
    def summ(sel):
        x = np.array([c for _, c, _, _ in sel])
        return dict(systems=len(sel), median_spf=round(float(np.median(x)), 3),
                    p25=round(float(np.percentile(x, 25)), 3), p75=round(float(np.percentile(x, 75)), 3)) if len(x) else None
    prim = summ([b for b in base if b[2] >= 330]) or {}
    return dict(generated=now(), median_spf=prim.get("median_spf"), n_systems=prim.get("systems"),
                headline="primary (coverage >= 330 days)",
                source=[f"{API}/system/stats/last365", f"{API}/system/list/public.json"],
                filters=f"public list; hp_type Air Source; hp_hybrid != 1; GB box lat {GB_BOX['lat']} lon {GB_BOX['lon']}; "
                        "combined_cop present and combined_heat_kwh > 0; coverage = combined_data_length / 86400 days",
                primary=dict(coverage_min_days=330, **prim),
                variants={"no_coverage_min": summ(base), "coverage_ge_300d": summ([b for b in base if b[2] >= 300]),
                          "coverage_ge_330d_not_data_flagged": summ([b for b in base if b[2] >= 330 and not b[3]]),
                          "no_coverage_min_not_data_flagged": summ([b for b in base if not b[3]])},
                previous_figure=dict(median_spf=3.88, systems=612))


def main():
    t0 = time.time()
    C = curves()
    logged = json.load(open(ROOT / "logs/hpm_shares_20261106.json"))
    fit_days = {sid: [d for a, b in WINTERS for d in rows(sid, a, b, "shares")] for sid in FIT_IDS}
    public = json.loads(get(f"{API}/system/list/public.json"))
    stats = json.loads(get(f"{API}/system/stats/last365"))
    all_days = [d for ds in fit_days.values() for d in ds]
    fit_counts = dict(generated=now(), systems=sum(1 for ds in fit_days.values() if len(ds) >= 40),
                      days_all=len(all_days), days_in_bands=sum(1 for d in all_days if band_of(d[3])),
                      bands=[bkey(b) for b in BANDS], winters=WINTERS, day_filter=SHARES_FILTER, system_ids=FIT_IDS,
                      note="days_all passes the quality filter (-15<out<18); days_in_bands is the subset inside the "
                           "six fitted bands (-10..16 C), which is what logs/hpm_shares_20261106.json counts",
                      physics_docstring_quotes=11628, docstring_matches_days_all=len(all_days) == 11628)
    res = dict(generated=now(), script="scripts/article/validation.py",
               model="COP = clip(share(out) x (flow+273.15)/max(flow-out,5), 1.3, 7); share = interp over band nodes",
               fit_counts=fit_counts,
               out_of_sample_share=out_of_sample(fit_days, C, logged), temporal_holdout=temporal(fit_days, C),
               litmus=litmus(public, C), house_454=house_454(C, stats), fleet_context=fleet(public, stats))
    res["runtime_s"] = round(time.time() - t0, 1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1))
    print(f"wrote {OUT} in {res['runtime_s']} s")


if __name__ == "__main__":
    main()
