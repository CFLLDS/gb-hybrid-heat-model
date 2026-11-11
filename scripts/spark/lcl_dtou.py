#!/usr/bin/env python3
"""How real households herd on a dynamic price: the Low Carbon London dynamic time-of-use trial (review, 9 Nov 2026).

Data: UK Power Networks, SmartMeter Energy Consumption Data in London Households (London Datastore, CC BY 4.0):
half-hourly electricity for 5,567 homes, Nov 2011 - Feb 2014; in 2013 about 1,100 of them ("ToU") were given
day-ahead High (67.20p), Low (3.99p) and Normal (11.76p) prices by in-home display or text, the rest ("Std") stayed
on a flat 14.228p. Tariffs.xlsx gives the 2013 schedule. The response is MANUAL (people acting on a displayed price),
not automated control, so this measures the behavioural baseline, not the model's automated herd.

Steps:
  1. Stream the 8.5 GB CSV; keep 2012-2013; per home a half-hourly series (kWh -> kW).
  2. Group means per half-hour, ToU and Std, and the difference in differences: (ToU - Std) in 2013 minus the same
     half-hour-of-week mean of (ToU - Std) in 2012 (before the trial), so standing differences between the groups
     cancel.
  3. Event study around the start of every Low and High period: mean DiD response (W per home and % of the ToU
     group's own pre-trial level) from 4 h before to 6 h after the price change.
  4. Synchronisation: the share of ToU homes whose demand in the first Low half-hour is above their own mean of the
     two half-hours before it, against the same for Std homes; and the group coincidence factor (Sun et al. 2019
     eq. 3) of ToU homes over Low-price days against matched Normal days.
    python lcl_dtou.py --csv LCL-FullData.zip --tariffs Tariffs.xlsx --out lcl_dtou.json
"""
import io
import json
import sys
import zipfile

import numpy as np
import pandas as pd


def ARG(k, d):
    return sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d


T0 = pd.Timestamp("2012-01-01")
NSLOT = 2 * 48 * 366                                   # 2012 (leap) .. 2013 at 30 min: 731 days


