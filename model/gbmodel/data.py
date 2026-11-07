"""Inputs: weather for one heating year, the 2025-26 prices and carbon by calendar day, the SD-Power shed shares.

Weather: 2025-26 from weather_year.json; any other year 1940-2024 from history.npz (ERA5 via Open-Meteo,
gb_history_data.py) or a weather_year<Y>.json if present. Prices and carbon are always the actual 2025-26 regional
half-hourly Agile, Cosy and NESO carbon intensity, matched by calendar day (1 Dec 1962 is priced as 1 Dec 2025);
29 Feb borrows 28 Feb.
"""
import json
import os

import jax.numpy as jnp
import numpy as np
import pandas as pd

from . import cfg


def history_year(y):
    h = np.load(f"{cfg.D}/history.npz")
    t0 = np.datetime64(str(h["start"]))
    a, b = np.datetime64(f"{y}-11-01T00:00"), np.datetime64(f"{y + 1}-11-01T00:00")
    i0, i1 = int((a - t0) / np.timedelta64(1, "h")), int((b - t0) / np.timedelta64(1, "h"))
    stamps = [str(x)[:16] for x in np.arange(a, b, np.timedelta64(1, "h"))]
    return {str(n): {k: (None if v == -32768 else v / 10) for k, v in zip(stamps, h["t"][ti, i0:i1].tolist())}
            for ti, n in enumerate(h["towns"])}


def weather():
    name = "weather_year" if cfg.WYEAR == "2025" else f"weather_year{cfg.WYEAR}"
    if os.path.exists(f"{cfg.D}/{name}.json"):
        return json.load(open(f"{cfg.D}/{name}.json"))
    return history_year(int(cfg.WYEAR))


def price_day(d):
    md = d[5:] if d[5:] != "02-29" else "02-28"
    return ("2025-" if md >= "11" else "2026-") + md


def region_weights(regs):
    """Gas-heated homes per region if gb_national_scale.py has written them, else equal weights."""
    p = f"{cfg.D}/region_weights.json"
    w = json.load(open(p))["homes"] if os.path.exists(p) else {}
    return np.array([float(w.get(r, 1.0)) for r in regs])


def load():
    G = json.load(open(f"{cfg.D}/towns.json"))
    W = weather()
    P, C = (json.load(open(f"{cfg.D}/{n}.json")) for n in ("prices_year", "carbon_year"))
    towns = [t for t in G["towns"] if t[0] in W]
    rows, temps, carb = [], [], []
    for ti, (name, la, lo, reg) in enumerate(towns):
        by = {}
        for k, v in W[name].items():
            if v is not None:
                by.setdefault(k[:10], {})[int(k[11:13])] = v
        cser = C[reg]
        cmean = np.nanmean(list(cser.values())) if cser else 150.
        for d, hrs in sorted(by.items()):
            if len(hrs) < 24:
                continue
            h = np.array([hrs[i] for i in range(24)] + [hrs[23]])
            temps.append(np.interp(np.arange(48) / 2, np.arange(25), h))
            cd = price_day(d)
            c = np.array([cser.get(f"{cd}T{i // 2:02d}:{30 * (i % 2):02d}Z", np.nan) for i in range(48)], float)
            carb.append(np.where(np.isnan(c), cmean, c))
            rows.append((ti, name, la, lo, reg, d, cd))
    days = pd.DataFrame(rows, columns=["town_ix", "town", "lat", "lon", "region", "date", "price_date"])
    regs = sorted(G["regions"])
    pr = {}
    for kind in ("agile", "cosy"):
        arrs = []
        for r in regs:
            by = {}
            for k, v in P[f"{kind}_{r}"].items():
                by.setdefault(k[:10], {})[k[11:16]] = v
            prev, full = None, []
            for d in cfg.YDATES:                              # actual rates in date order; a gap borrows the day before
                x = by.get(d, {})
                row = [x.get(f"{i // 2:02d}:{30 * (i % 2):02d}") for i in range(48)]
                if None in row:
                    row = [v if v is not None else (prev[i] if prev is not None else np.nanmean(
                        [w for w in row if w is not None] or [25.])) for i, v in enumerate(row)]
                prev = np.array(row, float)
                full.append(prev)
            arrs.append(np.stack(full))
        pr[kind] = jnp.array(np.stack(arrs))                  # (R, 365, 48)
    days["reg_ix"] = days["region"].map({r: i for i, r in enumerate(regs)})
    days["day_ix"] = days["price_date"].map({d: i for i, d in enumerate(cfg.YDATES)})
    assert days["day_ix"].notna().all(), "weather day with no matching price day"
    T = np.stack(temps)
    wdates = sorted(days["date"].unique())
    days["wday"] = days["date"].map({d: i for i, d in enumerate(wdates)})       # weather-day index (366 in leap years)
    return days, jnp.array(T), jnp.array(np.stack(carb)), pr, towns, regs, sdp_phi(len(wdates))


def sdp_phi(n_wdays):
    """(T, weather-days, 48) float: share of homes that shed to gas under SD-Power dispatch (pass 1 -> gb_sdp_phi.py).
    Zero without --sdp-phi, so sdp reproduces ccop exactly."""
    if not cfg.SDP_PHI:
        return jnp.zeros((len(cfg.TARIFFS), n_wdays, 48))
    f = np.load(cfg.SDP_PHI)
    assert list(f["tariffs"]) == cfg.TARIFFS and f["phi"].shape[1] == n_wdays, "sdp_phi does not match this run"
    return jnp.array(f["phi"].astype(np.float32))


def price_block(pr, reg_ix, pidx, shape):
    """(T, B, 48) electricity prices for every tariff in cfg.TARIFFS."""
    slot_h = jnp.arange(48) / 2
    iog = jnp.where((slot_h >= 23.5) | (slot_h < 5.5), cfg.IOG[0], cfg.IOG[1])
    blocks = [jnp.broadcast_to(iog, shape), jnp.full(shape, cfg.SVR_P),
              pr["agile"][reg_ix, pidx], pr["cosy"][reg_ix, pidx]]
    blocks += [jnp.full(shape, e) for e, _ in cfg.FLAT]
    return jnp.stack(blocks)
