"""Electrification of Heat (UKDS SN 9209, open) heating schedules as a habits library for the model (gbmodel/diversity.py,
--div-lib), the heat-pump counterpart of the IDEAL gas library (ideal_gas.py --lib).

Every non-hybrid heat-pump home-day in the heating months (November to March) with a daily mean outdoor temperature
below 8 C and at least 46 of 48 half-hours metered becomes one 48-slot on/off pattern: ON where the heat pump
delivered more than THR kWh of heat in the half-hour (0.1 kWh = 200 W averaged, above standby and pump-only running).
Patterns are grouped by an anonymous home index so a model home can keep one real home's habits for a whole winter.
Writes /w/work/eoh_schedules.npz (on (N, 48) bool, home (N,) int) and /w/work/eoh_schedules.json (aggregates only).
"""
import json

import numpy as np
import pandas as pd

P = "/w/work/eoh_hh.parquet"
THR = 0.1
cols = ["Property_ID", "Timestamp", "Heat_Pump_Energy_Output", "Boiler_Energy_Output", "External_Air_Temperature"]
df = pd.read_parquet(P, columns=cols).sort_values(["Property_ID", "Timestamp"]).reset_index(drop=True)
df["Property_ID"] = df["Property_ID"].astype(str)
g = df.groupby("Property_ID", sort=False)
same = g["Timestamp"].diff() == pd.Timedelta("30min")
for k, c in (("hp", "Heat_Pump_Energy_Output"), ("boil", "Boiler_Energy_Output")):
    d = g[c].diff().where(same)
    d = d.where((d >= 0) & (d <= 25))
    df[k] = d.astype("float32")
boil_tot = df.groupby("Property_ID")["boil"].sum()
hyb = set(boil_tot[boil_tot > 300].index)
w = df[(~df.Property_ID.isin(hyb)) & df.Timestamp.dt.month.isin([11, 12, 1, 2, 3])].copy()
del df
w["date"] = w.Timestamp.dt.floor("D")
w["hh"] = (w.Timestamp.dt.hour * 2 + w.Timestamp.dt.minute // 30).astype("int16")
day = w.groupby(["Property_ID", "date"]).agg(t=("External_Air_Temperature", "mean"), n=("hp", "count"))
ok = day[(day.t < 8) & (day.n >= 46)].reset_index()[["Property_ID", "date"]]
w = w.merge(ok, on=["Property_ID", "date"])
m = w.pivot_table(index=["Property_ID", "date"], columns="hh", values="hp").reindex(columns=range(48))
on = (m.fillna(0.0).values > THR)
home = pd.factorize(m.index.get_level_values(0))[0].astype(np.int64)
np.savez_compressed("/w/work/eoh_schedules.npz", on=on, home=home)
slots = on.sum(1)
per_home_night = pd.Series(on[:, 2:10].mean(1)).groupby(home).mean()
R = {"source": "UKDS SN 9209 (open): heat pump heat output, non-hybrid homes, Nov-Mar days with daily mean outdoor < 8 C",
     "threshold_kwh_per_hh": THR, "home_days": int(len(on)), "homes": int(home.max() + 1),
     "on_share": round(float(on.mean()), 3), "on_share_by_hh": [round(float(v), 3) for v in on.mean(0)],
     "hours_on_per_day": {f"p{p}": round(float(np.percentile(slots, p)) / 2, 1) for p in (10, 25, 50, 75, 90)},
     "share_days_on_all_day": round(float((slots >= 44).mean()), 3),
     "share_days_off_overnight": round(float((on[:, 2:10].sum(1) == 0).mean()), 3),
     "share_homes_mostly_overnight": round(float((per_home_night > 0.5).mean()), 3),
     "day_mean_outdoor_c": round(float(day.loc[day.t < 8, "t"].mean()), 2)}
json.dump(R, open("/w/work/eoh_schedules.json", "w"), indent=1)
print(json.dumps(R, indent=1))
