#!/usr/bin/env python3
"""Deployment-scale sensitivity (independent review, 10 Nov 2026, item 6): the herd and SD-Power when only a share of
Britain's gas-heated homes are hybrids, spread across tariffs, from the stored national outputs (no model rerun).

Adoption a scales the stock's heat-pump electricity (homes are interchangeable in expectation, as review_sdp.py);
the cap is the flat-tariff hybrid peak at the same adoption, as in the paper. For each adoption x tariff mix:
the uncoordinated peak, the herd above the cap (= what ideal dispatch removes), and what the scheduled imperfect
operator of Section 5.4 delivers (75% take part, 2% and 10% correlated forecast error, 90% comply, 2% outage days),
with the cap breaches kept separate from the GW removed. Worst over all winters in --src.
    .venv/bin/python scripts/article/review_adopt.py   -> docs/article/results/review_adopt.json
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.argv += ["--src", str(ROOT / "data" / "model" / "v4")] if "--src" not in sys.argv else []
sys.path.insert(0, str(Path(__file__).parent))
import review_sdp as RS  # noqa: E402

OUT = RS._a("--out", ROOT / "docs" / "article" / "results" / "review_adopt.json")
ADOPT = [0.05, 0.2, 0.5, 1.0]
MIXES = {"agile": {"agile": 1}, "even4": {"svr": .25, "agile": .25, "cosy": .25, "iog": .25},
         "svrheavy": {"svr": .6, "agile": .1, "cosy": .15, "iog": .15}}
SCHED = {"p": .75, "s_b": .02, "s_h": .10, "c": .9, "rho": .95, "outage": (.02, .3)}


def main():
    W = json.load(open(RS.GB / "region_weights.json"))["homes"]
    S = json.load(open(RS.GB / "base_demand.json"))["series"]
    years = sorted(int(p.name) for p in RS.SRC.iterdir() if (p / "flex_region.npz").exists())
    rng = np.random.default_rng(RS.SEED)
    R = {"years": len(years), "source": str(RS.SRC), "scheduled": SCHED, "by_year": {}}
    for y in years:
        d = RS.load_year(y, W, S)
        b = d["base"]
        Y = {"base_peak_gw": round(float(b.max()), 1)}
        for a in ADOPT:
            cap = float((b + a * d["ccop_svr"]).max())
            hp_peak = float((b + a * d["hp_svr"]).max())
            A = {"cap_gw": round(cap, 1), "hp_peak_gw": round(hp_peak, 1)}
            for m, sh in MIXES.items():
                h = a * sum(v * d[f"ccop_{k}"] for k, v in sh.items())
                tot0 = b + h
                ideal_tot, ideal_phi = RS.dispatch(b, h, cap)
                tot, phi = RS.dispatch(b, h, cap, rng=rng, **SCHED)
                A[m] = {"ccop_peak_gw": round(float(tot0.max()), 1), "ideal_peak_gw": round(float(ideal_tot.max()), 1),
                        "herd_gw": round(float(max(tot0.max() - cap, 0)), 1),
                        "sched": RS.score(tot, cap, ideal_phi, phi, h)}
            Y[f"a{a:g}"] = A
        R["by_year"][y] = Y
        print(y, {a: round(Y[f'a{a:g}']['agile']['herd_gw'], 1) for a in ADOPT}, flush=True)
    by = R["by_year"]
    N = {}
    for a in ADOPT:
        k, A = f"a{a:g}", f"{round(100 * a)}"
        N[f"REV_ADOPT_{A}_CAP_GW"] = f"{max(by[y][k]['cap_gw'] for y in years):.0f}"
        N[f"REV_ADOPT_{A}_HP_PEAK_GW"] = f"{max(by[y][k]['hp_peak_gw'] for y in years):.0f}"
        for m in MIXES:
            M = m.upper()
            c0 = max(by[y][k][m]["ccop_peak_gw"] for y in years)
            sp = max(by[y][k][m]["sched"]["peak_gw"] for y in years)
            N[f"REV_ADOPT_{A}_{M}_PEAK_GW"] = f"{c0:.0f}"
            # as review_sdp.py: the worst uncoordinated peak less the worst peak under ideal dispatch (the paper's herd)
            N[f"REV_ADOPT_{A}_{M}_HERD_GW"] = f"{c0 - max(by[y][k][m]['ideal_peak_gw'] for y in years):.0f}"
            N[f"REV_ADOPT_{A}_{M}_SCHED_GW"] = f"{c0 - sp:.0f}"
            N[f"REV_ADOPT_{A}_{M}_SCHED_OVER"] = str(sum(by[y][k][m]["sched"]["hh_over_cap"] > 0 for y in years))
            N[f"REV_ADOPT_{A}_{M}_SCHED_MAXOVER_GW"] = f"{max(by[y][k][m]['sched']['max_over_gw'] for y in years):.0f}"
            N[f"REV_ADOPT_{A}_{M}_GWH"] = f"{np.median([by[y][k][m]['sched']['shed_delivered_gwh'] for y in years]):,.0f}"
    N["REV_ADOPT_YEARS"] = str(len(years))
    R["numbers"] = N
    OUT.write_text(json.dumps(R, indent=1))
    print(json.dumps(N, indent=1))


if __name__ == "__main__":
    main()
