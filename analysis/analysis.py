#!/usr/bin/env python3
"""Results for LDS Public Class No. 1, from the per-year model outputs.

    .venv/bin/python scripts/article/analysis.py [--src data/model/v21]

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
SRC = ROOT / (sys.argv[sys.argv.index("--src") + 1] if "--src" in sys.argv else "data/model/v21")
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


def variance_share(years):
    """Share of the variance in 'hybrid beats heat pump %' explained by year, town and tariff main effects (balanced
    grid, sums of squares) -- the H1 test."""
    grid = {}
    for y in years:
        for r in read_csv(SRC / str(y) / "stock_summary.csv"):
            grid[(y, r["town"], r["tariff"])] = float(r["hybrid_beats_hp_pct"])
    ys, towns = years, sorted({k[1] for k in grid})
    X = np.array([[[grid[(y, tn, t)] for t in TARIFFS] for tn in towns] for y in ys])
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
            e, g, kg = (np.mean([r[k] for r in sel]) for k in ("elec_kwh_year", "gas_kwh_year", "kg_year_mean"))
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
        R[f"SDP_COST_{T}_MEAN"] = f"{sd.mean():.0f}"
    coldest = min(sev, key=lambda s: s["coldest_day_c"])
    R["COLDEST_YEAR"], R["COLDEST_DAY_C"] = f"{coldest['year']}–{(coldest['year'] + 1) % 100:02d}", f"{coldest['coldest_day_c']:.1f}"
    hardest = max(sev, key=lambda s: s["hdd"])
    R["HARDEST_YEAR"] = f"{hardest['year']}–{(hardest['year'] + 1) % 100:02d}"
    for r in carb:
        if r["tariff"] == "svr" and r["ctrl"] in ("hp", "ccop", "biv0", "ccop_c31.2", "gas"):
            R[f"KG_{r['ctrl'].upper().replace('.', '_')}_SVR"] = f"{r['avg_2025_26_actual']:,}"


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
    json.dump(dict(sorted(R.items())), open(OUT / "numbers_results.json", "w"), indent=1, ensure_ascii=False)
    print(f"{len(R)} headline numbers; variance shares {({k: round(v, 3) for k, v in vs.items()})}")