def load(path):
    ids, rows = {}, []
    tou = {}
    # the published zip uses Deflate64, which Python's zipfile cannot read: pass the extracted CSV (unzip it first)
    with (open(path, "rb") if path.endswith(".csv") else zipfile.ZipFile(path).open(
            [n for n in zipfile.ZipFile(path).namelist() if n.endswith(".csv")][0])) as fh:
        for ch in pd.read_csv(io.TextIOWrapper(fh), chunksize=10_000_000, header=0,
                              names=["id", "grp", "t", "kwh"], dtype={"id": str, "grp": str, "t": str, "kwh": str}):
            ch = ch[ch["t"].str[:4].isin(["2012", "2013"])]
            if ch.empty:
                continue
            t = pd.to_datetime(ch["t"].str[:19], format="%Y-%m-%d %H:%M:%S")
            k = pd.to_numeric(ch["kwh"].str.strip(), errors="coerce").astype("float32")
            slot = ((t - T0).dt.total_seconds() // 1800).astype("int32")
            for i, g in zip(ch["id"].unique(), ch.drop_duplicates("id")["grp"]):
                if i not in ids:
                    ids[i] = len(ids)
                    tou[i] = g.strip()
            rows.append(pd.DataFrame({"h": ch["id"].map(ids).astype("int32"), "s": slot, "k": k}))
            print("chunk", len(ids), "homes", flush=True)
    df = pd.concat(rows, ignore_index=True)
    X = np.full((len(ids), NSLOT), np.nan, dtype="float32")
    ok = (df["s"] >= 0) & (df["s"] < NSLOT)
    X[df["h"][ok].values, df["s"][ok].values] = df["k"][ok].values * 2          # kW
    grp = np.array([tou[i] for i in sorted(ids, key=ids.get)])
    return X, grp


def tariffs(path):
    t = pd.read_excel(path)
    t.columns = [c.strip() for c in t.columns]
    tc = [c for c in t.columns if "date" in c.lower() or "time" in c.lower()][0]
    vc = [c for c in t.columns if c != tc][0]
    t[tc] = pd.to_datetime(t[tc])
    s = ((t[tc] - T0).dt.total_seconds() // 1800).astype(int).values
    lab = np.full(NSLOT, "", dtype=object)
    lab[s[(s >= 0) & (s < NSLOT)]] = t[vc].astype(str).str.strip().values[(s >= 0) & (s < NSLOT)]
    return lab


def coincidence(M):
    M = M[~np.isnan(M).any(1)]
    return float(M.sum(0).max() / M.max(1).sum()) if len(M) else float("nan"), int(len(M))


def main():
    X, grp = load(ARG("--csv", "LCL-FullData.zip"))
    lab = tariffs(ARG("--tariffs", "Tariffs.xlsx"))
    tu, sd = grp == "ToU", grp == "Std"
    y13 = np.arange(NSLOT) >= 2 * 48 * 366 // 2 * 0 + 48 * 366                 # slots from 2013-01-01
    cover = (~np.isnan(X)).mean(1)
    keep = cover > 0.8                                                     # homes with >80% of 2012-13 present
    mt = np.nanmean(X[tu & keep], 0)
    ms = np.nanmean(X[sd & keep], 0)
    d = mt - ms
    # half-hour-of-week baseline of (ToU - Std) in 2012
    dow = ((np.arange(NSLOT) // 48) + T0.dayofweek) % 7
    how = dow * 48 + np.arange(NSLOT) % 48
    pre = ~y13
    base = np.array([np.nanmean(d[pre & (how == k)]) for k in range(7 * 48)])
    did = d - base[how]
    lvl = np.array([np.nanmean(mt[pre & (how == k)]) for k in range(7 * 48)])[how]
    R = {"source": "UK Power Networks, Low Carbon London smart meter data (London Datastore, CC BY 4.0)",
         "homes": {"tou": int((tu & keep).sum()), "std": int((sd & keep).sum()), "all": int(len(grp))},
         "tariff_counts": {k: int((lab[y13] == k).sum()) for k in ("High", "Low", "Normal")}}
    # event study at the start of each Low / High period
    for kind in ("Low", "High"):
        starts = [i for i in range(1, NSLOT) if lab[i] == kind and lab[i - 1] != kind]
        win = np.arange(-8, 13)
        ev = np.array([did[s + win] for s in starts if s - 8 >= 0 and s + 12 < NSLOT])
        evp = np.array([100 * did[s + win] / lvl[s + win] for s in starts if s - 8 >= 0 and s + 12 < NSLOT])
        lens = []
        for s in starts:
            n = 0
            while s + n < NSLOT and lab[s + n] == kind:
                n += 1
            lens.append(n)
        inside = np.array([np.nanmean(did[s:s + n]) for s, n in zip(starts, lens)])
        insidep = np.array([np.nanmean(100 * did[s:s + n] / lvl[s:s + n]) for s, n in zip(starts, lens)])
        # synchronisation: share of homes up (Low) or down (High) at the first half-hour vs their previous hour
        sgn = 1 if kind == "Low" else -1
        def share(mask):
            v = []
            for s in starts:
                a, b = X[mask, s], np.nanmean(X[mask][:, s - 2:s], 1)
                ok = ~np.isnan(a) & ~np.isnan(b)
                v.append(np.mean(sgn * (a[ok] - b[ok]) > 0.05))
            return float(np.mean(v))
        R[kind] = {"events": len(starts), "median_length_hh": float(np.median(lens)),
                   "did_w_by_slot": [round(1000 * float(np.nanmean(ev[:, j])), 1) for j in range(len(win))],
                   "did_pct_by_slot": [round(float(np.nanmean(evp[:, j])), 2) for j in range(len(win))],
                   "did_w_inside_mean": round(1000 * float(np.nanmean(inside)), 1),
                   "did_pct_inside_mean": round(float(np.nanmean(insidep)), 2),
                   "share_responding_tou": round(share(tu & keep), 3), "share_responding_std": round(share(sd & keep), 3)}
        print(kind, {k: v for k, v in R[kind].items() if "by_slot" not in k}, flush=True)
    # coincidence of ToU homes on days with a Low period vs days all Normal (2013, Nov-Mar)
    days13 = [(i // 48) for i in range(48 * 366, NSLOT, 48)]
    lowday = [d for d in days13 if (lab[d * 48:(d + 1) * 48] == "Low").any()]
    normday = [d for d in days13 if (lab[d * 48:(d + 1) * 48] == "Normal").all()]
    rng = np.random.default_rng(9112026)
    for name, dd in (("low_days", lowday), ("normal_days", normday)):
        cf = []
        for _ in range(100):
            ds = rng.choice(dd, min(11, len(dd)), replace=False)
            sl = np.concatenate([np.arange(d * 48, (d + 1) * 48) for d in ds])
            hs = rng.choice(np.where(tu & keep)[0], 34, replace=False)
            cf.append(coincidence(X[np.ix_(hs, sl)])[0])
        R[f"cf34_tou_{name}"] = round(float(np.nanmean(cf)), 3)
    R["profile_low_vs_normal"] = None
    print({k: R[k] for k in R if k.startswith("cf34") or k in ("homes", "tariff_counts")}, flush=True)
    json.dump(R, open(ARG("--out", "lcl_dtou.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
