#!/usr/bin/env python3
"""Domestic gas meters per GB electricity region (GSP group / DNO licence area).

Scales the per-home heat model in towns.json up to GB totals.

Method (all inputs downloaded, nothing typed in by hand):
  1. DESNZ subnational domestic gas statistics, MSOA / Intermediate Zone level,
     latest year in the file (2024): domestic gas meter count per small area.
  2. A point for each small area: ONS MSOA (Dec 2021) population-weighted
     centroids for England & Wales; Scottish Government Intermediate Zone 2022
     centroids for Scotland. Both in British National Grid (EPSG:27700).
  3. NESO "GB DNO Licence Areas 20240503" polygons (EPSG:27700), one per
     GSP group letter A..P. Each centroid is assigned to the polygon that
     contains it (point in polygon); a centroid that falls in no polygon
     (coastline generalisation) goes to the nearest polygon vertex.
  4. Meters summed per letter. DESNZ's small "Unallocated" line (meters it
     could not place) is shared pro rata across regions.
  A local-authority level total is computed as a cross-check (same file family).

Usage:  .venv/bin/python -I scripts/spark/gb_national_scale.py [--refresh]
Downloads are cached in data/model/gb/sources/ (treated as data only).
"""
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[2]
GB = ROOT / "data" / "model" / "gb"
SRC = GB / "sources"
OUT = GB / "region_weights.json"
ACCESSED = "2026-11-07"

GAS_MSOA = {
    "file": "gas_domestic_MSOA_stacked_2010-2024.csv",
    "url": "https://assets.publishing.service.gov.uk/media/69457a332f0261139350898e/gas_domestic_MSOA_stacked_2010-2024.csv",
    "title": "Domestic gas consumption by Middle Layer Super Output Area (MSOA), 2010 to 2024 "
             "(Stacked gas consumption statistics data)",
    "publisher": "Department for Energy Security and Net Zero (DESNZ)",
    "date": "2025-12-18 (published; dataset page revised 2026-05-05)",
}
GAS_LA = {
    "file": "gas_LA_stacked_2005-2024.csv",
    "url": "https://assets.publishing.service.gov.uk/media/69f9c094a40aa2232fede4af/gas_LA_stacked_2005-2024.csv",
    "title": "Gas consumption by Local Authority (LA), 2005 to 2024 (Stacked gas consumption statistics data)",
    "publisher": "Department for Energy Security and Net Zero (DESNZ)",
    "date": "2026-05-05 (revision of the 2025-12-18 release)",
}
DNO = {
    "file": "gb-dno-license-areas-20240503.geojson",
    "url": "https://api.neso.energy/dataset/0e377f16-95e9-4c15-a1fc-49e06a39cfa0/resource/"
           "1c6a7dc0-1b6c-443a-bc67-5f7125649434/download/gb-dno-license-areas-20240503-as-geojson.geojson",
    "title": "GIS Boundaries for GB DNO Licence Areas, 20240503 (GeoJSON, EPSG:27700)",
    "publisher": "National Energy System Operator (NESO) Data Portal",
    "date": "2024-05-03",
}
MSOA_PWC = {
    "file": "msoa_dec2021_ew_pwc_v2.json",
    "url": "https://services1.arcgis.com/ESMARspQHYMw9BZ9/ArcGIS/rest/services/"
           "MSOA_December_2021_EW_PWC_V2/FeatureServer/0/query",
    "title": "Middle layer Super Output Areas (December 2021) Population Weighted Centroids in England and Wales (V2)",
    "publisher": "Office for National Statistics, Open Geography Portal",
    "date": "2021 census geography",
}
CENSUS = {
    "file": "census2021_ts046_central_heating_ew.csv",
    "url": "https://www.nomisweb.co.uk/api/v01/dataset/NM_2064_1.data.csv?geography=K04000001"
           "&measures=20100&select=geography_name,c2021_heating_13_name,obs_value",
    "title": "Census 2021 TS046 Central heating, England and Wales (households)",
    "publisher": "Office for National Statistics, via Nomis",
    "date": "2021-03-21 census day (released 2023)",
}
IZ_CENT = {
    "file": "iz2022_centroids_scotland.geojson",
    "url": "https://maps.gov.scot/server/services/ScotGov/StatisticalUnits/MapServer/WFSServer"
           "?service=WFS&version=2.0.0&request=GetFeature&typeNames=SU:IntermediateZoneCent2022"
           "&outputFormat=GEOJSON&count=5000",
    "title": "Intermediate Zone Centroids 2022 (SU:IntermediateZoneCent2022, WFS)",
    "publisher": "Scottish Government, StatisticalUnits map service",
    "date": "2022 data zone geography",
}


