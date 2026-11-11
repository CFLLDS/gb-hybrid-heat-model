#!/usr/bin/env python3
"""Aggregate validation against the Electrification of Heat trial (independent review, 10 Nov 2026, item 1): the
model's all-electric homes against the trial's non-hybrid homes on the same nine cold days of winter 2022-23.

Measured: results/ukds/eoh_cf_sizes.json (scripts/spark/ukds/eoh_cf_sizes.py; whole-system electricity of the homes
with complete data on every window day). Model: results/diversity/val_cf_base.json and val_cf_eoh.json
(gb_coincidence.py --weather 2022 --dates ..., 4,000 homes in Newcastle, Edinburgh and Maidstone, the map towns
nearest the trial's clusters, without and with the trial's own heating habits). Compares, per home: coincident
demand (ADMD, mean of the daily maxima and the window maximum), the individual peak, electricity a day, the mean
daily profile (shape correlation and peak half-hour) and coincidence factors for groups of 34, 100 and 300 homes.
Writes results/diversity/eoh_validation.json with REV_V_* numbers.
"""
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "docs" / "article" / "results"
meas = json.load(open(R / "ukds" / "eoh_cf_sizes.json"))
runs = {k: json.load(open(R / "diversity" / f"val_cf_{k}.json"))["towns"] for k in ("base", "eoh")}


def corr(a, b):
    return float(np.corrcoef(a, b)[0, 1])


def model(towns):
    T = list(towns.values())
    admd_days = np.mean([t["hp_svr_daily_admd_kw"] for t in T], axis=0)       # mean over towns, per day
    prof = np.mean([t["profile_hp_svr"] for t in T], axis=0)
    return {"towns": list(towns), "admd_kw_mean": float(admd_days.mean()), "admd_kw_max": float(admd_days.max()),
            "admd_kw_by_day": [round(float(v), 3) for v in admd_days],
            "indiv_peak_kw_median": float(np.mean([t["hp_svr_indiv_peak_kw_median"] for t in T])),
            "kwh_day": float(np.mean([t["hp_svr_kwh_day"] for t in T])),
            "heat_kwh_day": float(np.mean([t["heat_kwh_day"] for t in T])),
            "cf_window": {n: float(np.mean([t["hp_svr"][n]["mean"] for t in T])) for n in ("10", "34", "100", "300", "1000")},
            "cf_perday": {n: float(np.mean([t["hp_svr_perday"][n] for t in T])) for n in ("10", "34", "100", "300", "1000")},
            "profile_kw_mean": [round(float(v), 3) for v in prof], "peak_hh": int(np.argmax(prof)),
            "shape_r": corr(prof, meas["profile_kw_mean"]),
            "cold_mean_c": float(np.mean([t["cold_mean_c"] for t in T]))}


out = {"dates": meas["dates"], "measured": meas, "model": {k: model(v) for k, v in runs.items()}}
N = {}
hh = lambda i: f"{i // 2:02d}:{30 * (i % 2):02d}"                                         # noqa: E731
N["REV_V_DAYS"] = str(len(meas["dates"]))
N["REV_V_MEAS_HOMES"] = str(meas["homes"])
N["REV_V_MEAS_TEMP_C"] = f"{meas['window_mean_temp_c']:.1f}".replace("-", "−")
N["REV_V_MEAS_ADMD_KW"] = f"{meas['admd_kw_mean']:.2f}"
N["REV_V_MEAS_ADMD_MAX_KW"] = f"{max(meas['admd_kw_by_day']):.2f}"
N["REV_V_MEAS_IPEAK_KW"] = f"{meas['indiv_peak_kw_median']:.1f}"
N["REV_V_MEAS_KWH_DAY"] = f"{meas['kwh_day']:.0f}"
N["REV_V_MEAS_PEAK_HH"] = hh(meas["peak_hh"])
for n in ("34", "100", "300"):
    N[f"REV_V_MEAS_CF{n}"] = f"{meas['cf_window'][n]:.2f}"
N["REV_V_MEAS_CFALL"] = f"{meas['cf_window']['all']:.2f}"
N["REV_V_MEAS_CF34_DAY"] = f"{meas['cf_perday']['34']:.2f}"
for k, K in (("base", "BASE"), ("eoh", "EOH")):
    m = out["model"][k]
    N[f"REV_V_{K}_ADMD_KW"] = f"{m['admd_kw_mean']:.2f}"
    N[f"REV_V_{K}_ADMD_MAX_KW"] = f"{m['admd_kw_max']:.2f}"
    N[f"REV_V_{K}_ADMD_ERR_PCT"] = f"{100 * (m['admd_kw_mean'] / meas['admd_kw_mean'] - 1):+.0f}".replace("-", "−")
    N[f"REV_V_{K}_IPEAK_KW"] = f"{m['indiv_peak_kw_median']:.1f}"
    N[f"REV_V_{K}_IPEAK_ERR_PCT"] = f"{100 * (m['indiv_peak_kw_median'] / meas['indiv_peak_kw_median'] - 1):+.0f}".replace("-", "−")
    N[f"REV_V_{K}_KWH_DAY"] = f"{m['kwh_day']:.0f}"
    N[f"REV_V_{K}_KWH_ERR_PCT"] = f"{100 * (m['kwh_day'] / meas['kwh_day'] - 1):+.0f}".replace("-", "−")
    N[f"REV_V_{K}_PEAK_HH"] = hh(m["peak_hh"])
    N[f"REV_V_{K}_SHAPE_R"] = f"{m['shape_r']:.2f}"
    for n in ("34", "100", "300"):
        N[f"REV_V_{K}_CF{n}"] = f"{m['cf_window'][n]:.2f}"
    N[f"REV_V_{K}_CF34_DAY"] = f"{m['cf_perday']['34']:.2f}"
    N[f"REV_V_{K}_TEMP_C"] = f"{m['cold_mean_c']:.1f}".replace("-", "−")
N["REV_V_TOWNS"] = ", ".join(out["model"]["base"]["towns"][:-1]) + " and " + out["model"]["base"]["towns"][-1]
out["numbers"] = N
json.dump(out, open(R / "diversity" / "eoh_validation.json", "w"), indent=1)
print(json.dumps(N, indent=1))
