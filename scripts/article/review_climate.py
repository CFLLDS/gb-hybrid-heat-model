#!/usr/bin/env python3
"""Hostile review (9 Nov 2026), major issue 9: 86 winters are not draws from today's climate.

Splits the record into 1940-41..1979-80 and 1986-87..2025-26 (40 winters each) and reports, per period: heating
degree days, the hybrid's winning share and the C-COP and all-heat-pump bills (median, 95th percentile = the paper's
"one-in-twenty", max) and the national peaks. Severity rankings stay valid; return periods are period-specific.
    .venv/bin/python scripts/article/review_climate.py -> docs/article/results/review_climate.json
"""
import csv
import json
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2] / "docs" / "article" / "results"
yrs = {int(r["year"]): r for r in csv.DictReader(open(R / "years.csv"))}
nat = list(csv.DictReader(open(R / "national.csv")))
P = {"early_1940_1979": range(1940, 1980), "recent_1986_2025": range(1986, 2026), "all": range(1940, 2026)}
q = lambda v: {"median": round(float(np.median(v)), 1), "p95": round(float(np.percentile(v, 95)), 1),  # noqa: E731
               "max": round(float(max(v)), 1), "p5": round(float(np.percentile(v, 5)), 1)}
out = {}
for name, rng in P.items():
    o = {"n": len(rng), "hdd": q([float(yrs[y]["hdd"]) for y in rng]),
         "coldest_day_c": q([float(yrs[y]["coldest_day_c"]) for y in rng])}
    for t in ("svr", "agile", "iog"):
        for c in ("hp", "ccop"):
            rows = [r for r in nat if r["tariff"] == t and r["ctrl"] == c and int(r["year"]) in rng]
            o[f"{c}_{t}_gbp"] = q([float(r["gbp_year_mean"]) for r in rows])
            o[f"{c}_{t}_peak_gw"] = q([float(r["system_peak_gw"]) for r in rows])
        rows = [r for r in nat if r["tariff"] == t and r["ctrl"] == "ccop" and int(r["year"]) in rng]
        o[f"hyb_wins_{t}_pct"] = q([float(r["beats_hp_pct"]) for r in rows])
    out[name] = o
(R / "review_climate.json").write_text(json.dumps(out, indent=1))
for k in ("hdd", "hyb_wins_svr_pct", "hp_svr_gbp", "ccop_svr_gbp", "hp_svr_peak_gw", "ccop_agile_peak_gw"):
    print(k, {n: out[n][k] for n in out})
