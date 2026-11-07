#!/usr/bin/env python3
"""What can a home sell to a flexibility market? DFS-style events with the P376 BL01 baseline, per controller.

    .venv/bin/python scripts/article/flex_events.py [--src data/model/v21] [--events 30]

Events: each heating year, the EVENTS one-hour windows (two half-hours) with the highest GB national demand (NESO ND,
the price-year calendar), on working days (Mon-Fri of the 2025-26 calendar day) between November and March, at
most one per day. Baseline (P376 BL01, no in-day adjustment, docs/article/lit/flex_markets.json): the mean of the same
half-hour over the 10 most recent non-event working days within the previous 60 days.
Delivery in an event:
  hybrids (biv*, ccop*, sdp)  the heat pump stops and the boiler carries the heat: event load 0
  all heat pump               EQUINOX trial: 0.6 kW mean turn-down, 48% of load (NGED2024) -> load x 0.52
  all gas                     nothing to sell
Paid turn-down = max(baseline - event load, 0), at GBP 152/MWh (DFS Q4 2025 mean), 210 (2024/25 mean), 500 (2026 GAP).
Fuel cost of a hybrid's event: the heat the heat pump would have made, from gas at GAS_P/0.9, less the electricity
saved at that half-hour's tariff price (2025-26); heat = elec x COP with COP from the stock curve at the region's outdoor temperature (level 0.86, weather-
compensated flow, design -3 C) -- an approximation, stated in the paper. All-heat-pump turn-down costs no fuel.
Per home = GB home-weighted mean (regional gas meters). Writes docs/article/results/flex_events.csv and adds
FLEX_* numbers to docs/article/results/numbers_results.json.
"""
import csv
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / (sys.argv[sys.argv.index("--src") + 1] if "--src" in sys.argv else "data/model/v21")
GB = ROOT / "data" / "model" / "gb"
OUT = ROOT / "docs" / "article" / "results"
EVENTS = int(sys.argv[sys.argv.index("--events") + 1]) if "--events" in sys.argv else 30
PRICES = {"p152": 152, "p210": 210, "p500": 500}
GAS_P, SVR_P, IOG = 8.17, 26.47, (6.6, 35.61)
_P = {}


def tariff_price(t, reg, pday, slot):
    """p/kWh the home would have paid for the electricity it no longer uses in that half-hour (2025-26 rates)."""
    if t == "svr":
        return SVR_P
    if t == "iog":
        return IOG[0] if (slot >= 47 or slot < 11) else IOG[1]
    if not _P:
        _P.update(json.load(open(GB / "prices_year.json")))
    return _P[f"{t}_{reg}"].get(f"{pday}T{slot // 2:02d}:{30 * (slot % 2):02d}Z", SVR_P)
SHARE_T = [-3.0, 1.5, 4.5, 7.5, 10.5, 14.0]
SHARE = [0.3415, 0.3506, 0.3628, 0.3620, 0.3434, 0.3124]


def price_day(d):
    md = d[5:] if d[5:] != "02-29" else "02-28"
    return ("2025-" if md >= "11" else "2026-") + md


def stock_cop(t):
    flow = np.clip(25 + (47.5 - 25) * (16 - t) / (16 + 3), 25, 52.5)
    return np.clip(0.86 * np.interp(t, SHARE_T, SHARE) * (flow + 273.15) / np.maximum(flow - t, 5), 1.3, 7)


_H = {}


def HIST():
    """history.npz, loaded once (57 MB compressed; reloading it per year dominated the run time)."""
    if not _H:
        z = np.load(GB / "history.npz")
        _H.update(t=z["t"], start=str(z["start"]), towns=z["towns"])
    return _H


def region_temps(year, dates, regs):
    """(days, R, 48) mean outdoor temperature of each region's towns, half-hourly."""
    G = json.load(open(GB / "towns.json"))
    reg = {t[0]: t[3] for t in G["towns"]}
    if year <= 2024:
        h = HIST()
        t0 = np.datetime64(str(h["start"]))
        i0 = int((np.datetime64(f"{year}-11-01T00:00") - t0) / np.timedelta64(1, "h"))
        n = len(dates) * 24
        hourly = {str(nm): h["t"][i, i0:i0 + n + 1].astype(float) / 10 for i, nm in enumerate(h["towns"])}
    else:
        W = json.load(open(GB / "weather_year.json"))
        hourly = {nm: np.array([v if v is not None else np.nan for _, v in sorted(s.items())] + [np.nan]) for nm, s in W.items()}
    out = np.zeros((len(dates), len(regs), 48))
    for ri, r in enumerate(regs):
        ts = [hourly[n] for n in hourly if reg.get(n) == r]
        m = np.nanmean(np.stack([x[:len(dates) * 24 + 1] for x in ts]), 0)
        m = np.where(np.isnan(m), np.nanmean(m), m)
        half = np.interp(np.arange(len(dates) * 48) / 2, np.arange(len(m)), m)
        out[:, ri, :] = half.reshape(len(dates), 48)
    return out


