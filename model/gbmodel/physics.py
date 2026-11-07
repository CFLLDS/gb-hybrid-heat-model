"""Heat pump physics shared by the monitored house and the stock (unchanged from v1, gb_map.py, 6 Nov 2026).

COP = Carnot share(outside temp) x (flow + 273.15) / max(flow - out, 5), clipped 1.3..7.
  - Monitored house: its own measured share (318 days of daily COP + its heatpumpmonitor.org space days 12-16 C).
  - Stock: the share of 55 GB space-split air-source systems on heatpumpmonitor.org (10,628 system-days), scaled per home
    between the Electrification of Heat median (SPF 2.80) and the tuned fleet (3.88): x0.72 .. x1.0.
Capacity: Daikin ERGA06 table (35/45 C flow), scaled to the unit size.
"""
import jax.numpy as jnp

CAP_OUT = jnp.array([-7., 2., 7., 12.])
CAP35, CAP45 = jnp.array([6.3, 6.2, 7.8, 7.6]), jnp.array([6.3, 6.1, 7.4, 7.0])
GAINS_SHAPE = jnp.array([0.7] * 12 + [1.1] * 6 + [0.8] * 14 + [1.3] * 10 + [1.0] * 6)
SIZES = jnp.array([4., 5., 6., 7., 8., 9., 11., 14., 16., 20.])
HOUSE_SHARE_T = jnp.array([1.5, 4.5, 7.5, 11.0, 14.0])
HOUSE_SHARE = jnp.array([0.353, 0.335, 0.313, 0.250, 0.205])
STOCK_SHARE_T = jnp.array([-3.0, 1.5, 4.5, 7.5, 10.5, 14.0])
STOCK_SHARE = jnp.array([0.3415, 0.3506, 0.3628, 0.3620, 0.3434, 0.3124])
STOCK_LEVEL = (2.80 / 3.88, 1.0)
A2A_COND = 38.


def carnot_cop(share, flow, out):
    return jnp.clip(share * (flow + 273.15) / jnp.maximum(flow - out, 5.), 1.3, 7.)


def cap_kw(out, flow, scale):
    a, b = jnp.interp(out, CAP_OUT, CAP35), jnp.interp(out, CAP_OUT, CAP45)
    return (a + (b - a) * jnp.clip((flow - 35.) / 10., 0., 1.)) * scale


def a2a_cop(out, mult):
    """Air-to-air COP: ASSUMED 0.40 x Carnot at ~38 C condensing, from manufacturer data incl. defrost."""
    return jnp.clip(0.40 * mult * (A2A_COND + 273.15) / jnp.maximum(A2A_COND - out, 5.), 1.5, 6.)


def a2a_derate(out):
    return jnp.clip(1. - 0.02 * jnp.maximum(7. - out, 0.), 0.6, 1.0)
