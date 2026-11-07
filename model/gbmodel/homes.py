"""The monitored house and the sampled housing stock (same draws as v1 gb_map.py so v2 reproduces v1).

stock_year(): the SAME B sampled homes run through every day of one town's year (lax.scan), returning per-home
year means for every tariff x controller, plus the per-day mean electricity per home per half-hour (for the grid
peak and flexibility analysis).
"""
import jax
import jax.numpy as jnp

from . import cfg
from .controllers import METRICS, a2a_policies, run_controllers
from .data import price_block
from .physics import (GAINS_SHAPE, HOUSE_SHARE, HOUSE_SHARE_T, SIZES, STOCK_LEVEL, STOCK_SHARE, STOCK_SHARE_T,
                      a2a_cop, a2a_derate, cap_kw, carnot_cop)

PEAK = jnp.zeros(48, bool).at[cfg.PEAK_SLOTS[0]:cfg.PEAK_SLOTS[1]].set(True)
NM = len(METRICS)


def gas_ps():
    return jnp.array(cfg.TARIFF_GAS)


def house_inputs(T, reg_ix, prA, prC, day_ix):
    """The monitored house's half-hourly demand, efficiency, capacity and prices on town-day rows (v1 physics)."""
    out = T
    prices = price_block({"agile": prA, "cosy": prC}, reg_ix, day_ix, out.shape)
    gains = 400. * GAINS_SHAPE[None, :]
    q_space = jnp.maximum(171.7 * (20.5 - out) - gains, 0.) * 0.5 / 1000
    q_dhw = jnp.zeros_like(out).at[:, 12:16].set(2.1 / 4).at[:, 35:39].set(2.1 / 4)
    flow = jnp.clip(46.4 - 0.95 * out - 7., 25., 55.)
    cop_s = carnot_cop(jnp.interp(out, HOUSE_SHARE_T, HOUSE_SHARE), flow, out)
    cop_d = carnot_cop(0.31, 41., out)
    q = q_space + q_dhw
    cop = jnp.where(q_dhw > 0, (q_space * cop_s + q_dhw * cop_d) / jnp.maximum(q, 1e-9), cop_s)
    cap = cap_kw(out, flow, 1.0) * 0.5
    eta = jnp.full(out.shape[0], 0.9)
    return dict(out=out, prices=prices, q_space=q_space, q_dhw=q_dhw, q=q, cop=cop, cop_s=cop_s, cap=cap, eta=eta, flow=flow)


def house(T, CARB, reg_ix, prA, prC, day_ix, wday, phi, key):
    """The monitored house on every town-day row (B = town-days). Same physics as v1 craig_house()."""
    h = house_inputs(T, reg_ix, prA, prC, day_ix)
    out, prices, q_space, q_dhw, q, cop, cop_s, cap, eta = (h[k] for k in
                                                            ("out", "prices", "q_space", "q_dhw", "q", "cop", "cop_s", "cap", "eta"))
    u = jax.random.uniform(key, out.shape)
    M, E = run_controllers(q, cop, cap, eta, out, prices, gas_ps(), CARB, phi[:, wday], u, PEAK)
    zone = jnp.full(out.shape[0], 0.45)
    nom = 0.45 * 171.7 * (20.5 - (-4.8)) / 1000 * 1.1 / a2a_derate(-4.8)
    a2 = a2a_policies(q_space, q_dhw, CARB, prices, gas_ps(), a2a_cop(out, 1.0), nom * a2a_derate(out) * 0.5, zone, eta)
    qs = q_space.sum(1)
    cop_w = jnp.where(qs > 0, qs / jnp.maximum((q_space / cop_s).sum(1), 1e-9), cop_s.mean(1))
    return M, a2, q.sum(1), jnp.stack([cop_w, qs, (q_space / cop_s).sum(1)])


