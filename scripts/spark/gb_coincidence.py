#!/usr/bin/env python3
"""Coincidence of the model's heat-pump demand against the Freedom trial (review, 9 Nov 2026: compare demand shape and
coincidence with measured evidence).

Sun et al. (2019, Section 4.3) measured, for the hybrid homes of the Freedom trial (Bridgend, winter 2017-18, a
cost-minimising controller on a two-rate tariff), a coincidence factor of 0.27 for 34 customers on cold days, with a
fitted asymptote of 0.12 for very large groups. Coincidence factor = the peak of the group's summed demand / the sum
of each home's own peak, over the same window.

This draws the v3 stock homes of the two map towns nearest Bridgend (Cardiff, Swansea) exactly as the national model
does (gbmodel.homes.sample_homes with the real stock and sourced inputs), runs them half-hour by half-hour through the
N coldest days of winter 2017-18 in that town, keeps EACH home's electricity (the national run keeps only the sum),
and computes the coincidence factor for random groups of 1..B homes, for the all-heat-pump home and the C-COP hybrid
on a flat tariff (SVR) and a two-rate tariff (IOG, the nearest to Freedom's).

    python gb_coincidence.py --weather 2017 --data /work/data/gb --stock-v3 cal --inputs sourced --stock 4000 \
        --towns Cardiff,Swansea --cold-days 10 --out /work/out/review_coincidence.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jax  # noqa: E402
import jax.numpy as jnp  # noqa: E402
import numpy as np  # noqa: E402

from gbmodel import cfg  # noqa: E402
from gbmodel.controllers import run_controllers  # noqa: E402
from gbmodel.diversity import scheduled_demand  # noqa: E402
from gbmodel.data import load, price_block  # noqa: E402
from gbmodel.homes import (GAINS_SHAPE, PEAK, STOCK_SHARE, STOCK_SHARE_T, cap_kw, carnot_cop, gas_ps,  # noqa: E402
                           sample_homes)

TOWNS = cfg.ARG("--towns", "Cardiff,Swansea").split(",")
NCOLD = cfg.ARG("--cold-days", 10)
GROUPS = [1, 5, 10, 31, 34, 100, 300, 1000, 3000]
P_CONT = cfg.ARG("--div-cont", -1.0)          # >= 0: household diversity (gbmodel/diversity.py) with this continuous share
SETBACK = cfg.ARG("--div-setback", 3.0)
DATES = [d for d in cfg.ARG("--dates", "").split(",") if d]   # explicit window (e.g. IDEAL's cold days)
BOILER_KW = cfg.ARG("--div-boiler-kw", 0.0)
LIB = None
if cfg.ARG("--div-lib", ""):                     # measured IDEAL schedules (ideal_gas.py --lib)
    _z = np.load(cfg.ARG("--div-lib", ""))
    _o = np.argsort(_z["home"], kind="stable")
    _hm, _st, _ct = np.unique(_z["home"][_o], return_index=True, return_counts=True)
    LIB = {"on": jnp.array(_z["on"][_o]), "start": jnp.array(_st), "count": jnp.array(_ct)}   # > 0: diversity heat limited by a boiler of this size (gas homes)
DRAWS = 300


def day_e(h, dout, out1, carb1, prices1, phi1, u, kdiv):
    """gbmodel.homes.stock_day, but returning each home's electricity E (T, C, B, 48) instead of the sum, and the
    heat q (B, 48). With --div-cont, heat demand comes from each home's own habits (gbmodel/diversity.py)."""
    B = h["ua"].shape[0]
    out = jnp.broadcast_to(out1, (B, 48))
    carb = jnp.broadcast_to(carb1, (B, 48))
    prices = jnp.broadcast_to(prices1[:, None, :], (prices1.shape[0], B, 48))
    phi = jnp.broadcast_to(phi1[:, None, :], (phi1.shape[0], B, 48))
    gains = h["gains_w"][:, None] * GAINS_SHAPE[None, :]
    q_space = jnp.maximum(h["ua"][:, None] * (h["tset"][:, None] - out) - gains, 0.) * 0.5 / 1000
    q_dhw = jnp.zeros_like(out).at[:, 12:16].set((h["dhw"] / 8)[:, None]).at[:, 35:39].set((h["dhw"] / 8)[:, None])
    flow = jnp.clip(25. + (h["fdes"][:, None] - 25.) * (16. - out) / (16. - dout), 25., h["fdes"][:, None] + 5.)
    cop_s = carnot_cop(h["frac"][:, None] * jnp.interp(out, STOCK_SHARE_T, STOCK_SHARE), flow, out)
    cop_d = carnot_cop(h["frac"][:, None] * 0.31, 48., out)
    cap = cap_kw(out, flow, (h["size"] / 6.)[:, None]) * 0.5
    if P_CONT >= 0:
        dcap = jnp.full_like(cap, BOILER_KW * 0.5) if BOILER_KW > 0 else cap
        q_space, q_dhw = scheduled_demand(kdiv, h, out, gains, dcap, P_CONT, SETBACK, LIB, u[:, 47] if LIB is not None else None)
    q = q_space + q_dhw
    cop = jnp.where(q_dhw > 0, (q_space * cop_s + q_dhw * cop_d) / jnp.maximum(q, 1e-9), cop_s)
    cap_h = None if cfg.HYB_SIZE >= 1.0 else cap_kw(out, flow, (h["size_h"] / 6.)[:, None]) * 0.5
    _, E = run_controllers(q, cop, cap, h["eta"], out, prices, gas_ps(), carb, phi, u, PEAK, cap_h, h.get("tb"))
    return E, q


