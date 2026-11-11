#!/usr/bin/env python3
"""Digest the stage H runs (gb_h.sh: the Electrification of Heat trial's measured habits and measured hybrid switching
inside the model) into review_h.json with REV_H_* numbers for the prose.

Each variant (rev4_eoh, rev4_bivm, rev4_eohbivm) is set against rev4_fb1/<Y>/k0: the same 8,000 homes per town,
the same arguments, no options. Peaks use review_spark.py's national weighting; the cap is each run's own flat-tariff
C-COP peak, as in the paper. Also checks that the drawn changeover temperatures reproduce the measured boiler-share
curve, and reads the measured-habits coincidence run (div_cf_eoh.json).
    python gb_h_digest.py --data /work/data/gb --out-dir /work/out --json /work/out/review_h.json
"""
import csv
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import review_spark as RS  # noqa: E402
from gb_sdp_phi import price_day  # noqa: E402

O, D = RS.O, RS.D
TAR = RS.TAR
VARS = (("base", "BASE"), ("eoh", "EOH"), ("bivm", "BIVM"), ("eohbivm", "EOHBIVM"))
CTRLS = ("hp", "ccop", "biv0", "biv2", "biv5", "bivm")


def peaks(run):
    f = np.load(run / "flex_region.npz")
    regs, tar, ctrl = list(f["regions"]), list(f["tariffs"]), list(f["ctrl"])
    w = np.array([RS.W[r] for r in regs], float)
    e = f["e"]
    dates = [str(d) for d in f["dates"]]
    base = np.array([[RS.S[f"{price_day(d)}T{s // 2:02d}:{30 * (s % 2):02d}Z"] / 1000 for s in range(48)] for d in dates])
    gw = lambda t, c: (e[:, :, tar.index(t), ctrl.index(c)].astype(np.float64) * w[:, None, None]).sum(0) * 2 / 1e6  # noqa: E731
    p = {f"{c}_{t}": float((base + gw(t, c)).max()) for t in TAR for c in CTRLS if c in ctrl}
    p["cap"] = p["ccop_svr"]
    p["base_max"] = float(base.max())
    return p


def nat(run):
    rows = list(csv.DictReader(open(run / "stock_summary.csv")))
    out = {}
    for t in TAR:
        sel = [r for r in rows if r["tariff"] == t]
        w = np.array([RS.TW[r["town"]] for r in sel])
        wm = lambda k: float((np.array([float(r[k]) for r in sel]) * w).sum() / w.sum()) if k in sel[0] else None  # noqa: E731
        out[t] = {"hyb_wins": wm("ccop_beats_hp_pct"), "hp_beats_gas": wm("hp_beats_gas_pct"),
                  "hp_gbp": wm("hp_gbp_year_mean"), "ccop_gbp": wm("ccop_gbp_year_mean"),
                  "hp_kg": wm("hp_kg_year_mean"), "ccop_kg": wm("ccop_kg_year_mean"), "gas_kg": wm("gas_kg_year_mean"),
                  "spf_p50": wm("hp_spf_p50"), "ccop_gas_share": wm("ccop_boiler_share_median"),
                  "biv0_gas_share": wm("biv0_boiler_share_median"),
                  "bivm_gbp": wm("bivm_gbp_year_mean"), "bivm_kg": wm("bivm_kg_year_mean"),
                  "bivm_gas_share": wm("bivm_boiler_share_median"), "bivm_beats_hp": wm("bivm_beats_hp_pct"),
                  "ccop_beats_bivm": wm("ccop_beats_bivm_pct"), "ccop_saving_vs_bivm": wm("ccop_saving_vs_bivm_gbp_year_mean"),
                  "ccop_saving_vs_biv0": wm("ccop_saving_vs_biv0_gbp_year_mean")}
    return out


