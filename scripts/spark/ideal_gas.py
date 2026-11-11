#!/usr/bin/env python3
"""Measured diversity of gas heating in IDEAL homes (review, 9 Nov 2026, P0: validate household timing diversity).

IDEAL (Pullinger et al. 2021, Scientific Data 8:146; Edinburgh DataShare doi 10.7488/ds/2836, CC BY 4.0): 255 homes
in Edinburgh and the Lothians, 2016-18, gas meter pulses (Wh per reading), boiler pipe temperatures (0.1 C) and an
Edinburgh outdoor temperature feed (0.1 C). Gas boilers are the stock the hybrid would join, so their measured
half-hourly diversity is a direct check on the model's heat demand timing, independent of heat pumps.

Per home: gas summed to UTC half-hours (kWh). A reading carrying more than 4 pulses is a gap being reconciled
(the meter count is kept, the timing is lost): that home-day is dropped. A home-day is valid if it lies inside the
home's monitoring period, its gas sensor reported at least once and no gap was reconciled. Central heating is ON in a
half-hour if the CH flow pipe's maximum exceeds 35 C there (hot-water-only use on a combi does not heat the CH flow).

Outputs (JSON): the cold-day window chosen as Freedom chose theirs (days with a sub-zero Edinburgh temperature,
homes valid on every day of the window); coincidence factor (Sun et al. 2019, eq. 3: coincident peak over the sum of
individual peaks, across the window) for random groups of n homes, for all gas and for gas in CH-on half-hours;
mean profile per home; heating habits (share of homes heating overnight, morning start, evening end).
    python ideal_gas.py --root ~/ideal/hs/sensordata --meta ~/ideal/meta/metadata --out ideal_gas.json
"""
import glob
import json
import os
import re
import sys

import numpy as np
import pandas as pd


def ARG(k, d):
    return sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d


ROOT, META = ARG("--root", ""), ARG("--meta", "")
WINDOW = int(ARG("--window", "11"))
GROUPS = [1, 2, 5, 10, 20, 34, 50, 100]
DRAWS = 200


def gas_home(path):
    g = pd.read_csv(path, header=None, names=["t", "wh"], parse_dates=["t"])
    if g.empty:
        return None, None
    pulse = g["wh"].mode().iloc[0]
    g["hh"] = g["t"].dt.floor("30min")
    gap_days = set(g.loc[g["wh"] > 4 * pulse, "hh"].dt.normalize())
    s = g.groupby("hh")["wh"].sum() / 1000.0
    return s, gap_days


def flow_home(path):
    f = pd.read_csv(path, header=None, names=["t", "v"], parse_dates=["t"])
    f["hh"] = f["t"].dt.floor("30min")
    return f.groupby("hh")["v"].max() / 10.0


