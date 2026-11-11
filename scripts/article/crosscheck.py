#!/usr/bin/env python3
"""Independent reference implementation of the GB hybrid model, for checking the maths (Craig, 7 Nov 2026: "it's
getting the maths right that's important").

Written from the equations in the article's method section in plain numpy. It deliberately imports NOTHING from the
JAX model (scripts/spark/gbmodel), so a shared bug cannot hide. Runs on a laptop CPU.
  1. HOUSE (deterministic): the monitored house in chosen towns and heating years, every day, every tariff and
     controller (except SD-Power, which depends on pass-2 shed shares): mean GBP/day and kg/day must equal the JAX
     model's town_summary.csv to rounding.
  2. STOCK (statistical): 4,000 homes drawn independently from the published distributions in each chosen town;
     the share of homes for which the C-COP hybrid beats all heat pump, and the median yearly costs, must agree with
     the JAX model's 32,000-home results within sampling error.
    .venv/bin/python scripts/article/crosscheck.py [--src data/model/v21] [--years 2025,1962] [--towns Poole,Aviemore,Leeds]
Writes docs/article/crosscheck.json; exits non-zero if any check fails.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
GB = ROOT / "data" / "model" / "gb"
ARG = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d          # noqa: E731
SRC = ROOT / ARG("--src", "data/model/v21")
YEARS = [int(y) for y in ARG("--years", "2025,1962").split(",")]
TOWNS = ARG("--towns", "Poole,Aviemore,Leeds").split(",")
N_STOCK = int(ARG("--homes", "4000"))

# ---- constants exactly as stated in the method section ---------------------------------------------------------
GAS_P, GAS_SC, SVR_P, IOG_CHEAP, IOG_PEAK, GAS_KG = 8.17, 29.16, 26.47, 6.6, 35.61, 0.183
# Review 4 fiscal basis (Section 4.2), read from each run's recorded arguments in main(): "--iog cheap:peak" sets the
# IOG rates, and "--exvat" divides the 2025-26 Agile and Cosy half-hours before 1 Oct 2026 00:00 BST by 1.05.
EXVAT, EXVAT_UNTIL = False, "2026-09-30T23:00Z"
LAMBDAS, BIVS = (4.0, 31.2), (0.0, 2.0, 5.0)
GAINS = np.array([0.7] * 12 + [1.1] * 6 + [0.8] * 14 + [1.3] * 10 + [1.0] * 6)           # daily gains profile
PEAK = np.zeros(48, bool); PEAK[32:38] = True                                           # 16:00-19:00
CAP_T, CAP35, CAP45 = [-7, 2, 7, 12], [6.3, 6.2, 7.8, 7.6], [6.3, 6.1, 7.4, 7.0]        # Daikin ERGA06 (kW)
SIZES = np.array([4, 5, 6, 7, 8, 9, 11, 14, 16, 20.])
HOUSE_T, HOUSE_S = [1.5, 4.5, 7.5, 11.0, 14.0], [0.353, 0.335, 0.313, 0.250, 0.205]
STOCK_T, STOCK_S = [-3.0, 1.5, 4.5, 7.5, 10.5, 14.0], [0.3415, 0.3506, 0.3628, 0.3620, 0.3434, 0.3124]
CTRL = ["gas", "hp", "biv0", "biv2", "biv5", "ccop", "ccop_c4", "ccop_c31.2", "ccop_nopeak"]


def carnot(share, flow, out):
    return np.clip(share * (flow + 273.15) / np.maximum(flow - out, 5.0), 1.3, 7.0)


def capacity(out, flow, scale):
    a, b = np.interp(out, CAP_T, CAP35), np.interp(out, CAP_T, CAP45)
    return (a + (b - a) * np.clip((flow - 35) / 10, 0, 1)) * scale


# ---- inputs -------------------------------------------------------------------------------------------------------
def weather(year, town):
    """Daily rows of 48 half-hourly temperatures: hourly ERA5, hour 24 = hour 23, linear interpolation."""
    if year == 2025:
        W = json.load(open(GB / "weather_year.json"))[town]
        hrs = {k: v for k, v in W.items()}
    else:
        h = np.load(GB / "history.npz")
        i = [str(x) for x in h["towns"]].index(town)
        t0 = np.datetime64(str(h["start"]))
        a, b = np.datetime64(f"{year}-11-01T00:00"), np.datetime64(f"{year + 1}-11-01T00:00")
        i0, i1 = int((a - t0) / np.timedelta64(1, "h")), int((b - t0) / np.timedelta64(1, "h"))
        stamps = [str(x)[:16] for x in np.arange(a, b, np.timedelta64(1, "h"))]
        hrs = {k: (None if v == -32768 else v / 10) for k, v in zip(stamps, h["t"][i, i0:i1].tolist())}
    by = {}
    for k, v in hrs.items():
        if v is not None:
            by.setdefault(k[:10], {})[int(k[11:13])] = v
    days, T = [], []
    for d, x in sorted(by.items()):
        if len(x) < 24:
            continue
        h25 = np.array([x[i] for i in range(24)] + [x[23]])
        T.append(np.interp(np.arange(48) / 2, np.arange(25), h25))
        days.append(d)
    return days, np.array(T)


def price_day(d):
    md = d[5:] if d[5:] != "02-29" else "02-28"
    return ("2025-" if md >= "11" else "2026-") + md


_PR, _CB = {}, {}


def day_inputs(region, days):
    """Per day: prices (tariff -> 48) and carbon (48), from the 2025-26 calendar day."""
    if not _PR:
        _PR.update(json.load(open(GB / "prices_year.json")))
        _CB.update(json.load(open(GB / "carbon_year.json")))
    ydates = [str(np.datetime64("2025-11-01") + np.timedelta64(i, "D")) for i in range(365)]
    series = {}
    for kind in ("agile", "cosy"):
        s = _PR[f"{kind}_{region}"]
        if EXVAT:
            s = {k: (v / 1.05 if k < EXVAT_UNTIL else v) for k, v in s.items()}
        prev, rows = None, {}
        for d in ydates:                                           # a missing half-hour borrows the day before
            row = [s.get(f"{d}T{i // 2:02d}:{30 * (i % 2):02d}Z") for i in range(48)]
            if None in row:
                fill = [w for w in row if w is not None]
                row = [v if v is not None else (prev[i] if prev is not None else (np.mean(fill) if fill else 25.0))
                       for i, v in enumerate(row)]
            prev = np.array(row, float)
            rows[d] = prev
        series[kind] = rows
    cser = _CB[region]
    cmean = np.nanmean(list(cser.values()))
    slot_h = np.arange(48) / 2
    iog = np.where((slot_h >= 23.5) | (slot_h < 5.5), IOG_CHEAP, IOG_PEAK)
    P, C = [], []
    for d in days:
        pd_ = price_day(d)
        P.append({"iog": iog, "svr": np.full(48, SVR_P), "agile": series["agile"][pd_], "cosy": series["cosy"][pd_]})
        c = np.array([cser.get(f"{pd_}T{i // 2:02d}:{30 * (i % 2):02d}Z", np.nan) for i in range(48)], float)
        C.append(np.where(np.isnan(c), cmean, c))
    return P, np.array(C)


# ---- controllers (method section table) ---------------------------------------------------------------------------
def controllers(q, cop, cap, eta, out, price, carb, gas_p=GAS_P, gas_sc=GAS_SC):
    """q, cop, cap, out, price, carb: (..., 48); eta broadcastable. Returns {ctrl: (cost_p, kg)} per row.
    gas_p, gas_sc: the tariff's gas unit rate and standing charge (today's cap, or the historical year's for "hist")."""
    GAS_P, GAS_SC = gas_p, gas_sc                                                   # noqa: N806 (shadow the constants)
    hp_heat = np.minimum(q, cap)
    unmet = q - hp_heat
    e_ = eta[..., None] if np.ndim(eta) else eta
    res = {}
    gas_fuel = q.sum(-1) / eta
    res["gas"] = (gas_fuel * GAS_P + GAS_SC, gas_fuel * GAS_KG)
    e = hp_heat / cop + unmet
    res["hp"] = ((e * price).sum(-1), (e * carb).sum(-1) / 1000)
    ccop = (GAS_P / e_) > (price / cop)
    masks = {f"biv{t:g}": out >= t for t in BIVS}
    masks["ccop"] = ccop
    for lam in LAMBDAS:
        masks[f"ccop_c{lam:g}"] = ((GAS_P + lam * GAS_KG) / e_) > ((price + lam * carb / 1000) / cop)
    masks["ccop_nopeak"] = ccop & ~PEAK
    for c, m in masks.items():
        hh = np.where(m, hp_heat, 0.0)
        el = hh / cop
        fuel = (q - hh).sum(-1) / eta
        res[c] = ((el * price).sum(-1) + fuel * GAS_P + GAS_SC, (el * carb).sum(-1) / 1000 + fuel * GAS_KG)
    return res


