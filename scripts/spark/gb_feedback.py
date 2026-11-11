#!/usr/bin/env python3
"""Price feedback of the stock's own demand on Agile (hostile review, 9 Nov 2026, critical issue 2).

Every main run treats each home as a price-taker: Britain's gas-heated homes add tens of GW in the cheap half-hours
and the Agile price does not move. This closes the loop with the within-year slope of wholesale price on national
demand estimated from 2016-26 (data/gb/years/feedback_beta.json, gb_v3_prices.py: Elexon MID on NESO ND, year-season
fixed effects, winter GBP 3.19/MWh per GW) and the Agile reconstruction (inc VAT = 1.05 x D x W/10, D ~ 2):

    add_k+1(t) = (1 - damp) x add_k(t) + damp x 1.05 x D x beta x scale x heat_ccop_agile_k(t) / 10     p/kWh

heat_ccop_agile_k(t) = national C-COP heat-pump demand on Agile in run k (GW, flex_region.npz, gas-meter weighted,
as gb_sdp_phi.py), by weather day mapped to its calendar price day. Only Agile can feed back: Cosy and IOG are fixed
time-of-use rates, set by the supplier, which do not move with demand.

The slope is fitted on the demand range Britain has seen; tens of GW of added heat lie outside it, and a convex supply
curve would make the true response steeper. --scale 2 tests that.

    python gb_feedback.py --flex out/X/1962/flex_region.npz [--prev add_k.npz] --data data/gb --out add_k1.npz
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from gb_sdp_phi import ARG, price_day  # noqa: E402


def main():
    D = ARG("--data", "/work/data/gb")
    damp, scale = float(ARG("--damp", "0.5")), float(ARG("--scale", "1.0"))
    beta = json.load(open(f"{D}/years/feedback_beta.json"))["recommended"]["winter"]          # GBP/MWh per GW
    coef = json.load(open(f"{D}/years/meta.json"))["agile_reconstruction"]["coefficients"]
    dmult = float(np.mean([c["D"] for c in coef.values()]))
    VAT = float(ARG("--vat", "1.05"))                     # review 4: 1.0 on the ex-VAT (v4) basis
    f = np.load(ARG("--flex", ""))
    regs, tar, ctrl = list(f["regions"]), list(f["tariffs"]), list(f["ctrl"])
    W = json.load(open(f"{D}/region_weights.json"))["homes"]
    w = np.array([W[r] for r in regs], float)
    heat = (f["e"][:, :, tar.index("agile"), ctrl.index("ccop")].astype(np.float64) * w[:, None, None]).sum(0) * 2 / 1e6
    y0 = int(ARG("--price-year", "2025"))
    ydates = [str(np.datetime64(f"{y0}-11-01") + np.timedelta64(i, "D"))
              for i in range(int((np.datetime64(f"{y0 + 1}-11-01") - np.datetime64(f"{y0}-11-01")) / np.timedelta64(1, "D")))]
    pix = {d: i for i, d in enumerate(ydates)}
    new = np.zeros((len(ydates), 48))
    for di, d in enumerate(str(x) for x in f["dates"]):
        new[pix[price_day(d, y0)]] = np.maximum(new[pix[price_day(d, y0)]], VAT * dmult * beta * scale * heat[di] / 10)
    prev = np.load(ARG("--prev", ""))["add"] if "--prev" in sys.argv else np.zeros_like(new)
    add = (1 - damp) * prev + damp * new
    os.makedirs(os.path.dirname(ARG("--out", "")) or ".", exist_ok=True)
    np.savez_compressed(ARG("--out", ""), add=add.astype(np.float32), beta=beta, dmult=dmult, scale=scale, damp=damp,
                        heat_peak_gw=float(heat.max()), change_max_p=float(np.abs(add - prev).max()))
    print(f"beta {beta} x{scale}, D {dmult:.3f}: heat peak {heat.max():.1f} GW, adder mean {add.mean():.2f}p "
          f"max {add.max():.2f}p, largest change {np.abs(add - prev).max():.2f}p", flush=True)


if __name__ == "__main__":
    main()