def fetch(spec, refresh):
    path = SRC / spec["file"]
    if path.exists() and path.stat().st_size > 0 and not refresh:
        return path
    SRC.mkdir(parents=True, exist_ok=True)
    if spec is MSOA_PWC:  # ArcGIS caps a page at 2000 records
        feats, off = [], 0
        while True:
            r = requests.get(spec["url"], timeout=120, params={
                "where": "1=1", "outFields": "MSOA21CD", "outSR": "27700", "f": "json",
                "resultOffset": off, "resultRecordCount": 2000, "orderByFields": "FID"})
            r.raise_for_status()
            page = r.json().get("features", [])
            feats += page
            if len(page) < 2000:
                break
            off += len(page)
        path.write_text(json.dumps({"features": feats}))
    elif spec is IZ_CENT:  # the WFS returns at most 1000 features a request
        feats = []
        while True:
            r = requests.get(spec["url"] + f"&startIndex={len(feats)}", timeout=300)
            r.raise_for_status()
            page = r.json().get("features", [])
            feats += page
            if len(page) < 1000:
                break
        path.write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
    else:
        r = requests.get(spec["url"], timeout=300)
        r.raise_for_status()
        path.write_bytes(r.content)
    return path


def read_csv(path):
    # DESNZ files are not valid UTF-8 (Welsh names); latin-1 never fails and
    # only touches the name columns, never the codes or numbers.
    with open(path, encoding="latin-1", newline="") as fh:
        return list(csv.DictReader(fh))


def latest_year(rows):
    return max(int(r["Year"]) for r in rows if r["Year"].isdigit())


def load_polygons(path):
    """letter -> list of rings (numpy Nx2). Even-odd rule over all rings."""
    gj = json.loads(path.read_text())
    crs = gj.get("crs", {}).get("properties", {}).get("name", "")
    if "27700" not in crs:
        raise SystemExit(f"DNO file CRS is {crs!r}, expected EPSG:27700")
    out = {}
    for f in gj["features"]:
        letter = f["properties"]["Name"].strip("_")
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        out[letter] = [np.asarray(ring, dtype=float)[:, :2] for poly in polys for ring in poly]
    return out


def inside(rings, x, y):
    """Vectorised even-odd point-in-polygon for points x, y."""
    hit = np.zeros(x.shape, dtype=bool)
    for ring in rings:
        x1, y1 = ring[:, 0], ring[:, 1]
        x2, y2 = np.roll(x1, -1), np.roll(y1, -1)
        for i in range(0, len(x1), 4000):  # chunk edges to bound memory
            a1, b1, a2, b2 = (v[i:i + 4000][None, :] for v in (x1, y1, x2, y2))
            px, py = x[:, None], y[:, None]
            crosses = (b1 > py) != (b2 > py)
            with np.errstate(divide="ignore", invalid="ignore"):
                xi = a1 + (py - b1) * (a2 - a1) / (b2 - b1)
            hit ^= (np.count_nonzero(crosses & (px < xi), axis=1) % 2).astype(bool)
    return hit


def assign(points, polys):
    """points: dict code -> (e, n). Returns code -> (letter, how)."""
    codes = list(points)
    x = np.array([points[c][0] for c in codes])
    y = np.array([points[c][1] for c in codes])
    found = {}
    owner = np.full(len(codes), "", dtype=object)
    for letter, rings in polys.items():
        h = inside(rings, x, y)
        clash = h & (owner != "")
        if clash.any():
            raise SystemExit(f"{clash.sum()} centroids inside two licence areas")
        owner[h] = letter
    verts = {k: np.vstack(v) for k, v in polys.items()}
    for i, c in enumerate(codes):
        if owner[i]:
            found[c] = (owner[i], "inside")
        else:
            d = {k: float(np.min((v[:, 0] - x[i]) ** 2 + (v[:, 1] - y[i]) ** 2)) for k, v in verts.items()}
            k = min(d, key=d.get)
            found[c] = (k, f"nearest boundary, {math.sqrt(d[k]) / 1000:.1f} km")
    return found