def sample_homes(key, B, dout):
    """B homes for one town, drawn exactly as v1 stock() (same key splits, same order)."""
    k = jax.random.split(key, 12)
    ua = jnp.clip(jnp.exp(jnp.log(180.) + 0.45 * jax.random.normal(k[1], (B,))), 60., 450.)
    tset = jax.random.uniform(k[2], (B,), minval=19., maxval=21.5)
    gains_w = jax.random.uniform(k[3], (B,), minval=250., maxval=700.)
    dhw = jax.random.uniform(k[4], (B,), minval=2., maxval=8.)
    fdes = jax.random.uniform(k[5], (B,), minval=40., maxval=55.)
    frac = jax.random.uniform(k[6], (B,), minval=STOCK_LEVEL[0], maxval=STOCK_LEVEL[1])
    eta = jax.random.uniform(k[7], (B,), minval=0.85, maxval=0.92)
    load = ua * (tset - dout) / 1000 * jax.random.uniform(k[8], (B,), minval=1.0, maxval=1.2)
    per_kw = cap_kw(dout, fdes, 1.0) / 6.
    size = SIZES[jnp.clip(jnp.searchsorted(SIZES, load / per_kw), 0, SIZES.shape[0] - 1)]
    size_h = SIZES[jnp.clip(jnp.searchsorted(SIZES, cfg.HYB_SIZE * load / per_kw), 0, SIZES.shape[0] - 1)]
    k2 = jax.random.split(k[11], 3)
    zone = jax.random.uniform(k2[0], (B,), minval=0.3, maxval=0.6)
    amult = jax.random.uniform(k2[1], (B,), minval=0.85, maxval=1.15)
    nom = zone * ua * (tset - dout) / 1000 * jax.random.uniform(k2[2], (B,), minval=1.0, maxval=1.2) / a2a_derate(dout)
    return dict(ua=ua, tset=tset, gains_w=gains_w, dhw=dhw, fdes=fdes, frac=frac, eta=eta, size=size, size_h=size_h, zone=zone,
                amult=amult, nom=nom)


def stock_day(h, dout, out1, carb1, prices1, phi1, u):
    """All B homes on one day. out1, carb1: (48,); prices1, phi1: (T, 48); u: (B, 48) uniform draws.
    Returns M (T, C, NM, B), A2A (T, 5, B), heat q (B,), E-sum (T, C, 48) summed over homes."""
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
    q = q_space + q_dhw
    cop = jnp.where(q_dhw > 0, (q_space * cop_s + q_dhw * cop_d) / jnp.maximum(q, 1e-9), cop_s)
    cap = cap_kw(out, flow, (h["size"] / 6.)[:, None]) * 0.5
    cap_h = None if cfg.HYB_SIZE >= 1.0 else cap_kw(out, flow, (h["size_h"] / 6.)[:, None]) * 0.5
    M, E = run_controllers(q, cop, cap, h["eta"], out, prices, gas_ps(), carb, phi, u, PEAK, cap_h)
    a2 = a2a_policies(q_space, q_dhw, carb, prices, gas_ps(), a2a_cop(out, h["amult"][:, None]),
                      (h["nom"][:, None] * a2a_derate(out)) * 0.5, h["zone"], h["eta"])
    return M, a2, q.sum(1), E.sum(2)


def stock_year(key, T, CARB, dout, town_days, reg_ix, day_ix, wday, prA, prC, phi, B):
    """Every home through every day of the town. Returns (year-mean M (T,C,NM,B), heat-weighted boiler share
    (T,C,B), year-mean A2A (T,5,B) with row 3 heat-weighted, E per day (days, T, C, 48) mean kWh per home)."""
    h = sample_homes(key, B, dout)
    ku = jax.random.fold_in(key, 7777)          # SD-Power shed draws: independent of the home draws (v1-identical)
    pr = {"agile": prA, "cosy": prC}

    def step(c, d):
        p1 = price_block(pr, reg_ix[d][None], day_ix[d][None], (1, 48))[:, 0, :]
        u = jax.random.uniform(jax.random.fold_in(ku, d), (B, 48))
        M, a2, q, Es = stock_day(h, dout, T[d], CARB[d], p1, phi[:, wday[d]], u)
        sm, sa, sq, sa_share = c
        return (sm + M, sa + a2, sq + q, sa_share + a2[:, 3] * q), Es / B

    nT, nC = len(cfg.TARIFFS), len(cfg.CTRL)
    z = (jnp.zeros((nT, nC, NM, B)), jnp.zeros((nT, 5, B)), jnp.zeros(B), jnp.zeros((nT, B)))
    (sm, sa, sq, sas), Ed = jax.lax.scan(step, z, town_days)
    n = town_days.shape[0]
    boiler_share = sm[:, :, METRICS.index("boiler_heat_kwh")] / jnp.maximum(sq, 1e-9)
    a2m = (sa / n).at[:, 3].set(sas / jnp.maximum(sq, 1e-9))
    return sm / n, boiler_share, a2m, Ed