def year_events(year, base):
    f = np.load(SRC / str(year) / "flex_region.npz")
    regs, tar, ctrl = list(f["regions"]), list(f["tariffs"]), list(f["ctrl"])
    dates = [str(d) for d in f["dates"]]
    W = json.load(open(GB / "region_weights.json"))["homes"]
    w = np.array([W[r] for r in regs], float)
    w /= w.sum()
    e = f["e"].astype(np.float64)                                        # (R, day, T, C, 48) kWh per home
    pdays = [price_day(d) for d in dates]
    wk = np.array([dt.date.fromisoformat(p).weekday() < 5 for p in pdays])
    season = np.array([d[5:7] in ("11", "12", "01", "02", "03") for d in dates])
    nd = np.array([[base[f"{p}T{s // 2:02d}:{30 * (s % 2):02d}Z"] for s in range(48)] for p in pdays])
    hour = nd[:, 0::2] + nd[:, 1::2]                                     # (day, 24) one-hour windows on the hour
    cand = [(hour[d, h], d, h) for d in range(len(dates)) if wk[d] and season[d] for h in range(24)]
    cand.sort(reverse=True)
    ev, used = [], set()
    for _, d, h in cand:
        if d not in used:
            ev.append((d, h))
            used.add(d)
        if len(ev) == EVENTS:
            break
    evdays = {d for d, _ in ev}
    temps = region_temps(year, dates, regs)
    cop = stock_cop(temps)                                               # (day, R, 48)
    rows = []
    for ti, t in enumerate(tar):
        for ci, c in enumerate(ctrl):
            if c == "gas":
                continue
            paid = fuel = 0.0
            for d, h in ev:
                prev = [x for x in range(d - 1, max(-1, d - 61), -1) if wk[x] and x not in evdays][:10]
                for s in (2 * h, 2 * h + 1):
                    load = e[:, d, ti, ci, s]                            # (R,)
                    bl = e[:, prev, ti, ci, s].mean(1) if prev else load
                    ev_load = load * 0.52 if c == "hp" else np.zeros_like(load)
                    paid += float((np.maximum(bl - ev_load, 0) * w).sum())
                    if c != "hp":                                                  # net fuel-switch cost, GBP
                        heat = load * cop[d, :, s]
                        pe = np.array([tariff_price(t, r, pdays[d], s) for r in regs])
                        fuel += float(((heat * GAS_P / 0.9 - load * pe) / 100 * w).sum())
            row = {"year": year, "tariff": t, "ctrl": c, "events": len(ev), "paid_kwh_home": round(paid, 4),
                   "fuel_gbp_home": round(fuel, 3)}
            for k, p in PRICES.items():
                row[f"gross_gbp_{k}"] = round(paid * p / 1000, 3)
            rows.append(row)
    return rows


def main():
    years = sorted(int(p.parent.name) for p in SRC.glob("*/flex_region.npz"))
    base = json.load(open(GB / "base_demand.json"))["series"]
    rows = [r for y in years for r in year_events(y, base)]
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "flex_events.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    R = json.load(open(OUT / "numbers_results.json")) if (OUT / "numbers_results.json").exists() else {}
    for t in ("svr", "agile", "cosy", "iog"):
        for c in ("hp", "biv0", "ccop", "sdp"):
            sel = [r for r in rows if r["tariff"] == t and r["ctrl"] == c]
            if not sel:
                continue
            T, C = t.upper(), c.upper()
            R[f"FLEX_KWH_{C}_{T}"] = f"{np.mean([r['paid_kwh_home'] for r in sel]):.1f}"
            R[f"FLEX_GBP210_{C}_{T}"] = f"{np.mean([r['gross_gbp_p210'] for r in sel]):.2f}"
            R[f"FLEX_GBP500_{C}_{T}"] = f"{np.mean([r['gross_gbp_p500'] for r in sel]):.2f}"
            R[f"FLEX_FUEL_{C}_{T}"] = f"{np.mean([r['fuel_gbp_home'] for r in sel]):.2f}"
    R["FLEX_EVENTS"] = str(EVENTS)
    json.dump(dict(sorted(R.items())), open(OUT / "numbers_results.json", "w"), indent=1, ensure_ascii=False)
    print(f"{len(years)} years, {len(rows)} rows -> results/flex_events.csv")
    for t in ("svr", "agile"):
        print(t, {c: (R.get(f"FLEX_KWH_{c.upper()}_{t.upper()}"), R.get(f"FLEX_GBP210_{c.upper()}_{t.upper()}"),
                      R.get(f"FLEX_FUEL_{c.upper()}_{t.upper()}")) for c in ("hp", "biv0", "ccop", "sdp")})


if __name__ == "__main__":
    main()
