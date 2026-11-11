"""Thermal mass and pre-heating (model v3; docs/article/lit/methods_v3.md section 1).

Each home is one thermal node (1R1C): heat-loss coefficient UA (kW/K) and heat capacity C (kWh/K), so tau = C/UA.
Comfort is a floor: the home may be warmed up to X_MAX above its set point (stored heat) but never below it.
State x = excess temperature above set point, on K levels 0..X_MAX. In each half-hour the heat the system must make
to move from x to x' is the energy balance

    h = q_space + UA * (x + x') / 2 * dt + C * (x' - x)              (q_space: heat to hold the set point, as v2)

which must be >= 0 (a home cannot cool faster than its own losses allow). Besides moving to any level, the home can
COAST (heating off): it then cools by its own losses and lands between levels, where the value is interpolated --
without this a 0.25 K grid could never coast (a typical home cools ~0.1 K per half-hour). Hot water is made when it
is used. A backward dynamic programme over the 48 half-hours values every level; the forward pass, from x = 0 at
midnight, follows the continuous temperature and recovers the heat, electricity and gas.

Two controllers:
  hp_pre    all heat pump, pre-heating into cheap half-hours; beyond capacity, direct electric at COP 1
  ccop_pre  hybrid C-COP, pre-heating: each kWh of heat from whichever source is cheaper in that half-hour
Simplifications (stated in the paper): COP is not reduced for the slightly hotter water that stored heat needs;
1R1C ignores the fast air node and emitter mass; days are independent (x = 0 at each midnight).
"""
import jax
import jax.numpy as jnp

X_MAX, K, DT = 3.0, 9, 0.5          # 9 levels (0.375 K); the coast action covers in-between temperatures
LEVELS = jnp.linspace(0.0, X_MAX, K)


def _slot_cost(h, cop, cap, price, gas_p, eta, carb, hybrid):
    """Cost (p), electricity (kWh), gas fuel (kWh), kg for making heat h (kWh) in one half-hour. Shapes broadcast."""
    hp_h = jnp.minimum(h, cap)
    if hybrid:
        hp_cheaper = (price / cop) < (gas_p / eta)
        hp_part = jnp.where(hp_cheaper, hp_h, 0.0)
        elec = hp_part / cop
        gas = (h - hp_part) / eta
    else:
        elec = hp_h / cop + (h - hp_h)
        gas = jnp.zeros_like(h)
    cost = elec * price + gas * gas_p
    kg = elec * carb / 1000.0 + gas * 0.183
    return cost, elec, gas, kg


def _interp(V, x):
    """V: (B, K) on LEVELS; x: (B,) continuous excess in [0, X_MAX] -> linear interpolation (B,)."""
    step = X_MAX / (K - 1)
    u = jnp.clip(x / step, 0.0, K - 1 - 1e-6)
    i = jnp.floor(u).astype(jnp.int32)
    w = u - i
    b = jnp.arange(V.shape[0])
    return (1 - w) * V[b, i] + w * V[b, jnp.minimum(i + 1, K - 1)]