def main():
    refresh = "--refresh" in sys.argv
    paths = {k: fetch(s, refresh) for k, s in
             (("msoa", GAS_MSOA), ("la", GAS_LA), ("dno", DNO), ("pwc", MSOA_PWC), ("iz", IZ_CENT), ("census", CENSUS))}

    rows = read_csv(paths["msoa"])
    year = latest_year(rows)
    rows = [r for r in rows if r["Year"] == str(year)]
    meters = {r["MSOA_code"]: float(r["Meters"] or 0) for r in rows}
    la_of = {r["MSOA_code"]: (r["LA_code"], r["LA"]) for r in rows}
    unalloc = meters.pop("Unallocated", 0.0)

    points = {}
    for f in json.loads(paths["pwc"].read_text())["features"]:
        points[f["attributes"]["MSOA21CD"]] = (f["geometry"]["x"], f["geometry"]["y"])
    for f in json.loads(paths["iz"].read_text())["features"]:
        p = f["properties"]
        points[p["IZCode"]] = (float(p["Easting"]), float(p["Northing"]))

    missing = [c for c in meters if c not in points]
    if missing:
        raise SystemExit(f"{len(missing)} small areas have no centroid, e.g. {missing[:5]}")

    polys = load_polygons(paths["dno"])
    owner = assign({c: points[c] for c in meters}, polys)

    allocated = sum(meters.values())
    by_region = defaultdict(float)
    for c, m in meters.items():
        by_region[owner[c][0]] += m
    homes = {k: round(by_region[k] * (1 + unalloc / allocated)) for k in sorted(by_region)}

    # Local authorities whose small areas fall in more than one region
    la_split = defaultdict(lambda: defaultdict(float))
    for c, m in meters.items():
        la_split[la_of[c]][owner[c][0]] += m
    straddling = []
    for (code, name), parts in sorted(la_split.items()):
        if len(parts) > 1:
            tot = sum(parts.values())
            straddling.append({"la_code": code, "la": name, "meters": round(tot),
                               "split": {k: round(v) for k, v in sorted(parts.items(), key=lambda kv: -kv[1])}})
    outside = [{"area": c, "assigned": owner[c][0], "how": owner[c][1], "meters": round(meters[c])}
               for c in meters if owner[c][1] != "inside"]

    la_rows = [r for r in read_csv(paths["la"]) if r["Year"] == str(year)]
    la_total = sum(float(r["Domestic_meters_thouasands"] or 0) * 1000 for r in la_rows)
    total = sum(homes.values())

    # Census 2021 cross-check (England & Wales only; Scotland's census is separate)
    with open(paths["census"], encoding="utf-8", newline="") as fh:
        ts046 = {r["C2021_HEATING_13_NAME"]: int(r["OBS_VALUE"]) for r in csv.DictReader(fh)}
    gas_only = ts046["Mains gas only"]
    multi = (ts046["Two or more types of central heating (not including renewable energy)"]
             + ts046["Two or more types of central heating (including renewable energy)"])
    ew_meters = sum(m for c, m in meters.items() if c[:1] in "EW")

    regions = json.loads((GB / "towns.json").read_text())["regions"]
    if set(regions) != set(homes):
        raise SystemExit(f"region letters differ: towns.json {sorted(regions)} vs DNO {sorted(homes)}")
    names = {f["properties"]["Name"].strip("_"): f["properties"]["Area"]
             for f in json.loads(paths["dno"].read_text())["features"]}

    out = {
        "homes": homes,
        "region_names": {k: names[k] for k in homes},
        "share": {k: round(v / total, 5) for k, v in homes.items()},
        "total": total,
        "year": year,
        "basis": (f"Domestic gas meters in GB, calendar year {year} (DESNZ subnational gas statistics: "
                  "meters on the domestic consumption profile, Annual Quantity < 73,200 kWh, with a "
                  "valid reading). This counts gas METERS, not gas-HEATED homes: it includes some "
                  "cooking-only or vacant connections and misses gas-heated flats on a shared/communal "
                  "meter or on a non-domestic (>73,200 kWh) meter. Used as the scaling count of homes "
                  "on the gas grid; see assumptions for the size of the difference."),
        "method": ("Each DESNZ MSOA (England & Wales, 2021 MSOAs) and Intermediate Zone (Scotland, 2022) "
                   "domestic meter count was placed at its published centroid (ONS population-weighted "
                   "centroids for MSOAs; Scottish Government IZ centroids) and assigned by point-in-polygon "
                   "to the NESO DNO licence area polygon that contains it; licence areas map one-to-one to "
                   "the 14 GSP group letters A..P used by Octopus. Centroids outside every polygon (coastal "
                   "generalisation) go to the nearest polygon. DESNZ's 'Unallocated' meters were spread pro "
                   "rata. Cross-checked against the DESNZ local-authority file total for the same year. "
                   "Reproduce with: .venv/bin/python -I scripts/spark/gb_national_scale.py"),
        "assumptions": [
            "Small-area assignment is by centroid: an MSOA/IZ whose area straddles a licence-area boundary "
            "goes wholly to the area holding its centroid. MSOAs hold ~3,000 meters each, so the error is "
            "a boundary effect of order one MSOA per straddle, not a regional bias.",
            f"DESNZ 'Unallocated' domestic meters ({round(unalloc):,}) were shared pro rata across regions "
            f"(factor {1 + unalloc / allocated:.5f}).",
            "DNO licence areas (NESO, 2024-05-03) are taken as identical to the GSP groups / Octopus region "
            "letters; this is how the letters are defined (A Eastern = UKPN East, ... P = SSEN North of Scotland).",
            "Meters are not homes. A meter count over-states gas-HEATED homes by cooking-only and vacant "
            "connections and under-states them by communal-boiler flats; the net effect is not measured here. "
            "If a gas-heated-homes basis is needed, the census 2021 (England & Wales) 'mains gas only' central "
            "heating share is the usual scaler: see census_2021_ew_cross_check for the ratios (England & Wales only).",
            "Year is the latest in the DESNZ file; meter counts are a snapshot, not the stock of buildings.",
            "Northern Ireland is outside GB and outside the DESNZ GB gas series.",
        ],
        "cross_check": {
            "la_file_total_domestic_meters": round(la_total),
            "msoa_file_total_incl_unallocated": round(allocated + unalloc),
            "difference_pct": round(100 * (allocated + unalloc - la_total) / la_total, 3),
        },
        "census_2021_ew_cross_check": {
            "households_all": ts046["Total: All households"],
            "households_mains_gas_only_central_heating": gas_only,
            "households_two_or_more_central_heating_types": multi,
            "desnz_domestic_meters_ew_same_basis": round(ew_meters),
            "gas_only_households_per_meter": round(gas_only / ew_meters, 4),
            "upper_bound_per_meter_if_every_multi_fuel_home_uses_gas": round((gas_only + multi) / ew_meters, 4),
            "note": "Census day 2021 vs meters in DESNZ year; England & Wales only. Multiply 'homes' by "
                    "one of these ratios to move from a meter basis to a gas-heated-household basis.",
        },
        "straddling_local_authorities": straddling,
        "centroids_outside_polygons": outside,
        "sources": [{"title": s["title"], "url": s["url"], "publisher": s["publisher"],
                     "date": s["date"], "accessed": ACCESSED, "local_file": f"sources/{s['file']}"}
                    for s in (GAS_MSOA, GAS_LA, DNO, MSOA_PWC, IZ_CENT, CENSUS)],
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    for k, v in homes.items():
        print(f"{k} {names[k]:<40} {v:>11,}  {100 * v / total:5.2f}%")
    print(f"total {total:,}   LA file {la_total:,.0f}   outside-polygon {len(outside)}   "
          f"straddling LAs {len(straddling)}")
    print(f"census 2021 E&W: mains-gas-only CH households {gas_only:,} = {gas_only / ew_meters:.3f} per E&W "
          f"meter; with all multi-fuel homes {(gas_only + multi) / ew_meters:.3f}")


if __name__ == "__main__":
    main()
