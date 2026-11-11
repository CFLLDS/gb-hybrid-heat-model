#!/usr/bin/env python3
"""Sensitivity runs of the v3 final model against the main run (gb_v3_final.sh phases MATCHED, SENS, pre).

    .venv/bin/python scripts/article/sensitivity.py

  matched  data/model/v3f_matched/<Y>  weather Y priced on Y's OWN tariffs (price years 2016-24) vs v3fp2/<Y> on 2025-26
  half     data/model/v3f_half/<Y>     hybrid heat pump sized at 0.55 of the all-electric unit
  levy     data/model/v3f_levy/<Y>     flat tariffs elec:gas p/kWh 34.3:8.17, 20.4:8.17, 16.3:8.17, 22:9.5 (levy moves)
  pre      data/model/v3f_pre/<Y>      thermal-mass pre-heating controllers hp_pre, ccop_pre (8,000 homes per town)
National figures weight each town by its share of its region's domestic gas meters (as analysis.py). Peaks: GB
national demand (NESO ND, same calendar half-hour of the run's price year) plus the stock's heat-pump demand.
Writes docs/article/results/sensitivity.csv and merges SENS_* numbers into results/numbers_results.json.
"""
import csv
import json
import statistics as st
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
M = ROOT / "data" / "model"
GB = M / "gb"
# --set v4 reads the model v4 folders (review 4/5): v4_matched, v4_half, v4_levy, v4pre, against v4p2c (pass 1 + SD-Power
# pass 2 for the 12 test winters); default v3f
_SET = sys.argv[sys.argv.index("--set") + 1] if "--set" in sys.argv else "v3f"
RUN = ({"matched": "v4_matched", "half": "v4_half", "levy": "v4_levy", "pre": "v4pre", "base": "v4p2c"} if _SET == "v4" else
       {"matched": "v3f_matched", "half": "v3f_half", "levy": "v3f_levy", "pre": "v3f_pre", "base": "v3fp2"})
OUT = ROOT / "docs" / "article" / "results"


def town_weights():
    G = json.load(open(GB / "towns.json"))
    W = json.load(open(GB / "region_weights.json"))["homes"]
    reg = {t[0]: t[3] for t in G["towns"]}
    per = {}
    for r in reg.values():
        per[r] = per.get(r, 0) + 1
    return {t: W[r] / per[r] for t, r in reg.items()}


TW = town_weights()


def nat(d):
    """{tariff: {col: national weighted mean}} from <d>/stock_summary.csv."""
    rows = list(csv.DictReader(open(d / "stock_summary.csv")))
    out = {}
    for t in {r["tariff"] for r in rows}:
        R = [r for r in rows if r["tariff"] == t]
        w = sum(TW[r["town"]] for r in R)
        out[t] = {k: sum(float(r[k]) * TW[r["town"]] for r in R) / w for k in R[0]
                  if k not in ("town", "tariff", "basis") and r_is_num(R[0][k])}
    return out


def r_is_num(v):
    try:
        float(v)
        return True
    except ValueError:
        return False


def peak_gw(d, base_file):
    """GB system peak (GW) per tariff x controller: base demand + stock heat-pump demand, from flex_region.npz."""
    f = np.load(d / "flex_region.npz")
    regs, tar, ctrl = list(f["regions"]), list(f["tariffs"]), list(f["ctrl"])
    W = json.load(open(GB / "region_weights.json"))["homes"]
    w = np.array([W[r] for r in regs], float)
    heat = (f["e"].astype(np.float64) * w[:, None, None, None, None]).sum(0) * 2 / 1e6        # (day, T, C, 48) GW
    info = json.load(open(d / "run.json"))
    py = next((int(a.rstrip("/").split("/")[-1]) for a in info["argv"] if "gb_years/" in a), 2025)
    S = json.load(open(base_file(py)))["series"]
    dates = [str(x) for x in f["dates"]]

    def pday(dd):
        y = py if dd[5:] >= "11" else py + 1
        md = dd[5:] if not (dd[5:] == "02-29" and (y % 4)) else "02-28"
        return f"{y}-{md}"
    base = np.array([[S.get(f"{pday(dd)}T{s // 2:02d}:{30 * (s % 2):02d}Z", np.nan) / 1000 for s in range(48)] for dd in dates])
    tot = base[:, None, None, :] + heat
    return {(t, c): float(np.nanmax(tot[:, ti, ci])) for ti, t in enumerate(tar) for ci, c in enumerate(ctrl)}


