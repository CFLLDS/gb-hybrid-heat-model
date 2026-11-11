#!/usr/bin/env python3
"""Staggered response: the national peaks when homes do not all act on the same half-hour (review, 9 Nov 2026:
"add realistic diversity as a sensitivity").

The model's homes act on a price edge in the same half-hour, so its herd is a synchronised stress case (coincidence
factor 1.00 for 34 hybrid homes on a two-rate tariff, against 0.27 measured in Freedom). This spreads each home's
response: every home's whole electricity schedule is shifted by its own random offset, uniform over -W..+W half-hours.
With offsets independent of the homes, the expected national demand is the national series convolved with a uniform
kernel of 2W+1 half-hours, so no per-home data are needed. The shift is applied to the stock's electricity only, not to
Britain's baseline, and to every controller alike; the homes' costs are not recomputed (a shifted home pays the price of
the half-hour it moved into, so this is a demand-side test only).

Herd = worst-winter Agile C-COP peak - SD-Power's cap (worst-winter flat-tariff C-COP peak, unstaggered), as
HERD_EXCESS_AGILE_GW. Peak removed = (all-HP peak - C-COP peak) / (all-HP peak - baseline peak), mean over winters.

    python gb_stagger.py --data /work/data/gb --src /work/out/v3f --out /work/out/review_stagger.json
"""
import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gb_sdp_phi import ARG, price_day  # noqa: E402

TAR = ("svr", "agile", "cosy", "iog")
WIDTHS = (0, 1, 2, 4)                     # +-0, +-30 min, +-1 h, +-2 h


def main():
    D = ARG("--data", "/work/data/gb")
    W = json.load(open(f"{D}/region_weights.json"))["homes"]
    S = json.load(open(f"{D}/base_demand.json"))["series"]
    runs = sorted(glob.glob(f"{ARG('--src', '/work/out/v3f')}/[12][0-9][0-9][0-9]/flex_region.npz"))
    per = {w: [] for w in WIDTHS}
    for fpath in runs:
        f = np.load(fpath)
        regs, tar, ctrl = list(f["regions"]), list(f["tariffs"]), list(f["ctrl"])
        wt = np.array([W[r] for r in regs], float)
        dates = [str(d) for d in f["dates"]]
        order = np.argsort(dates)
        base = np.array([[S[f"{price_day(d)}T{s // 2:02d}:{30 * (s % 2):02d}Z"] / 1000 for s in range(48)]
                         for d in dates])[order].ravel()
        gw = {(t, c): ((f["e"][:, :, tar.index(t), ctrl.index(c)].astype(np.float64) * wt[:, None, None]).sum(0)
                       * 2 / 1e6)[order].ravel() for t in TAR for c in ("hp", "ccop")}
        for w in WIDTHS:
            k = np.ones(2 * w + 1) / (2 * w + 1)
            sm = {kc: (np.convolve(np.pad(v, w, mode="edge"), k, mode="valid") if w else v) for kc, v in gw.items()}
            p = {f"{c}_{t}": float((base + sm[(t, c)]).max()) for (t, c) in sm}
            p["base"] = float(base.max())
            per[w].append(p)
        print(os.path.basename(os.path.dirname(fpath)), {w: round(per[w][-1]["ccop_agile"], 1) for w in WIDTHS}, flush=True)
    cap = max(p["ccop_svr"] for p in per[0])
    N, R = {}, {"years": len(runs), "cap_gw": cap, "by_width": {}}
    for w in WIDTHS:
        P = per[w]
        r = {"herd_agile_gw": max(p["ccop_agile"] for p in P) - cap,
             "herd_cosy_gw": max(p["ccop_cosy"] for p in P) - cap, "herd_iog_gw": max(p["ccop_iog"] for p in P) - cap}
        for t in TAR:
            r[f"removed_{t}_pct"] = float(np.mean([100 * (p[f"hp_{t}"] - p[f"ccop_{t}"]) / (p[f"hp_{t}"] - p["base"]) for p in P]))
            r[f"hp_{t}_max_gw"] = max(p[f"hp_{t}"] for p in P)
        R["by_width"][w] = r
        tag = {0: "W0", 1: "W30", 2: "W60", 4: "W120"}[w]
        N[f"REV_STAG_{tag}_HERD_AGILE_GW"] = f"{max(r['herd_agile_gw'], 0):.0f}"
        N[f"REV_STAG_{tag}_HERD_COSY_GW"] = f"{max(r['herd_cosy_gw'], 0):.0f}"
        N[f"REV_STAG_{tag}_HERD_IOG_GW"] = f"{max(r['herd_iog_gw'], 0):.0f}"
        for t in ("svr", "agile", "cosy", "iog"):
            N[f"REV_STAG_{tag}_REMOVED_{t.upper()}"] = f"{r[f'removed_{t}_pct']:.0f}"
        N[f"REV_STAG_{tag}_HP_SVR_MAX_GW"] = f"{r['hp_svr_max_gw']:.0f}"
    N["REV_STAG_YEARS"] = str(len(runs))
    R["numbers"] = N
    json.dump(R, open(ARG("--out", "/work/out/review_stagger.json"), "w"), indent=1)
    print(json.dumps(N, indent=1))


if __name__ == "__main__":
    main()
