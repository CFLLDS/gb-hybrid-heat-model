#!/usr/bin/env python3
"""GB national electricity demand for the price year (1 Nov 2025 - 31 Oct 2026), half-hourly, UTC.

Source: NESO Historic Demand Data 2025 and 2026 (data/model/gb/sources/neso_demand/), column ND (national demand:
transmission-metered demand, excluding embedded generation, station load, pumping and exports). Settlement periods
are UK local time (46/50 on clock-change days) and are converted to UTC. Days the 2026 file does not yet cover are
filled from the same calendar date a year earlier (stated in the output). Writes data/model/gb/base_demand.json:
    {"series": {"YYYY-MM-DDTHH:MMZ": MW}, "filled_from_prior_year": [...dates], "source": ...}
"""
import csv
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "model" / "gb" / "sources" / "neso_demand"
LON = ZoneInfo("Europe/London")
A, B = dt.date(2025, 11, 1), dt.date(2026, 11, 1)


def read(path):
    out = {}
    for r in csv.DictReader(open(path)):
        d = dt.date.fromisoformat(r["SETTLEMENT_DATE"].strip('"')[:10])
        sp = int(r["SETTLEMENT_PERIOD"])
        local0 = dt.datetime(d.year, d.month, d.day, tzinfo=LON)            # local midnight
        t = (local0.astimezone(dt.timezone.utc) + dt.timedelta(minutes=30 * (sp - 1)))
        out[t.strftime("%Y-%m-%dT%H:%MZ")] = float(r["ND"])
    return out


if __name__ == "__main__":
    raw = {**read(SRC / "demanddata_2025.csv"), **read(SRC / "demanddataupdate_2026.csv")}
    series, filled = {}, set()
    t = dt.datetime(A.year, A.month, A.day, tzinfo=dt.timezone.utc)
    while t.date() < B:
        k = t.strftime("%Y-%m-%dT%H:%MZ")
        if k in raw:
            series[k] = raw[k]
        else:
            prior = (t - dt.timedelta(days=365)).strftime("%Y-%m-%dT%H:%MZ")
            series[k] = raw[prior]
            filled.add(t.date().isoformat())
        t += dt.timedelta(minutes=30)
    v = list(series.values())
    json.dump({"series": series, "filled_from_prior_year": sorted(filled), "unit": "MW", "column": "ND",
               "source": "NESO Historic Demand Data 2025 and 2026 (accessed 7 November 2026)",
               "stats": {"max_mw": max(v), "min_mw": min(v), "mean_mw": sum(v) / len(v)}},
              open(ROOT / "data" / "model" / "gb" / "base_demand.json", "w"))
    print(f"{len(series)} half-hours, peak {max(v):,.0f} MW, min {min(v):,.0f}, filled {len(filled)} days from prior year")
