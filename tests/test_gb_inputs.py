"""Known-answer tests for the sourced home inputs (scripts/spark/gbmodel/inputs.py); numpy only, runs anywhere.
Each test checks a formula against the number its source states (docs/article/lit/model_inputs.md)."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "spark"))
from gbmodel import inputs as IN  # noqa: E402

RNG = np.random.default_rng(1)


def test_sap_occupancy_matches_sap_table_1b():
    assert IN.sap_occupancy(np.array(10.0), np) == pytest.approx(1.0)                 # tiny homes: one person
    assert 2.3 < float(IN.sap_occupancy(np.array(85.0), np)) < 2.7                     # a typical GB home ~2.5
    assert float(IN.sap_occupancy(np.array(200.0), np)) < 3.3                          # saturates


def test_hot_water_mean_matches_est_2008():
    # EST 2008: 122 litres/day mean -> ~4.7 kWh/day at the tap; with 1.15 losses ~5.3-5.4 kWh/day of heat
    n = np.full(200_000, (122 - 46) / 26)                                             # occupancy giving 122 L/day
    d = IN.dhw_kwh_day(n, RNG.standard_normal(n.size), np)
    assert d.mean() == pytest.approx(4.18 * 122 * 36.7 / 3600 * 1.15, rel=0.02)
    assert np.percentile(d, 10) < 3.5 and np.percentile(d, 90) > 7.5                  # wider than the old U(2, 8)


def test_gains_match_sap_anchors():
    assert IN.gains_w(np.array(50.0), np.array(0.5), np) == pytest.approx(360.0)
    assert IN.gains_w(np.array(120.0), np.array(0.5), np) == pytest.approx(620.0)


def test_set_point_and_boiler_distributions():
    t = IN.set_point(RNG.standard_normal(200_000), np)
    e = IN.boiler_eta(RNG.standard_normal(200_000), np)
    assert t.mean() == pytest.approx(18.8, abs=0.02) and t.min() >= 16 and t.max() <= 21.5
    assert e.mean() == pytest.approx(0.84, abs=0.002) and e.min() >= 0.72 and e.max() <= 0.91
