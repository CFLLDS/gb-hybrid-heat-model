"""Realised SPF of the stock at one fixed efficiency level (review 5, recalibration of the low end).

Reads out/v4cal/<Y>_L<L>/stock_summary.csv (runs with --cop-level L:L, 8,000 homes) and prints, per level, the
national median-home SPF (towns weighted by their region's gas-heated homes, as gb_v4_digest.py) for each winter and
the mean over the winters given. Target: 2.78, the Electrification of Heat median SPFH4 over 12-month windows in
Oct 2020 - Sep 2023 (ESC 2024, Table 1.2), so winters 2020, 2021, 2022.
Usage: python gb_spf_cal.py [--years 2020,2021,2022] [--json out.json]
"""
import csv
import json
import sys
from pathlib import Path

ARG = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d   # noqa: E731
D, O = Path("/work/data/gb"), Path("/work/out/v4cal")
G = json.load(open(D / "towns.json"))
W = json.load(open(D / "region_weights.json"))["homes"]
REG = {t[0]: t[3] for t in G["towns"]}
PER = {}
for r in REG.values():
    PER[r] = PER.get(r, 0) + 1
TW = {t: W[r] / PER[r] for t, r in REG.items()}
YS = ARG("--years", "2020,2021,2022").split(",")
res = {}
for d in sorted(O.glob("*_L*")):
    y, L = d.name.split("_L")
    f = d / "stock_summary.csv"
    if not f.exists():
        continue
    rows = [r for r in csv.DictReader(open(f)) if r["tariff"] == "svr"]
    w = sum(TW[r["town"]] for r in rows)
    res.setdefault(L, {})[y] = sum(float(r["hp_spf_p50"]) * TW[r["town"]] for r in rows) / w
for L, v in sorted(res.items()):
    m = [v[y] for y in YS if y in v]
    print(f"L={L}", {y: round(s, 3) for y, s in sorted(v.items())}, "mean", round(sum(m) / len(m), 3) if m else None)
if ARG("--json"):
    json.dump(res, open(ARG("--json"), "w"), indent=1)
