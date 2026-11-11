"""Sourced home inputs (model v3, "--inputs sourced"; docs/article/lit/model_inputs.{json,md}).

Replaces the v2 assumptions with distributions from GB evidence. The same formulas are used by the model (JAX) and
by the stock calibration (numpy, gb_v3_calibrate.py), so the two cannot drift apart (pass xp = jnp or np).
  occupancy N      SAP 10.2 Table 1b: N = 1 + 1.76 (1 - exp(-0.000349 (TFA - 13.9)^2)) + 0.0013 (TFA - 13.9), TFA > 13.9
  hot water        EST (2008) in-situ study: litres/day = 46 + 26 N (mean 122 L); heat = 4.18 x L x 36.7 K / 3600 kWh,
                   x 1.15 distribution and storage losses, x household scatter LN(-0.08, 0.4) (mean 1) -> ~5.3 kWh/day
  internal gains   SAP 10.2 total internal gains by floor area (~360 W at 50 m2 to ~620 W at 120 m2, linear, clipped
                   250-900 W) x U(0.75, 1.25); the daily profile (homes.GAINS_SHAPE) remains an assumption
  set point        24-hour whole-house heating-season mean, Energy Follow-Up Survey 2017: N(18.8, 1.0) on [16, 21.5]
  boiler           in-use seasonal efficiency, gross CV, EST (2009) field trial (combi 82.5%) / SAP default 84%:
                   N(0.84, 0.035) on [0.72, 0.91]
"""


def sap_occupancy(tfa, xp):
    d = xp.maximum(tfa - 13.9, 0.0)
    return xp.where(tfa > 13.9, 1 + 1.76 * (1 - xp.exp(-0.000349 * d ** 2)) + 0.0013 * d, 1.0)


def dhw_kwh_day(n_occ, scatter, xp):
    """scatter: standard-normal draws -> lognormal household factor with mean 1."""
    litres = 46 + 26 * n_occ
    return 4.18 * litres * 36.7 / 3600 * 1.15 * xp.exp(-0.08 + 0.4 * scatter)


def gains_w(tfa, u01, xp):
    """u01: uniform(0,1) draws -> x U(0.75, 1.25)."""
    base = xp.clip(360.0 + (620.0 - 360.0) / 70.0 * (tfa - 50.0), 250.0, 900.0)
    return base * (0.75 + 0.5 * u01)


def truncnorm(z, mean, sd, lo, hi, xp):
    """Map standard-normal draws to a normal clipped to [lo, hi] (clipping, stated in the paper; the tails are small)."""
    return xp.clip(mean + sd * z, lo, hi)


def set_point(z, xp):
    return truncnorm(z, 18.8, 1.0, 16.0, 21.5, xp)


def boiler_eta(z, xp):
    return truncnorm(z, 0.84, 0.035, 0.72, 0.91, xp)
