"""EFUS 2011 (UKDS SN 7471, safeguarded): measured heating patterns and room temperatures, weighted aggregates only.
Writes /w/work/efus_results.json. No household-level values leave this script."""
import json
import re

import numpy as np
import pandas as pd

X = "/w/x/UKDA-7471-tab/tab"
hp = pd.read_csv(f"{X}/temperature/temperature_heating_patterns.tab", sep="\t", dtype=str)
tw = pd.read_csv(f"{X}/temperature/temperature_weight.tab", sep="\t")
mr = pd.read_csv(f"{X}/temperature/mean_room_temperatures.tab", sep="\t", na_values=["-99", "-9"])
mh = pd.read_csv(f"{X}/interview/main_heating_derived.tab", sep="\t", na_values=["-99", "-88"])
iw = pd.read_csv(f"{X}/interview/interview_weight.tab", sep="\t")
mf = pd.read_csv(f"{X}/matching_file/matching_file.tab", sep="\t", dtype=str)
hp = hp.merge(tw, on="temperature_id")
W = hp.TemperatureWeight.astype(float).values
months = sorted({re.match(r"([A-Z][a-z]{2})heatingperiod1startWD", c).group(1) for c in hp.columns if re.match(r"([A-Z][a-z]{2})heatingperiod1startWD", c)}, key=lambda m: ["Nov", "Dec", "Jan", "Feb", "Mar"].index(m))
R = {"homes": int(len(hp)), "months": months}

def hhmm(s):
    """'5:20:00' -> hours; '0:00:-9' or missing -> nan."""
    if not isinstance(s, str) or s.endswith("-9") or s.startswith("-"):
        return np.nan
    h, m, _ = s.split(":")
    return int(h) + int(m) / 60

def wq(x, w, q):
    m = np.isfinite(x)
    x, w = x[m], w[m]
    o = np.argsort(x)
    cw = np.cumsum(w[o]) / w[o].sum()
    return float(x[o][np.searchsorted(cw, q)])

def wmean(x, w):
    m = np.isfinite(x)
    return float((x[m] * w[m]).sum() / w[m].sum())

def summ(x, w):
    x = np.asarray(x, float)
    return {"n": int(np.isfinite(x).sum()), "mean": round(wmean(x, w), 2), "p10": round(wq(x, w, .1), 2), "p50": round(wq(x, w, .5), 2), "p90": round(wq(x, w, .9), 2)}

out = {}
for mo in months:
    for day in ("WD", "WE"):
        periods = []
        for k in (1, 2, 3):
            s = hp[f"{mo}heatingperiod{k}start{day}"].map(hhmm).values
            e = hp[f"{mo}heatingperiod{k}end{day}"].map(hhmm).values
            periods.append((s, e))
        has = np.array([[np.isfinite(p[0][i]) for p in periods] for i in range(len(hp))])
        nper = has.sum(1).astype(float)
        hours = np.zeros(len(hp))
        night = np.zeros(len(hp), bool)
        for s, e in periods:
            d = np.where(np.isfinite(s), np.where(e >= s, e - s, e + 24 - s), 0)
            hours += d
            night |= np.isfinite(s) & ((e < s) | (s < 5))        # period crossing midnight or starting before 05:00
        hours[nper == 0] = np.nan
        first = np.nanmin(np.where(has, np.array([p[0] for p in periods]).T, np.nan), axis=1) if has.any() else np.full(len(hp), np.nan)
        s1, e1 = periods[0]
        lr_start = hp[f"{mo}HP1livingroomaverageatstart{day}"].astype(float).replace(-99, np.nan).values
        last_end = np.full(len(hp), np.nan)
        for k in (3, 2, 1):
            v = hp[f"{mo}HP{k}livingroomaverageatend{day}"].astype(float).replace(-99, np.nan).values
            last_end = np.where(np.isnan(last_end), v, last_end)
        bd_start = hp[f"{mo}HP1bedroomaverageatstart{day}"].astype(float).replace(-99, np.nan).values
        key = f"{mo}_{day}"
        valid = nper > 0
        wv = W * valid
        out[key] = {"homes_with_pattern": int(valid.sum()),
                    "periods_share": {str(int(k)): round(float(W[nper == k].sum() / W[valid].sum()), 3) for k in (1, 2, 3)},
                    "hours_heated": summ(hours, W), "share_over_16h": round(float(W[valid & (hours > 16)].sum() / W[valid].sum()), 3),
                    "share_overnight": round(float(W[valid & night].sum() / W[valid].sum()), 3),
                    "first_start_h": summ(first, W), "living_room_at_p1_start_c": summ(lr_start, W),
                    "living_room_at_last_end_c": summ(last_end, W),
                    "overnight_drop_living_k": summ(last_end - lr_start, W), "bedroom_at_p1_start_c": summ(bd_start, W)}
R["patterns"] = out
# winter room temperatures (all days), Dec 2010 to Feb 2011
mr = mr.merge(tw, on="temperature_id")
Wm = mr.TemperatureWeight.astype(float).values
R["mean_room_temps"] = {}
for mo in ("Dec2010", "Jan2011", "Feb2011", "Mar2011"):
    for room in ("Livingroom", "Hallway", "Bedroom"):
        c = f"Alldays{mo}{room}"
        if c in mr:
            R["mean_room_temps"][f"{mo}_{room}"] = summ(mr[c].astype(float).values, Wm)
# interview: heating patterns reported by the full sample
mh = mh.merge(iw, on="interview_id")
Wi = mh.InterviewWeight.astype(float).values
ch = mh.CHpresent == 1
R["interview"] = {"n": int(len(mh)), "ch_share": round(float(Wi[ch].sum() / Wi.sum()), 3)}
for c, lab in (("MainHeatPatWkday", "pattern_wkday"), ("CHcontrol", "ch_control"), ("MainHeatSeasonLgth6x", "season_len"), ("MainHeatAllYear", "all_year"), ("RegularOverride", "override")):
    v = mh[c]
    ok = v.notna() & (v >= 0)
    R["interview"][lab] = {str(int(k)): round(float(Wi[ok & (v == k)].sum() / Wi[ok].sum()), 3) for k in sorted(v[ok].unique())}
for c in ("MainHrsWkday", "MainHrsWkend", "MainHeatTotHrsWkday"):
    v = mh[c].astype(float).values.copy()
    v[v < 0] = np.nan
    R["interview"][c] = summ(v, Wi) | {"share_over_16h": round(float(Wi[np.isfinite(v) & (v > 16)].sum() / Wi[np.isfinite(v)].sum()), 3),
                                        "share_24h": round(float(Wi[np.isfinite(v) & (v >= 23.5)].sum() / Wi[np.isfinite(v)].sum()), 3)}
json.dump(R, open("/w/work/efus_results.json", "w"), indent=1)
print(json.dumps({k: R["patterns"][k] for k in R["patterns"] if k.startswith("Jan")}, indent=0)[:3000])
print(json.dumps(R["interview"], indent=0)[:2500])
