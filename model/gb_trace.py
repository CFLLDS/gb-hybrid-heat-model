#!/usr/bin/env python3
"""Three days in the life of an SD-Power hybrid: half-hourly traces for the article's interactive.

The monitored house (Poole), run as a HYBRID (heat pump + its old boiler), through three real days of one weather
year, priced on 2025-26 (region H). Same physics and controllers as the national model (gbmodel.homes.house_inputs,
gbmodel.controllers.run_controllers). The three days are chosen by rule, not by hand:
  frost   the coldest day of the year in Poole
  cheap   the heating-season (Nov-Mar) day with the most negative Agile half-hours in the house's region
  stress  the day SD-Power sheds the most GB heat-pump demand on Agile (from pass 1 shed shares, sdp_phi.npz)
For SD-Power the house switches in a half-hour when its own random draw falls below the shed share phi, exactly
as each sampled home does in the national model; the GB context shows the share phi itself.
Also exports the GB context for each day: national demand, stock heat-pump load under C-COP and under SD-Power.
    python gb_trace.py --weather 2010 --data /work/data/gb --run /work/out/v21/2010 --out /work/out/v21/trace_2010.json
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
from gbmodel.data import load, price_day  # noqa: E402
from gbmodel.homes import PEAK, gas_ps, house_inputs  # noqa: E402

TOWN = cfg.ARG("--town", "Poole")
RUN = cfg.ARG("--run", "")
SHOW = ["gas", "hp", "biv0", "ccop", "ccop_c31.2", "sdp"]


def main():
    days, T, CARB, pr, towns, regs, _ = load()
    rows = np.where(days["town"].values == TOWN)[0]
    d = days.iloc[rows]
    Tt = np.asarray(T)[rows]
    agile = np.asarray(pr["agile"])[int(d["reg_ix"].iloc[0])]                     # (365, 48)
    di = d["day_ix"].values
    frost = int(np.argmin(Tt.mean(1)))
    neg = (agile[di] < 0).sum(1) - 1e-3 * agile[di].mean(1)
    neg = np.where(np.isin(d["date"].str[5:7].values, ["11", "12", "01", "02", "03"]), neg, -1e9)   # heating season
    cheap = int(np.argmax(neg))
    fx = np.load(f"{RUN}/../../v2/{cfg.WYEAR}/sdp_phi.npz") if RUN else None
    phi_all = fx["phi"] if fx is not None else np.zeros((len(cfg.TARIFFS), len(d), 48))
    ai = list(fx["tariffs"]).index("agile") if fx is not None else 2
    stress = int(np.argmax(phi_all[ai].sum(1))) if fx is not None else frost
    picks = {"frost": frost, "cheap": cheap, "stress": stress}

    sel = np.array(list(picks.values()))
    r = rows[sel]
    h = house_inputs(T[r], jnp.array(days["reg_ix"].values[r]), pr["agile"], pr["cosy"], jnp.array(days["day_ix"].values[r]))
    wd = days["wday"].values[r]
    phi = jnp.array(phi_all[:, wd])                                                  # (T, 3, 48)
    u = jax.random.uniform(jax.random.PRNGKey(cfg.SEED + 2), (len(sel), 48))        # this house's own random draws
    M, E = run_controllers(h["q"], h["cop"], h["cap"], h["eta"], h["out"], h["prices"], gas_ps(), CARB[r], phi, u, PEAK)
    E, M = np.asarray(E), np.asarray(M)
    q, cap, cop = (np.asarray(h[k]) for k in ("q", "cap", "cop"))

    nat = {}
    if RUN and os.path.exists(f"{RUN}/flex_region.npz"):
        f = np.load(f"{RUN}/flex_region.npz")
        W = json.load(open(f"{cfg.D}/region_weights.json"))["homes"]
        w = np.array([W[x] for x in f["regions"]], float)
        gw = (f["e"].astype(np.float64) * w[:, None, None, None, None]).sum(0) * 2 / 1e6
        S = json.load(open(f"{cfg.D}/base_demand.json"))["series"]
        fd = [str(x) for x in f["dates"]]
        for name, i in picks.items():
            date = d["date"].values[i]
            k = fd.index(date)
            base = [S[f"{price_day(date)}T{s // 2:02d}:{30 * (s % 2):02d}Z"] / 1000 for s in range(48)]
            nat[name] = {t: {"base_gw": base,
                             "ccop_gw": gw[k, list(f["tariffs"]).index(t), list(f["ctrl"]).index("ccop")].round(2).tolist(),
                             "sdp_gw": gw[k, list(f["tariffs"]).index(t), list(f["ctrl"]).index("sdp")].round(2).tolist(),
                             "hp_gw": gw[k, list(f["tariffs"]).index(t), list(f["ctrl"]).index("hp")].round(2).tolist()}
                         for t in ("svr", "agile", "cosy", "iog")}
    out = {"town": TOWN, "weather_year": cfg.WYEAR, "tariffs": cfg.TARIFFS, "controllers": SHOW, "gas_p": cfg.GAS_P,
           "gas_sc": cfg.GAS_SC, "gas_kg": cfg.GAS_KG, "days": {}}
    for j, (name, i) in enumerate(picks.items()):
        out["days"][name] = {
            "date": d["date"].values[i], "price_date": d["price_date"].values[i],
            "out_c": Tt[i].round(2).tolist(), "heat_kwh": q[j].round(4).tolist(), "cap_kwh": cap[j].round(4).tolist(),
            "cop": cop[j].round(3).tolist(), "carb_g": np.asarray(CARB[r[j]]).round(1).tolist(),
            "price_p": {t: np.asarray(h["prices"][ti, j]).round(3).tolist() for ti, t in enumerate(cfg.TARIFFS)},
            "phi": {t: np.asarray(phi[ti, j]).round(3).tolist() for ti, t in enumerate(cfg.TARIFFS)},
            "elec_kwh": {t: {c: E[ti, cfg.CTRL.index(c), j].round(4).tolist() for c in SHOW} for ti, t in enumerate(cfg.TARIFFS)},
            "day_cost_p": {t: {c: float(M[ti, cfg.CTRL.index(c), 0, j]) for c in SHOW} for ti, t in enumerate(cfg.TARIFFS)},
            "day_kg": {t: {c: float(M[ti, cfg.CTRL.index(c), 1, j]) for c in SHOW} for ti, t in enumerate(cfg.TARIFFS)},
            "gb": nat.get(name)}
    json.dump(out, open(cfg.ARG("--out", "/work/out/trace.json"), "w"), separators=(",", ":"))
    print({k: out["days"][k]["date"] for k in picks})


if __name__ == "__main__":
    main()
