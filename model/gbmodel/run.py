"""GB hybrid-heating model v2: one heating year, every town, the monitored house + the sampled stock, all controllers.

    python scripts/gb_v2.py --weather 1962 --out /work/out/v2/1962 [--stock 32000] [--flat 20:9.5,...]
Writes to --out:
  house_days.parquet   monitored house, every town-day x tariff (v1 columns + per-controller columns)
  town_summary.csv     monitored house per town x tariff (v1 columns + per-controller)
  stock_summary.csv    stock per town x tariff (v1 columns + per-controller shares, medians, carbon, energy)
  flex_region.npz      mean electricity per home, kWh per half-hour: (region, day, tariff, controller, 48) float16
  run.json             arguments, timing, versions (reproducibility appendix)
"""
import json
import os
import sys
import time

import jax
import jax.numpy as jnp
import numpy as np
import pandas as pd

from . import cfg
from .controllers import METRICS
from .data import load
from .homes import house, stock_year

MI = {m: i for i, m in enumerate(METRICS)}


def house_frame(days, T, M, a2, heat, cop):
    M, a2, heat, cop = (np.asarray(x) for x in (M, a2, heat, cop))
    C = cfg.CTRL
    frames = []
    for ti, t in enumerate(cfg.TARIFFS):
        f = days[["town_ix", "town", "lat", "lon", "region", "date", "price_date"]].copy()
        f["tariff"], f["heat_kwh"], f["cop_space"] = t, heat, cop[0]
        f["space_kwh"], f["space_elec_kwh"], f["out_mean_c"] = cop[1], cop[2], np.asarray(T.mean(1))
        for ci, c in enumerate(C):
            for m in ("cost_p", "kg", "elec_kwh", "gas_kwh", "boiler_heat_kwh"):
                f[f"{m}_{c}"] = M[ti, ci, MI[m]]
        g = lambda c, m: M[ti, C.index(c), MI[m]]                                       # noqa: E731
        f["cost_gas"], f["cost_hp"], f["cost_hybrid"], f["cost_hybrid_net"] = (g("gas", "cost_p"), g("hp", "cost_p"),
                                                                               g("ccop", "cost_p"), g("ccop_nopeak", "cost_p"))
        f["kg_gas"], f["kg_hp"], f["kg_hybrid"] = g("gas", "kg"), g("hp", "kg"), g("ccop", "kg")
        f["boiler_share"] = g("ccop", "boiler_heat_kwh") / np.maximum(heat, 1e-9)
        f["unmet_kwh"] = g("hp", "unmet_kwh")
        f["peak_kw_hp"] = g("hp", "peak_elec_kwh") * 2 / (cfg.PEAK_SLOTS[1] - cfg.PEAK_SLOTS[0])
        for ci, c in enumerate(["cost_a2a_ctrl", "cost_a2a_dumb", "kg_a2a_ctrl", "a2a_share", "peak_kw_a2a"]):
            f[c] = a2[ti, ci]
        frames.append(f)
    return pd.concat(frames, ignore_index=True)


def town_summary(hd):
    agg = dict(days=("date", "size"), out_mean_c=("out_mean_c", "mean"), coldest_day_c=("out_mean_c", "min"),
               heat_kwh_day=("heat_kwh", "mean"), space_kwh=("space_kwh", "sum"), space_elec_kwh=("space_elec_kwh", "sum"),
               gas_gbp_day=("cost_gas", "mean"), hp_gbp_day=("cost_hp", "mean"), hybrid_gbp_day=("cost_hybrid", "mean"),
               hybrid_net_gbp_day=("cost_hybrid_net", "mean"), boiler_share=("boiler_share", "mean"),
               unmet_kwh_winter=("unmet_kwh", "sum"), kg_gas_day=("kg_gas", "mean"), kg_hp_day=("kg_hp", "mean"),
               kg_hybrid_day=("kg_hybrid", "mean"), peak_kw_hp=("peak_kw_hp", "mean"),
               a2a_ctrl_gbp_day=("cost_a2a_ctrl", "mean"), a2a_dumb_gbp_day=("cost_a2a_dumb", "mean"),
               a2a_share=("a2a_share", "mean"), kg_a2a_day=("kg_a2a_ctrl", "mean"))
    for c in cfg.CTRL:
        agg[f"{c}_gbp_day"] = (f"cost_p_{c}", "mean")
        agg[f"{c}_kg_day"] = (f"kg_{c}", "mean")
        agg[f"{c}_elec_kwh_day"] = (f"elec_kwh_{c}", "mean")
        agg[f"{c}_gas_kwh_day"] = (f"gas_kwh_{c}", "mean")
    g = hd.groupby(["town", "lat", "lon", "region", "tariff"]).agg(**agg).reset_index()
    g["cop_space"] = g["space_kwh"] / g["space_elec_kwh"]
    g = g.drop(columns=["space_kwh", "space_elec_kwh"])
    for c in [c for c in g.columns if c.endswith("_gbp_day")]:
        g[c] = g[c] / 100
    g["cheapest"] = g[["gas_gbp_day", "hp_gbp_day", "hybrid_gbp_day"]].idxmin(axis=1).str.replace("_gbp_day", "")
    return g.round(4).sort_values(["tariff", "lat"], ascending=[True, False])


