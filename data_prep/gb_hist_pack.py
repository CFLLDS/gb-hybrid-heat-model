#!/usr/bin/env python3
"""Pack every heating year's town results into one small binary for the GB map's year slider.

    python3 scripts/spark/gb_hist_pack.py [--src data/model/v21]

Reads <src>/<year>/{town_summary,stock_summary}.csv for every year present (model v2.1: v1 columns plus the corrected
Agile controller) and the town order from the live page's DATA (docs/artifacts/gb_hybrid_map.html), and writes
  docs/artifacts/gb_hist.bin   little-endian, year-major then town (page order), 38 bytes per town-year:
      int16 out_mean_c x10, int16 coldest_day_c x10, uint16 cop_space x100, uint16 heat_kwh_day x10,
      uint16 gas p/day, then per tariff (svr, iog, cosy, agile): uint16 hp p/day, uint16 hybrid p/day,
      uint8 boiler share %, uint8 stock hybrid-beats-hp %, uint8 stock hp-beats-gas %
  docs/artifacts/gb_hist.json  {years, towns, tariffs, bytes_per_record, fields}
"""
import csv
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / (sys.argv[sys.argv.index("--src") + 1] if "--src" in sys.argv else "data/model/v21")
PAGE = ROOT / "docs" / "artifacts" / "gb_hybrid_map.html"
TAR = ["svr", "iog", "cosy", "agile"]
REC = struct.Struct("<hhHHH" + "HHBBB" * 4)


def page_towns():
    s = PAGE.read_text()
    d = json.loads(re.search(r"^const (?:DATA|BASE) = (\{.*\});$", s, re.M).group(1))
    return [t["name"] for t in d["towns"]]


def clip(v, lo, hi):
    return max(lo, min(hi, int(round(v))))


def main():
    towns = page_towns()
    years = sorted(int(p.parent.name) for p in SRC.glob("*/stock_summary.csv") if (p.parent / "town_summary.csv").exists())
    out = bytearray()
    for y in years:
        T = {(r["town"], r["tariff"]): r for r in csv.DictReader(open(SRC / str(y) / "town_summary.csv"))}
        S = {(r["town"], r["tariff"]): r for r in csv.DictReader(open(SRC / str(y) / "stock_summary.csv"))}
        for n in towns:
            a = T[(n, "svr")]
            vals = [clip(float(a["out_mean_c"]) * 10, -32768, 32767), clip(float(a["coldest_day_c"]) * 10, -32768, 32767),
                    clip(float(a["cop_space"]) * 100, 0, 65535), clip(float(a["heat_kwh_day"]) * 10, 0, 65535),
                    clip(float(a["gas_gbp_day"]) * 100, 0, 65535)]
            for t in TAR:
                h, s = T[(n, t)], S[(n, t)]
                vals += [clip(float(h["hp_gbp_day"]) * 100, 0, 65535), clip(float(h["hybrid_gbp_day"]) * 100, 0, 65535),
                         clip(float(h["boiler_share"]) * 100, 0, 255), clip(float(s["hybrid_beats_hp_pct"]), 0, 255),
                         clip(float(s["hp_beats_gas_pct"]), 0, 255)]
            out += REC.pack(*vals)
    (ROOT / "docs" / "artifacts" / "gb_hist.bin").write_bytes(bytes(out))
    json.dump({"years": years, "towns": towns, "tariffs": TAR, "bytes_per_record": REC.size, "source": str(SRC.relative_to(ROOT)),
               "fields": "see scripts/spark/gb_hist_pack.py docstring"}, open(ROOT / "docs" / "artifacts" / "gb_hist.json", "w"))
    print(f"{len(years)} years x {len(towns)} towns x {REC.size} B = {len(out) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
