#!/usr/bin/env python3
"""Weather-matched prices, carbon and national demand (review 4, 9 Nov 2026, Tier 1 point 2).

The main runs price 1 Dec 1962 as 1 Dec 2025, so the herd piles into half-hours that were cheap because of 2025-26
weather, and cold still days are paired with 2025-26 carbon. This test instead gives each weather day of a historic
winter the market of the 2016-26 day whose GB mean temperature was nearest, among days of the same type (weekday or
weekend) within 30 days of the same date in the year, so daylight and the seasonal shape of demand stay comparable.

The matched day's Agile (per region), carbon intensity (per region), NESO ND and transmission wind are each scaled
by the ratio of the 2025-26 annual mean to that year's annual mean, so the experiment keeps today's price, carbon and
demand LEVELS and takes from the matched day only how they moved with the weather. Cosy (fixed windows) is left as
in the main runs. 2016-25 Agile is the reconstruction from Elexon MID with today's Agile formula (gb_v3_prices.py).

GB mean temperature = the town-weighted mean of the towns' daily means (towns weight their region's gas-heated homes
equally, as analysis.py). Days of the historic winter colder than any pool day take the coldest candidate; their
share is reported.

Writes <out>/<Y>/ for each weather year: prices_year.json, carbon_year.json, base_demand.json and wind.json keyed by
the 2025-26 calendar day the model reads (gbmodel.data.price_day), every other input symlinked from --data; and
<out>/<Y>/wmatch.json with the mapping and diagnostics. Run on the Spark in the model container:
    python gb_wmatch.py --data /work/data/gb --out /work/data/gb_wm --years 1962,2025,...
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gb_sdp_phi import ARG, price_day  # noqa: E402

D, OUT = ARG("--data", "/work/data/gb"), ARG("--out", "/work/data/gb_wm")
POOL = range(2016, 2026)                                 # heating years 2016-17 .. 2025-26
WINDOW = 30
REWRITE = ("prices_year.json", "carbon_year.json", "base_demand.json", "wind.json")


def ydates(y):
    n = int((np.datetime64(f"{y + 1}-11-01") - np.datetime64(f"{y}-11-01")) / np.timedelta64(1, "D"))
    return [str(np.datetime64(f"{y}-11-01") + np.timedelta64(i, "D")) for i in range(n)]


def town_weights():
    G = json.load(open(f"{D}/towns.json"))
    W = json.load(open(f"{D}/region_weights.json"))["homes"]
    reg = {t[0]: t[3] for t in G["towns"]}
    per = {}
    for r in reg.values():
        per[r] = per.get(r, 0) + 1
    return {t: W[r] / per[r] for t, r in reg.items()}


def national_daily(y, H, TW):
    """{date: GB mean temperature} for heating year y (2025 from weather_year.json, else history.npz)."""
    if y == 2025:
        Wy = json.load(open(f"{D}/weather_year.json"))
        towns = {n: {k: v for k, v in s.items() if v is not None} for n, s in Wy.items()}
    else:
        t0 = np.datetime64(str(H["start"]))
        a, b = np.datetime64(f"{y}-11-01T00:00"), np.datetime64(f"{y + 1}-11-01T00:00")
        i0, i1 = int((a - t0) / np.timedelta64(1, "h")), int((b - t0) / np.timedelta64(1, "h"))
        stamps = [str(x)[:16] for x in np.arange(a, b, np.timedelta64(1, "h"))]
        towns = {str(n): {k: v / 10 for k, v in zip(stamps, H["t"][ti, i0:i1].tolist()) if v != -32768}
                 for ti, n in enumerate(H["towns"])}
    out = {}
    for d in ydates(y):
        num = den = 0.0
        for n, s in towns.items():
            if n not in TW:
                continue
            v = [s[f"{d}T{h:02d}:00"] for h in range(24) if f"{d}T{h:02d}:00" in s]
            if len(v) >= 20:
                num += TW[n] * float(np.mean(v))
                den += TW[n]
        out[d] = num / den if den else np.nan
    return out


def pool_files(y):
    base = D if y == 2025 else f"{D}/years/{y}"
    P = json.load(open(f"{base}/prices_year.json"))
    C = json.load(open(f"{base}/carbon_year.json"))
    S = json.load(open(f"{base}/base_demand.json"))["series"]
    return P, C, S


def slots(d):
    return [f"{d}T{s // 2:02d}:{30 * (s % 2):02d}Z" for s in range(48)]


def main():
    H = np.load(f"{D}/history.npz")
    TW = town_weights()
    Wind = json.load(open(f"{D}/wind.json"))["series"]
    cur = {k: json.load(open(f"{D}/{k}")) for k in REWRITE}
    regs = sorted(json.load(open(f"{D}/towns.json"))["regions"])

    def ymean(series, keys):
        v = [series[k] for k in keys if k in series and series[k] is not None]
        return float(np.mean(v)) if v else np.nan

    # the pool: every 2016-26 day with its GB temperature, day type, day of year, and scale factors to 2025-26 levels
    pool, files, scale = [], {}, {}
    k25 = [k for d in ydates(2025) for k in slots(d)]
    for y in POOL:
        P, C, S = pool_files(y)
        files[y] = (P, C, S)
        ky = [k for d in ydates(y) for k in slots(d)]
        sc = {"nd": ymean(cur["base_demand.json"]["series"], k25) / ymean(S, ky),
              "wind": ymean(Wind, k25) / ymean(Wind, ky)}
        for r in regs:
            sc[f"agile_{r}"] = ymean(cur["prices_year.json"][f"agile_{r}"], k25) / ymean(P[f"agile_{r}"], ky)
            sc[f"c_{r}"] = ymean(cur["carbon_year.json"][r], k25) / ymean(C[r], ky)
        scale[y] = sc
        for d, t in national_daily(y, H, TW).items():
            if not np.isnan(t):
                dt = np.datetime64(d)
                pool.append((y, d, t, int(((dt - np.datetime64("1970-01-05")).astype(int) % 7) >= 5),
                             int((dt - np.datetime64(d[:4] + "-01-01")).astype(int))))
    print(len(pool), "pool days", flush=True)
    pt = np.array([p[2] for p in pool])
    pw = np.array([p[3] for p in pool])
    pd_ = np.array([p[4] for p in pool])

    for Y in [int(x) for x in ARG("--years", "1962").split(",")]:
        o = f"{OUT}/{Y}"
        os.makedirs(o, exist_ok=True)
        for n in os.listdir(D):
            if n not in REWRITE and not os.path.lexists(f"{o}/{n}"):
                os.symlink(os.path.abspath(f"{D}/{n}"), f"{o}/{n}")
        new = {k: json.loads(json.dumps(v)) for k, v in cur.items()}
        Tn = national_daily(Y, H, TW)
        mapping, gaps, colder = {}, [], 0
        for d in ydates(Y):
            dt = np.datetime64(d)
            we = int(((dt - np.datetime64("1970-01-05")).astype(int) % 7) >= 5)
            doy = int((dt - np.datetime64(d[:4] + "-01-01")).astype(int))
            dd = np.abs(pd_ - doy)
            ok = (pw == we) & (np.minimum(dd, 365 - dd) <= WINDOW)
            if np.isnan(Tn[d]) or not ok.any():
                gaps.append(d)
                continue
            i = np.where(ok)[0][np.argmin(np.abs(pt[ok] - Tn[d]))]
            colder += int(Tn[d] < pt[ok].min())
            y, pdte = pool[i][0], pool[i][1]
            mapping[d] = {"pool_year": y, "pool_date": pdte, "t_weather": round(Tn[d], 2), "t_pool": round(pt[i], 2)}
            P, C, S = files[y]
            tgt = price_day(d)
            for s_t, s_p in zip(slots(tgt), slots(pdte)):
                if s_p in S:
                    new["base_demand.json"]["series"][s_t] = S[s_p] * scale[y]["nd"]
                if s_p in Wind:
                    new["wind.json"]["series"][s_t] = Wind[s_p] * scale[y]["wind"]
                for r in regs:
                    a = P[f"agile_{r}"].get(s_p)
                    if a is not None:
                        new["prices_year.json"][f"agile_{r}"][s_t] = round(min(a * scale[y][f"agile_{r}"], 100.0), 3)
                    c = C[r].get(s_p)
                    if c is not None:
                        new["carbon_year.json"][r][s_t] = c * scale[y][f"c_{r}"]
        for k, v in new.items():
            json.dump(v, open(f"{o}/{k}", "w"))
        tw = np.array([m["t_weather"] for m in mapping.values()])
        tp = np.array([m["t_pool"] for m in mapping.values()])
        diag = {"year": Y, "days": len(mapping), "gaps": gaps, "colder_than_pool": colder,
                "abs_temp_err_mean": round(float(np.abs(tw - tp).mean()), 2),
                "coldest_weather_c": round(float(tw.min()), 1), "coldest_matched_c": round(float(tp.min()), 1),
                "pool_years_used": {str(y): sum(m["pool_year"] == y for m in mapping.values()) for y in POOL},
                "scale": {str(y): {k: round(v, 3) for k, v in scale[y].items() if k in ("nd", "wind", "agile_H", "c_H")}
                          for y in POOL},
                "mapping": mapping}
        json.dump(diag, open(f"{o}/wmatch.json", "w"), indent=1)
        print(Y, {k: diag[k] for k in ("days", "colder_than_pool", "abs_temp_err_mean", "coldest_weather_c",
                                       "coldest_matched_c")}, diag["pool_years_used"], flush=True)


if __name__ == "__main__":
    main()