def stock_rows(name, dout, n_days, Mm, bshare, a2, B):
    Mm, bshare, a2 = np.asarray(Mm), np.asarray(bshare), np.asarray(a2)
    C, rows = cfg.CTRL, []
    for ti, t in enumerate(cfg.TARIFFS):
        cost = lambda c: Mm[ti, C.index(c), MI["cost_p"]]                               # noqa: E731
        c_gas, c_hp, c_hyb = cost("gas"), cost("hp"), cost("ccop")
        r = {"town": name, "tariff": t, "houses": B, "basis": "house-year", "days_per_house": n_days, "design_c": dout,
             "hybrid_beats_hp_pct": float((c_hyb < c_hp).mean() * 100), "hp_beats_gas_pct": float((c_hp < c_gas).mean() * 100),
             "boiler_share_median": float(np.median(bshare[ti, C.index("ccop")])),
             "hp_gbp_day_median": float(np.median(c_hp) / 100), "hybrid_gbp_day_median": float(np.median(c_hyb) / 100),
             "gas_gbp_day_median": float(np.median(c_gas) / 100),
             "a2a_ctrl_gbp_day_median": float(np.median(a2[ti, 0]) / 100), "a2a_dumb_gbp_day_median": float(np.median(a2[ti, 1]) / 100),
             "a2a_ctrl_beats_gas_pct": float((a2[ti, 0] < c_gas).mean() * 100),
             "a2a_ctrl_beats_hp_pct": float((a2[ti, 0] < c_hp).mean() * 100),
             "a2a_ctrl_beats_wet_hybrid_pct": float((a2[ti, 0] < c_hyb).mean() * 100),
             "orchestration_saving_gbp_winter_mean": float((a2[ti, 1] - a2[ti, 0]).mean() / 100 * 365),
             "a2a_share_median": float(np.median(a2[ti, 3]))}
        gap = (c_hp - c_hyb) * 365 / 100
        r.update(hp_minus_hybrid_gbp_year_p10=float(np.percentile(gap, 10)), hp_minus_hybrid_gbp_year_p50=float(np.median(gap)),
                 hp_minus_hybrid_gbp_year_p90=float(np.percentile(gap, 90)))
        for c in C:
            ci = C.index(c)
            r[f"{c}_gbp_year_median"] = float(np.median(Mm[ti, ci, MI["cost_p"]]) * 365 / 100)
            r[f"{c}_gbp_year_mean"] = float(Mm[ti, ci, MI["cost_p"]].mean() * 365 / 100)
            r[f"{c}_kg_year_mean"] = float(Mm[ti, ci, MI["kg"]].mean() * 365)
            r[f"{c}_elec_kwh_year_mean"] = float(Mm[ti, ci, MI["elec_kwh"]].mean() * 365)
            r[f"{c}_gas_kwh_year_mean"] = float(Mm[ti, ci, MI["gas_kwh"]].mean() * 365)
            r[f"{c}_unmet_kwh_year_mean"] = float(Mm[ti, ci, MI["unmet_kwh"]].mean() * 365)
            r[f"{c}_boiler_share_median"] = float(np.median(bshare[ti, ci]))
            r[f"{c}_beats_hp_pct"] = float((Mm[ti, ci, MI["cost_p"]] < c_hp).mean() * 100)
            r[f"{c}_cheapest_pct"] = float((Mm[ti, ci, MI["cost_p"]] <= Mm[ti, :, MI["cost_p"]].min(0)).mean() * 100)
        biv = [c for c in C if c.startswith("biv")]
        for b in biv:
            r[f"ccop_beats_{b}_pct"] = float((c_hyb < cost(b)).mean() * 100)
            r[f"ccop_saving_vs_{b}_gbp_year_mean"] = float((cost(b) - c_hyb).mean() * 365 / 100)
        rows.append(r)
    return rows