def curve_check():
    """Draw changeovers exactly as gbmodel.homes.biv_meas_tb does and compare P(T_b > T) with the measured share."""
    hb = json.load(open(D / "eoh.json"))["hybrid_boiler_share_by_temp"]
    pairs = sorted((float(t) + 1.0, s) for t, s in hb.items() if -8 <= float(t) <= 14)
    t, s = np.array([p[0] for p in pairs]), np.array([p[1] for p in pairs])
    o = np.argsort(s)
    u = np.random.default_rng(9209).uniform(size=1_000_000)
    tb = np.interp(u, s[o], t[o])
    tb = np.where(u > s.max(), -50., np.where(u < s.min(), 50., tb))
    got = {float(tt): float((tb > tt).mean()) for tt in t}
    return {"measured": {str(int(tt - 1)): float(ss) for tt, ss in zip(t, s)},
            "drawn": {str(int(tt - 1)): round(got[float(tt)], 3) for tt in t},
            "max_abs_diff": round(max(abs(got[float(tt)] - ss) for tt, ss in zip(t, s)), 4),
            "never_boiler_pct": round(100 * float((tb == -50).mean()), 1),
            "never_heat_pump_pct": round(100 * float((tb == 50).mean()), 1),
            "changeover_p50_c": round(float(np.median(tb[(tb > -50) & (tb < 50)])), 1)}


