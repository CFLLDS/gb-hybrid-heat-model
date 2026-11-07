#!/usr/bin/env python3
"""Merge the literature strands (docs/article/lit/*.json) into docs/article/sources.json, the ONLY citation
register the article build accepts. Every entry was fetched and read by a review agent (quotes + locators kept).
Duplicate works under different keys are folded with ALIASES (alias -> canonical key)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIT = ROOT / "docs" / "article" / "lit"
ALIASES = {"WPD_WWU2018Freedom": "FREEDOM2018"}

out, seen = {}, {}
for f in sorted(LIT.glob("*.json")):
    j = json.load(open(f))
    for s in j["sources"]:
        k = ALIASES.get(s["key"], s["key"])
        if k in out:
            out[k]["claims"] += s.get("claims", [])
            out[k]["strands"].append(f.stem)
            continue
        out[k] = {**s, "key": k, "strands": [f.stem]}
    seen[f.stem] = j.get("not_verified", [])
json.dump({"aliases": ALIASES, "sources": out, "not_verified": seen}, open(ROOT / "docs" / "article" / "sources.json", "w"),
          indent=1, ensure_ascii=False)
print(f"{len(out)} sources, {sum(len(s['claims']) for s in out.values())} claims")
