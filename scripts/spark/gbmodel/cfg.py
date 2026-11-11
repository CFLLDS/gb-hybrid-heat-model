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
# The price/carbon year every weather year is priced on (default 2025-26). "--price-year Y" with --data pointing at a
# folder holding that year's prices_year/carbon_year/tariffs.json (data/gb/years/<Y>, gb_v3_prices.py) runs a
# matched weather+price year; tariffs.json then replaces the flat SVR, gas, gas standing charge and IOG rates.
PRICE_YEAR = ARG("--price-year", 2025)
_n_days = int((np.datetime64(f"{PRICE_YEAR + 1}-11-01") - np.datetime64(f"{PRICE_YEAR}-11-01")) / np.timedelta64(1, "D"))
YDATES = [str(np.datetime64(f"{PRICE_YEAR}-11-01") + np.timedelta64(i, "D")) for i in range(_n_days)]

# Fixed prices (Ofgem cap Oct-Dec 2025 era, as v1): gas p/kWh, gas standing p/day, SVR p/kWh, IOG (cheap, peak)
GAS_P, GAS_SC, SVR_P, IOG = 8.17, 29.16, 26.47, (6.6, 35.61)
if PRICE_YEAR != 2025:                                   # that year's flat rates (money of the day, Ofgem cap / scaled)
    import json as _json
    _t = _json.load(open(f"{D}/tariffs.json"))
    GAS_P, GAS_SC, SVR_P, IOG = _t["gas_p"], _t["gas_sc_p_day"], _t["svr_p"], tuple(_t["iog"])
# Review 4 (9 Nov 2026), one fiscal basis: "--iog cheap:peak" overrides the IOG rates (v4: 6.6:36.39, Southern
# INTELLI-VAR-24-10-29-H from 25 Oct 2026, VAT-free, the same period as the Oct-Dec 2026 cap SVR and gas); "--exvat"
# divides the 2025-26 Agile and Cosy rates before 1 Oct 2026 (when VAT on domestic electricity was removed) by 1.05.
if "--iog" in sys.argv:
    IOG = tuple(float(x) for x in ARG("--iog", "").split(":"))
EXVAT = "--exvat" in sys.argv
EXVAT_UNTIL = "2026-09-30T23:00Z"            # 1 Oct 2026 00:00 BST; earlier half-hours carried 5% VAT
GAS_KG = 0.183                               # kgCO2 per kWh of gas burned (v1 value; article cites the source)
# Extra flat tariffs for the levy-rebalancing sweep: "--flat 20:9.5,15:10.5" = elec p : gas p pairs (gas SC unchanged)
FLAT = [tuple(float(x) for x in p.split(":")) for p in ARG("--flat", "").split(",") if p]
# That year's real prices (Craig, 7 Nov: "run each winter at that year's real prices... lean into fuel poverty"):
# "--hist-price elec:gas:gas_sc" = the year's electricity and gas UNIT rates (p/kWh) and gas standing charge (p/day),
# 2025 money, split from the 80-year all-in series (data/gb/hist_prices.json, see its "basis") -> tariff "hist".
HIST = tuple(float(x) for x in ARG("--hist-price", "").split(":")) if "--hist-price" in sys.argv else None
TARIFFS = (["iog", "svr", "agile", "cosy"] + [f"flat{e:g}_{g:g}" for e, g in FLAT] + (["hist"] if HIST else []))
TARIFF_GAS = [GAS_P] * 4 + [g for _, g in FLAT] + ([HIST[1]] if HIST else [])
TARIFF_SCV = [GAS_SC] * (4 + len(FLAT)) + ([HIST[2]] if HIST else [])    # gas standing charge p/day per tariff

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
# Thermal mass and pre-heating (model v3, thermal.py): adds controllers hp_pre and ccop_pre. Sampled homes get a time
# constant drawn log-normally around the measured GB median (Halloran et al. 2024: 30.6 h; GB range 23-44 h); the
# monitored house uses its measured fabric store, 7.78 kWh/K.
PREHEAT = "--preheat" in sys.argv
# Real housing stock (v3, gb_v3_stock.py -> data/gb/stock_v3.npz): each home's heat-loss coefficient and heat capacity
# are drawn from its town's dwelling records (Canet et al. 2022 EPC by LSOA + NEED, calibrated to DESNZ metered gas)
# instead of the sampled log-normal. Other home parameters (set point, gains, hot water, emitters, efficiency level,
# boiler) stay sampled. "--stock-v3 central|low|high" picks the gas-per-heated-home variant (htc_<variant> if present).
STOCK_V3 = ARG("--stock-v3", "")
INPUTS = ARG("--inputs", "v2")                       # "sourced": set point, gains, hot water, boiler from inputs.py
C_VARIANT = ARG("--thermal-mass", "medium")            # SAP 2012 Table 1f: low 100, medium 250, high 450 kJ/m2K
TAU_MEDIAN_H, TAU_SIGMA = ARG("--tau-median", 31.0), 0.30
HOUSE_C_KWH_K = 7.78
PEAK_SLOTS = (32, 38)                        # 16:00-19:00

