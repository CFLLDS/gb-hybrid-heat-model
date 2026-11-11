#!/usr/bin/env python3
"""SD-Power dispatch, pass 1 -> pass 2: the share of homes that must use gas in each half-hour.

For one heating year, from pass 1's out/v2/<Y>/flex_region.npz (mean C-COP electricity per home per half-hour per
region) scaled by each region's domestic gas meters (data/gb/region_weights.json), plus Britain's own national
demand in the same calendar half-hour of the price year (default 2025-26; --price-year Y with that year's
base_demand.json in --data), NESO ND:

  total(t)  = base(t) + heat_ccop(t)
  cap       = max over the year of base + heat_ccop on SVR    ("no peakier than C-COP on a flat tariff")
  phi(t)    = clip(1 - (cap - base(t)) / heat_ccop(t), 0, 1)  where total(t) > cap, else 0

so that shedding a random share phi of homes to gas holds the total at the cap. One phi for all regions.
    python gb_sdp_phi.py --flex out/v2/1962/flex_region.npz --data data/gb --out out/v2/1962/sdp_phi.npz
"""
import json
import sys

import numpy as np


def ARG(k, d):
    return sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d


def price_day(d, py=None):
    """Same mapping as gbmodel.data.price_day: Nov-Dec -> price year, Jan-Oct -> price year + 1."""
    py = int(ARG("--price-year", "2025")) if py is None else py
    y = py if d[5:] >= "11" else py + 1
    md = d[5:]
    if md == "02-29" and not (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)):
        md = "02-28"
    return f"{y}-{md}"


def main():
    f = np.load(ARG("--flex", ""))
    D = ARG("--data", "/work/data/gb")
    regs, tar, ctrl = list(f["regions"]), list(f["tariffs"]), list(f["ctrl"])
    dates = [str(d) for d in f["dates"]]
    W = json.load(open(f"{D}/region_weights.json"))["homes"]
    w = np.array([W[r] for r in regs], float)
    heat = (f["e"][:, :, :, ctrl.index("ccop")].astype(np.float64) * w[:, None, None, None]).sum(0) * 2 / 1e6  # GW (day,T,48)
    S = json.load(open(f"{D}/base_demand.json"))["series"]
    base = np.array([[S[f"{price_day(d)}T{s // 2:02d}:{30 * (s % 2):02d}Z"] / 1000 for s in range(48)] for d in dates])
    if ARG("--basis", "gross") == "residual":         # review 4: cap demand net of transmission wind (gb_wind.py)
        Wd = json.load(open(f"{D}/wind.json"))["series"]
        base = base - np.array([[Wd[f"{price_day(d)}T{s // 2:02d}:{30 * (s % 2):02d}Z"] / 1000 for s in range(48)]
                                for d in dates])
    cap = float((base + heat[:, tar.index("svr")]).max())
    tot = base[:, None, :] + heat
    phi = np.where(tot > cap, np.clip(1 - (cap - base[:, None, :]) / np.maximum(heat, 1e-9), 0, 1), 0.)
    phi = np.transpose(phi, (1, 0, 2)).astype(np.float32)                          # (T, days, 48)
    np.savez_compressed(ARG("--out", ""), phi=phi, tariffs=np.array(tar), dates=np.array(dates), cap_gw=cap,
                        peak_before_gw=tot.max(axis=(0, 2)), base_peak_gw=float(base.max()))
    print(f"cap {cap:.1f} GW; peak before by tariff " + ", ".join(f"{t} {tot[:, i].max():.1f}" for i, t in enumerate(tar))
          + f"; shed half-hours " + ", ".join(f"{t} {(phi[i] > 0).sum()}" for i, t in enumerate(tar)))


if __name__ == "__main__":
    main()