# ---- 1. the monitored house -----------------------------------------------------------------------------------------
def house(year, town, region):
    days, T = weather(year, town)
    P, C = day_inputs(region, days)
    q_space = np.maximum(171.7 * (20.5 - T) - 400 * GAINS, 0) * 0.5 / 1000
    q_dhw = np.zeros_like(T); q_dhw[:, 12:16] = 2.1 / 4; q_dhw[:, 35:39] = 2.1 / 4
    flow = np.clip(46.4 - 0.95 * T - 7, 25, 55)
    cop_s = carnot(np.interp(T, HOUSE_T, HOUSE_S), flow, T)
    cop_d = carnot(0.31, 41.0, T)
    q = q_space + q_dhw
    cop = np.where(q_dhw > 0, (q_space * cop_s + q_dhw * cop_d) / np.maximum(q, 1e-9), cop_s)
    cap = capacity(T, flow, 1.0) * 0.5
    out = {}
    for t in tariffs():
        pr = np.full_like(T, HIST[0]) if t == "hist" else np.array([p[t] for p in P])
        r = controllers(q, cop, cap, 0.9, T, pr, C, *gas_of(t))
        out[t] = {c: (float(v[0].mean() / 100), float(v[1].mean())) for c, v in r.items()}
    return out


# ---- historical-price tariff (v3 "hist": that winter's real unit rates and gas standing charge, 2025 money) -------
HIST = None                                                                         # (elec p/kWh, gas p/kWh, gas SC p/day)