def main():
    t0 = time.time()
    os.makedirs(cfg.OUT, exist_ok=True)
    days, T, CARB, pr, towns, regs, phi = load()
    reg_ix = jnp.array(days["reg_ix"].values)
    day_ix = jnp.array(days["day_ix"].values, jnp.int32)
    wday = jnp.array(days["wday"].values, jnp.int32)
    print(f"{jax.devices()} weather {cfg.WYEAR}: {len(towns)} towns, {len(days)} town-days, "
          f"{len(cfg.TARIFFS)} tariffs x {len(cfg.CTRL)} controllers", flush=True)
    M, a2, heat, cop = jax.jit(house)(T, CARB, reg_ix, pr["agile"], pr["cosy"], day_ix, wday, phi,
                                      jax.random.PRNGKey(cfg.SEED + 1))
    hd = house_frame(days, T, M, a2, heat, cop)
    hd.to_parquet(f"{cfg.OUT}/house_days.parquet", index=False)
    town_summary(hd).to_csv(f"{cfg.OUT}/town_summary.csv", index=False)
    print(f"house: {len(hd):,} town-day-tariffs in {time.time() - t0:.1f}s", flush=True)

    DESIGN = {k: v["design_c"] for k, v in json.load(open(f"{cfg.D}/towns.json"))["design"].items()}
    key = jax.random.PRNGKey(cfg.SEED)
    sfn = jax.jit(stock_year, static_argnums=(11,))
    srows = []
    n_days = int((days["town_ix"] == 0).sum())
    flex = np.zeros((len(regs), n_days, len(cfg.TARIFFS), len(cfg.CTRL), 48), np.float32)
    nreg = np.zeros(len(regs))
    for ti, (name, *_rest, reg) in enumerate(towns):
        t1 = time.time()
        idx = jnp.array(np.where(days["town_ix"].values == ti)[0])
        key, sub = jax.random.split(key)
        Mm, bs, a2m, Ed = sfn(sub, T, CARB, DESIGN[name], idx, reg_ix, day_ix, wday, pr["agile"], pr["cosy"], phi, cfg.STOCK)
        srows += stock_rows(name, DESIGN[name], int(idx.shape[0]), Mm, bs, a2m, cfg.STOCK)
        ri = regs.index(reg)
        flex[ri] += np.asarray(Ed)
        nreg[ri] += 1
        if ti == 0:
            print(f"first town {name}: {time.time() - t1:.1f}s", flush=True)
    pd.DataFrame(srows).round(4).to_csv(f"{cfg.OUT}/stock_summary.csv", index=False)
    flex /= np.maximum(nreg, 1)[:, None, None, None, None]
    np.savez_compressed(f"{cfg.OUT}/flex_region.npz", e=flex.astype(np.float16), regions=np.array(regs),
                        dates=np.array(sorted(days.loc[days.town_ix == 0, "date"])), tariffs=np.array(cfg.TARIFFS),
                        ctrl=np.array(cfg.CTRL), towns_per_region=nreg)
    hdays = cfg.STOCK * len(days)
    info = dict(argv=sys.argv, weather=cfg.WYEAR, stock=cfg.STOCK, seed=cfg.SEED, tariffs=cfg.TARIFFS, ctrl=cfg.CTRL,
                lambda_p_per_kg=cfg.LAMBDA, bivalent_c=cfg.BIVALENT, sdp_phi=cfg.SDP_PHI, hyb_size=cfg.HYB_SIZE, flat=cfg.FLAT, town_days=len(days),
                house_days=hdays, half_hours=hdays * 48, seconds=round(time.time() - t0, 1), jax=jax.__version__,
                device=str(jax.devices()[0]), commit=os.environ.get("GIT_COMMIT", ""))
    json.dump(info, open(f"{cfg.OUT}/run.json", "w"), indent=1)
    print(f"done: house {len(hd):,} + stock {hdays:,} house-days ({hdays * 48:,} half-hours) x {len(cfg.TARIFFS)} tariffs"
          f" x {len(cfg.CTRL)} controllers in {time.time() - t0:.0f}s", flush=True)
