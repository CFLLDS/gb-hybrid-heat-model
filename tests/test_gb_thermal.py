"""Known-answer tests for the v3 thermal-mass and pre-heating controller (scripts/spark/gbmodel/thermal.py).
Runs in the Spark image (needs JAX):
  docker run --rm -e JAX_PLATFORMS=cpu -v $HOME/cfl-model/v3:/work -w /work cfl-model:1 python -m pytest -q tests/test_gb_thermal.py
"""
import os
import sys

import numpy as np
import pytest

jnp = pytest.importorskip("jax.numpy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "spark"))
sys.path.insert(0, "/work/scripts")
from gbmodel.thermal import X_MAX, preheat, tau_hours  # noqa: E402

GAS = 8.17


def run(price, q=0.8, c=6.5, ua=0.21, cop=3.0, cap=3.0, hybrid=False, dhw=0.0):
    """One home, one day. price: (48,) p/kWh. q: heat to hold the set point per half-hour (kWh)."""
    f = lambda v: jnp.broadcast_to(jnp.asarray(v, jnp.float32), (1, 48))                 # noqa: E731
    el, gs, hs, cost, kg, x = preheat(f(q), f(dhw), f(cop), f(cap), jnp.array([0.9]), f(price), GAS, f(150.),
                                      jnp.array([ua]), jnp.array([c]), hybrid)
    return np.asarray(el[0]), np.asarray(gs[0]), np.asarray(hs[0]), float(cost[0]), np.asarray(x[0])


def plain_cost(price, q=0.8, cop=3.0, hybrid=False):
    p = np.asarray(price, float)
    if hybrid:
        return float(np.minimum(p / cop, GAS / 0.9).sum() * q)
    return float((p / cop).sum() * q)


def test_flat_price_never_pre_heats():
    price = np.full(48, 25.0)
    el, gs, hs, cost, x = run(price)
    assert cost == pytest.approx(plain_cost(price), rel=1e-4)
    assert x.max() == 0


def test_no_thermal_mass_gives_the_plain_controller():
    price = np.where(np.arange(48) < 11, 7.0, 30.0)
    *_, cost, x = run(price, c=1e-4)
    assert cost == pytest.approx(plain_cost(price), rel=2e-3)


def test_cheap_window_is_used_and_the_floor_is_never_breached():
    price = np.where((np.arange(48) >= 8) & (np.arange(48) < 12), 5.0, 35.0)    # 04:00-06:00 cheap
    el, gs, hs, cost, x = run(price)
    assert cost < plain_cost(price) * 0.95                                    # pre-heating saves money
    assert x.min() >= 0 and x.max() <= X_MAX + 1e-6                           # comfort floor and band held
    assert x[12] > 0                                                          # stored heat leaving the window
    assert hs.sum() >= 0.8 * 48 - 1e-3                                        # never less heat than the day needs


def test_hybrid_pre_heat_never_costs_more_than_hybrid_plain():
    rng = np.random.default_rng(1)
    for _ in range(5):
        price = rng.uniform(-5, 60, 48)
        *_, cost, _ = run(price, hybrid=True)
        assert cost <= plain_cost(price, hybrid=True) + 1e-3


def test_time_constant_matches_measured_gb_homes():
    # Halloran et al. 2024 median: C 6.5 kWh/K, heat loss 0.21 kW/K -> tau ~31 h (measured GB range 23-44 h)
    assert 23 <= float(tau_hours(jnp.array(0.21), jnp.array(6.5))) <= 44


@pytest.mark.parametrize("hybrid", [False, True])
def test_stored_heat_never_exceeds_heat_pump_capacity(hybrid):
    """Fix 8 Nov 2026: a very cheap (even negative) slot must not 'charge' the home beyond the heat pump's output.
    Heat made in any half-hour <= max(capacity, heat to hold the set point) -- no 40 kW resistance pre-heat."""
    price = np.full(48, 35.0)
    price[8:10] = -5.0                                                        # two negative Agile slots
    cap, q = 1.0, 0.8
    el, gs, hs, cost, x = run(price, q=q, cap=cap, hybrid=hybrid)
    assert (hs <= np.maximum(cap, q + 0.21 * x[:-1] * 0.5) + 1e-4).all()
    assert x.min() >= 0
    if not hybrid:
        assert el.max() <= max(cap / 3.0, q) + 1e-4                           # never direct-electric storage
