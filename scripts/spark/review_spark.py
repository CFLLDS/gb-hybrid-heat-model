#!/usr/bin/env python3
"""Digest the hostile-review Spark runs (gb_review.sh) into results/review_spark.json, with REV_* numbers for the prose.

Runs on the Spark next to the outputs (about 160 runs; the flex arrays are not copied off the box):
    docker run --rm -v ~/cfl-model:/work cfl-model:1 python /work/v3r/scripts/review_spark.py \
        --data /work/data/gb --out-dir /work/out --json /work/out/review_spark.json
Every variant is compared with rev_fb1/<Y>/k0: the same 8,000 homes per town and the same arguments, price-taking.
National figures weight towns as analysis.py does (gas meters per region, shared by the region's towns); national
demand adds each run's C-COP or all-heat-pump demand to 2025-26 NESO ND matched by calendar day, as the paper.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from gb_sdp_phi import ARG, price_day  # noqa: E402

D, O = Path(ARG("--data", "/work/data/gb")), Path(ARG("--out-dir", "/work/out"))
REV = ARG("--rev", "rev")                    # run-folder prefix: "rev" (v3 basis) or "rev4" (v4, gb_v4.sh stage G)
SENS = [1962, 2025, 1941, 1945, 1950, 1965, 1974, 1981, 1992, 1998, 2004, 2024]
FB2 = [1962, 2025, 1981, 2004]
TAR = ("svr", "agile", "cosy", "iog")
G = json.load(open(D / "towns.json"))
W = json.load(open(D / "region_weights.json"))["homes"]
REG = {t[0]: t[3] for t in G["towns"]}
PER = {}
for r in REG.values():
    PER[r] = PER.get(r, 0) + 1
TW = {t: W[r] / PER[r] for t, r in REG.items()}
S = json.load(open(D / "base_demand.json"))["series"]


def nat(run):
    """National town-weighted means per tariff from stock_summary.csv."""
    rows = list(csv.DictReader(open(run / "stock_summary.csv")))
    out = {}
    for t in TAR:
        sel = [r for r in rows if r["tariff"] == t]
        w = np.array([TW[r["town"]] for r in sel])
        wm = lambda k: float((np.array([float(r[k]) for r in sel]) * w).sum() / w.sum())  # noqa: E731
        out[t] = {"hyb_wins": wm("ccop_beats_hp_pct"), "hp_beats_gas": wm("hp_beats_gas_pct"),
                  "hp_gbp": wm("hp_gbp_year_mean"), "ccop_gbp": wm("ccop_gbp_year_mean"),
                  "hp_kg": wm("hp_kg_year_mean"), "ccop_kg": wm("ccop_kg_year_mean"),
                  "save_biv0": wm("ccop_saving_vs_biv0_gbp_year_mean")}
    return out


def peaks(run):
    f = np.load(run / "flex_region.npz")
    regs, tar, ctrl = list(f["regions"]), list(f["tariffs"]), list(f["ctrl"])
    w = np.array([W[r] for r in regs], float)
    e = f["e"]
    dates = [str(d) for d in f["dates"]]
    base = np.array([[S[f"{price_day(d)}T{s // 2:02d}:{30 * (s % 2):02d}Z"] / 1000 for s in range(48)] for d in dates])
    gw = lambda t, c: (e[:, :, tar.index(t), ctrl.index(c)].astype(np.float64) * w[:, None, None]).sum(0) * 2 / 1e6  # noqa: E731
    p = {f"{c}_{t}": float((base + gw(t, c)).max()) for t in TAR for c in ("hp", "ccop")}
    p["cap"] = p["ccop_svr"]
    return p


def main():
    R = {"by_year": {}, "numbers": {}}
    for y in SENS:
        Y = {}
        k0 = O / f"{REV}_fb1" / str(y) / "k0"
        if not (k0 / "run.json").exists():
            continue
        Y["central"] = {"nat": nat(k0), "peaks": peaks(k0)}
        for sc, years in ((1, SENS), (2, FB2)):
            if y not in years:
                continue
            B = O / f"{REV}_fb{sc}" / str(y)
            ks = sorted(int(p.name[1:]) for p in B.glob("k*") if (p / "run.json").exists())
            if len(ks) < 2:
                continue
            last = max(ks)
            pk = {k: peaks(B / f"k{k}") for k in ks}
            add = np.load(B / f"add{last}.npz")["add"]
            Y[f"fb{sc}"] = {"k": last, "nat": nat(B / f"k{last}"), "peaks": pk[last],
                            "agile_peak_by_k": [round(pk[k]["ccop_agile"], 2) for k in ks],
                            "adder_mean_p": float(add.mean()), "adder_max_p": float(add.max()),
                            "converge_gw": abs(pk[last]["ccop_agile"] - pk[last - 1]["ccop_agile"])}
        for v in ("coplo", "cophi", "copcorr", "wday"):
            run = O / f"{REV}_{v}" / str(y)
            if (run / "run.json").exists():
                Y[v] = {"nat": nat(run), "peaks": peaks(run)}
        R["by_year"][y] = Y
        print(y, {k: round(Y[k]["peaks"]["ccop_agile"], 1) for k in Y if "peaks" in Y[k]}, flush=True)
    N = R["numbers"]
    by = R["by_year"]
    R["complete"] = len(by) == len(SENS) and all("wday" in by[y] for y in SENS)
    over = lambda Y, key: max(Y[key]["peaks"]["ccop_agile"] - Y["central"]["peaks"]["cap"], 0)  # noqa: E731
    med = lambda v: float(np.median(v))                                                       # noqa: E731
    for sc, years in ((1, SENS), (2, FB2)):
        k = f"fb{sc}"
        ys = [y for y in years if y in by and k in by[y]]
        if not ys:
            continue
        N[f"REV_FB{sc}_YEARS"] = str(len(ys))
        N[f"REV_FB{sc}_HERD_K0_GW"] = f"{max(over(by[y], 'central') for y in ys):.0f}"
        N[f"REV_FB{sc}_HERD_GW"] = f"{max(over(by[y], k) for y in ys):.0f}"
        N[f"REV_FB{sc}_PEAK_K0_GW"] = f"{max(by[y]['central']['peaks']['ccop_agile'] for y in ys):.0f}"
        N[f"REV_FB{sc}_PEAK_GW"] = f"{max(by[y][k]['peaks']['ccop_agile'] for y in ys):.0f}"
        N[f"REV_FB{sc}_ADD_MEAN_P"] = f"{med([by[y][k]['adder_mean_p'] for y in ys]):.1f}"
        N[f"REV_FB{sc}_ADD_MAX_P"] = f"{max(by[y][k]['adder_max_p'] for y in ys):.0f}"
        N[f"REV_FB{sc}_HYB_AGILE_K0"] = f"{med([by[y]['central']['nat']['agile']['hyb_wins'] for y in ys]):.0f}"
        N[f"REV_FB{sc}_HYB_AGILE"] = f"{med([by[y][k]['nat']['agile']['hyb_wins'] for y in ys]):.0f}"
        N[f"REV_FB{sc}_CONVERGE_GW"] = f"{max(by[y][k]['converge_gw'] for y in ys):.1f}"
        N[f"REV_FB{sc}_PASSES"] = str(min(by[y][k]["k"] for y in ys))
        # the iteration does not settle (the herd hops between half-hours), so report the range over passes 1..k
        ex = {y: [p - by[y]["central"]["peaks"]["cap"] for p in by[y][k]["agile_peak_by_k"][1:]] for y in ys}
        N[f"REV_FB{sc}_WORST_GW"] = f"{max(max(e) for e in ex.values()):.0f}"
        N[f"REV_FB{sc}_WORST_MED_GW"] = f"{med([max(e) for e in ex.values()]):.0f}"
        N[f"REV_FB{sc}_BEST_MED_GW"] = f"{med([min(e) for e in ex.values()]):.0f}"
        N[f"REV_FB{sc}_UNDER"] = str(sum(sum(1 for v in e if v <= 0) for e in ex.values()))
        N[f"REV_FB{sc}_RUNS"] = str(sum(len(e) for e in ex.values()))
        N[f"REV_FB{sc}_SWING_GW"] = f"{max(max(e) - min(e) for e in ex.values()):.0f}"
        N[f"REV_FB{sc}_SWING_MED_GW"] = f"{med([max(e) - min(e) for e in ex.values()]):.0f}"
    for v, V in (("central", "MID"), ("coplo", "LO"), ("cophi", "HI"), ("copcorr", "CORR")):
        ys = [y for y in SENS if y in by and v in by[y]]
        if not ys:
            continue
        for t in TAR:
            T = t.upper()
            N[f"REV_COP_{V}_HYB_{T}"] = f"{med([by[y][v]['nat'][t]['hyb_wins'] for y in ys]):.0f}"
            N[f"REV_COP_{V}_KGGAP_{T}"] = f"{med([by[y][v]['nat'][t]['ccop_kg'] - by[y][v]['nat'][t]['hp_kg'] for y in ys]):,.0f}"
            N[f"REV_COP_{V}_HPGBP_{T}"] = f"{med([by[y][v]['nat'][t]['hp_gbp'] for y in ys]):,.0f}"
        N[f"REV_COP_{V}_HP_BEATS_GAS_SVR"] = f"{med([by[y][v]['nat']['svr']['hp_beats_gas'] for y in ys]):.0f}"
        N[f"REV_COP_{V}_HP_PEAK_MAX"] = f"{max(by[y][v]['peaks']['hp_svr'] for y in ys):.0f}"
        N[f"REV_COP_{V}_HERD_AGILE_GW"] = f"{max(max(by[y][v]['peaks']['ccop_agile'] - by[y][v]['peaks']['cap'], 0) for y in ys):.0f}"
    ys = [y for y in SENS if y in by and "wday" in by[y]]
    if ys:
        d = [abs(by[y]["wday"]["nat"][t]["hyb_wins"] - by[y]["central"]["nat"][t]["hyb_wins"]) for y in ys for t in TAR]
        N["REV_WDAY_HYB_MAXDIFF_PTS"] = f"{max(d):.1f}"
        dp = [abs(by[y]["wday"]["peaks"][f"ccop_{t}"] - by[y]["central"]["peaks"][f"ccop_{t}"]) for y in ys for t in TAR]
        N["REV_WDAY_PEAK_MAXDIFF_GW"] = f"{max(dp):.1f}"
        sa = [by[y]["wday"]["peaks"]["ccop_agile"] - by[y]["central"]["peaks"]["ccop_agile"] for y in ys]
        N["REV_WDAY_AGILE_PEAK_MED_GW"] = f"{med(sa):.1f}"
        N["REV_WDAY_AGILE_PEAK_UP"] = str(sum(1 for v in sa if v > 0.05))
        N["REV_WDAY_HERD_GW"] = f"{max(max(by[y]['wday']['peaks']['ccop_agile'] - by[y]['central']['peaks']['cap'], 0) for y in ys):.0f}"
        N["REV_WDAY_YEARS"] = str(len(ys))
        dg = [abs(by[y]["wday"]["nat"][t]["ccop_gbp"] - by[y]["central"]["nat"][t]["ccop_gbp"]) for y in ys for t in TAR]
        N["REV_WDAY_GBP_MAXDIFF"] = f"{max(dg):.0f}"
    N["REV_SPARK_HOMES"] = "8,000"
    N["REV_FB_BETA"] = f'{json.load(open(D / "years" / "feedback_beta.json"))["recommended"]["winter"]:.2f}'
    co = json.load(open(D / "years" / "meta.json"))["agile_reconstruction"]["coefficients"]
    N["REV_FB_D"] = f'{np.mean([c["D"] for c in co.values()]):.2f}'
    json.dump(R, open(ARG("--json", "/work/out/review_spark.json"), "w"), indent=1)
    print(json.dumps(N, indent=1))


if __name__ == "__main__":
    main()
