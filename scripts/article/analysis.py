#!/usr/bin/env python3
"""Results for LDS Public Class No. 1, from the per-year model outputs.

    .venv/bin/python scripts/article/analysis.py [--src data/model/v3fp2]

Inputs (pulled from the Spark): <src>/<year>/{stock_summary.csv,town_summary.csv,run.json,flex_region.npz};
data/model/gb/{towns,region_weights,base_demand}.json, history.npz + weather_year.json (year severity).
Outputs in docs/article/results/:
  years.csv            per heating year: national heating degree days, coldest national day
  national.csv         per year x tariff x controller: home-weighted GB means (cost, kg, elec, gas, boiler share,
                       share of homes beating all-heat-pump), GB system peak GW (base + stock heat pumps)
  towns_prob.csv       per town x tariff: share of years in which the hybrid (C-COP) wins most homes
  carbon.csv           per tariff x controller: mean kg/home/yr under each emission-factor scenario, all years
  numbers_results.json named headline numbers for the prose (merged by article_numbers.py)
National weighting: every town stands for an equal share of its region's domestic gas meters (DESNZ 2024).
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / (sys.argv[sys.argv.index("--src") + 1] if "--src" in sys.argv else "data/model/v3fp2")
P1 = sys.argv[sys.argv.index("--p1") + 1] if "--p1" in sys.argv else "v3f"   # pass-1 runs holding sdp_phi*.npz
GB = ROOT / "data" / "model" / "gb"
OUT = ROOT / "docs" / "article" / "results"
TARIFFS = ["svr", "agile", "cosy", "iog"]
GAS_KG = 0.183
# Constant electricity emission factors (kg/kWh) for post-hoc carbon scenarios (docs/article/lit/carbon_policy.json)
EF = {"avg_2025_26_actual": None,                       # as run: regional half-hourly NESO intensity
      "lrmef_2025": 0.211, "lrmef_2030": 0.095, "lrmef_2035": 0.039,            # DESNZ 2026 Table 1, domestic
      "marginal_low_0.26": 0.26, "marginal_high_0.53": 0.53, "marginal_srmef_0.69": 0.69,   # Hawkes 2014; 2010
      "fes_ht_2030_excl_beccs": 0.0143 * 1.105, "fes_fb_2030": 0.0799 * 1.105}   # NESO FES 2025 ES1, + T&D
R = {}                                                  # headline numbers for the prose


def town_weights():
    G = json.load(open(GB / "towns.json"))
    W = json.load(open(GB / "region_weights.json"))["homes"]
    reg = {t[0]: t[3] for t in G["towns"]}
    per = {}
    for t, r in reg.items():
        per[r] = per.get(r, 0) + 1
    return {t: W[r] / per[r] for t, r in reg.items()}, reg, W


def years_available():
    return sorted(int(p.parent.name) for p in SRC.glob("*/stock_summary.csv"))


def read_csv(p):
    return list(csv.DictReader(open(p)))


def severity(years):
    """National heating degree days (base 15.5 C, home-weighted towns) and coldest national daily mean, per year."""
    h = np.load(GB / "history.npz")
    tw, _, _ = town_weights()
    names = [str(n) for n in h["towns"]]
    w = np.array([tw[n] for n in names])
    t = h["t"].astype(float) / 10
    nd = t.shape[1] // 24
    daily = (t[:, :nd * 24].reshape(len(names), nd, 24).mean(2) * w[:, None]).sum(0) / w.sum()
    rows = []
    for y in years:
        if y <= 2024:
            a = int((np.datetime64(f"{y}-11-01") - np.datetime64("1940-11-01")) / np.timedelta64(1, "D"))
            d = daily[a:a + (366 if (y + 1) % 4 == 0 else 365)]
        else:
            W = json.load(open(GB / "weather_year.json"))
            by = {}
            for n in names:
                for k, v in W[n].items():
                    if v is not None:
                        by.setdefault(k[:10], [0., 0.])
                        by[k[:10]][0] += v * tw[n] / 24
                        by[k[:10]][1] += tw[n] / 24
            d = np.array([s / c for s, c in (by[k] for k in sorted(by))])
        rows.append({"year": y, "hdd": round(float(np.maximum(15.5 - d, 0).sum()), 1),
                     "coldest_day_c": round(float(d.min()), 2), "winter_mean_c": round(float(d[30:120].mean()), 2)})
    return rows


def national(years):
    tw, reg, W = town_weights()
    S = json.load(open(GB / "base_demand.json"))["series"]
    rows = []
    for y in years:
        st = read_csv(SRC / str(y) / "stock_summary.csv")
        ctrl = json.load(open(SRC / str(y) / "run.json"))["ctrl"]
        fx = np.load(SRC / str(y) / "flex_region.npz") if (SRC / str(y) / "flex_region.npz").exists() else None
        if fx is not None:
            regs, ftar, fctrl = list(fx["regions"]), list(fx["tariffs"]), list(fx["ctrl"])
            wr = np.array([W[r] for r in regs], float)
            gw = (fx["e"].astype(np.float64) * wr[:, None, None, None, None]).sum(0) * 2 / 1e6     # (day,T,C,48)
            md = lambda d: d[5:] if d[5:] != "02-29" else "02-28"                                 # noqa: E731
            base = np.array([[S[f"{('2025-' if md(str(d)) >= '11' else '2026-') + md(str(d))}T{s // 2:02d}:{30 * (s % 2):02d}Z"] / 1000
                              for s in range(48)] for d in fx["dates"]])
        for t in TARIFFS:
            sel = [r for r in st if r["tariff"] == t]
            wts = np.array([tw[r["town"]] for r in sel])
            wm = lambda k: float((np.array([float(r[k]) for r in sel]) * wts).sum() / wts.sum())  # noqa: E731
            for c in ctrl:
                row = {"year": y, "tariff": t, "ctrl": c, "gbp_year_mean": wm(f"{c}_gbp_year_mean"),
                       "kg_year_mean": wm(f"{c}_kg_year_mean"), "elec_kwh_year": wm(f"{c}_elec_kwh_year_mean"),
                       "gas_kwh_year": wm(f"{c}_gas_kwh_year_mean"), "boiler_share_median": wm(f"{c}_boiler_share_median"),
                       "beats_hp_pct": wm(f"{c}_beats_hp_pct")}
                if fx is not None and c in fctrl:
                    tot = base + gw[:, ftar.index(t), fctrl.index(c)]
                    row["system_peak_gw"] = float(tot.max())
                    row["heat_peak_gw"] = float(gw[:, ftar.index(t), fctrl.index(c)].max())
                rows.append(row)
        # v4: SD-Power's pass 2 exists only for the sensitivity winters. Elsewhere the "sdp" column equals C-COP
        # (no phi), so it must not be read as SD-Power: ideal dispatch holds each winter's total at min(C-COP peak,
        # cap) exactly (cap = that winter's flat-tariff C-COP peak), and its cost and carbon are left out (NaN), so
        # every SD-Power cost and carbon mean is over the winters that have pass 2.
        if not json.load(open(SRC / str(y) / "run.json")).get("sdp_phi"):
            yr = [r for r in rows if r["year"] == y]
            pk = {(r["tariff"], r["ctrl"]): r.get("system_peak_gw") for r in yr}
            cap = pk.get(("svr", "ccop"))
            for r in yr:
                if r["ctrl"] == "sdp":
                    for k in ("gbp_year_mean", "kg_year_mean", "elec_kwh_year", "gas_kwh_year", "boiler_share_median",
                              "beats_hp_pct"):
                        r[k] = float("nan")
                    if cap is not None and pk.get((r["tariff"], "ccop")) is not None:
                        r["system_peak_gw"] = min(pk[(r["tariff"], "ccop")], cap)
    if fx is not None:
        R["BASE_PEAK_GW"] = f"{float(base.max()):.1f}"
    return rows


def towns_prob(years):
    out = {}
    for y in years:
        for r in read_csv(SRC / str(y) / "stock_summary.csv"):
            k = (r["town"], r["tariff"])
            out.setdefault(k, []).append(float(r["hybrid_beats_hp_pct"]) > 50)
    return [{"town": k[0], "tariff": k[1], "years": len(v), "hybrid_majority_years": int(sum(v)),
             "p_hybrid_majority": round(sum(v) / len(v), 3)} for k, v in sorted(out.items())]


def variance_share(years, tariffs=None, drop_towns=()):
    """Share of the variance in 'hybrid beats heat pump %' explained by year, town and tariff main effects (balanced
    grid, sums of squares) -- the H1 test. Review 4: also without IOG, and without the Scottish towns whose housing
    mix is North East England's (drop_towns)."""
    tariffs = tariffs or TARIFFS
    grid = {}
    for y in years:
        for r in read_csv(SRC / str(y) / "stock_summary.csv"):
            grid[(y, r["town"], r["tariff"])] = float(r["hybrid_beats_hp_pct"])
    ys, towns = years, sorted({k[1] for k in grid} - set(drop_towns))
    X = np.array([[[grid[(y, tn, t)] for t in tariffs] for tn in towns] for y in ys])
    m = X.mean()
    ss = lambda a: float(((a - m) ** 2).sum())                                                    # noqa: E731
    tot = ss(X)
    sy = ss(X.mean((1, 2), keepdims=True) * np.ones_like(X))
    st_ = ss(X.mean((0, 2), keepdims=True) * np.ones_like(X))
    sf = ss(X.mean((0, 1), keepdims=True) * np.ones_like(X))
    return {"year": sy / tot, "town": st_ / tot, "tariff": sf / tot, "interactions_and_rest": 1 - (sy + st_ + sf) / tot}


