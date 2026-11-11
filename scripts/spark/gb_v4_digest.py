#!/usr/bin/env python3
"""Review 4 digest (9 Nov 2026): the weather-matched market and SD-Power's residual-demand cap, 12 winters, model v4.

  weather-matched   out/v4wm/<Y> (prices, carbon, ND and wind of the nearest-temperature 2016-26 day, gb_wmatch.py)
                    against out/v4/<Y> (calendar-matched): Agile herd above the flat-tariff cap, hybrid winning share
                    per tariff, C-COP minus heat-pump carbon per tariff, all-heat-pump peak. Each run's national total
                    uses its own baseline (data/gb_wm/<Y>/base_demand.json for the matched runs).
  residual cap      out/v4/<Y>/sdp_phi_{gross,residual}.npz and pass 2 out/v4p2/<Y> (gross) and out/v4p2r/<Y>
                    (residual). For the gross cap: half-hours a year in which it binds on Agile, and the share of them
                    in surplus periods, when the national Agile price is at or below zero or transmission wind meets
                    more than half of national demand. For each cap: what it removes from the residual and gross peaks,
                    its fuel cost and carbon against plain C-COP.
National weighting: towns share their region's gas-heated homes (region_weights.json "homes"), as analysis.py.
    python gb_v4_digest.py --data /work/data/gb --out-dir /work/out --json /work/out/review_v4.json
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from gb_sdp_phi import ARG, price_day  # noqa: E402

D, O = Path(ARG("--data", "/work/data/gb")), Path(ARG("--out-dir", "/work/out"))
SENS = [1962, 2025, 1941, 1945, 1950, 1965, 1974, 1981, 1992, 1998, 2004, 2024]
TAR = ("svr", "agile", "cosy", "iog")
G = json.load(open(D / "towns.json"))
W = json.load(open(D / "region_weights.json"))["homes"]
REG = {t[0]: t[3] for t in G["towns"]}
PER = {}
for r in REG.values():
    PER[r] = PER.get(r, 0) + 1
TW = {t: W[r] / PER[r] for t, r in REG.items()}


def slots(d):
    return [f"{price_day(d)}T{s // 2:02d}:{30 * (s % 2):02d}Z" for s in range(48)]


def nat(run):
    rows = list(csv.DictReader(open(run / "stock_summary.csv")))
    out = {}
    for t in TAR:
        sel = [r for r in rows if r["tariff"] == t]
        w = np.array([TW[r["town"]] for r in sel])
        wm = lambda k: float((np.array([float(r[k]) for r in sel]) * w).sum() / w.sum())  # noqa: E731
        out[t] = {"hyb_wins": wm("ccop_beats_hp_pct"), "ccop_kg": wm("ccop_kg_year_mean"), "hp_kg": wm("hp_kg_year_mean"),
                  "ccop_gbp": wm("ccop_gbp_year_mean"), "sdp_gbp": wm("sdp_gbp_year_mean"), "sdp_kg": wm("sdp_kg_year_mean")}
    return out


def series(run, ddir):
    """Heat GW (day, T, C, 48), base ND GW and wind GW (day, 48) on the run's price days."""
    f = np.load(run / "flex_region.npz")
    regs, tar, ctrl = list(f["regions"]), list(f["tariffs"]), list(f["ctrl"])
    w = np.array([W[r] for r in regs], float)
    gw = (f["e"].astype(np.float64) * w[:, None, None, None, None]).sum(0) * 2 / 1e6
    dates = [str(d) for d in f["dates"]]
    S = json.load(open(ddir / "base_demand.json"))["series"]
    Wd = json.load(open(ddir / "wind.json"))["series"]
    base = np.array([[S[k] / 1000 for k in slots(d)] for d in dates])
    wind = np.array([[Wd[k] / 1000 for k in slots(d)] for d in dates])
    return gw, base, wind, tar, ctrl, dates


def agile_nat(ddir, dates, exvat=True):
    """Town-weighted national Agile price (p/kWh) per weather day and slot, as the model priced it."""
    P = json.load(open(ddir / "prices_year.json"))
    rw = {r: sum(TW[t] for t, rr in REG.items() if rr == r) for r in set(REG.values())}
    tot = sum(rw.values())
    out = np.zeros((len(dates), 48))
    for r, wr in rw.items():
        s = P[f"agile_{r}"]
        v = np.array([[(s.get(k, np.nan) / (1.05 if exvat and k < "2026-09-30T23:00Z" else 1.0)) for k in slots(d)]
                      for d in dates])
        out += wr / tot * np.nan_to_num(v, nan=np.nanmean(v))
    return out


