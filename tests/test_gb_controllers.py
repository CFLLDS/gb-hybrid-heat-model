"""Known-answer tests for the GB model v2 controllers (scripts/spark/gbmodel/controllers.py).

Needs JAX, so it runs in the Spark image:
  docker run --rm -e JAX_PLATFORMS=cpu -v $HOME/cfl-model:/work cfl-model:1 python -m pytest -q /work/tests/test_gb_controllers.py
"""
import os
import sys

import numpy as np
import pytest

jnp = pytest.importorskip("jax.numpy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "spark"))
sys.path.insert(0, "/work/scripts")
from gbmodel import cfg  # noqa: E402
from gbmodel.controllers import METRICS, run_controllers  # noqa: E402

C = {c: i for i, c in enumerate(cfg.CTRL)}
M = {m: i for i, m in enumerate(METRICS)}


def case(price, cop, out=5., q=1.0, cap=10., carb=200., phi=0.0, u=0.5, eta=0.9, gas_p=cfg.GAS_P):
    """One home, one day, flat across 48 slots. Returns M (C, NM) for tariff 0 and E (C, 48)."""
    f = lambda v: jnp.full((1, 48), v)                                                   # noqa: E731
    Mx, E = run_controllers(f(q), f(cop), f(cap), jnp.array([eta]), f(out), jnp.full((1, 1, 48), price),
                            jnp.array([gas_p]), f(carb), jnp.full((1, 1, 48), phi), f(u), jnp.zeros(48, bool))
    return np.asarray(Mx[0, :, :, 0]), np.asarray(E[0, :, 0])


def test_ccop_switches_exactly_at_heat_per_penny_parity():
    parity = cfg.GAS_P / 0.9 * 3.0                       # price at which elec heat per penny == gas, COP 3
    hp_side, _ = case(parity - 0.01, 3.0)
    gas_side, _ = case(parity + 0.01, 3.0)
    assert hp_side[C["ccop"], M["gas_kwh"]] == 0
    assert gas_side[C["ccop"], M["elec_kwh"]] == 0


def test_ccop_uses_heat_pump_on_negative_prices():         # v1 chose gas here (ratio test sign bug)
    r, _ = case(-5.0, 3.0)
    assert r[C["ccop"], M["gas_kwh"]] == 0 and r[C["ccop"], M["cost_p"]] < cfg.GAS_SC


def test_bivalent_follows_outside_temperature_not_price():
    for t in cfg.BIVALENT:
        warm, _ = case(100.0, 1.5, out=t + 0.1)            # absurd price, still heat pump above the switch
        cold, _ = case(1.0, 6.0, out=t - 0.1)              # nearly free, still boiler below it
        assert warm[C[f"biv{t:g}"], M["gas_kwh"]] == 0
        assert cold[C[f"biv{t:g}"], M["elec_kwh"]] == 0


def test_carbon_price_moves_choice_to_lower_carbon():
    # cheap-but-dirty electricity: cost says heat pump; a huge carbon price on a 900 g grid says gas
    lam = max(cfg.LAMBDA)
    r, _ = case(5.0, 2.0, carb=900.)
    assert r[C["ccop"], M["gas_kwh"]] == 0
    kg_e, kg_g = 900 / 1000 / 2.0, cfg.GAS_KG / 0.9         # per kWh heat
    if lam * kg_e > lam * kg_g + (cfg.GAS_P / 0.9 - 5.0 / 2.0):
        assert r[C[f"ccop_c{lam:g}"], M["elec_kwh"]] == 0


def test_sdp_sheds_a_home_only_when_its_draw_is_below_phi():
    shed, e = case(10.0, 3.0, phi=0.6, u=0.5)        # u < phi: this home is in the shed share -> gas
    keep, _ = case(10.0, 3.0, phi=0.4, u=0.5)        # u >= phi: keeps the heat pump
    assert shed[C["ccop"], M["gas_kwh"]] == 0
    assert shed[C["sdp"], M["elec_kwh"]] == 0 and e[C["sdp"]].sum() == 0
    assert keep[C["sdp"], M["gas_kwh"]] == 0


def test_sdp_equals_ccop_without_shedding():
    r, _ = case(30.0, 2.5, out=-3., phi=0.0)
    assert np.allclose(r[C["sdp"]], r[C["ccop"]])


def test_capacity_shortfall():
    r, _ = case(10.0, 3.0, q=2.0, cap=1.5)
    assert r[C["hp"], M["unmet_kwh"]] == pytest.approx(0.5 * 48)
    assert r[C["ccop"], M["boiler_heat_kwh"]] == pytest.approx(0.5 * 48)      # hybrid boiler tops up
    assert r[C["hp"], M["cost_p"]] == pytest.approx((1.5 / 3 + 0.5) * 10 * 48)  # shortfall at COP 1, no gas SC


def test_standing_charge_only_with_a_gas_meter():
    r, _ = case(10.0, 3.0, q=0.0)
    assert r[C["hp"], M["cost_p"]] == 0
    for c in cfg.CTRL:
        if c != "hp":
            assert r[C[c], M["cost_p"]] == pytest.approx(cfg.GAS_SC)


def test_smaller_hybrid_heat_pump_hands_more_to_the_boiler():
    f = lambda v: jnp.full((1, 48), v)                                                   # noqa: E731
    args = (f(2.0), f(3.0), f(10.0), jnp.array([0.9]), f(5.), jnp.full((1, 1, 48), 10.0), jnp.array([cfg.GAS_P]), f(200.),
            jnp.zeros((1, 1, 48)), f(0.5), jnp.zeros(48, bool))
    full, _ = run_controllers(*args)
    half, _ = run_controllers(*args, cap_hyb=f(1.2))
    full, half = np.asarray(full[0, :, :, 0]), np.asarray(half[0, :, :, 0])
    assert half[C["hp"]].tolist() == full[C["hp"]].tolist()                             # all-electric unit unchanged
    assert half[C["ccop"], M["boiler_heat_kwh"]] == pytest.approx(0.8 * 48)            # 2.0 - 1.2 per slot to gas