def tariffs():
    return ("iog", "svr", "agile", "cosy") + (("hist",) if HIST else ())


def gas_of(t):
    return (HIST[1], HIST[2]) if t == "hist" else (GAS_P, GAS_SC)


# ---- 2b. the v3 stock: real dwelling records + sourced home inputs, written from the method text --------------------
# Each home is one dwelling record drawn at random from the town's calibrated records (stock_v3.npz: htc_cal W/K,
# floor area m2). Sourced inputs (docs/article/lit/model_inputs.md):
#   set point      N(18.8, 1.0) clipped to [16, 21.5] C                              (EFUS 2017)
#   gains          360 + 260/70 (TFA - 50) W, clipped 250-900, x U(0.75, 1.25)          (SAP 10.2)
#   occupancy      SAP 10.2 Table 1b; hot water litres/day 46 + 26 N, 36.7 K rise, x1.15 losses, x LN(-0.08, 0.4)
#   boiler         N(0.84, 0.035) clipped to [0.72, 0.91]                            (EST 2009 / SAP)
#   sizing         MCS: UA x (20 C - design outdoor) x U(1, 1.2), next size up
# Flow design, COP level and the rest are as in v2.
def stock_v3(year, town, region, dout, rng, rec):
    B = N_STOCK
    pick = rng.integers(0, len(rec["htc"]), B)
    ua, tfa = rec["htc"][pick].astype(float), rec["floor"][pick].astype(float)
    tset = np.clip(18.8 + rng.standard_normal(B), 16.0, 21.5)
    gains = np.clip(360 + 260 / 70 * (tfa - 50), 250, 900) * rng.uniform(0.75, 1.25, B)
    n = np.where(tfa > 13.9, 1 + 1.76 * (1 - np.exp(-0.000349 * (tfa - 13.9) ** 2)) + 0.0013 * (tfa - 13.9), 1.0)
    dhw = 4.18 * (46 + 26 * n) * 36.7 / 3600 * 1.15 * np.exp(-0.08 + 0.4 * rng.standard_normal(B))
    eta = np.clip(0.84 + 0.035 * rng.standard_normal(B), 0.72, 0.91)
    fdes, level = rng.uniform(40, 55, B), rng.uniform(0.816, 1.0, B)
    load = ua * (20.0 - dout) / 1000 * rng.uniform(1.0, 1.2, B)
    size = SIZES[np.clip(np.searchsorted(SIZES, load / (capacity(dout, fdes, 1.0) / 6)), 0, len(SIZES) - 1)]
    return run_stock(year, town, region, dout, ua, tset, gains, dhw, fdes, level, eta, size)


