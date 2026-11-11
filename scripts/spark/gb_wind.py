#!/usr/bin/env python3
"""Transmission-metered wind, half-hourly, for SD-Power's residual-demand cap (review 4, 9 Nov 2026).

NESO ND already nets off embedded (distribution-connected) wind and solar, so the demand left for the rest of the
transmission system after wind is ND - WIND, with WIND the transmission-metered wind in NESO's historic generation
mix (df_fuel_ckan.csv, UTC half-hours, MW). Writes data/model/gb/wind.json {"series": {"YYYY-MM-DDTHH:MMZ": MW}} for
1 Nov 2016 - 31 Oct 2026, the price years the model uses, keyed like base_demand.json.
    python3 scripts/spark/gb_wind.py
"""
import csv
import json
from pathlib import Path

G = Path(__file__).resolve().parents[2] / "data" / "model" / "gb"
SRC = G / "sources" / "neso_genmix" / "df_fuel_ckan.csv"


def main():
    S = {}
    with open(SRC, newline="") as fh:
        for r in csv.DictReader(fh):
            t = r["DATETIME"]
            if "2016-11-01" <= t[:10] < "2026-11-01" and r["WIND"]:
                S[f"{t[:16]}Z"] = float(r["WIND"])
    out = {"series": S, "unit": "MW", "column": "WIND (transmission-metered)",
           "source": "NESO Data Portal, Historic generation mix (df_fuel_ckan.csv), accessed 2026-11-07",
           "note": "ND excludes embedded wind and solar, so residual demand = ND - WIND"}
    (G / "wind.json").write_text(json.dumps(out))
    print(len(S), "half-hours", min(S), max(S))


if __name__ == "__main__":
    main()
