#!/usr/bin/env python3
"""Calibrate the v3 real stock IN THE MODEL'S OWN TERMS (7 Nov 2026, after Craig's check "is our maths correct? the
price cap is only ~1,800 for both fuels"): the first v3 run used ~13% more gas than DESNZ metered gas, because the
stock was calibrated with degree-hours at a 15.5 C base while the model computes demand from each home's set point
and internal gains (an implicit base nearer 17-18 C).

For each town, using exactly the model's space-heat equation (gbmodel/homes.py stock_day)
    q_space = max(UA (Tset - T) - G g(t), 0) x 0.5 h,   Tset ~ U(19, 21.5), G ~ U(250, 700) W, g = GAINS_SHAPE
over 10 years spanning 1991-2020 (every third heating year, hourly ERA5 from history.npz), find ONE multiplier f on
the town's dwelling-record HTCs so that mean modelled gas per home, (space heat + hot water) / boiler efficiency,
equals DESNZ 2024 mean domestic gas per gas-HEATED home (per meter / 0.86). Hot water and efficiency use the model's
own means: U(2, 8) kWh/day and U(0.85, 0.92). Writes htc_cal (records x f) into stock_v3.npz and the multipliers
into stock_v3_meta.json under "model_calibration". DESNZ gas is weather-corrected to the industry's 2015-2020
seasonal normal, so the calibration weather is heating years 2014-15 to 2019-20; homes use the sourced inputs.
    .venv/bin/python -I scripts/spark/gb_v3_calibrate.py
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gbmodel import inputs as IN  # noqa: E402  (the model's own sourced input formulas)

ROOT = Path(__file__).resolve().parents[2]
GB = ROOT / "data" / "model" / "gb"
GAINS = np.array([0.7] * 12 + [1.1] * 6 + [0.8] * 14 + [1.3] * 10 + [1.0] * 6)
H_HEATED = 0.86
# DESNZ sub-national domestic gas is weather-corrected (Xoserve AQ) to the gas industry's seasonal normal, adjusted to
# the expected 2015-2020 climate (docs/article/lit/model_inputs.json), so calibrate against heating years 2014-15 ..
# 2019-20. Homes use the model's SOURCED inputs (gbmodel/inputs.py): set point, gains by floor area, hot water by
# SAP occupancy, in-use boiler efficiency.
N_HOMES, YEARS = 600, list(range(2014, 2020))


def town_half_hours(h, i):
    """(n_half_hours,) temperature for the chosen heating years, hourly ERA5 interpolated to half-hours, plus the
    matching gains-profile index (slot of day)."""
    t0 = np.datetime64(str(h["start"]))
    out, slots = [], []
    for y in YEARS:
        a = int((np.datetime64(f"{y}-11-01T00:00") - t0) / np.timedelta64(1, "h"))
        hr = h["t"][i, a:a + 365 * 24 + 1].astype(float) / 10
        hr = np.where(hr <= -3276, np.nan, hr)
        hr = np.where(np.isnan(hr), np.nanmean(hr), hr)
        half = np.interp(np.arange(365 * 48) / 2, np.arange(len(hr)), hr)
        out.append(half)
        slots.append(np.tile(np.arange(48), 365))
    return np.concatenate(out), np.concatenate(slots)


def mean_gas(f, ua, tset, gw, T, g, dhw_yr, eta):
    """Mean annual gas per home (kWh) at HTC multiplier f, the model's equation and sourced inputs."""
    q = np.maximum((f * ua)[:, None] * (tset[:, None] - T[None, :]) - (gw[:, None] * g[None, :]), 0) * 0.5 / 1000
    space = q.sum(1) / len(YEARS)
    return float(((space + dhw_yr) / eta).mean())


def main():
    z = dict(np.load(GB / "stock_v3.npz"))
    meta = json.load(open(GB / "stock_v3_meta.json"))
    h = np.load(GB / "history.npz")
    hist_towns = [str(x) for x in h["towns"]]
    rng = np.random.default_rng(7112026)
    mt = {t["town"]: t for t in meta["towns"]}
    htc_cal = np.zeros_like(z["htc_w_k"])
    res = {}
    for ti, name in enumerate(z["towns"]):
        name = str(name)
        target = mt[name]["gas_mean_kwh_per_meter_2024"] / H_HEATED
        recs = z["htc_w_k"][ti]
        pick = rng.integers(0, len(recs), N_HOMES)
        ua, tfa = recs[pick], z["floor_area"][ti][pick]
        tset = IN.set_point(rng.standard_normal(N_HOMES), np)
        gw = IN.gains_w(tfa, rng.uniform(size=N_HOMES), np)
        dhw_yr = IN.dhw_kwh_day(IN.sap_occupancy(tfa, np), rng.standard_normal(N_HOMES), np) * 365
        eta = IN.boiler_eta(rng.standard_normal(N_HOMES), np)
        T, slot = town_half_hours(h, hist_towns.index(name))
        g = GAINS[slot]
        lo, hi = 0.2, 3.0
        for _ in range(22):                                        # bisection: modelled gas rises with f
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if mean_gas(mid, ua, tset, gw, T, g, dhw_yr, eta) < target else (lo, mid)
        f = (lo + hi) / 2
        before = mean_gas(1.0, ua, tset, gw, T, g, dhw_yr, eta)
        htc_cal[ti] = recs * f
        res[name] = {"target_gas_kwh": round(target), "model_gas_before_kwh": round(before), "htc_multiplier": round(f, 4),
                     "median_htc_cal_w_k": round(float(np.median(recs * f)), 1),
                     "median_tau_cal_h": round(float(np.median(z["c_kwh_k"][ti] / (recs * f / 1000))), 1)}
        print(f"{name:14} target {target:7,.0f}  model {before:7,.0f} kWh  f {f:.3f}  HTC {np.median(recs * f):5.0f} W/K", flush=True)
    z["htc_cal"] = htc_cal
    np.savez_compressed(GB / "stock_v3.npz", **z)
    m = np.array([r["htc_multiplier"] for r in res.values()])
    meta["model_calibration"] = {"method": __doc__.split("For each town")[0].strip() + " See gb_v3_calibrate.py.",
                                 "h_heated_homes_per_meter": H_HEATED, "years": YEARS, "homes_per_town": N_HOMES,
                                 "multiplier_median": round(float(np.median(m)), 3), "multiplier_range": [round(float(m.min()), 3), round(float(m.max()), 3)],
                                 "median_htc_cal_w_k": round(float(np.median([r["median_htc_cal_w_k"] for r in res.values()])), 1),
                                 "median_tau_cal_h": round(float(np.median([r["median_tau_cal_h"] for r in res.values()])), 1),
                                 "towns": res}
    json.dump(meta, open(GB / "stock_v3_meta.json", "w"), indent=1)
    print(f"multiplier median {np.median(m):.3f} (range {m.min():.3f}-{m.max():.3f}); "
          f"median HTC {meta['model_calibration']['median_htc_cal_w_k']} W/K, tau {meta['model_calibration']['median_tau_cal_h']} h")


if __name__ == "__main__":
    main()