def _candidates(x, s, V_next, q_space, q_dhw, cop, cap, eta, price, gas_p, carb, ua, c, hybrid):
    """From continuous excess x (B,) in slot s: every grid target level, plus 'coast' (heating off, landing between
    levels), plus 'full' (heat pump at capacity). Returns total (B, K+2), next x (B, K+2) and the slot's (cost, elec, gas, kg, space heat) per candidate."""
    # 'full': run the heat pump at capacity and store what is left after the demand (lands between levels; without it
    # a 0.375 K grid step can need more heat than a small heat pump makes in a half-hour, so it could never charge)
    h_max = jnp.maximum(cap[:, s], q_space[:, s] + ua * x * DT + q_dhw[:, s])
    x_full = jnp.clip((h_max - q_dhw[:, s] - q_space[:, s] - ua * x * DT / 2 + c * x) / (c + ua * DT / 2), 0.0, X_MAX)
    xn = jnp.concatenate([jnp.broadcast_to(LEVELS, (x.shape[0], K)),
                          ((c * x - q_space[:, s] - ua * x * DT / 2) / (c + ua * DT / 2))[:, None], x_full[:, None]], axis=1)
    hs = q_space[:, s][:, None] + ua[:, None] * (x[:, None] + xn) / 2 * DT + c[:, None] * (xn - x[:, None])
    coast = jnp.zeros_like(hs, bool).at[:, K].set(True)
    ok = (hs >= -1e-6) & (xn >= -1e-6) & (xn <= X_MAX + 1e-6)
    hs = jnp.where(coast, 0.0, jnp.maximum(hs, 0.0))
    h = hs + q_dhw[:, s][:, None]
    # Power limit (fix 8 Nov 2026): heat can be STORED only from the heat pump, within its capacity. Above capacity
    # the boiler (hybrid) or direct electric (all heat pump) meets only the demand of the moment, i.e. holding the
    # current temperature; without this the DP "charged" homes at up to ~40 kW from resistance heat on cheap slots.
    ok = ok & (coast | (h <= h_max[:, None] + 1e-6))
    cost, el, gs, kg = _slot_cost(h, cop[:, s][:, None], cap[:, s][:, None], price[:, s][:, None], gas_p,
                                  eta[:, None], carb[:, s][:, None], hybrid)
    xn = jnp.clip(xn, 0.0, X_MAX)
    vn = jax.vmap(lambda col: _interp(V_next, col), in_axes=1, out_axes=1)(xn)
    tot = jnp.where(ok, cost + vn, jnp.inf)
    return tot, xn, (cost, el, gs, kg, hs)


def preheat(q_space, q_dhw, cop, cap, eta, price, gas_p, carb, ua_kw, c_kwh, hybrid):
    """q_space, q_dhw, cop, cap, price, carb: (B, 48); eta, ua_kw, c_kwh: (B,); gas_p scalar.
    Returns elec (B, 48), gas_fuel (B, 48), heat_space_made (B, 48), cost_p (B,), kg (B,), x_path (B, 49)."""
    B = q_space.shape[0]
    args = (q_space, q_dhw, cop, cap, eta, price, gas_p, carb, ua_kw, c_kwh, hybrid)
    grid = jnp.broadcast_to(LEVELS, (B, K))

    def back(V_next, s):                            # value of each grid level at the start of slot s
        tot = jax.vmap(lambda xcol: _candidates(xcol, s, V_next, *args)[0].min(1), in_axes=1, out_axes=1)(grid)
        return tot, V_next

    V0 = jnp.zeros((B, K))
    _, Vs = jax.lax.scan(back, V0, jnp.arange(47, -1, -1))      # Vs[i] = V at the start of slot (47 - i) + 1
    Vnext = Vs[::-1]                                             # Vnext[s] = value-to-go from the start of slot s+1

    def fwd(x, s):
        tot, xn, (cost, el, gs, kg, hs) = _candidates(x, s, Vnext[s], *args)
        j = tot.argmin(1)
        b = jnp.arange(B)
        return xn[b, j], (el[b, j], gs[b, j], kg[b, j], cost[b, j], hs[b, j], xn[b, j])

    _, (el, gs, kg, cost, hs, xs) = jax.lax.scan(fwd, jnp.zeros(B), jnp.arange(48))
    el, gs, kg, cost, hs, xs = (a.T for a in (el, gs, kg, cost, hs, xs))
    return el, gs, hs, cost.sum(1), kg.sum(1), jnp.concatenate([jnp.zeros((B, 1)), xs], axis=1)


def tau_hours(ua_kw, c_kwh):
    return c_kwh / jnp.maximum(ua_kw, 1e-9)


def capacity_from_floor(floor_m2, kj_per_m2k=250.0):
    """SAP thermal mass parameter (kJ/m2K) x floor area -> kWh/K. 250 = SAP 'medium' (Canet & Qadrdan 2023)."""
    return kj_per_m2k * floor_m2 / 3600.0