def base_file(py):
    p = GB / "years" / str(py) / "base_demand.json"
    return p if py != 2025 and p.exists() else GB / "base_demand.json"


def main():
    rows, N = [], {}
    # matched price years
    mt = {}
    for d in sorted((M / RUN["matched"]).glob("*/stock_summary.csv")):
        y = int(d.parent.name)
        a, b = nat(d.parent), nat(M / RUN["base"] / str(y))
        for t in ("svr", "agile", "cosy", "iog"):
            for k, lab in (("hybrid_beats_hp_pct", "hyb_wins"), ("hp_gbp_year_mean", "hp_gbp"), ("ccop_gbp_year_mean", "ccop_gbp"),
                           ("gas_gbp_year_mean", "gas_gbp")):
                rows.append({"run": "matched", "year": y, "tariff": t, "metric": lab, "variant": round(a[t][k], 2), "main": round(b[t][k], 2)})
            mt.setdefault(t, []).append((y, a[t]["hybrid_beats_hp_pct"], b[t]["hybrid_beats_hp_pct"]))
    for t, v in mt.items():
        N[f"SENS_MATCHED_HYB_{t.upper()}_RANGE"] = f"{min(x[1] for x in v):.0f}–{max(x[1] for x in v):.0f}"
        N[f"SENS_MATCHED_HYB_{t.upper()}_MAIN_RANGE"] = f"{min(x[2] for x in v):.0f}–{max(x[2] for x in v):.0f}"
        best = max(v, key=lambda x: x[1])
        N[f"SENS_MATCHED_HYB_{t.upper()}_MAX_YEAR"] = f"{best[0]}–{(best[0] + 1) % 100:02d}"
    # half-size hybrid, levy, pre: same weather years as the main run
    half, pre = [], []
    for d in sorted((M / RUN["half"]).glob("*/stock_summary.csv")):
        y = int(d.parent.name)
        a, b = nat(d.parent), nat(M / RUN["base"] / str(y))
        pa, pb = peak_gw(d.parent, base_file), peak_gw(M / RUN["base"] / str(y), base_file)
        for t in ("svr", "agile", "cosy", "iog"):
            half.append((y, t, a[t]["ccop_gbp_year_mean"] - b[t]["ccop_gbp_year_mean"], a[t]["hybrid_beats_hp_pct"], b[t]["hybrid_beats_hp_pct"],
                         pa[(t, "ccop")], pb[(t, "ccop")], a[t]["ccop_kg_year_mean"] - b[t]["ccop_kg_year_mean"]))
            rows.append({"run": "half", "year": y, "tariff": t, "metric": "ccop_gbp", "variant": round(a[t]["ccop_gbp_year_mean"], 2), "main": round(b[t]["ccop_gbp_year_mean"], 2)})
            rows.append({"run": "half", "year": y, "tariff": t, "metric": "hyb_wins", "variant": round(a[t]["hybrid_beats_hp_pct"], 2), "main": round(b[t]["hybrid_beats_hp_pct"], 2)})
            rows.append({"run": "half", "year": y, "tariff": t, "metric": "ccop_peak_gw", "variant": round(pa[(t, "ccop")], 1), "main": round(pb[(t, "ccop")], 1)})
    for t in ("svr", "agile", "cosy", "iog"):
        h = [x for x in half if x[1] == t]
        N[f"SENS_HALF_{t.upper()}_COST_DELTA"] = f"{st.mean(x[2] for x in h):.0f}"
        N[f"SENS_HALF_{t.upper()}_HYB_WINS"] = f"{st.median(x[3] for x in h):.0f}"
        N[f"SENS_HALF_{t.upper()}_HYB_WINS_MAIN"] = f"{st.median(x[4] for x in h):.0f}"
        N[f"SENS_HALF_{t.upper()}_PEAK"] = f"{max(x[5] for x in h):.0f}"
        N[f"SENS_HALF_{t.upper()}_PEAK_MAIN"] = f"{max(x[6] for x in h):.0f}"
        N[f"SENS_HALF_{t.upper()}_KG_DELTA"] = f"{st.mean(x[7] for x in h):.0f}"
    lv = {}
    for d in sorted((M / RUN["levy"]).glob("*/stock_summary.csv")):
        y = int(d.parent.name)
        a = nat(d.parent)
        for t in a:
            if t.startswith("flat"):
                lv.setdefault(t, []).append((a[t]["hybrid_beats_hp_pct"], a[t]["hp_beats_gas_pct"], a[t]["ccop_kg_year_mean"], a[t]["hp_gbp_year_mean"], a[t]["gas_gbp_year_mean"]))
                for k, lab in (("hybrid_beats_hp_pct", "hyb_wins"), ("hp_beats_gas_pct", "hp_beats_gas"), ("ccop_kg_year_mean", "ccop_kg")):
                    rows.append({"run": "levy", "year": y, "tariff": t, "metric": lab, "variant": round(a[t][k], 2), "main": ""})
    for t, v in lv.items():
        k = t.replace("flat", "").replace(".", "p").replace("_", "_G").upper()
        N[f"SENS_LEVY_{k}_HYB_WINS"] = f"{st.median(x[0] for x in v):.0f}"
        N[f"SENS_LEVY_{k}_HP_BEATS_GAS"] = f"{st.median(x[1] for x in v):.0f}"
        N[f"SENS_LEVY_{k}_CCOP_KG"] = f"{st.mean(x[2] for x in v):,.0f}"
    for d in sorted((M / RUN["pre"]).glob("*/stock_summary.csv")):
        y = int(d.parent.name)
        a = nat(d.parent)
        pa = peak_gw(d.parent, base_file)
        for t in ("svr", "agile", "cosy", "iog"):
            pre.append((y, t, a[t]["hp_pre_gbp_year_mean"] - a[t]["hp_gbp_year_mean"], a[t]["ccop_pre_gbp_year_mean"] - a[t]["ccop_gbp_year_mean"],
                        pa[(t, "hp_pre")], pa[(t, "hp")], pa[(t, "ccop_pre")], pa[(t, "ccop")],
                        a[t]["ccop_pre_kg_year_mean"] - a[t]["ccop_kg_year_mean"]))
            for c in ("hp", "hp_pre", "ccop", "ccop_pre"):
                rows.append({"run": "pre", "year": y, "tariff": t, "metric": f"{c}_gbp", "variant": round(a[t][f"{c}_gbp_year_mean"], 2), "main": ""})
                rows.append({"run": "pre", "year": y, "tariff": t, "metric": f"{c}_peak_gw", "variant": round(pa[(t, c)], 1), "main": ""})
    for t in ("svr", "agile", "cosy", "iog"):
        p = [x for x in pre if x[1] == t]
        N[f"SENS_PRE_{t.upper()}_HP_SAVE"] = f"{-st.mean(x[2] for x in p):.0f}"
        N[f"SENS_PRE_{t.upper()}_CCOP_SAVE"] = f"{-st.mean(x[3] for x in p):.0f}"
        N[f"SENS_PRE_{t.upper()}_HP_PEAK"] = f"{max(x[4] for x in p):.0f}"
        N[f"SENS_PRE_{t.upper()}_HP_PEAK_PLAIN"] = f"{max(x[5] for x in p):.0f}"
        N[f"SENS_PRE_{t.upper()}_CCOP_PEAK"] = f"{max(x[6] for x in p):.0f}"
        N[f"SENS_PRE_{t.upper()}_CCOP_PEAK_PLAIN"] = f"{max(x[7] for x in p):.0f}"
        N[f"SENS_PRE_{t.upper()}_CCOP_KG_DELTA"] = f"{st.mean(x[8] for x in p):.0f}"
        N[f"SENS_PRE_{t.upper()}_CCOP_KG_CUT"] = f"{-st.mean(x[8] for x in p):.0f}"
    N["SENS_YEARS"] = str(len({x[0] for x in half}))
    N["SENS_PRE_HOMES"] = "8,000"
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "sensitivity.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["run", "year", "tariff", "metric", "variant", "main"])
        w.writeheader()
        w.writerows(rows)
    p = OUT / "numbers_results.json"
    R = json.load(open(p)) if p.exists() else {}
    R = {k: v for k, v in R.items() if not k.startswith("SENS_")}
    R.update(N)
    json.dump(R, open(p, "w"), indent=1, ensure_ascii=False)
    print(f"{len(rows)} rows -> results/sensitivity.csv")
    for k, v in N.items():
        print(f"  {k:36} {v}")


if __name__ == "__main__":
    main()
