#!/usr/bin/env python3
"""Household base load for the local-feeder case (feeder_case.py), from the Low Carbon London smart-meter data
(UK Power Networks, London Datastore, CC BY 4.0): the flat-tariff ("Std") homes' half-hourly electricity on winter
weekdays, December 2012 to February 2013, one 48-slot kW profile per home-day, grouped by an anonymous home index.
These homes' electricity includes whatever heating they had (London, 2013: mostly none electric), so it stands for
the feeder's load before heat pumps. Writes lcl_base.npz (kw (N, 48) float16, home (N,) int) and lcl_base.json.
    python lcl_base.py --csv ~/lcl/CC_LCL-FullData.csv --out ~/lcl/lcl_base.npz
"""
import io
import json
import sys

import numpy as np
import pandas as pd

ARG = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d       # noqa: E731
CSV, OUT = ARG("--csv", "/w/CC_LCL-FullData.csv"), ARG("--out", "/w/lcl_base.npz")
MONTHS = ("2012-12", "2013-01", "2013-02")
rows = []
for ch in pd.read_csv(CSV, chunksize=10_000_000, header=0, names=["id", "grp", "t", "kwh"],
                      dtype={"id": str, "grp": str, "t": str, "kwh": str}):
    ch = ch[(ch["grp"].str.strip() == "Std") & ch["t"].str[:7].isin(MONTHS)]
    if ch.empty:
        continue
    t = pd.to_datetime(ch["t"].str[:19], format="%Y-%m-%d %H:%M:%S")
    rows.append(pd.DataFrame({"id": ch["id"].values, "date": t.dt.strftime("%Y-%m-%d").values,
                              "wd": t.dt.weekday.values, "hh": (t.dt.hour * 2 + t.dt.minute // 30).values,
                              "kw": pd.to_numeric(ch["kwh"].str.strip(), errors="coerce").astype("float32").values * 2}))
    print("chunk", sum(len(r) for r in rows), flush=True)
df = pd.concat(rows, ignore_index=True)
df = df[df.wd < 5]
m = df.pivot_table(index=["id", "date"], columns="hh", values="kw").reindex(columns=range(48))
m = m.dropna(thresh=46)
m = m[(m.max(1) < 30)]                                     # drop meter faults
kw = m.fillna(0.0).values.astype(np.float16)
home = pd.factorize(m.index.get_level_values(0))[0].astype(np.int64)
np.savez_compressed(OUT, kw=kw, home=home)
pk = kw.astype(float)
R = {"source": "UKPN Low Carbon London smart-meter data, Std homes, winter weekdays Dec 2012 to Feb 2013",
     "home_days": int(len(kw)), "homes": int(home.max() + 1), "kwh_day_mean": round(float(pk.sum(1).mean() / 2), 2),
     "indiv_peak_kw_median": round(float(np.median(pk.max(1))), 2), "profile_kw_mean": [round(float(v), 3) for v in pk.mean(0)],
     "admd_kw_mean_day": round(float(pk.mean(0).max()), 3)}
json.dump(R, open(OUT.replace(".npz", ".json"), "w"), indent=1)
print(json.dumps(R, indent=1))