def carbon(nat):
    rows = []
    for t in TARIFFS:
        for c in sorted({r["ctrl"] for r in nat}):
            sel = [r for r in nat if r["tariff"] == t and r["ctrl"] == c]
            if not sel:
                continue
            e, g, kg = (np.nanmean([r[k] for r in sel]) for k in ("elec_kwh_year", "gas_kwh_year", "kg_year_mean"))
            row = {"tariff": t, "ctrl": c, "elec_kwh": round(e), "gas_kwh": round(g)}
            for k, f in EF.items():
                row[k] = round(kg if f is None else e * f + g * GAS_KG)
            rows.append(row)
    return rows


def write(name, rows):
    if not rows:
        return
    with open(OUT / name, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote results/{name} ({len(rows)} rows)")


def headlines(years, sev, nat, tp, vs, carb):
    get = lambda y, t, c, k: next(r[k] for r in nat if r["year"] == y and r["tariff"] == t and r["ctrl"] == c)  # noqa: E731
    R["RES_YEARS"] = str(len(years))
    R["VAR_YEAR_PCT"], R["VAR_TOWN_PCT"], R["VAR_TARIFF_PCT"] = (f"{100 * vs[k]:.0f}" for k in ("year", "town", "tariff"))
    v2 = variance_share(years, ["svr", "agile", "cosy"])
    R["VAR_YEAR_NOIOG_PCT"], R["VAR_TOWN_NOIOG_PCT"], R["VAR_TARIFF_NOIOG_PCT"] = (f"{100 * v2[k]:.0f}" for k in ("year", "town", "tariff"))
    G = json.load(open(GB / "towns.json"))
    scot = [t[0] for t in G["towns"] if t[3] in ("N", "P")]
    v3 = variance_share(years, drop_towns=scot)
    R["N_TOWNS_SCOT"] = str(len(scot))
    R["VAR_TOWN_NOSCOT_PCT"], R["VAR_TARIFF_NOSCOT_PCT"] = (f"{100 * v3[k]:.0f}" for k in ("town", "tariff"))
    hdd = {s["year"]: s["hdd"] for s in sev}
    for t in TARIFFS:
        b = np.array([get(y, t, "ccop", "beats_hp_pct") for y in years])
        h = np.array([hdd[y] for y in years])
        T = t.upper()
        R[f"HYB_WINS_{T}_MEDIAN"] = f"{np.median(b):.0f}"
        R[f"HYB_WINS_{T}_MIN"], R[f"HYB_WINS_{T}_MAX"] = f"{b.min():.0f}", f"{b.max():.0f}"
        R[f"HYB_WINS_{T}_MAJ_YEARS"] = str(int((b > 50).sum()))
        R[f"HYB_HDD_CORR_{T}"] = f"{np.corrcoef(b, h)[0, 1]:.2f}" if len(years) > 2 else "n/a"
        for bv in ("biv0", "biv2", "biv5"):
            s = np.array([get(y, t, bv, "gbp_year_mean") - get(y, t, "ccop", "gbp_year_mean") for y in years])
            R[f"SAVE_{bv.upper()}_{T}_MEAN"] = f"{s.mean():.0f}"
            R[f"SAVE_{bv.upper()}_{T}_RANGE"] = f"£{s.min():.0f}–{s.max():.0f}"
        pk = {c: np.array([get(y, t, c, "system_peak_gw") for y in years if "system_peak_gw" in
                           next(r for r in nat if r["year"] == y and r["tariff"] == t and r["ctrl"] == c)])
              for c in ("hp", "biv0", "biv5", "ccop", "sdp")}
        for c, v in pk.items():
            if len(v):
                R[f"PEAK_{c.upper()}_{T}_MAX"] = f"{v.max():.0f}"
                R[f"PEAK_{c.upper()}_{T}_P95"] = f"{np.percentile(v, 95):.0f}"
        sd = np.array([get(y, t, "sdp", "gbp_year_mean") - get(y, t, "ccop", "gbp_year_mean") for y in years])
        R[f"SDP_COST_{T}_MEAN"] = f"{np.nanmean(sd):.0f}"
        R["SDP_COST_YEARS"] = str(int(np.isfinite(sd).sum()))
    coldest = min(sev, key=lambda s: s["coldest_day_c"])
    R["COLDEST_YEAR"], R["COLDEST_DAY_C"] = f"{coldest['year']}–{(coldest['year'] + 1) % 100:02d}", f"{coldest['coldest_day_c']:.1f}"
    hardest = max(sev, key=lambda s: s["hdd"])
    R["HARDEST_YEAR"] = f"{hardest['year']}–{(hardest['year'] + 1) % 100:02d}"
    for r in carb:
        if r["tariff"] == "svr" and r["ctrl"] in ("hp", "ccop", "biv0", "ccop_c31.2", "gas"):
            R[f"KG_{r['ctrl'].upper().replace('.', '_')}_SVR"] = f"{r['avg_2025_26_actual']:,}"


def extra_angles(years, sev, nat):
    """Craig's extra angles (7 Nov): bill-shock insurance, the warming trend, peaks by region, the gas standing-charge
    break-even. Adds results/insurance.csv, results/regional_peaks.csv and headline numbers."""
    get = lambda y, t, c, k: next(r[k] for r in nat if r["year"] == y and r["tariff"] == t and r["ctrl"] == c)  # noqa: E731
    rows = []
    for t in TARIFFS:
        for c in ("gas", "hp", "biv0", "ccop", "ccop_c31.2"):
            v = np.array([get(y, t, c, "gbp_year_mean") for y in years])
            rows.append({"tariff": t, "ctrl": c, "median": round(float(np.median(v))), "p95_1in20": round(float(np.percentile(v, 95))),
                         "max": round(float(v.max())), "max_year": years[int(v.argmax())], "spread_p95_minus_median": round(float(np.percentile(v, 95) - np.median(v)))})
    write("insurance.csv", rows)
    for r in rows:
        if r["ctrl"] in ("hp", "ccop", "biv0") and r["tariff"] in ("svr", "agile"):
            k = f"{r['ctrl'].upper()}_{r['tariff'].upper()}"
            R[f"BILL_MEDIAN_{k}"], R[f"BILL_P95_{k}"], R[f"BILL_SPREAD_{k}"] = (f"{r['median']:,}", f"{r['p95_1in20']:,}",
                                                                                f"{r['spread_p95_minus_median']:,}")
    # warming: national HDD and the SVR hybrid win share against the start year, OLS slope per decade
    ys = np.array(years, float)
    hdd = np.array([next(s["hdd"] for s in sev if s["year"] == y) for y in years])
    win = np.array([get(y, "svr", "ccop", "beats_hp_pct") for y in years])
    sh = np.polyfit(ys, hdd, 1)[0] * 10
    sw = np.polyfit(ys, win, 1)[0] * 10
    R["HDD_TREND_DECADE"], R["HYB_WIN_TREND_DECADE_SVR"] = f"{sh:.0f}", f"{sw:.1f}"
    R["HDD_TREND_PCT_DECADE"] = f"{100 * sh / hdd.mean():.1f}"
    # peaks by region: heat-pump electricity only (no regional base demand published), max over all years
    reg_rows, regs = [], None
    for y in years:
        p = SRC / str(y) / "flex_region.npz"
        if not p.exists():
            continue
        f = np.load(p)
        regs, ftar, fctrl = list(f["regions"]), list(f["tariffs"]), list(f["ctrl"])
        W = json.load(open(GB / "region_weights.json"))["homes"]
        for ri, r in enumerate(regs):
            for t in ("svr", "agile"):
                for c in ("hp", "biv0", "ccop"):
                    if c not in fctrl:
                        continue
                    gw = float(f["e"][ri, :, ftar.index(t), fctrl.index(c), :].astype(np.float64).max()) * 2 * W[r] / 1e6
                    reg_rows.append((r, t, c, y, gw))
    out = []
    for r in sorted({x[0] for x in reg_rows}):
        for t in ("svr", "agile"):
            for c in ("hp", "biv0", "ccop"):
                v = [x[4] for x in reg_rows if x[0] == r and x[1] == t and x[2] == c]
                if v:
                    out.append({"region": r, "tariff": t, "ctrl": c, "heat_peak_gw_max": round(max(v), 2),
                                "heat_peak_gw_p95": round(float(np.percentile(v, 95)), 2)})
    write("regional_peaks.csv", out)
    # gas standing charge break-even: how far the gas SC could rise before the median home's hybrid stops winning
    gaps = []
    for y in years:
        st_ = read_csv(SRC / str(y) / "stock_summary.csv")
        gaps += [float(r["hp_minus_hybrid_gbp_year_p50"]) for r in st_ if r["tariff"] == "svr"]
    g = np.array(gaps)
    R["SC_BREAKEVEN_P_DAY_MEDIAN"] = f"{max(0.0, float(np.median(g))) * 100 / 365:.1f}"
    R["SC_BREAKEVEN_SHARE_POS"] = f"{100 * (g > 0).mean():.0f}"


def chapter5(years, nat, carb):
    """Further headline numbers for the results chapter (v3, 8 Nov 2026): 86-winter mean bills and boiler gas per
    controller, the carbon gap on future grids, what pricing carbon costs, SD-Power's carbon, and how much of the
    heat-driven peak each stock removes."""
    m = lambda t, c, k: float(np.nanmean([r[k] for r in nat if r["tariff"] == t and r["ctrl"] == c]))  # noqa: E731
    for t in TARIFFS:
        for c in ("gas", "hp", "biv0", "biv2", "biv5", "ccop", "ccop_c31.2", "sdp"):
            R[f"MEAN_GBP_{c.upper().replace('.', '_')}_{t.upper()}"] = f"{m(t, c, 'gbp_year_mean'):,.0f}"
        for c in ("biv0", "ccop", "ccop_c31.2", "sdp"):
            R[f"MEAN_KG_{c.upper().replace('.', '_')}_{t.upper()}"] = f"{m(t, c, 'kg_year_mean'):,.0f}"
        R[f"C312_PREMIUM_{t.upper()}"] = f"{m(t, 'ccop_c31.2', 'gbp_year_mean') - m(t, 'ccop', 'gbp_year_mean'):,.0f}"
        gap = m(t, "ccop", "kg_year_mean") - m(t, "hp", "kg_year_mean")
        R[f"C312_GAP_CLOSED_PCT_{t.upper()}"] = f"{100 * (m(t, 'ccop', 'kg_year_mean') - m(t, 'ccop_c31.2', 'kg_year_mean')) / gap:.0f}"
        # SD-Power has pass-2 results for the 12 test winters only: compare winter by winter, not 12-winter vs 86-winter means
        d = [r["kg_year_mean"] - next(q["kg_year_mean"] for q in nat if q["year"] == r["year"] and q["tariff"] == t
                                      and q["ctrl"] == "ccop")
             for r in nat if r["tariff"] == t and r["ctrl"] == "sdp" and np.isfinite(r["kg_year_mean"])]
        R[f"SDP_KG_DELTA_{t.upper()}"] = f"{np.mean(d):.0f}"
        base = m(t, "gas", "system_peak_gw")
        R[f"PEAK_MEAN_{'HP'}_{t.upper()}"] = f"{m(t, 'hp', 'system_peak_gw'):.0f}"
        R[f"PEAK_MEAN_CCOP_{t.upper()}"] = f"{m(t, 'ccop', 'system_peak_gw'):.0f}"
        R[f"PEAK_MEAN_SDP_{t.upper()}"] = f"{m(t, 'sdp', 'system_peak_gw'):.0f}"
        R[f"PEAK_REMOVED_CCOP_PCT_{t.upper()}"] = f"{100 * (m(t, 'hp', 'system_peak_gw') - m(t, 'ccop', 'system_peak_gw')) / (m(t, 'hp', 'system_peak_gw') - base):.0f}"
        R[f"HP_BEATS_GAS_HP_{t.upper()}"] = f"{100 - m(t, 'gas', 'beats_hp_pct'):.0f}"
    R["PEAK_MEAN_BASE"] = f"{m('svr', 'gas', 'system_peak_gw'):.0f}"
    # review 4: realised seasonal performance of the all-electric home (all heat / all electricity), every winter
    # whose run carries the columns (run.py, v4); towns weighted as everywhere else
    tw, _, _ = town_weights()
    spf = {}
    for y in years:
        rows = [r for r in read_csv(SRC / str(y) / "stock_summary.csv") if r["tariff"] == "svr"]
        if rows and "hp_spf_p50" in rows[0]:
            w = np.array([tw[r["town"]] for r in rows])
            spf[y] = {k: float((np.array([float(r[f"hp_spf_{k}"]) for r in rows]) * w).sum() / w.sum())
                      for k in ("p10", "p50", "p90", "pooled")}
    if spf:
        med = lambda k: float(np.median([v[k] for v in spf.values()]))                         # noqa: E731
        R["REAL_SPF_YEARS"] = str(len(spf))
        R["REAL_SPF_P50"], R["REAL_SPF_P10"], R["REAL_SPF_P90"] = (f"{med(k):.2f}" for k in ("p50", "p10", "p90"))
        R["REAL_SPF_MAX_YEAR_VAL"] = f"{max(v['p50'] for v in spf.values()):.2f}"
        R["REAL_SPF_MIN_YEAR_VAL"] = f"{min(v['p50'] for v in spf.values()):.2f}"
        R["BREAKEVEN_RATIO_MODEL"] = f"{med('p50') / 0.84:.1f}"
    # review 4: every controller the model runs, on every tariff (Table "every controller")
    CT = ("gas", "hp", "biv0", "biv2", "biv5", "ccop", "ccop_c4", "ccop_c31.2", "ccop_nopeak", "sdp")
    rows = []
    for t in TARIFFS:
        for c in CT:
            sel = [r for r in nat if r["tariff"] == t and r["ctrl"] == c]
            if not sel:
                continue
            pk = [r["system_peak_gw"] for r in sel if r.get("system_peak_gw") is not None]
            row = {"tariff": t, "ctrl": c, "gbp_year_mean": round(m(t, c, "gbp_year_mean")),
                   "kg_year_mean": round(m(t, c, "kg_year_mean")), "beats_hp_pct": round(m(t, c, "beats_hp_pct"), 1),
                   "peak_gw_max": round(max(pk), 1) if pk else None,
                   "years_cost": int(np.isfinite([r["gbp_year_mean"] for r in sel]).sum())}
            rows.append(row)
            k = f"{c.upper().replace('.', '_')}_{t.upper()}"
            R[f"CT_GBP_{k}"] = f"{row['gbp_year_mean']:,}"
            R[f"CT_KG_{k}"] = f"{row['kg_year_mean']:,}"
            R[f"CT_WIN_{k}"] = f"{row['beats_hp_pct']:.0f}" if c != "hp" else "–"
            R[f"CT_PEAK_{k}"] = f"{row['peak_gw_max']:.0f}" if row["peak_gw_max"] is not None else "–"
    write("controllers.csv", rows)
    for t in TARIFFS:                                  # the best of the fixed switches, and what C-COP adds beyond it
        best = min(("biv0", "biv2", "biv5"), key=lambda b: m(t, b, "gbp_year_mean"))
        R[f"BEST_BIV_{t.upper()}_C"] = best[3:]
        R[f"SAVE_BESTBIV_{t.upper()}_MEAN"] = f"{m(t, best, 'gbp_year_mean') - m(t, 'ccop', 'gbp_year_mean'):.0f}"
    mx = lambda t, c: max(r["system_peak_gw"] for r in nat if r["tariff"] == t and r["ctrl"] == c)    # noqa: E731
    shed = {}                                          # SD-Power shed shares from pass 1 (out/v3f/<Y>/sdp_phi.npz)
    for y in years:
        f = next((q for q in (SRC.parent / P1 / str(y) / "sdp_phi.npz", SRC.parent / P1 / str(y) / "sdp_phi_gross.npz")
                  if q.exists()), SRC.parent / P1 / str(y) / "sdp_phi.npz")
        if f.exists():
            z = np.load(f)
            for i, t in enumerate(z["tariffs"]):
                ph = z["phi"][i]
                shed.setdefault(str(t), []).append((int((ph > 0).sum()), float(ph[ph > 0].mean()) if (ph > 0).any() else None,
                                                    float(ph.sum() / ph.size)))
    for t in ("agile", "cosy", "iog"):
        if shed.get(t):
            v = shed[t]
            R[f"SDP_SHED_HH_MEDIAN_{t.upper()}"] = f"{np.median([x[0] for x in v]):,.0f}"
            R[f"SDP_SHED_SHARE_PCT_{t.upper()}"] = f"{100 * np.mean([x[1] for x in v if x[1] is not None]):.0f}"
            R[f"SDP_SHED_ALL_PCT_{t.upper()}"] = f"{100 * np.mean([x[2] for x in v]):.1f}"
    for t in ("agile", "cosy", "iog"):                 # GW the SD-Power cap takes off the uncoordinated herd, worst winter
        R[f"HERD_EXCESS_{t.upper()}_GW"] = f"{mx(t, 'ccop') - mx(t, 'sdp'):.0f}"
    for y in (1962, 2010, 2025):                       # towns where the hybrid wins most homes, on SVR
        rows = [r for r in read_csv(SRC / str(y) / "stock_summary.csv") if r["tariff"] == "svr"]
        R[f"TOWNS_HYB_MAJ_SVR_{y}"] = str(sum(float(r["hybrid_beats_hp_pct"]) > 50 for r in rows))
        R[f"TOWNS_HYB_MAJ_SVR_{y}"] = "none" if R[f"TOWNS_HYB_MAJ_SVR_{y}"] == "0" else R[f"TOWNS_HYB_MAJ_SVR_{y}"]
    C = {(r["tariff"], r["ctrl"]): r for r in carb}
    for t in ("svr", "agile", "cosy", "iog"):          # review 4: the same controller against the switch it replaces
        R[f"KG_GAP_CCOP_BIV0_{t.upper()}"] = f"{float(C[(t, 'ccop')]['avg_2025_26_actual']) - float(C[(t, 'biv0')]['avg_2025_26_actual']):,.0f}"
    for sc, lab in (("avg_2025_26_actual", "NOW"), ("lrmef_2025", "2025"), ("lrmef_2030", "2030"), ("lrmef_2035", "2035"), ("marginal_high_0.53", "MARG053")):
        for t in ("svr", "agile"):
            R[f"KG_GAP_CCOP_HP_{lab}_{t.upper()}"] = f"{float(C[(t, 'ccop')][sc]) - float(C[(t, 'hp')][sc]):,.0f}"
    R["KG_HYB_AHEAD_MARG053_SVR"] = f"{float(C[('svr', 'hp')]['marginal_high_0.53']) - float(C[('svr', 'ccop')]['marginal_high_0.53']):,.0f}"


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    years = years_available()
    print(f"{len(years)} years from {SRC}")
    sev = severity(years)
    nat = national(years)
    tp = towns_prob(years)
    vs = variance_share(years)
    carb = carbon(nat)
    write("years.csv", sev)
    write("national.csv", [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()} for r in nat])
    write("towns_prob.csv", tp)
    write("carbon.csv", carb)
    headlines(years, sev, nat, tp, vs, carb)
    extra_angles(years, sev, nat)
    chapter5(years, nat, carb)
    old = OUT / "numbers_results.json"                  # keep what burden.py and sensitivity.py merged in
    if old.exists():
        R.update({k: v for k, v in json.load(open(old)).items() if k.startswith(("BURDEN_", "SENS_", "REV_")) and k not in R})
    json.dump(dict(sorted(R.items())), open(OUT / "numbers_results.json", "w"), indent=1, ensure_ascii=False)
    print(f"{len(R)} headline numbers; variance shares {({k: round(v, 3) for k, v in vs.items()})}")
