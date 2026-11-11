#!/usr/bin/env python3
"""Independent EPC-register check of the v3 stock (gb_v3_stock.py) for the English and Welsh towns.

For each town: draw LSOAs from the town's v3 LSOA set weighted by Canet dwelling count, take each LSOA's
population-weighted centroid, find the nearest postcode (postcodes.io bulk reverse geocode, OGL/ONSPD data),
list that postcode's certificates (EPC API /api/domestic/search?postcode=), keep the latest per UPRN, and fetch
up to CERTS_PER_PC certificates (/api/certificate) until CAP certificates for the town. From each: dwelling form
(property_type + built_form), total floor area, main heating (mains gas or not) and the RdSAP space-heat demand
(renewable_heat_incentive.space_heating_existing_dwelling, kWh/yr). EPC HTC = that demand / the town's
1991-2020 degree-hours (same basis as the Canet HTC before calibration); "calibrated" multiplies by the town's
gas factor. Results go into stock_v3_meta.json under "epc_check". Extracted fields only are cached (no address,
no UPRN) in data/model/gb/sources/epc_check/<town>.jsonl so a rerun resumes.

API notes (probed 7 Nov 2026): search needs a FULL postcode (sector / district -> 400) or a date range
(date_start, date_end; page, page_size up to 5000, pagination block in the reply). local_authority and council
filters are ignored or rejected. No OpenAPI document at /api/docs or /openapi.json.
Key: state/epc.key, sent only as a Bearer header; never printed. <= 2 EPC requests/s.
Run:  .venv/bin/python scripts/spark/gb_v3_epc_check.py [--cap 150]
"""
import json, sys, time
from pathlib import Path
import numpy as np
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gb_v3_stock as st  # noqa: E402

ROOT, G = st.ROOT, st.G
OUT = st.SRC / "epc_check"
CAP = int(sys.argv[sys.argv.index("--cap") + 1]) if "--cap" in sys.argv else 150
CERTS_PER_PC, MAX_PC = 6, 60
API = "https://api.get-energy-performance-data.communities.gov.uk"
PCIO = "https://api.postcodes.io/postcodes"
_last = [0.0]


def epc_get(path, params, key):
    wait = 0.5 - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()
    for attempt in range(3):
        try:
            r = requests.get(API + path, params=params, timeout=60,
                             headers={"Authorization": f"Bearer {key}", "Accept": "application/json"})
        except requests.RequestException:
            time.sleep(5)
            continue
        if r.status_code == 429:
            time.sleep(10 * (attempt + 1))
            continue
        return r.json() if r.status_code == 200 else None
    return None


def to_latlon(e, n, lat0, lon0):
    """Invert st.osgb near the town by a local Jacobian (two Newton steps; error far below a postcode)."""
    lat, lon = lat0, lon0
    for _ in range(2):
        x0, y0 = st.osgb(lat, lon)
        xa, ya = st.osgb(lat + 1e-3, lon)
        xb, yb = st.osgb(lat, lon + 1e-3)
        J = np.array([[xa - x0, xb - x0], [ya - y0, yb - y0]]) / 1e-3
        d = np.linalg.solve(J, [e - x0, n - y0])
        lat, lon = lat + d[0], lon + d[1]
    return lat, lon


def postcodes_for(points):
    out = []
    for i in range(0, len(points), 100):
        body = {"geolocations": [{"latitude": la, "longitude": lo, "radius": 1000, "limit": 1} for la, lo in points[i:i + 100]]}
        r = requests.post(PCIO, json=body, timeout=60)
        r.raise_for_status()
        for q in r.json()["result"]:
            if q["result"]:
                out.append(q["result"][0]["postcode"])
        time.sleep(0.5)
    return out


def extract(d):
    pt, bf = d.get("property_type"), d.get("built_form")
    form = 3 if pt in (2, 3) else {1: 0, 2: 1, 3: 2, 4: 2, 5: 2, 6: 2}.get(bf)
    mh = " ".join(str((m or {}).get("description", "")) for m in (d.get("main_heating") or []))
    rhi = d.get("renewable_heat_incentive") or {}
    return {"cert": d.get("certificate_number"), "form": form, "property_type": pt, "built_form": bf,
            "tfa": d.get("total_floor_area"), "gas": "mains gas" in mh.lower(),
            "boiler": "boiler" in mh.lower(), "space_kwh": rhi.get("space_heating_existing_dwelling"),
            "water_kwh": rhi.get("water_heating"), "band": d.get("current_energy_efficiency_band"),
            "sap_version": d.get("sap_version"), "registered": d.get("registration_date")}