def main():
    homes = pd.read_csv(f"{META}/home.csv", encoding="utf-8-sig")
    homes["start"] = pd.to_datetime(homes["starttime"], dayfirst=True)
    homes["end"] = pd.to_datetime(homes["endtime"], dayfirst=True)
    w = pd.read_csv(f"{ROOT}/weatherreading.csv.gz", dtype={"value": str})
    w = w[w["feedid"] == 1]
    w["t"] = pd.to_datetime(w["time"])
    w["c"] = pd.to_numeric(w["value"], errors="coerce") / 10.0
    tday = w.groupby(w["t"].dt.normalize())["c"].agg(["min", "mean"])

    G, F, valid = {}, {}, {}
    for p in sorted(glob.glob(f"{ROOT}/*gas-pulse_gas.csv.gz")):
        hid = int(re.match(r"home(\d+)_", os.path.basename(p)).group(1))
        s, gaps = gas_home(p)
        if s is None:
            continue
        h = homes[homes["homeid"] == hid].iloc[0]
        days = pd.date_range(h["start"].normalize() + pd.Timedelta(days=1), h["end"].normalize() - pd.Timedelta(days=1))
        idx = pd.date_range(days.min(), days.max() + pd.Timedelta(hours=23, minutes=30), freq="30min") if len(days) else None
        if idx is None:
            continue
        s = s.reindex(idx, fill_value=0.0)
        rep = s.groupby(s.index.normalize()).size()          # every day has 48 slots after reindex
        seen = set(pd.Series(1, index=s[s > 0].index).index.normalize())
        valid[hid] = {d for d in days if d in seen and d not in gaps}
        G[hid] = s
        fp = glob.glob(f"{ROOT}/home{hid}_*central-heating-flow.csv.gz")
        if fp:
            F[hid] = flow_home(fp[0]).reindex(idx)
        del rep
    print(f"{len(G)} homes with gas; {len(F)} with CH flow", flush=True)

    # cold days: at least one sub-zero reading (Freedom's rule); window = the WINDOW such days with most homes valid on all
    cold = [d for d in tday.index if tday.loc[d, "min"] < 0 and d.month in (11, 12, 1, 2, 3)]
    win, alive = [], set(valid)                              # greedy: add the cold day that keeps most homes
    while len(win) < WINDOW:
        d = max((d for d in cold if d not in win), key=lambda d: sum(d in valid[h] for h in alive))
        win.append(d)
        alive = {h for h in alive if d in valid[h]}
    best = (sorted(win), sorted(alive))
    win, hs = best
    print(f"window {len(win)} days, {len(hs)} homes valid on all", flush=True)
    sl = pd.DatetimeIndex(np.concatenate([pd.date_range(d, d + pd.Timedelta(hours=23, minutes=30), freq="30min") for d in win]))
    X = np.array([G[h].reindex(sl).fillna(0).values * 2 for h in hs])      # kW
    ch = np.array([(F[h].reindex(sl).values > 35).astype(float) if h in F else np.full(len(sl), np.nan) for h in hs])
    Xch = np.where(np.isnan(ch), np.nan, X * ch)
    rng = np.random.default_rng(9112026)

    def cf(M):
        M = M[~np.isnan(M).any(1)]
        out = {}
        for n in GROUPS:
            if n > len(M):
                continue
            v = []
            for _ in range(DRAWS if n < len(M) else 1):
                g = rng.choice(len(M), n, replace=False)
                v.append(M[g].sum(0).max() / max(M[g].max(1).sum(), 1e-9))
            out[n] = {"mean": round(float(np.mean(v)), 3), "p5": round(float(np.percentile(v, 5)), 3),
                      "p95": round(float(np.percentile(v, 95)), 3)}
        out["all"] = {"n": int(len(M)), "cf": round(float(M.sum(0).max() / M.max(1).sum()), 3)}
        return out

    # habits on the window days (CH flow), local clock = UTC in winter
    on = ch.reshape(len(hs), len(win), 48)
    night = np.nanmean(on[:, :, 2:10], axis=(1, 2))           # 01:00-05:00
    first = [int(np.argmax(r[10:] > 0)) + 10 if (r[10:] > 0).any() else None for r in np.nanmean(on, 1)]
    R = {"source": "IDEAL (Pullinger et al. 2021), doi 10.7488/ds/2836, CC BY 4.0",
         "window_days": [str(d.date()) for d in win], "window_tmin_c": [float(tday.loc[d, "min"]) for d in win],
         "window_tmean_c": round(float(np.mean([tday.loc[d, "mean"] for d in win])), 1),
         "homes": len(hs), "homes_with_ch_flow": int((~np.isnan(ch).any(1)).sum()),
         "cf_gas": cf(X), "cf_gas_ch": cf(Xch),
         "profile_kw": [round(float(v), 3) for v in X.reshape(len(hs), len(win), 48).mean((0, 1))],
         "ch_on_share_by_hh": [round(float(v), 3) for v in np.nanmean(on, axis=(0, 1))],
         "share_heating_overnight": round(float(np.nanmean(night > 0.5)), 3),
         "gas_kwh_day_mean": round(float(X.sum(1).mean() / 2 / len(win)), 1),
         "indiv_peak_kw_median": round(float(np.median(X.max(1))), 1),
         "first_on_after_0500_median_slot": float(np.median([f for f in first if f is not None])) if any(first) else None}
    # schedule library for the model (gbmodel/diversity.py): every valid winter home-day with a CH flow probe and a
    # daily mean below 8 C, as a 48-slot on/off pattern, grouped by home so a model home can keep one real home's habits
    lib, owner = [], []
    for h in sorted(F):
        if h not in valid:
            continue
        on_h = (F[h] > 35)
        for d in sorted(valid[h]):
            if d.month not in (11, 12, 1, 2, 3) or d not in tday.index or not tday.loc[d, "mean"] < 8:
                continue
            v = F[h].reindex(pd.date_range(d, d + pd.Timedelta(hours=23, minutes=30), freq="30min"))
            if v.isna().sum() > 6:                                # Freedom's rule: at least 41 of 48 half-hours
                continue
            lib.append(on_h.reindex(v.index).fillna(False).values.astype(bool))
            owner.append(h)
    lib, owner = np.array(lib), np.array(owner)
    np.savez_compressed(ARG("--lib", "ideal_schedules.npz"), on=lib, home=owner)
    R["library"] = {"home_days": int(len(lib)), "homes": int(len(set(owner.tolist()))),
                    "on_share_by_hh": [round(float(v), 3) for v in lib.mean(0)],
                    "share_homes_mostly_overnight": round(float(np.mean([lib[owner == h][:, 2:10].mean() > 0.5
                                                                         for h in set(owner.tolist())])), 3)}
    print("library", R["library"]["home_days"], "home-days from", R["library"]["homes"], "homes; overnight share",
          R["library"]["share_homes_mostly_overnight"], flush=True)
    json.dump(R, open(ARG("--out", "ideal_gas.json"), "w"), indent=1)
    print(json.dumps({k: R[k] for k in ("window_tmean_c", "homes", "homes_with_ch_flow", "share_heating_overnight",
                                         "gas_kwh_day_mean", "indiv_peak_kw_median")}))
    print("CF gas", {k: v for k, v in R["cf_gas"].items()})
    print("CF gas CH-on", {k: v for k, v in R["cf_gas_ch"].items()})


if __name__ == "__main__":
    main()
