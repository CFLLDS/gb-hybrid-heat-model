#!/usr/bin/env python3
"""The article's house animation, hybrid edition: docs/article/sd_power_hybrid/house/index.html.

Craig, 7 Nov 2026: "we need the house animation.. TestbedDT.html#playout -- something similar to this could clearly
show the cutover and the room temps". The TestbedDT house (assets/testbed: model.js, scene3d.js, style.css and the
measured parameters from scripts/testbed_dt.py params()) run as a HYBRID -- heat pump plus a wall-hung gas combi --
through the three real days of docs/article/data/trace_2010.json (scripts/spark/gb_trace.py), priced on 2025-26.

Layered, not copied: model.js, scene3d.js and style.css are inlined unchanged; assets/hybrid_house/ holds only the
new pieces (the section drawing with the boiler, the 3D boiler overlay, the playout driver, the hybrid CSS). One
self-contained offline file; nothing in state/pages is written and testbed_dt's own build is untouched.

    .venv/bin/python scripts/article/hybrid_house.py [--out FILE]
"""
import base64
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import testbed_dt  # noqa: E402

TB = ROOT / "assets" / "testbed"
HY = ROOT / "assets" / "hybrid_house"
TRACE = ROOT / "docs" / "article" / "data" / "trace_2010.json"
OUT = ROOT / "docs" / "article" / "sd_power_hybrid" / "house" / "index.html"

CONTROLLERS = [("biv0", "Fixed 0 °C switch", "ships today"), ("ccop", "C-COP", "price only"),
               ("sdp", "SD-Power", "price + the grid")]
# The trace's heat_kwh is space heating PLUS hot water. Hot water, as gbmodel.homes.house_inputs builds it: 2.1 kWh
# in each of two 2-hour blocks, half-hour slots 12-15 (06:00-08:00) and 35-38 (17:30-19:30), 0.525 kWh a slot.
# Only the space heating goes to the radiators; the cylinder takes the rest.
DHW_SLOTS = [12, 13, 14, 15, 35, 36, 37, 38]
DHW_KWH_SLOT = 2.1 / 4


def params() -> dict:
    """testbed_dt.params(), without its network fetch or its cache write: this page prices carbon from the trace,
    so the grid-carbon profile it would fetch is not used -- read the existing cache, or leave a stub."""
    real = testbed_dt.carbon_profile

    def cached():
        try:
            return json.load(open(testbed_dt.CARBON_CACHE))
        except (OSError, ValueError):
            return {"g_per_kwh": [0] * 48, "region": "-", "from": "-", "to": "-", "gas_g_per_kwh": testbed_dt.GAS_G_PER_KWH}
    testbed_dt.carbon_profile = cached
    try:
        return testbed_dt.params()
    finally:
        testbed_dt.carbon_profile = real


def trace() -> dict:
    t = json.load(open(TRACE))
    order = sorted(t["days"], key=lambda k: t["days"][k]["date"])
    keep = ("date", "price_date", "out_c", "heat_kwh", "cap_kwh", "cop", "carb_g", "price_p", "phi", "day_cost_p", "day_kg", "gb")
    days = {}
    for k in order:
        d = t["days"][k]
        days[k] = {kk: d[kk] for kk in keep}
        days[k]["elec_kwh"] = {tar: {c: d["elec_kwh"][tar][c] for c in ("gas", "hp", "biv0", "ccop", "sdp")} for tar in d["elec_kwh"]}
    return {"town": t["town"], "weather_year": t["weather_year"], "gas_p": t["gas_p"], "gas_sc": t["gas_sc"], "gas_kg": t["gas_kg"],
            "boiler_eff": 0.9, "controllers": CONTROLLERS, "order": order, "days": days,
            "dhw_slots": DHW_SLOTS, "dhw_kwh_slot": DHW_KWH_SLOT}


def build() -> str:
    tb = lambda f: (TB / f).read_text()
    hy = lambda f: (HY / f).read_text()
    logo = "data:image/svg+xml;base64," + base64.b64encode(tb("lds-logo-light.svg").encode()).decode()
    html = hy("index.html")
    p = params()
    p.pop("batt", None); p.pop("car", None)              # this edition is about heat; the scene shows neither
    for key, val in (("/*STYLE*/", tb("style.css") + "\n" + hy("hybrid.css")),
                     ("/*PARAMS*/", "const P = " + json.dumps(p, separators=(",", ":")) + ";\nconst TRACE = "
                      + json.dumps(trace(), separators=(",", ":")) + ";"),
                     ("/*MODEL*/", tb("model.js")), ("/*SCENE3D*/", tb("scene3d.js")),
                     ("/*HYSCENE*/", hy("hybrid_scene.js")), ("/*VIEW*/", hy("hybrid_view.js")), ("__LOGO__", logo)):
        assert key in html, key
        html = html.replace(key, val)
    return html


if __name__ == "__main__":
    page = build()
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print(f"wrote {out} ({len(page) / 1024:.0f} KB)")