def sample_town(name, lat, lon, lsoa_xy, w, key, rng):
    path = OUT / (name.replace(" ", "_").replace("'", "") + ".jsonl")
    recs = [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []
    if len(recs) >= CAP:
        return recs
    seen = {r["cert"] for r in recs}
    pick = rng.choice(len(w), MAX_PC, p=w / w.sum())
    pcs = postcodes_for([to_latlon(*lsoa_xy[j], lat, lon) for j in pick])
    with open(path, "a") as fh:
        for pc in dict.fromkeys(pcs):
            s = epc_get("/api/domestic/search", {"postcode": pc.replace(" ", "")}, key)
            rows = (s or {}).get("data") or []
            latest = {}
            for r in rows if isinstance(rows, list) else []:
                u = r.get("uprn") or r.get("certificateNumber")
                if u not in latest or (r.get("registrationDate") or "") > (latest[u].get("registrationDate") or ""):
                    latest[u] = r
            certs = [r["certificateNumber"] for r in latest.values() if r.get("certificateNumber") not in seen]
            rng.shuffle(certs)
            for c in certs[:CERTS_PER_PC]:
                d = epc_get("/api/certificate", {"certificate_number": c}, key)
                if not d or not isinstance(d.get("data"), dict):
                    continue
                rec = extract(d["data"])
                rec["cert"] = c
                seen.add(c)
                recs.append(rec)
                fh.write(json.dumps(rec) + "\n")
                if len(recs) >= CAP:
                    return recs
    return recs


def ks(a, b):
    a, b = np.sort(a), np.sort(b)
    x = np.concatenate([a, b])
    return float(np.max(np.abs(np.searchsorted(a, x, "right") / len(a) - np.searchsorted(b, x, "right") / len(b))))


def q(v):
    return [round(float(x), 1) for x in np.percentile(v, [25, 50, 75])] if len(v) else None


def main():
    key = (ROOT / "state/epc.key").read_text().strip()
    OUT.mkdir(parents=True, exist_ok=True)
    meta_path = G / "stock_v3_meta.json"
    meta = json.loads(meta_path.read_text())
    stock = np.load(G / "stock_v3.npz")
    towns = json.loads((G / "towns.json").read_text())["towns"]
    codes, cnt, dem, alln = st.load_canet(st.SRC / st.CANET["dir"] / st.CANET["file"])
    pwc = json.loads((st.SRC / st.LSOA_PWC["dir"] / st.LSOA_PWC["file"]).read_text())
    have = np.array([c in pwc for c in codes])
    lxy = np.array([pwc.get(c, (np.nan, np.nan)) for c in codes])
    diag = {d["town"]: d for d in meta["towns"]}
    rng = np.random.default_rng(st.SEED + 1)
    rows = []
    for i, (name, lat, lon, letter) in enumerate(towns):
        if letter in ("N", "P"):
            continue
        dg = diag[name]
        x, y = st.osgb(lat, lon)
        sel = have & (np.hypot(lxy[:, 0] - x, lxy[:, 1] - y) / 1000 <= dg["radius_km"])
        idx = np.nonzero(sel)[0]
        recs = sample_town(name, lat, lon, lxy[idx], alln[idx].astype(float), key, rng)
        dh = float(stock["degree_hours"][i])
        f = float(stock["gas_factor"][i])
        gas = [r for r in recs if r["gas"] and r["form"] is not None]
        allf = [r for r in recs if r["form"] is not None]
        tfa = np.array([r["tfa"] for r in gas if r["tfa"]], float)
        sh = np.array([r["space_kwh"] for r in gas if r["space_kwh"]], float)
        raw = sh * 1000 / dh
        pr = np.array([(r["tfa"], r["space_kwh"]) for r in gas if r["tfa"] and r["space_kwh"]], float).reshape(-1, 2)
        m_form = stock["form_code"][i]
        m_htc, m_area = stock["htc_w_k"][i], stock["floor_area"][i]
        row = {"town": name, "n_certs": len(recs), "n_gas": len(gas), "n_gas_with_space_heat": int(len(sh)),
               "gas_share": round(len(gas) / max(len(allf), 1), 3),
               "form_share_epc_gas": [round(sum(r["form"] == k for r in gas) / max(len(gas), 1), 3) for k in range(4)],
               "form_share_epc_all": [round(sum(r["form"] == k for r in allf) / max(len(allf), 1), 3) for k in range(4)],
               "form_share_model": [round(float((m_form == k).mean()), 3) for k in range(4)],
               "floor_q_epc": q(tfa), "floor_q_model": q(m_area),
               "ks_floor": round(ks(tfa, m_area), 3) if len(tfa) else None,
               "epc_mean_space_heat_kwh": round(float(sh.mean())) if len(sh) else None,
               "canet_mean_space_heat_kwh": dg["epc_mean_space_heat_kwh"],
               "htc_raw_q_epc": q(raw), "htc_calibrated_q_epc": q(raw * f), "htc_q_model": q(m_htc),
               "ks_htc_calibrated": round(ks(raw * f, m_htc), 3) if len(raw) else None,
               "tau_median_epc_calibrated_h": round(float(np.median(st.TMP["medium"] * pr[:, 0] / 3.6 / (pr[:, 1] * 1000 / dh * f))), 1)
               if len(pr) else None,
               "bands_epc_gas": {b: sum(r["band"] == b for r in gas) for b in "ABCDEFG"}}
        rows.append(row)
        print(f"{name:14s} n={len(recs):3d} gas={len(gas):3d} floor med epc {row['floor_q_epc'][1] if row['floor_q_epc'] else '-'} "
              f"model {row['floor_q_model'][1]}  HTC med epc-cal {row['htc_calibrated_q_epc'][1] if len(raw) else '-'} "
              f"model {row['htc_q_model'][1]}  EPC/Canet heat {row['epc_mean_space_heat_kwh']}/{row['canet_mean_space_heat_kwh']}",
              flush=True)

    def med(k, j=None):
        v = [r[k] if j is None else r[k][j] for r in rows if r[k] is not None]
        return round(float(np.median(v)), 3) if v else None
    ratio = [r["epc_mean_space_heat_kwh"] / r["canet_mean_space_heat_kwh"] for r in rows if r["epc_mean_space_heat_kwh"]]
    meta["epc_check"] = {
        "method": __doc__.split("Run:")[0].strip(), "cap_per_town": CAP, "certs_per_postcode": CERTS_PER_PC,
        "sources": [{"title": "EPC register API (domestic), MHCLG", "url": API, "licence": "OGL v3 (EPC open data terms; "
                     "address data restricted - none stored)"},
                    {"title": "postcodes.io bulk reverse geocode (ONS Postcode Directory)", "url": PCIO, "licence": "OGL v3"}],
        "summary": {"towns": len(rows), "certificates": int(sum(r["n_certs"] for r in rows)),
                    "median_epc_over_canet_space_heat": round(float(np.median(ratio)), 3) if ratio else None,
                    "median_town_floor_epc_m2": med("floor_q_epc", 1), "median_town_floor_model_m2": med("floor_q_model", 1),
                    "median_town_htc_epc_calibrated": med("htc_calibrated_q_epc", 1),
                    "median_town_htc_model": med("htc_q_model", 1), "median_ks_floor": med("ks_floor"),
                    "median_ks_htc": med("ks_htc_calibrated"), "median_tau_epc_calibrated_h": med("tau_median_epc_calibrated_h")},
        "caveats": ["Certificates are the latest per UPRN at sampled postcodes: the register over-represents sold and "
                    "rented homes and recent certificates (newer SAP versions), not the whole stock.",
                    "EPC space heat is RdSAP's standard-occupancy figure; raw HTC is on the same basis as Canet's before "
                    "the gas factor, so 'calibrated' applies the town's v3 gas factor.",
                    "Postcodes come from dwelling-weighted LSOA centroids, so a few postcodes per LSOA dominate."],
        "towns": rows}
    meta_path.write_text(json.dumps(meta, indent=1, default=str))
    print(json.dumps(meta["epc_check"]["summary"], indent=1))


if __name__ == "__main__":
    main()