def main():
    R, N = {"by_year": {}}, {}
    for y in SENS:
        a, m = O / "v4" / str(y), O / "v4wm" / str(y)
        if not (a / "run.json").exists():
            continue
        Y = {}
        gw, base, wind, tar, ctrl, dates = series(a, D)
        pk = lambda g, b, t, c: float((b + g[:, tar.index(t), ctrl.index(c)]).max())  # noqa: E731
        cap = pk(gw, base, "svr", "ccop")
        Y["cal"] = {"cap": cap, "agile": pk(gw, base, "agile", "ccop"), "hp": pk(gw, base, "svr", "hp"), "nat": nat(a)}
        # residual-demand view of the same run
        resid = base - wind
        rcap = pk(gw, resid, "svr", "ccop")
        Y["cal"]["rcap"], Y["cal"]["ragile"] = rcap, pk(gw, resid, "agile", "ccop")
        ph = O / "v4" / str(y) / "sdp_phi_gross.npz"
        if ph.exists():
            f = np.load(ph)
            ti = list(f["tariffs"]).index("agile")
            bind = f["phi"][ti] > 0                                      # (days, 48)
            price = agile_nat(D, dates)
            share_wind = wind / np.maximum(base, 1e-9)
            surplus = (price <= 0) | (share_wind > 0.5)
            Y["gross_bind_hh"] = int(bind.sum())
            Y["gross_bind_surplus_hh"] = int((bind & surplus).sum())
            Y["gross_bind_negprice_hh"] = int((bind & (price <= 0)).sum())
            fr = np.load(O / "v4" / str(y) / "sdp_phi_residual.npz")
            Y["resid_bind_hh"] = int((fr["phi"][ti] > 0).sum())
            Y["resid_bind_surplus_hh"] = int(((fr["phi"][ti] > 0) & surplus).sum())
        for k, d in (("p2", "v4p2"), ("p2r", "v4p2r")):
            run = O / d / str(y)
            if (run / "run.json").exists():
                g2, b2, w2, t2, c2, _ = series(run, D)
                Y[k] = {"gross_agile": float((b2 + g2[:, t2.index("agile"), c2.index("sdp")]).max()),
                        "resid_agile": float((b2 - w2 + g2[:, t2.index("agile"), c2.index("sdp")]).max()),
                        "nat": nat(run)}
        if (m / "run.json").exists():
            dm = D.parent / "gb_wm" / str(y)
            g3, b3, w3, t3, c3, _ = series(m, dm)
            pk3 = lambda t, c: float((b3 + g3[:, t3.index(t), c3.index(c)]).max())  # noqa: E731
            Y["wm"] = {"cap": pk3("svr", "ccop"), "agile": pk3("agile", "ccop"), "hp": pk3("svr", "hp"), "nat": nat(m)}
        R["by_year"][y] = Y
        print(y, {k: round(v["agile"] - v["cap"], 1) for k, v in Y.items() if isinstance(v, dict) and "cap" in v},
              Y.get("gross_bind_hh"), Y.get("gross_bind_surplus_hh"), flush=True)
    by = R["by_year"]
    med = lambda v: float(np.median(v))                                   # noqa: E731
    herd = lambda Y, k: max(Y[k]["agile"] - Y[k]["cap"], 0)              # noqa: E731
    ys = [y for y in by if "wm" in by[y]]
    if ys:
        N["REV4_WM_YEARS"] = str(len(ys))
        N["REV4_WM_HERD_CAL_GW"] = f"{max(herd(by[y], 'cal') for y in ys):.0f}"
        N["REV4_WM_HERD_GW"] = f"{max(herd(by[y], 'wm') for y in ys):.0f}"
        dh = [herd(by[y], "wm") - herd(by[y], "cal") for y in ys]
        N["REV4_WM_HERD_UP_N"] = str(sum(d > 0.5 for d in dh))           # winters whose herd grew by more than 0.5 GW
        N["REV4_WM_HERD_DOWN_N"] = str(sum(d < -0.5 for d in dh))
        N["REV4_WM_HP_PEAK_CAL_GW"] = f"{max(by[y]['cal']['hp'] for y in ys):.0f}"
        N["REV4_WM_HP_PEAK_GW"] = f"{max(by[y]['wm']['hp'] for y in ys):.0f}"
        for t in TAR:
            T = t.upper()
            N[f"REV4_WM_HYB_CAL_{T}"] = f"{med([by[y]['cal']['nat'][t]['hyb_wins'] for y in ys]):.0f}"
            N[f"REV4_WM_HYB_{T}"] = f"{med([by[y]['wm']['nat'][t]['hyb_wins'] for y in ys]):.0f}"
            gap = lambda Y, k: Y[k]["nat"][t]["ccop_kg"] - Y[k]["nat"][t]["hp_kg"]  # noqa: E731
            N[f"REV4_WM_KGGAP_CAL_{T}"] = f"{med([gap(by[y], 'cal') for y in ys]):,.0f}"
            N[f"REV4_WM_KGGAP_{T}"] = f"{med([gap(by[y], 'wm') for y in ys]):,.0f}"
    ys = [y for y in by if "gross_bind_hh" in by[y]]
    if ys:
        N["REV4_RES_YEARS"] = str(len(ys))
        N["REV4_GROSS_BIND_HH"] = f"{med([by[y]['gross_bind_hh'] for y in ys]):,.0f}"
        N["REV4_GROSS_BIND_SURPLUS_PCT"] = f"{100 * sum(by[y]['gross_bind_surplus_hh'] for y in ys) / max(sum(by[y]['gross_bind_hh'] for y in ys), 1):.0f}"
        N["REV4_GROSS_BIND_NEGPRICE_PCT"] = f"{100 * sum(by[y]['gross_bind_negprice_hh'] for y in ys) / max(sum(by[y]['gross_bind_hh'] for y in ys), 1):.0f}"
        N["REV4_RESID_BIND_HH"] = f"{med([by[y]['resid_bind_hh'] for y in ys]):,.0f}"
        N["REV4_RESID_BIND_SURPLUS_PCT"] = f"{100 * sum(by[y]['resid_bind_surplus_hh'] for y in ys) / max(sum(by[y]['resid_bind_hh'] for y in ys), 1):.0f}"
        N["REV4_RES_HERD_GW"] = f"{max(max(by[y]['cal']['ragile'] - by[y]['cal']['rcap'], 0) for y in ys):.0f}"
    ys = [y for y in by if "p2" in by[y] and "p2r" in by[y]]
    if ys:
        N["REV4_P2_YEARS"] = str(len(ys))
        for k, K in (("p2", "GROSS"), ("p2r", "RESID")):
            N[f"REV4_{K}_COST_AGILE"] = f"{np.mean([by[y][k]['nat']['agile']['sdp_gbp'] - by[y][k]['nat']['agile']['ccop_gbp'] for y in ys]):.0f}"
            N[f"REV4_{K}_KG_AGILE"] = f"{np.mean([by[y][k]['nat']['agile']['sdp_kg'] - by[y][k]['nat']['agile']['ccop_kg'] for y in ys]):.0f}"
            N[f"REV4_{K}_GROSS_PEAK_AGILE"] = f"{max(by[y][k]['gross_agile'] for y in ys):.0f}"
            N[f"REV4_{K}_RESID_PEAK_AGILE"] = f"{max(by[y][k]['resid_agile'] for y in ys):.0f}"
        N["REV4_GROSS_CAP_MAX"] = f"{max(by[y]['cal']['cap'] for y in ys):.0f}"
        N["REV4_RESID_CAP_MAX"] = f"{max(by[y]['cal']['rcap'] for y in ys):.0f}"
        N["REV4_CCOP_AGILE_PEAK_MAX"] = f"{max(by[y]['cal']['agile'] for y in ys):.0f}"
        N["REV4_CCOP_AGILE_RESID_PEAK_MAX"] = f"{max(by[y]['cal']['ragile'] for y in ys):.0f}"
    pre = {}                                                    # both homes may pre-heat (v4pre, 8,000 homes)
    for y in SENS:
        f = O / "v4pre" / str(y) / "stock_summary.csv"
        if f.exists():
            rows = list(csv.DictReader(open(f)))
            if rows and "ccop_pre_beats_hp_pre_pct" in rows[0]:
                for t in TAR:
                    sel = [r for r in rows if r["tariff"] == t]
                    w = np.array([TW[r["town"]] for r in sel])
                    for k, col in (("pre", "ccop_pre_beats_hp_pre_pct"), ("nopre", "ccop_beats_hp_pct")):
                        pre.setdefault((t, k), []).append(float((np.array([float(r[col]) for r in sel]) * w).sum() / w.sum()))
    for t in TAR:
        if pre.get((t, "pre")):
            N[f"REV_PRE_HYB_{t.upper()}"] = f"{np.median(pre[(t, 'pre')]):.0f}"
            N[f"REV_PRE_NOPRE_HYB_{t.upper()}"] = f"{np.median(pre[(t, 'nopre')]):.0f}"
            N["REV_PRE_YEARS"] = str(len(pre[(t, "pre")]))
    cj = O / "v4cal" / "spf_cal.json"                           # recalibration of the low level (gb_spf_cal.py)
    if cj.exists():
        C = json.load(open(cj))
        tri = lambda L: sum(C[L][y] for y in ("2020", "2021", "2022")) / 3   # noqa: E731
        if "0.7216" in C:
            N["REV_CAL_SPF_OLD"] = f"{tri('0.7216'):.2f}"
        if "0.816" in C:
            N["REV_CAL_SPF_NEW"] = f"{tri('0.816'):.2f}"
        if "1.0" in C and "2025" in C["1.0"]:
            N["REV_CAL_SPF_HI_2025"] = f"{C['1.0']['2025']:.2f}"
    wj = D.parent / "gb_wm" / "1962" / "wmatch.json"           # how far 1962-63 lies beyond the 2016-26 pool
    if wj.exists():
        w = json.load(open(wj))
        N["REV4_WM_COLDER_1962"] = str(w["colder_than_pool"])
        N["REV4_WM_COLDEST_1962"] = f"{w['coldest_weather_c']:.1f}".replace("-", "−")
        N["REV4_WM_POOL_COLDEST"] = f"{w['coldest_matched_c']:.1f}".replace("-", "−")
        N["REV4_WM_TERR_1962"] = f"{w['abs_temp_err_mean']:.2f}"
    R["numbers"] = N
    json.dump(R, open(ARG("--json", "/work/out/review_v4.json"), "w"), indent=1)
    print(json.dumps(N, indent=1))


if __name__ == "__main__":
    main()