def run_stock(year, town, region, dout, ua, tset, gains, dhw, fdes, level, eta, size):
    B = len(ua)
    days, T = weather(year, town)
    P, C = day_inputs(region, days)
    tot = {t: {c: np.zeros(B) for c in CTRL} for t in tariffs()}
    for di in range(len(days)):
        out = np.broadcast_to(T[di], (B, 48))
        q_space = np.maximum(ua[:, None] * (tset[:, None] - out) - gains[:, None] * GAINS, 0) * 0.5 / 1000
        q_dhw = np.zeros((B, 48)); q_dhw[:, 12:16] = (dhw / 8)[:, None]; q_dhw[:, 35:39] = (dhw / 8)[:, None]
        flow = np.clip(25 + (fdes[:, None] - 25) * (16 - out) / (16 - dout), 25, fdes[:, None] + 5)
        cop_s = carnot(level[:, None] * np.interp(out, STOCK_T, STOCK_S), flow, out)
        cop_d = carnot(level[:, None] * 0.31, 48.0, out)
        q = q_space + q_dhw
        cop = np.where(q_dhw > 0, (q_space * cop_s + q_dhw * cop_d) / np.maximum(q, 1e-9), cop_s)
        cap = capacity(out, flow, (size / 6)[:, None]) * 0.5
        for t in tot:
            pr = np.full((B, 48), HIST[0]) if t == "hist" else np.broadcast_to(P[di][t], (B, 48))
            r = controllers(q, cop, cap, eta, out, pr, np.broadcast_to(C[di], (B, 48)), *gas_of(t))
            for c in CTRL:
                tot[t][c] += r[c][0]
    n = len(days)
    return {t: {"hybrid_beats_hp_pct": float((tot[t]["ccop"] < tot[t]["hp"]).mean() * 100),
                **{f"{c}_gbp_year_median": float(np.median(tot[t][c]) / n * 365 / 100) for c in CTRL}} for t in tot}


# ---- 2. the stock (independent draws) --------------------------------------------------------------------------------
def stock(year, town, region, dout, rng):
    B = N_STOCK
    ua = np.clip(np.exp(np.log(180) + 0.45 * rng.standard_normal(B)), 60, 450)
    tset, gains = rng.uniform(19, 21.5, B), rng.uniform(250, 700, B)
    dhw, fdes = rng.uniform(2, 8, B), rng.uniform(40, 55, B)
    level, eta = rng.uniform(0.816, 1.0, B), rng.uniform(0.85, 0.92, B)
    load = ua * (tset - dout) / 1000 * rng.uniform(1.0, 1.2, B)
    per_kw = capacity(dout, fdes, 1.0) / 6
    size = SIZES[np.clip(np.searchsorted(SIZES, load / per_kw), 0, len(SIZES) - 1)]
    days, T = weather(year, town)
    P, C = day_inputs(region, days)
    tot = {t: {c: np.zeros(B) for c in CTRL} for t in ("iog", "svr", "agile", "cosy")}
    for di in range(len(days)):
        out = np.broadcast_to(T[di], (B, 48))
        q_space = np.maximum(ua[:, None] * (tset[:, None] - out) - gains[:, None] * GAINS, 0) * 0.5 / 1000
        q_dhw = np.zeros((B, 48)); q_dhw[:, 12:16] = (dhw / 8)[:, None]; q_dhw[:, 35:39] = (dhw / 8)[:, None]
        flow = np.clip(25 + (fdes[:, None] - 25) * (16 - out) / (16 - dout), 25, fdes[:, None] + 5)
        cop_s = carnot(level[:, None] * np.interp(out, STOCK_T, STOCK_S), flow, out)
        cop_d = carnot(level[:, None] * 0.31, 48.0, out)
        q = q_space + q_dhw
        cop = np.where(q_dhw > 0, (q_space * cop_s + q_dhw * cop_d) / np.maximum(q, 1e-9), cop_s)
        cap = capacity(out, flow, (size / 6)[:, None]) * 0.5
        for t in tot:
            r = controllers(q, cop, cap, eta, out, np.broadcast_to(P[di][t], (B, 48)), np.broadcast_to(C[di], (B, 48)))
            for c in CTRL:
                tot[t][c] += r[c][0]
    n = len(days)
    return {t: {"hybrid_beats_hp_pct": float((tot[t]["ccop"] < tot[t]["hp"]).mean() * 100),
                **{f"{c}_gbp_year_median": float(np.median(tot[t][c]) / n * 365 / 100) for c in CTRL}} for t in tot}