# Hostile-review sensitivities (9 Nov 2026). All inert at their defaults; a default run reproduces v3-final exactly.
# --cop-level lo:hi   stock heat-pump efficiency level range (default physics.STOCK_LEVEL, 0.72..1.0); lo == hi fixes it
# --cop-corr r        Gaussian-copula correlation between the level and -log(heat loss): r > 0 gives leakier homes the
#                     poorer installations (default 0 = independent, the v3 draw, unchanged)
# --weekday-align     price each weather day on the 2025-26 day with the same weekday, nearest to the calendar match
#                     (shift -3..+3 days, kept inside the price year), instead of the same calendar day
# --agile-add f.npz   adder (p/kWh inc VAT, array "add" shaped (price-days, 48)) on every region's Agile, capped at
#                     the Agile cap 100p: the price feedback of the stock's own demand (gb_feedback.py)
COP_LEVEL = tuple(float(x) for x in ARG("--cop-level", "").split(":")) if "--cop-level" in sys.argv else None
COP_CORR = ARG("--cop-corr", 0.0)
WEEKDAY_ALIGN = "--weekday-align" in sys.argv
AGILE_ADD = ARG("--agile-add", "")
DIV_LIB = ARG("--div-lib", "")               # review: measured heating habits library (gbmodel/diversity.py); "" = off
DIV_SETBACK = ARG("--div-setback", 3.0)
# Measured hybrid switching (10 Nov 2026, from the Electrification of Heat trial's 141 metered hybrids, UKDS SN 9209):
# "--biv-meas f.json" adds controller bivm, a fixed per-home changeover temperature drawn so that the stock's boiler
# share of heat at each outdoor temperature equals the trial's measured share ("hybrid_boiler_share_by_temp" in the
# file: 2 C bins, lower edge -> share). Homes whose draw lies beyond the coldest bin never use the boiler; beyond the
# warmest bin they never use the heat pump in the heating season. Inert when unset.
BIV_MEAS = ARG("--biv-meas", "")
if BIV_MEAS:
    import json as _json
    _hb = _json.load(open(BIV_MEAS))["hybrid_boiler_share_by_temp"]
    _pairs = sorted((float(t) + 1.0, s) for t, s in _hb.items() if -8 <= float(t) <= 14)   # bin centre, boiler share
    BIV_MEAS_T = np.array([t for t, _ in _pairs])
    BIV_MEAS_S = np.array([s for _, s in _pairs])
    CTRL = CTRL + ["bivm"]

if PREHEAT:
    CTRL = CTRL + ["hp_pre", "ccop_pre"]
DAY_IX = None                                # per town-day row: index into YDATES (set by data.load before tracing)