def main():
    R = {"by_year": {}, "numbers": {}}
    for y in RS.SENS:
        runs = {"base": O / f"{RS.REV}_fb1" / str(y) / "k0"}
        for v in ("eoh", "bivm", "eohbivm"):
            runs[v] = O / f"{RS.REV}_{v}" / str(y)
        if not all((r / "run.json").exists() for r in runs.values()):
            continue
        R["by_year"][y] = {v: {"peaks": peaks(r), "nat": nat(r)} for v, r in runs.items()}
        print(y, {v: round(R["by_year"][y][v]["peaks"]["ccop_agile"], 1) for v in runs},
              {v: round(R["by_year"][y][v]["peaks"].get("bivm_agile", 0), 1) for v in ("bivm", "eohbivm")}, flush=True)
    by = R["by_year"]
    if not by:
        raise SystemExit("no finished winters")
    N = R["numbers"]
    med = lambda v: float(np.median(v))                                                       # noqa: E731
    N["REV_H_YEARS"] = str(len(by))
    for v, V in VARS:
        P = {y: by[y][v]["peaks"] for y in by}
        cap = max(p["ccop_svr"] for p in P.values())
        N[f"REV_H_{V}_CAP_GW"] = f"{cap:.0f}"
        for t in TAR:
            T = t.upper()
            hp_max = max(p[f"hp_{t}"] for p in P.values())
            N[f"REV_H_{V}_PEAK_HP_{T}_MAX"] = f"{hp_max:.0f}"
            N[f"REV_H_{V}_PEAK_CCOP_{T}_MAX"] = f"{max(p[f'ccop_{t}'] for p in P.values()):.0f}"
            N[f"REV_H_{V}_HERD_{T}_GW"] = f"{max(max(p[f'ccop_{t}'] for p in P.values()) - cap, 0):.0f}"
            N[f"REV_H_{V}_HYB_{T}"] = f"{med([by[y][v]['nat'][t]['hyb_wins'] for y in by]):.0f}"
            N[f"REV_H_{V}_HPGBP_{T}"] = f"{med([by[y][v]['nat'][t]['hp_gbp'] for y in by]):,.0f}"
            N[f"REV_H_{V}_CCOPGBP_{T}"] = f"{med([by[y][v]['nat'][t]['ccop_gbp'] for y in by]):,.0f}"
            N[f"REV_H_{V}_HPKG_{T}"] = f"{med([by[y][v]['nat'][t]['hp_kg'] for y in by]):,.0f}"
            N[f"REV_H_{V}_CCOPKG_{T}"] = f"{med([by[y][v]['nat'][t]['ccop_kg'] for y in by]):,.0f}"
            N[f"REV_H_{V}_CCOP_GAS_{T}"] = f"{100 * med([by[y][v]['nat'][t]['ccop_gas_share'] for y in by]):.0f}"
            if f"bivm_{t}" in next(iter(P.values())):
                bm_max = max(p[f"bivm_{t}"] for p in P.values())
                N[f"REV_H_{V}_PEAK_BIVM_{T}_MAX"] = f"{bm_max:.0f}"
                N[f"REV_H_{V}_BIVM_HERD_{T}_GW"] = f"{max(bm_max - cap, 0):.0f}"
                N[f"REV_H_{V}_BIVM_CUT_{T}_GW"] = f"{hp_max - bm_max:.0f}"           # worst-winter peak, all-HP less measured hybrids
                N[f"REV_H_{V}_IDEAL_CUT_{T}_GW"] = f"{hp_max - cap:.0f}"             # all-HP less SD-Power's cap
                N[f"REV_H_{V}_CCOP_CUT_{T}_GW"] = f"{hp_max - max(p[f'ccop_{t}'] for p in P.values()):.0f}"
                N[f"REV_H_{V}_BIVM_SHARE_OF_IDEAL_{T}"] = f"{100 * (hp_max - bm_max) / max(hp_max - cap, 1e-9):.0f}"
                nt = lambda k: med([by[y][v]["nat"][t][k] for y in by])                          # noqa: E731
                N[f"REV_H_{V}_BIVMGBP_{T}"] = f"{nt('bivm_gbp'):,.0f}"
                N[f"REV_H_{V}_BIVMKG_{T}"] = f"{nt('bivm_kg'):,.0f}"
                N[f"REV_H_{V}_BIVM_GAS_{T}"] = f"{100 * nt('bivm_gas_share'):.0f}"
                N[f"REV_H_{V}_BIVM_BEATS_HP_{T}"] = f"{nt('bivm_beats_hp'):.0f}"
                N[f"REV_H_{V}_CCOP_BEATS_BIVM_{T}"] = f"{nt('ccop_beats_bivm'):.0f}"
                N[f"REV_H_{V}_CCOP_SAVE_BIVM_{T}"] = f"{nt('ccop_saving_vs_bivm'):.0f}"
                N[f"REV_H_{V}_CCOP_SAVE_BIV0_{T}"] = f"{nt('ccop_saving_vs_biv0'):.0f}"
            for b in ("biv0", "biv5"):
                N[f"REV_H_{V}_PEAK_{b.upper()}_{T}_MAX"] = f"{max(p[f'{b}_{t}'] for p in P.values()):.0f}"
        N[f"REV_H_{V}_SPF_P50"] = f"{med([by[y][v]['nat']['svr']['spf_p50'] for y in by]):.2f}"
        N[f"REV_H_{V}_HP_BEATS_GAS_SVR"] = f"{med([by[y][v]['nat']['svr']['hp_beats_gas'] for y in by]):.0f}"
    cap0 = float(N["REV_H_BASE_CAP_GW"])
    for v, V in VARS[1:]:
        for t in TAR:
            N[f"REV_H_{V}_HERD_{t.upper()}_VS_BASECAP_GW"] = f"{max(max(by[y][v]['peaks'][f'ccop_{t}'] for y in by) - cap0, 0):.0f}"
    R["curve_check"] = cc = curve_check()
    N["REV_H_BIVM_CURVE_MAXDIFF_PTS"] = f"{100 * cc['max_abs_diff']:.1f}"
    N["REV_H_BIVM_NEVER_BOILER_PCT"] = f"{cc['never_boiler_pct']:.0f}"
    N["REV_H_BIVM_NEVER_HP_PCT"] = f"{cc['never_heat_pump_pct']:.0f}"
    N["REV_H_BIVM_CHANGEOVER_P50_C"] = f"{cc['changeover_p50_c']:.1f}"
    cf = O / "div_cf_eoh.json"
    if cf.exists():
        C = json.load(open(cf))["towns"]
        R["cf"] = {t: {k: C[t][k]["34"]["mean"] for k in ("hp_svr", "ccop_iog", "ccop_svr")} for t in C}
        for k in ("hp_svr", "ccop_iog", "ccop_svr"):
            N[f"REV_H_CF34_{k.upper()}"] = f"{np.mean([C[t][k]['34']['mean'] for t in C]):.2f}"
            N[f"REV_H_CF34_{k.upper()}_PERDAY"] = f"{np.mean([C[t][f'{k}_perday']['34'] for t in C]):.2f}"
        N["REV_H_CF_HEAT_KWH_DAY"] = f"{np.mean([C[t]['heat_kwh_day'] for t in C]):.0f}"
    json.dump(R, open(RS.ARG("--json", "/work/out/review_h.json"), "w"), indent=1)
    print(json.dumps(N, indent=1))


if __name__ == "__main__":
    main()