def coincidence(e, rng):
    """e: (B, slots) electricity per home over the window. Mean and 5-95% CF for random groups of each size."""
    B = e.shape[0]
    own = e.max(1)
    res = {}
    for n in GROUPS:
        if n > B:
            continue
        cf = []
        for _ in range(DRAWS if n < B else 1):
            g = rng.choice(B, n, replace=False)
            cf.append(float(e[g].sum(0).max() / max(own[g].sum(), 1e-12)))
        res[n] = {"mean": round(float(np.mean(cf)), 3), "p5": round(float(np.percentile(cf, 5)), 3),
                  "p95": round(float(np.percentile(cf, 95)), 3)}
    return res


def main():
    days, T, CARB, pr, towns, regs, phi = load()
    DESIGN = {k: v["design_c"] for k, v in json.load(open(f"{cfg.D}/towns.json"))["design"].items()}
    z = np.load(f"{cfg.D}/stock_v3.npz")
    htc_key = f"htc_{cfg.STOCK_V3}" if f"htc_{cfg.STOCK_V3}" in z.files else "htc_w_k"
    REC = {str(n): {"htc": jnp.array(z[htc_key][i], jnp.float32), "c": jnp.array(z["c_kwh_k"][i], jnp.float32),
                    "floor": jnp.array(z["floor_area"][i], jnp.float32)} for i, n in enumerate(z["towns"])}
    names = [t[0] for t in towns]
    fn = jax.jit(day_e)
    rng = np.random.default_rng(9112026)
    out = {"source": "Sun et al. (2019) Section 4.3: CF 0.27 for 34 customers on cold days; asymptote 0.12",
           "argv": sys.argv, "stock": cfg.STOCK, "towns": {}}
    key = jax.random.PRNGKey(cfg.SEED)
    for town in TOWNS:
        ti = names.index(town)
        rows = np.where(days["town_ix"].values == ti)[0]
        tmean = np.asarray(T[rows]).mean(1)
        cold = rows[np.argsort(tmean)[:NCOLD]]
        if DATES:
            dv = days["date"].astype(str).values
            cold = np.array([r for r in rows if dv[r][:10] in DATES])
        cold = cold[np.argsort(days["date"].values[cold])]                      # chronological window
        h = sample_homes(jax.random.fold_in(key, ti), cfg.STOCK, DESIGN[town], REC[town])
        Es, Qs = [], []
        for d in cold:
            p1 = price_block(pr, jnp.array([days["reg_ix"].values[d]]), jnp.array([days["day_ix"].values[d]]), (1, 48))[:, 0, :]
            u = jax.random.uniform(jax.random.fold_in(key, int(d)), (cfg.STOCK, 48))
            e1, q1 = fn(h, DESIGN[town], T[d], CARB[d], p1, phi[:, int(days["wday"].values[d])], u,
                        jax.random.fold_in(key, 4242 + ti))                     # habits fixed per home across days
            Es.append(np.asarray(e1))
            Qs.append(np.asarray(q1))
        E = np.concatenate(Es, axis=-1)                                         # (T, C, B, 48 x NCOLD)
        R = {"cold_days": [str(days["date"].values[d]) for d in cold],
             "cold_mean_c": round(float(np.asarray(T[cold]).mean()), 1),
             "heat_kwh_day": round(float(np.mean([q.sum(1).mean() for q in Qs])), 2), "p_cont": P_CONT}
        Q = np.concatenate(Qs, axis=-1) / np.asarray(h["eta"])[:, None]            # boiler gas, kWh per half-hour
        R["gas"] = coincidence(Q * 2, rng)
        R["gas_profile_kw"] = [round(float(v), 3) for v in np.mean([q.mean(0) * 2 / np.asarray(h["eta"]).mean() for q in Qs], 0)]
        R["gas_kwh_day"] = round(float(Q.sum(1).mean() / len(Qs)), 1)
        R["gas_indiv_peak_kw_median"] = round(float(np.median(Q.max(1) * 2)), 1)
        for t in ("svr", "iog", "agile"):                                        # mean kW per home by half-hour
            for c in ("hp", "ccop"):
                R[f"profile_{c}_{t}"] = [round(float(v), 3) for v in
                                         np.mean([e[cfg.TARIFFS.index(t), cfg.CTRL.index(c)].mean(0) * 2 for e in Es], 0)]
        for t in ("svr", "iog"):
            for c in ("hp", "ccop"):
                R[f"{c}_{t}"] = coincidence(E[cfg.TARIFFS.index(t), cfg.CTRL.index(c)], rng)
        e_hp = E[cfg.TARIFFS.index("svr"), cfg.CTRL.index("hp")]                      # each home's electricity, kWh/hh
        R["hp_svr_indiv_peak_kw_median"] = round(float(np.median(e_hp.max(1) * 2)), 2)
        R["hp_svr_kwh_day"] = round(float(e_hp.sum(1).mean() / len(Es)), 1)
        R["hp_svr_daily_admd_kw"] = [round(float(e[cfg.TARIFFS.index("svr"), cfg.CTRL.index("hp")].mean(0).max() * 2), 3) for e in Es]
        # per-day windows (one cold day at a time), the stricter reading of "on cold days"
        for t in ("svr", "iog"):
            for c in ("hp", "ccop"):
                per = [coincidence(Es[k][cfg.TARIFFS.index(t), cfg.CTRL.index(c)], rng) for k in range(len(Es))]
                R[f"{c}_{t}_perday"] = {n: round(float(np.mean([p[n]["mean"] for p in per])), 3) for n in per[0]}
        out["towns"][town] = R
        if cfg.ARG("--save-e", ""):                      # per-home electricity for the local-feeder case (feeder_case.py)
            np.savez_compressed(cfg.ARG("--save-e", "").replace(".npz", f"_{town}.npz"), e=E.astype(np.float16),
                                tariffs=np.array(cfg.TARIFFS), ctrl=np.array(cfg.CTRL), dates=np.array(R["cold_days"]),
                                ua=np.asarray(h["ua"]), size=np.asarray(h["size"]), q=np.concatenate(Qs, axis=-1).astype(np.float16))
        print(town, R["cold_mean_c"], "GAS", R["gas"][31]["mean"], R["gas_indiv_peak_kw_median"], R["gas_kwh_day"], {k: (R[k][34]["mean"], R[k][max(R[k])]["mean"]) for k in ("hp_svr", "ccop_svr", "hp_iog", "ccop_iog")},
              flush=True)
    json.dump(out, open(cfg.ARG("--out", "/work/out/review_coincidence.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
