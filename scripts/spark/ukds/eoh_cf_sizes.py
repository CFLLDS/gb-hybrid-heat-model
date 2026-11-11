"""EoH (UKDS SN 9209, open) cold-day aggregate statistics for the model's validation (gb_coincidence.py on the same
dates): for the trial's winter 2022-23 cold days, the non-hybrid homes' coincident demand per home (ADMD), individual
peak, electricity per day, mean profile and coincidence factors for groups of 10, 34, 100, 300 and all homes, over the
window of all days together (as the model's) and day by day. Aggregates only; writes /w/work/eoh_cf_sizes.json."""
import json
import sys

import numpy as np
import pandas as pd

DATES = sys.argv[1].split(",") if len(sys.argv) > 1 else ["2022-12-09", "2022-12-11", "2022-12-13", "2022-12-15", "2022-12-17",
                                                           "2023-01-17", "2023-01-19", "2023-01-21", "2023-03-08"]
GROUPS = [10, 34, 100, 300]
rng = np.random.default_rng(9209)
cols = ["Property_ID", "Timestamp", "Whole_System_Energy_Consumed", "Boiler_Energy_Output", "External_Air_Temperature"]
df = pd.read_parquet("/w/work/eoh_hh.parquet", columns=cols).sort_values(["Property_ID", "Timestamp"]).reset_index(drop=True)
df["Property_ID"] = df["Property_ID"].astype(str)
g = df.groupby("Property_ID", sort=False)
same = g["Timestamp"].diff() == pd.Timedelta("30min")
for k, c in (("sys", "Whole_System_Energy_Consumed"), ("boil", "Boiler_Energy_Output")):
    d = g[c].diff().where(same)
    df[k] = d.where((d >= 0) & (d <= 25)).astype("float32")
bt = df.groupby("Property_ID")["boil"].sum()
hyb = set(bt[bt > 300].index)
df["date"] = df.Timestamp.dt.strftime("%Y-%m-%d")
w = df[(~df.Property_ID.isin(hyb)) & df.date.isin(DATES)].copy()
w["hh"] = (w.Timestamp.dt.hour * 2 + w.Timestamp.dt.minute // 30).astype(int)
w["kw"] = w["sys"] * 2
# homes with (nearly) complete data on every window day, as the model's window
m = w.pivot_table(index="Property_ID", columns=["date", "hh"], values="kw")
m = m.reindex(columns=pd.MultiIndex.from_product([DATES, range(48)])).dropna(thresh=int(0.95 * 48 * len(DATES))).fillna(0.0)
E = m.values                                                   # (homes, days*48)
def cf(e, n):
    B = e.shape[0]
    if n >= B:
        return float(e.sum(0).max() / e.max(1).sum())
    v = []
    for _ in range(300):
        s = e[rng.choice(B, n, replace=False)]
        v.append(s.sum(0).max() / s.max(1).sum())
    return float(np.mean(v))
R = {"dates": DATES, "homes": int(E.shape[0]), "window_mean_temp_c": round(float(w.External_Air_Temperature.mean()), 2),
     "cf_window": {str(n): round(cf(E, n), 3) for n in GROUPS} | {"all": round(cf(E, E.shape[0]), 3)},
     "indiv_peak_kw_median": round(float(np.median(E.max(1))), 2), "kwh_day": round(float(E.sum(1).mean() / 2 / len(DATES)), 1)}
per = {str(n): [] for n in GROUPS} | {"all": []}
admd, prof = [], []
for i, d in enumerate(DATES):
    e = E[:, i * 48:(i + 1) * 48]
    for n in GROUPS:
        per[str(n)].append(cf(e, n))
    per["all"].append(cf(e, e.shape[0]))
    admd.append(float(e.mean(0).max()))
    prof.append(e.mean(0))
R["cf_perday"] = {k: round(float(np.mean(v)), 3) for k, v in per.items()}
R["admd_kw_by_day"] = [round(a, 3) for a in admd]
R["admd_kw_mean"] = round(float(np.mean(admd)), 3)
R["profile_kw_mean"] = [round(float(v), 3) for v in np.mean(prof, 0)]
R["peak_hh"] = int(np.argmax(np.mean(prof, 0)))
json.dump(R, open("/w/work/eoh_cf_sizes.json", "w"), indent=1)
print(json.dumps(R, indent=1))