def main():
    G = json.load(open(GB / "towns.json"))
    region = {t[0]: t[3] for t in G["towns"]}
    design = {k: v["design_c"] for k, v in G["design"].items()}
    rng = np.random.default_rng(20261107)
    report, fails = {"house": [], "stock": []}, []
    global HIST, EXVAT, IOG_CHEAP, IOG_PEAK
    for y in YEARS:
        info = json.load(open(SRC / str(y) / "run.json"))
        HIST = tuple(info["hist_price"]) if info.get("hist_price") else None
        argv = info.get("argv", [])
        EXVAT = "--exvat" in argv
        if "--iog" in argv:
            IOG_CHEAP, IOG_PEAK = (float(x) for x in argv[argv.index("--iog") + 1].split(":"))
        v3 = info.get("stock_v3") and info.get("inputs") == "sourced"
        if v3:
            z = np.load(GB / "stock_v3.npz")
            key = f"htc_{info['stock_v3']}" if f"htc_{info['stock_v3']}" in z.files else "htc_w_k"
            recs = {str(n): {"htc": z[key][i], "floor": z["floor_area"][i]} for i, n in enumerate(z["towns"])}
        ts = {(r["town"], r["tariff"]): r for r in csv.DictReader(open(SRC / str(y) / "town_summary.csv"))}
        ss = {(r["town"], r["tariff"]): r for r in csv.DictReader(open(SRC / str(y) / "stock_summary.csv"))}
        for town in TOWNS:
            h = house(y, town, region[town])
            for t, res in h.items():
                for c, (gbp, kg) in res.items():
                    jax_gbp, jax_kg = float(ts[(town, t)][f"{c}_gbp_day"]), float(ts[(town, t)][f"{c}_kg_day"])
                    ok = abs(gbp - jax_gbp) <= 1e-3 + 1e-4 * jax_gbp and abs(kg - jax_kg) <= 1e-3 + 1e-4 * jax_kg
                    report["house"].append({"year": y, "town": town, "tariff": t, "ctrl": c, "ref_gbp_day": round(gbp, 5),
                                            "model_gbp_day": jax_gbp, "ref_kg_day": round(kg, 4), "model_kg_day": jax_kg, "ok": ok})
                    if not ok:
                        fails.append(f"house {y} {town} {t} {c}: ref £{gbp:.4f} {kg:.3f} kg vs model £{jax_gbp:.4f} {jax_kg:.3f} kg")
            s = stock_v3(y, town, region[town], design[town], rng, recs[town]) if v3 else stock(y, town, region[town], design[town], rng)
            for t, res in s.items():
                m = ss[(town, t)]
                p = res["hybrid_beats_hp_pct"] / 100
                tol_share = 100 * 4 * np.sqrt(max(p * (1 - p), 0.01) / N_STOCK) + 1.0           # 4 s.e. + 1 point
                d_share = res["hybrid_beats_hp_pct"] - float(m["hybrid_beats_hp_pct"])
                worst = max(abs(res[f"{c}_gbp_year_median"] / float(m[f"{c}_gbp_year_median"]) - 1) for c in CTRL)
                ok = abs(d_share) <= tol_share and worst <= 0.03
                report["stock"].append({"year": y, "town": town, "tariff": t, "ref_hybrid_wins_pct": round(res["hybrid_beats_hp_pct"], 2),
                                        "model_hybrid_wins_pct": float(m["hybrid_beats_hp_pct"]), "tolerance_pts": round(tol_share, 2),
                                        "worst_median_cost_diff_pct": round(100 * worst, 2), "ok": ok})
                if not ok:
                    fails.append(f"stock {y} {town} {t}: hybrid wins ref {res['hybrid_beats_hp_pct']:.1f}% vs model {m['hybrid_beats_hp_pct']}% "
                                 f"(tol {tol_share:.1f}); worst median cost diff {100 * worst:.1f}%")
            print(f"{y} {town}: done", flush=True)
    report["summary"] = {"house_checks": len(report["house"]), "house_pass": sum(r["ok"] for r in report["house"]),
                         "stock_checks": len(report["stock"]), "stock_pass": sum(r["ok"] for r in report["stock"]),
                         "max_house_gbp_diff": max(abs(r["ref_gbp_day"] - r["model_gbp_day"]) for r in report["house"]),
                         "max_stock_share_diff_pts": max(abs(r["ref_hybrid_wins_pct"] - r["model_hybrid_wins_pct"]) for r in report["stock"]),
                         "max_stock_median_cost_diff_pct": max(r["worst_median_cost_diff_pct"] for r in report["stock"]),
                         "src": str(SRC.relative_to(ROOT)), "years": YEARS, "towns": TOWNS, "stock_homes": N_STOCK}
    txt = json.dumps(report, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))   # numpy scalars
    (ROOT / "docs" / "article" / "crosscheck.json").write_text(txt)
    print(json.dumps(report["summary"], indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    if fails:
        print("FAILED:\n  " + "\n  ".join(fails[:40]))
        sys.exit(1)


if __name__ == "__main__":
    main()
