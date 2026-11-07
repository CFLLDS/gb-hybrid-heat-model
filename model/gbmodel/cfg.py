"""Run configuration for the GB hybrid-heating model v2 (LDS Public Class No. 1, Nov 2026).

Everything the CLI can change lives here, so every module reads one source. Prices in pence, energy in kWh per
half-hour slot unless named otherwise, carbon in gCO2/kWh, carbon prices in pence per kg (GBP 1/t = 0.1 p/kg).
"""
import sys

import numpy as np


def ARG(k, d):
    return type(d)(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d


STOCK, SEED = ARG("--stock", 32000), ARG("--seed", 5112026)
WYEAR = ARG("--weather", "2025")            # heating year 1 Nov WYEAR .. 31 Oct WYEAR+1 (1940..2025)
D, OUT = ARG("--data", "/work/data/gb"), ARG("--out", "/work/out/v2/2025")
YDATES = [str(np.datetime64("2025-11-01") + i) for i in range(365)]     # the price/carbon year every weather year uses

# Fixed prices (Ofgem cap Oct-Dec 2025 era, as v1): gas p/kWh, gas standing p/day, SVR p/kWh, IOG (cheap, peak)
GAS_P, GAS_SC, SVR_P, IOG = 8.17, 29.16, 26.47, (6.6, 35.61)
GAS_KG = 0.183                               # kgCO2 per kWh of gas burned (v1 value; article cites the source)
# Extra flat tariffs for the levy-rebalancing sweep: "--flat 20:9.5,15:10.5" = elec p : gas p pairs (gas SC unchanged)
FLAT = [tuple(float(x) for x in p.split(":")) for p in ARG("--flat", "").split(",") if p]
TARIFFS = ["iog", "svr", "agile", "cosy"] + [f"flat{e:g}_{g:g}" for e, g in FLAT]
TARIFF_GAS = [GAS_P] * 4 + [g for _, g in FLAT]

# Controllers. Carbon-aware C-COP prices carbon at LAMBDA p/kg (GBP 1/t = 0.1 p/kg). Defaults, from
# docs/article/lit/carbon_policy.json: ~GBP 40/t, the UK ETS traded range 2025 (DESNZ Feb 2026, GBP 22-44), and
# GBP 312/t, the DESNZ central appraisal carbon value for 2025 (data tables, Oct 2026).
LAMBDA = tuple(float(x) for x in ARG("--lambda", "4,31.2").split(","))
# Fixed changeover outside temps, C (docs/article/lit/controls_flex.json): 0 = Vaillant sensoCOMFORT factory default
# ("Bivalence pt" heating 0 C); 2 = the EU 813/2013 bivalent ceiling, ~Daikin's worked example (2.5 C); 5 = a cautious
# installer setting.
BIVALENT = tuple(float(x) for x in ARG("--bivalent", "0,2,5").split(","))
CTRL = (["gas", "hp"] + [f"biv{t:g}" for t in BIVALENT] + ["ccop"] + [f"ccop_c{lam:g}" for lam in LAMBDA]
        + ["ccop_nopeak", "sdp"])
# SD-Power dispatch (v2.1): C-COP, except that in any half-hour where Britain's total demand (NESO national demand
# + the stock's heat-pump load under C-COP) would exceed a cap, a random fraction phi of homes use gas instead, just
# enough to hold the total at the cap. phi (tariff, weather-day, slot) comes from pass 1 (gb_sdp_phi.py); without
# --sdp-phi it is zero and sdp == ccop.
SDP_PHI = ARG("--sdp-phi", "")
# Hybrid heat-pump sizing (sensitivity, Craig 7 Nov): share of the design heat load the HYBRID's heat pump is sized to
# cover. 1.0 = the same unit as the all-electric home (default, as every main result); 0.55 = the MCS MIS 3005-D
# minimum for a hybrid (docs/article/lit/methods_data.json). The all-heat-pump home always keeps the full-size unit.
HYB_SIZE = ARG("--hyb-size", 1.0)
PEAK_SLOTS = (32, 38)                        # 16:00-19:00

DAY_IX = None                                # per town-day row: index into YDATES (set by data.load before tracing)
