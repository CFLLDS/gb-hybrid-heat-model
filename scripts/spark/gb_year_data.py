#!/usr/bin/env python3
"""Full-year inputs for the GB map (Craig, 6 Nov 2026: "sample over the entire year of actual temps.. and just let the
spark churn the numbers.. every location every day").

Year 1 Nov 2025 - 31 Oct 2026, all 79 towns in data/model/gb/towns.json:
  weather_year.json  {town: {"YYYY-MM-DDTHH:00": C}}       Open-Meteo archive, hourly temperature_2m, GMT
  prices_year.json   {"agile_X"/"cosy_X": {"...Z": p}}     Octopus actual import unit rates per region, half-hourly
  carbon_year.json   {"X": {"...Z": gCO2/kWh}}             carbonintensity.org.uk regional forecast, half-hourly
Resumable: each file is reloaded and only what is missing is fetched. Polite: 0.3-1 s between calls.
    .venv/bin/python scripts/spark/gb_year_data.py
then rsync data/model/gb/*_year.json <your-gpu-host>:<path>
"""
import datetime as dt
import json
import os
import sys
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
G = os.path.join(ROOT, "data", "model", "gb")
A, B = dt.datetime(2025, 11, 1, tzinfo=dt.timezone.utc), dt.datetime(2026, 11, 1, tzinfo=dt.timezone.utc)
# --weather 2010: weather only, 1 Nov 2010 - 31 Oct 2011 into weather_year2010.json (the hard winter; prices and carbon
# did not exist then, so the model prices it on 2025-26 by calendar day)
WY = int(sys.argv[sys.argv.index("--weather") + 1]) if "--weather" in sys.argv else 2025
WA, WB = dt.date(WY, 11, 1), dt.date(WY + 1, 11, 1)
WFILE = "weather_year.json" if WY == 2025 else f"weather_year{WY}.json"
UA = {"User-Agent": "lds-gb-map/1.0"}
towns = json.load(open(os.path.join(G, "towns.json")))
REGIONS = towns["regions"]


def load(name):
    try:
        return json.load(open(os.path.join(G, name)))
    except (OSError, ValueError):
        return {}


def save(name, obj):
    tmp = os.path.join(G, name + ".tmp")
    json.dump(obj, open(tmp, "w"), separators=(",", ":"))
    os.replace(tmp, os.path.join(G, name))


def weather():
    W = load(WFILE)
    for name, la, lo, _ in towns["towns"]:
        if len(W.get(name, {})) >= 365 * 24 - 2:
            continue
        r = requests.get("https://archive-api.open-meteo.com/v1/archive", headers=UA, timeout=120, params={
            "latitude": la, "longitude": lo, "start_date": WA.isoformat(),
            "end_date": (WB - dt.timedelta(days=1)).isoformat(), "hourly": "temperature_2m", "timezone": "GMT"})
        r.raise_for_status()
        h = r.json()["hourly"]
        W[name] = dict(zip(h["time"], h["temperature_2m"]))
        save(WFILE, W)
        print(f"weather {name}: {sum(v is not None for v in W[name].values())} h", flush=True)
        time.sleep(1)


def prices():
    P = load("prices_year.json")
    for reg in REGIONS:
        for prod in ("AGILE-24-10-01", "COSY-22-12-08"):
            key = f"{prod.split('-')[0].lower()}_{reg}"
            if len(P.get(key, {})) >= 365 * 48 - 4:
                continue
            P[key] = {}
            url = f"https://api.octopus.energy/v1/products/{prod}/electricity-tariffs/E-1R-{prod}-{reg}/standard-unit-rates/"
            params = {"period_from": A.strftime("%Y-%m-%dT%H:%MZ"), "period_to": B.strftime("%Y-%m-%dT%H:%MZ"),
                      "page_size": 1500}
            nxt = url
            while nxt:
                j = requests.get(nxt, params=params, headers=UA, timeout=60).json()
                params = None
                for x in j["results"]:
                    a = dt.datetime.fromisoformat(x["valid_from"].replace("Z", "+00:00"))
                    b = (dt.datetime.fromisoformat(x["valid_to"].replace("Z", "+00:00")) if x.get("valid_to")
                         else a + dt.timedelta(minutes=30))
                    a, b = max(a, A), min(b, B)
                    while a < b:
                        P[key][a.strftime("%Y-%m-%dT%H:%MZ")] = x["value_inc_vat"]
                        a += dt.timedelta(minutes=30)
                nxt = j.get("next")
                time.sleep(0.3)
            save("prices_year.json", P)
            print(f"prices {key}: {len(P[key])} half-hours", flush=True)


def carbon():
    """Regions in parallel (4 at a time); each region's half-hours go in its own dict, saved together at the end."""
    from concurrent.futures import ThreadPoolExecutor
    C = load("carbon_year.json")
    for reg in REGIONS:
        C.setdefault(reg, {})
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(lambda kv: _carbon_region(C, *kv), REGIONS.items()))
    save("carbon_year.json", C)


def _carbon_region(C, reg, rid):
    if True:
        d = A
        while d < B:
            e = min(d + dt.timedelta(days=13), B)
            want = int((e - d).total_seconds() // 1800)
            have = sum(1 for i in range(want) if (d + dt.timedelta(minutes=30 * i)).strftime("%Y-%m-%dT%H:%MZ") in C[reg])
            if have < want - 2:
                try:
                    j = requests.get(f"https://api.carbonintensity.org.uk/regional/intensity/{d:%Y-%m-%dT%H:%MZ}/"
                                     f"{e:%Y-%m-%dT%H:%MZ}/regionid/{rid}", headers=UA, timeout=60).json()
                    for x in j["data"]["data"]:
                        C[reg][x["from"][:16] + "Z"] = x["intensity"]["forecast"]
                except Exception as ex:                        # noqa: BLE001
                    print(f"carbon {reg} {d:%Y-%m-%d}: {ex}", flush=True)
                time.sleep(0.5)
            d = e
        print(f"carbon {reg}: {len(C[reg])} half-hours", flush=True)


if __name__ == "__main__":
    weather()
    if WY == 2025:
        prices()
        carbon()
    print("done")
