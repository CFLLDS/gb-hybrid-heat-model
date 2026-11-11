#!/usr/bin/env python3
"""Every weather year Open-Meteo has, for the GB map (Craig 7 Nov 2026: "take it back 10 years or however long
openmeteo history goes back").

ERA5 starts 1 Jan 1940, so the first full heating year is 1 Nov 1940 - 31 Oct 1941. For each of the 79 towns this
fetches hourly temperature_2m from 1940-11-01 to 2025-10-31 (Open-Meteo archive; the paid customer host if
state/openmeteo.key exists, never printed, else the free host) and stores it as tenths of a degree, int16, in data/model/gb/history.npz:
    t      (79, hours) int16, tenths of C, -32768 = missing
    start  "1940-11-01T00:00" (GMT), towns  names in towns.json order
The model reads one heating year at a time: gb_map.py --year --weather 1962 (1 Nov 1962 - 31 Oct 1963).
Resumable: towns already in data/model/gb/history_parts/ are skipped.
    .venv/bin/python scripts/spark/gb_history_data.py
"""
import datetime as dt
import json
import os
import time

import numpy as np
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
G = os.path.join(ROOT, "data", "model", "gb")
PARTS = os.path.join(G, "history_parts")
START, END = dt.date(1940, 11, 1), dt.date(2025, 10, 31)
HOURS = ((END - START).days + 1) * 24
UA = {"User-Agent": "lds-gb-map/1.0"}


def key():
    """Paid Open-Meteo key from state/openmeteo.key if present (never printed); None -> the free host (non-commercial
    use, rate-limited: fetch takes longer but gives the same ERA5 data)."""
    try:
        return open(os.path.join(ROOT, "state", "openmeteo.key")).read().strip() or None
    except OSError:
        return None


def fetch(name, la, lo):
    out = os.path.join(PARTS, f"{name}.npy")
    if os.path.exists(out):
        return np.load(out)
    for attempt in range(5):
        try:
            k = key()
            params = {"latitude": la, "longitude": lo, "start_date": START.isoformat(), "end_date": END.isoformat(),
                      "hourly": "temperature_2m", "timezone": "GMT"}
            if k:
                params["apikey"] = k
            host = "customer-archive-api" if k else "archive-api"
            r = requests.get(f"https://{host}.open-meteo.com/v1/archive", headers=UA, timeout=600, params=params)
            if r.status_code == 200:
                break
            print(f"{name}: HTTP {r.status_code}, retry", flush=True)       # body may echo the URL: not printed
        except requests.RequestException as e:
            print(f"{name}: {type(e).__name__}, retry", flush=True)
        time.sleep(10 * (attempt + 1))
    else:
        raise SystemExit(f"{name}: gave up")
    h = r.json()["hourly"]
    assert h["time"][0] == START.isoformat() + "T00:00" and len(h["time"]) == HOURS, (name, h["time"][0], len(h["time"]))
    a = np.array([-32768 if v is None else round(v * 10) for v in h["temperature_2m"]], np.int16)
    np.save(out, a)
    return a


if __name__ == "__main__":
    os.makedirs(PARTS, exist_ok=True)
    towns = json.load(open(os.path.join(G, "towns.json")))["towns"]
    arrs = []
    for name, la, lo, _ in towns:
        t0 = time.time()
        a = fetch(name, la, lo)
        arrs.append(a)
        print(f"{name}: {int((a != -32768).sum()):,} h, {time.time() - t0:.1f}s", flush=True)
    np.savez_compressed(os.path.join(G, "history.npz"), t=np.stack(arrs), start=START.isoformat() + "T00:00",
                        towns=np.array([t[0] for t in towns]))
    print("done")
