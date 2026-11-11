#!/usr/bin/env python3
"""REV_* numbers for the prose from the hostile-review tests (9 Nov 2026), merged into results/numbers_results.json.

Reads results/review_sdp.json (review_sdp.py), review_baseline.json (review_baseline.py), review_climate.json
(review_climate.py) and, when present, review_spark.json (review_spark.py: price feedback, efficiency level, weekday
calendar). Run after those scripts, then article_numbers.py.
    .venv/bin/python scripts/article/review_numbers.py
"""
import json
from pathlib import Path

R = Path(__file__).resolve().parents[2] / "docs" / "article" / "results"
N = {}
f0 = lambda x: f"{x:.0f}"                                                 # noqa: E731
f1 = lambda x: f"{x:.1f}"                                                 # noqa: E731

S = json.load(open(R / "review_sdp.json"))
w = S["worst"]
N["REV_SDP_REPLAY_GW"] = f"{max(v['max_abs_peak_diff_gw'] for v in S['check'].values()):.2f}"
for t in ("agile", "cosy", "iog"):
    T = t.upper()
    h = w[t]["herd_removed_gw"]
    for k in ("ideal", "p75", "p50", "p25", "fc_small", "fc_large", "comply90", "comply70", "lag1", "realistic",
              "fc_small_ar", "fc_large_ar", "outage_2pct_30", "outage_5pct_50", "scheduled_real"):
        N[f"REV_SDP_{T}_{k.upper()}_GW"] = f0(h[k])
        N[f"REV_SDP_{T}_{k.upper()}_WINTERS_OVER"] = str(w[t]["winters_over_cap"][k])
        N[f"REV_SDP_{T}_{k.upper()}_MAXOVER_GW"] = f0(w[t]["max_over_gw"][k])
        N[f"REV_SDP_{T}_{k.upper()}_LONGEST_HH"] = str(w[t]["longest_over_hh"][k])
    N[f"REV_SDP_{T}_DISPATCHED_GWH"] = f"{w[t]['dispatched_gwh_median']['ideal']:,.0f}"
    N[f"REV_SDP_{T}_HOME_HH_PCT"] = f"{w[t]['home_hh_pct_median']['ideal']:.1f}"
    for k in ("p50", "p25"):
        N[f"REV_SDP_{T}_{k.upper()}_WINTERS_OVER"] = str(w[t]["winters_over_cap"][k])
SEEDS = R / "review_sdp_seeds.json"                       # worst-winter summaries of 20 independent draws (review_sdp.py --seed)
if SEEDS.exists():
    import numpy as np
    draws = json.load(open(SEEDS))["worst"]
    N["REV_SDP_SEEDS"] = str(len(draws))
    for t in ("agile", "iog"):
        for k in ("fc_small", "fc_large", "fc_small_ar", "fc_large_ar", "outage_2pct_30", "outage_5pct_50",
                  "scheduled_real", "realistic", "comply90", "comply70"):
            v = [d[t]["herd_removed_gw"][k] for d in draws]
            N[f"REV_SDP_{t.upper()}_{k.upper()}_GW"] = f0(np.median(v))
            N[f"REV_SDP_{t.upper()}_{k.upper()}_LO_GW"] = f0(np.percentile(v, 5))
            N[f"REV_SDP_{t.upper()}_{k.upper()}_HI_GW"] = f0(np.percentile(v, 95))
            N[f"REV_SDP_{t.upper()}_{k.upper()}_MAXOVER_GW"] = f0(np.median([d[t]["max_over_gw"][k] for d in draws]))
for m, v in w["mix"].items():
    N[f"REV_MIX_{m.upper()}_OVER_GW"] = f0(v["herd_over_cap_max_gw"])
    N[f"REV_MIX_{m.upper()}_PEAK_GW"] = f0(v["ccop_max_gw"])
N["REV_FIXED_CAP_LO_GW"], N["REV_FIXED_CAP_HI_GW"] = "55", "75"
N["REV_FIXED55_SHED_PCT_AGILE"] = f"{w['agile']['fixed_shed_hh_share_pct_median']['55']:.1f}"
N["REV_FIXED75_SHED_PCT_AGILE"] = f"{w['agile']['fixed_shed_hh_share_pct_median']['75']:.2f}"
N["REV_FIXED55_REMOVED_AGILE_GW"] = f0(w["agile"]["herd_removed_gw"]["fixed55"])
N["REV_FIXED75_REMOVED_AGILE_GW"] = f0(w["agile"]["herd_removed_gw"]["fixed75"])

B = json.load(open(R / "review_baseline.json"))
fit, s = B["fit"], B["summary"]
N["REV_BASE_R2"] = f"{fit['r2']:.2f}"
N["REV_BASE_RMSE_GW"] = f1(fit["rmse_gw"])
pk = fit["temp_coef_gw_per_k"]["32-40"]
N["REV_BASE_PEAK_GW_PER_K"] = f"{pk[0] + pk[1]:.2f}"
N["REV_BASE_FIT_COLDEST_C"] = f1(fit["fit_coldest_gb_c"][0])
for var in ("linear", "capped"):
    V = var.upper()
    N[f"REV_BASE_{V}_BASE_MAX_GW"] = f1(s[var]["base_peak"]["max"])
    N[f"REV_BASE_{V}_HP_MAX_GW"] = f0(s[var]["hp_svr"]["max"])
    N[f"REV_BASE_{V}_CAP_MAX_GW"] = f0(s[var]["ccop_svr"]["max"])
    N[f"REV_BASE_{V}_CCOP_AGILE_MAX_GW"] = f0(s[var]["ccop_agile"]["max"])
    N[f"REV_BASE_{V}_HERD_AGILE_GW"] = f0(s[var]["herd_excess_agile"])
    N[f"REV_BASE_{V}_HERD_IOG_GW"] = f0(s[var]["herd_excess_iog"])
if "cv_summary" in fit:
    for spec, F in (("LIN", fit), ("QUAD", fit.get("quad", {}))):
        c = F.get("cv_summary", {})
        if c:
            N[f"REV_BASE_CV_{spec}_RMSE_GW"] = f1(c["rmse_gw"])
            N[f"REV_BASE_CV_{spec}_COLD_BIAS_GW"] = f1(c["cold5_bias_gw"])
            N[f"REV_BASE_CV_{spec}_TOP20_BIAS_GW"] = f1(abs(c["top20_bias_gw"]))     # negative = under-prediction; the text says so
            N[f"REV_BASE_CV_{spec}_TOP20_WORST_GW"] = f1(c["top20_bias_worst_gw"])
    for var in ("quad", "quad_capped"):
        if var in s:
            N[f"REV_BASE_{var.upper()}_HERD_AGILE_GW"] = f0(s[var]["herd_excess_agile"])
            N[f"REV_BASE_{var.upper()}_HP_MAX_GW"] = f0(s[var]["hp_svr"]["max"])
            N[f"REV_BASE_{var.upper()}_CAP_MAX_GW"] = f1(s[var]["ccop_svr"]["max"])
N["REV_BASE_FIXED_BASE_MAX_GW"] = f1(s["fixed"]["base_peak"]["max"])

C = json.load(open(R / "review_climate.json"))
for p, P in (("early_1940_1979", "EARLY"), ("recent_1986_2025", "RECENT")):
    c = C[p]
    N[f"REV_CLIM_{P}_HDD_MEDIAN"] = f"{c['hdd']['median']:,.0f}"
    N[f"REV_CLIM_{P}_HYB_SVR_MEDIAN"] = f0(c["hyb_wins_svr_pct"]["median"])
    N[f"REV_CLIM_{P}_HYB_SVR_P95"] = f0(c["hyb_wins_svr_pct"]["p95"])
    N[f"REV_CLIM_{P}_SPREAD_HP_SVR"] = f0(c["hp_svr_gbp"]["p95"] - c["hp_svr_gbp"]["median"])
    N[f"REV_CLIM_{P}_SPREAD_CCOP_SVR"] = f0(c["ccop_svr_gbp"]["p95"] - c["ccop_svr_gbp"]["median"])
    N[f"REV_CLIM_{P}_HP_PEAK_MAX"] = f0(c["hp_svr_peak_gw"]["max"])

# validation against the Freedom trial (review, 9 Nov): after-diversity added peak per home, and coincidence factor
import csv
import numpy as np
NUM = json.load(open(R.parent / "numbers.json"))
meters = float(NUM["GB_GAS_METERS"].split()[0]) * 1e6
nat = list(csv.DictReader(open(R / "national.csv")))
hp = {r["year"]: float(r["system_peak_gw"]) for r in nat if r["tariff"] == "svr" and r["ctrl"] == "hp"}
gas = {r["year"]: float(r["system_peak_gw"]) for r in nat if r["tariff"] == "svr" and r["ctrl"] == "gas"}
inc = np.array([hp[y] - gas[y] for y in hp]) * 1e6 / meters
N["REV_ADMD_HP_MEDIAN_KW"], N["REV_ADMD_HP_P95_KW"], N["REV_ADMD_HP_MAX_KW"] = (f"{np.median(inc):.1f}",
                                                                              f"{np.percentile(inc, 95):.1f}", f"{inc.max():.1f}")
cf = R / "review_coincidence.json"
if cf.exists():
    C2 = json.load(open(cf))["towns"]
    for k, K in (("hp_svr", "HP"), ("ccop_iog", "CCOP_IOG"), ("ccop_svr", "CCOP_SVR")):
        v = [C2[t][k]["34"]["mean"] for t in C2]
        N[f"REV_CF34_{K}_LO"], N[f"REV_CF34_{K}_HI"] = f"{min(v):.2f}", f"{max(v):.2f}"
    N["REV_CF_TOWNS"] = " and ".join(C2)
    N["REV_CF_COLD_DAYS"] = str(len(next(iter(C2.values()))["cold_days"]))

for name in ("review_spark.json", "review_stagger.json", "review_v4.json"):   # gb_stagger.py; gb_v4_digest.py (review 4)
    sp = R / name
    if sp.exists():
        N.update(json.load(open(sp))["numbers"])

sj = R / "review_spark.json"                    # price-feedback diagnostics: GW over SD-Power's cap, pass by pass
if sj.exists():
    for y, Y in json.load(open(sj))["by_year"].items():
        cap = Y["central"]["peaks"]["cap"]
        for sc in (1, 2):
            if f"fb{sc}" in Y:
                for k, pk in enumerate(Y[f"fb{sc}"]["agile_peak_by_k"]):
                    N[f"REV_FB{sc}_TR_{y}_K{k}"] = f"{pk - cap:.0f}"

DV = R / "diversity"                               # IDEAL validation and measured-habit runs (ideal_gas.py, gb_div*.sh)
if (DV / "ideal_gas.json").exists():
    import math
    ig = json.load(open(DV / "ideal_gas.json"))
    n_all = ig["cf_gas"]["all"]["n"]
    N["REV_IDEAL_HOMES"] = str(ig["homes"])
    N["REV_IDEAL_DAYS"] = str(len(ig["window_days"]))
    N["REV_IDEAL_TMEAN_C"] = f"{ig['window_tmean_c']:.1f}"
    N["REV_IDEAL_CF"] = f"{ig['cf_gas']['all']['cf']:.2f}"
    N["REV_IDEAL_CF10"] = f"{ig['cf_gas']['10']['mean']:.2f}"
    N["REV_IDEAL_PEAK_KW"] = f"{ig['indiv_peak_kw_median']:.1f}"
    N["REV_IDEAL_KWH_DAY"] = f"{ig['gas_kwh_day_mean']:.0f}"
    N["REV_IDEAL_LIB_DAYS"] = f"{ig['library']['home_days']:,}"
    N["REV_IDEAL_LIB_HOMES"] = str(ig["library"]["homes"])
    N["REV_IDEAL_OVERNIGHT_PCT"] = f"{100 * ig['library']['share_homes_mostly_overnight']:.0f}"
    prof = ig["profile_kw"]

    def corr(a, b):
        a = [x / sum(a) for x in a]; b = [x / sum(b) for x in b]
        ma, mb = sum(a) / 48, sum(b) / 48
        return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
    for tag, f in (("BASE", "ideal_cf_base.json"), ("LIB", "ideal_cf_lib_b14.json")):
        m = json.load(open(DV / f))["towns"]["Edinburgh"]
        N[f"REV_IDEAL_MODEL_{tag}_CF"] = f"{m['gas'][str(n_all)]['mean'] if str(n_all) in m['gas'] else m['gas']['31']['mean']:.2f}"
        N[f"REV_IDEAL_MODEL_{tag}_CF10"] = f"{m['gas']['10']['mean']:.2f}"
        N[f"REV_IDEAL_MODEL_{tag}_PEAK_KW"] = f"{m['gas_indiv_peak_kw_median']:.1f}"
        N[f"REV_IDEAL_MODEL_{tag}_KWH_DAY"] = f"{m['gas_kwh_day']:.0f}"
        N[f"REV_IDEAL_MODEL_{tag}_SHAPE_R"] = f"{corr(prof, m['gas_profile_kw']):.2f}"
    hp = json.load(open(DV / "div_cf_lib.json"))["towns"]
    for k in ("hp_svr", "ccop_iog"):
        N[f"REV_DIV_CF34_{k.upper()}"] = f"{sum(t[k]['34']['mean'] for t in hp.values()) / len(hp):.2f}"
if (DV / "review_div.json").exists():
    N.update(json.load(open(DV / "review_div.json"))["numbers"])
for _f in ("review_adopt.json",):                  # adoption x tariff mix (review_adopt.py, stored v4 outputs)
    if (R / _f).exists():
        N.update(json.load(open(R / _f))["numbers"])
for _y in (1962, 2024):                            # local feeder case (scripts/spark/feeder_case.py, Birmingham cold days)
    _fc = DV / f"feeder_case_{_y}.json"
    if not _fc.exists():
        continue
    _F = json.load(open(_fc))
    _Y = str(_y)
    N[f"REV_LF_{_Y}_FEEDERS"] = str(_F["feeders"])
    N[f"REV_LF_{_Y}_DAYS"] = str(len(_F["dates"]))
    N[f"REV_LF_{_Y}_BASE_PEAK_KW"] = f"{_F['base']['peak_kw_per_home_mean']:.2f}"
    N[f"REV_LF_{_Y}_BASE_KWH_DAY"] = f"{_F['base']['kwh_day_per_home']:.1f}"
    N[f"REV_LF_{_Y}_HP_DIV_KW"] = f"{_F['hp_diversified_kw_per_home']:.2f}"
    N[f"REV_LF_{_Y}_HP_PEAK_KW"] = f"{_F['hp_peak_kw_per_home_mean']:.2f}"
    N[f"REV_LF_{_Y}_NAT_SLOTS"] = str(_F["national_shed_slots"])
    if (DV / f"feeder_cf_{_y}.json").exists():
        N[f"REV_LF_{_Y}_TEMP_C"] = f"{json.load(open(DV / f'feeder_cf_{_y}.json'))['towns']['Birmingham']['cold_mean_c']:.1f}".replace("-", "−")
    for _k, _S in _F["scenarios"].items():
        _mix, _h = _k.split("_h")
        _K = f"REV_LF_{_Y}_{_mix.upper()}_H{_h.replace('.', 'P')}"
        for _sc, _T in (("all_electric", "HP"), ("hybrid_ccop", "CC"), ("hybrid_national", "NAT"), ("hybrid_local", "LOC"), ("hybrid_both", "BOTH")):
            _m = _S[_sc]
            N[f"{_K}_{_T}_FEEDERS"] = f"{_m['feeders_ever_over_pct']:.0f}"
            N[f"{_K}_{_T}_DAYS"] = f"{_m['feeder_days_over_pct']:.0f}"
            N[f"{_K}_{_T}_MAXOVER"] = f"{max(_m['max_over_pct_of_cap'], 0):.0f}"
            N[f"{_K}_{_T}_PEAK_KW"] = f"{_m['peak_kw_per_home_mean']:.2f}"
            if "home_slots_to_gas_pct" in _m:
                N[f"{_K}_{_T}_GAS"] = f"{_m['home_slots_to_gas_pct']:.1f}"
        _c = _S["conflict_feeder_slots"]
        N[f"{_K}_CONF_LOCAL_ONLY"] = f"{_c['feeder_over_national_silent_pct']:.1f}"
        N[f"{_K}_CONF_NAT_ONLY"] = f"{_c['national_sheds_feeder_fine_pct']:.1f}"
        N[f"{_K}_CONF_BOTH"] = f"{_c['both_pct']:.1f}"
N["REV_LF_HOMES_PER_FEEDER"] = "100"
if (DV / "lcl_base.json").exists():                 # the feeders' base load: London flat-tariff homes (lcl_base.py)
    _L = json.load(open(DV / "lcl_base.json"))
    N["REV_LF_LCL_HOMES"] = f"{_L['homes']:,}"
    N["REV_LF_LCL_DAYS"] = f"{_L['home_days']:,}"
    N["REV_LF_LCL_ADMD_KW"] = f"{_L['admd_kw_mean_day']:.2f}"
    N["REV_LF_LCL_KWH_DAY"] = f"{_L['kwh_day_mean']:.1f}"
    N["REV_LF_LCL_IPEAK_KW"] = f"{_L['indiv_peak_kw_median']:.1f}"
if (DV / "eoh_validation.json").exists():           # the model against the trial's cold days (validation_eoh.py)
    N.update(json.load(open(DV / "eoh_validation.json"))["numbers"])
# Delivery cost (independent review, 10 Nov 2026): hypothetical GBP per home per year across the gas-heated homes, per kW
# of the Agile herd removed, ideal and scheduled-imperfect (review_sdp.json), against the Capacity Market T-4 price.
if "REV_SDP_AGILE_IDEAL_GW" in N:
    _homes = float(NUM["GB_HEATED_HOMES"].split()[0]) * 1e6
    _cm = 27.10                                                   # Ofgem2026_CM_AnnualReport: T-4 2029/30, GBP/kW/yr de-rated
    for _c in (5, 20, 50):
        _tot = _c * _homes
        N[f"REV_DC_{_c}_TOTAL_M"] = f"{_tot / 1e6:,.0f}"
        N[f"REV_DC_{_c}_IDEAL"] = f"{_tot / (float(N['REV_SDP_AGILE_IDEAL_GW']) * 1e6):.0f}"
        _sched = _tot / (float(N["REV_SDP_AGILE_SCHEDULED_REAL_GW"]) * 1e6)
        N[f"REV_DC_{_c}_SCHED"] = f"{_sched:.0f}"
        N[f"REV_DC_{_c}_CM"] = f"{_sched / _cm:.1f}x"
# Whole-life bound (review item 8): keeping a boiler = service GBP 70-150/yr (FantasticServices2026_Service,
# FuseEnergy2026_Service) + a like-for-like replacement GBP 1,800-3,600 (FantasticServices2026_Replace) over 12-15 years;
# against the hybrid's running-cost advantage (hp minus hybrid, GBP/yr, national town-weighted, median over winters).
N["REV_WL_KEEP_LO"], N["REV_WL_KEEP_HI"], N["REV_WL_KEEP_MID"] = f"{70 + 1800 / 15:.0f}", f"{150 + 3600 / 12:.0f}", f"{110 + 2700 / 13.5:.0f}"
_v4 = R.parents[2] / "data" / "model" / "v4"
_gb = R.parents[2] / "data" / "model" / "gb"
if _v4.exists() and (_gb / "towns.json").exists():
    _tw = json.load(open(_gb / "towns.json"))
    _W = json.load(open(_gb / "region_weights.json"))["homes"]
    _reg = {t[0]: t[3] for t in _tw["towns"]}
    _per = {}
    for _r in _reg.values():
        _per[_r] = _per.get(_r, 0) + 1
    _TW = {t: _W[r] / _per[r] for t, r in _reg.items()}
    _gap = {}
    for _y in sorted(_v4.iterdir()):
        if not (_y / "stock_summary.csv").exists():
            continue
        for _row in csv.DictReader(open(_y / "stock_summary.csv")):
            for _q in ("p50", "p90"):
                _gap.setdefault((_row["tariff"], _q), {}).setdefault(_y.name, []).append((float(_row[f"hp_minus_hybrid_gbp_year_{_q}"]), _TW[_row["town"]]))
    for (_t, _q), _ys in _gap.items():
        _wm = [sum(v * w for v, w in rows) / sum(w for _, w in rows) for rows in _ys.values()]
        N[f"REV_WL_GAP_{_q.upper()}_{_t.upper()}"] = f"{np.median(_wm):,.0f}"
        _g = float(np.median(_wm))
        N[f"REV_WL_{_q.upper()}_{_t.upper()}"] = (f"save £{_g:,.0f}" if _g >= 0.5 else f"lose £{-_g:,.0f}")   # hybrid vs all-electric
if (DV / "review_h.json").exists():                 # stage H: the heat-pump trial's habits and switching in the model (gb_h.sh)
    N.update(json.load(open(DV / "review_h.json"))["numbers"])
    _kg = lambda k: float(N[k].replace(",", ""))                                           # noqa: E731
    N["REV_H_BIVM_KG_OVER_CCOP_SVR"] = f"{_kg('REV_H_BIVM_BIVMKG_SVR') - _kg('REV_H_BIVM_CCOPKG_SVR'):,.0f}"   # the two medians' gap
for tag, f in (("B", "review_sdp_base12.json"), ("D", "review_sdp_div.json"), ("E", "review_sdp_eoh.json")):
    if (DV / f).exists():
        wv = json.load(open(DV / f))["worst"]
        for t in ("agile", "cosy", "iog"):
            for case in ("ideal", "p50", "fc_large_ar", "scheduled_real", "realistic"):
                c = case.upper()
                N[f"REV_DSDP_{tag}_{t.upper()}_{c}_GW"] = f"{wv[t]['herd_removed_gw'][case]:.0f}"
                N[f"REV_DSDP_{tag}_{t.upper()}_{c}_OVER"] = str(wv[t]["winters_over_cap"][case])
                N[f"REV_DSDP_{tag}_{t.upper()}_{c}_MAXOVER_GW"] = f"{wv[t]['max_over_gw'][case]:.0f}"
            N[f"REV_DSDP_{tag}_{t.upper()}_GWH"] = f"{wv[t]['dispatched_gwh_median']['ideal']:,.0f}"
        N[f"REV_DSDP_{tag}_EVEN4_GW"] = f"{wv['mix']['even4']['herd_over_cap_max_gw']:.0f}"
if all((DV / f).exists() for f in ("review_sdp_base12.json", "review_sdp_div.json")):
    b = json.load(open(DV / "review_sdp_base12.json"))["worst"]; d = json.load(open(DV / "review_sdp_div.json"))["worst"]
    for t in ("agile", "cosy", "iog"):
        N[f"REV_DSDP_{t.upper()}_GWH_CUT_PCT"] = f"{100 * (1 - d[t]['dispatched_gwh_median']['ideal'] / b[t]['dispatched_gwh_median']['ideal']):.0f}"

if (DV / "lcl_dtou.json").exists():                 # London dynamic time-of-use trial (lcl_dtou.py)
    lc = json.load(open(DV / "lcl_dtou.json"))
    N["REV_LCL_TOU_HOMES"] = f"{lc['homes']['tou']:,}"
    N["REV_LCL_STD_HOMES"] = f"{lc['homes']['std']:,}"
    for kind in ("Low", "High"):
        K = kind.upper()
        e = lc[kind]
        N[f"REV_LCL_{K}_EVENTS"] = str(e["events"])
        N[f"REV_LCL_{K}_W"] = f"{abs(e['did_w_inside_mean']):.0f}"
        N[f"REV_LCL_{K}_PCT"] = f"{abs(e['did_pct_inside_mean']):.1f}"
        N[f"REV_LCL_{K}_SHARE_TOU"] = f"{100 * e['share_responding_tou']:.0f}"
        N[f"REV_LCL_{K}_SHARE_STD"] = f"{100 * e['share_responding_std']:.0f}"
        w = e["did_w_by_slot"][8:]
        N[f"REV_LCL_{K}_PEAK_W"] = f"{max(abs(v) for v in w):.0f}"
        pc = e["did_pct_by_slot"][8:]
        N[f"REV_LCL_{K}_PEAK_PCT"] = f"{max(abs(v) for v in pc):.0f}"
    N["REV_LCL_LOW_PRE_DIP_W"] = f"{abs(min(lc['Low']['did_w_by_slot'][:8])):.0f}"
    N["REV_LCL_CF34_LOW"] = f"{lc['cf34_tou_low_days']:.2f}"
    N["REV_LCL_CF34_NORMAL"] = f"{lc['cf34_tou_normal_days']:.2f}"

UK = R / "ukds"                                     # UK Data Service microdata digests (scripts/spark/ukds, aggregates only)
if (UK / "eoh.json").exists():                      # Electrification of Heat half-hourly data, SN 9209 (open)
    e = json.load(open(UK / "eoh.json"))
    N["REV_EOH_HOMES"] = str(e["homes"])
    N["REV_EOH_HYBRIDS"] = str(e["hybrid_homes"])
    for y, tag in (("2021-2022", "Y1"), ("2022-2023", "Y2")):
        s = e["spf_12m"][y]
        N[f"REV_EOH_SPF_{tag}_N"] = str(s["all_h4"]["n"])
        for q in ("p10", "p25", "p50", "p75", "p90"):
            N[f"REV_EOH_SPF_{tag}_{q.upper()}"] = f"{s['all_h4'][q]:.2f}"
        N[f"REV_EOH_SPF_{tag}_ASHP_P50"] = f"{s['ashp_nonhybrid_h4']['p50']:.2f}"
        N[f"REV_EOH_SPF_{tag}_HYB_P50"] = f"{s['hybrid_hp_only_h4']['p50']:.2f}"
        N[f"REV_EOH_HEAT_{tag}_P50"] = f"{s['heat_kwh_year']['p50']:,.0f}"
    hb = e["hybrid_boiler_share_by_temp"]
    for t in ("-4", "0", "4", "8", "12"):
        N[f"REV_EOH_HYB_GAS_AT_{t.replace('-', 'M')}C"] = f"{100 * hb[t]:.0f}"
    N["REV_EOH_HYB_GAS_WINTER_P50"] = f"{e['hybrid_winter_boiler_share_per_home']['p50']:.0f}"
    N["REV_EOH_HYB_GAS_WINTER_P25"] = f"{e['hybrid_winter_boiler_share_per_home']['p25']:.0f}"
    N["REV_EOH_HYB_GAS_WINTER_P75"] = f"{e['hybrid_winter_boiler_share_per_home']['p75']:.0f}"
    N["REV_EOH_HYB_CROSS_P50_C"] = f"{e['hybrid_crossover_bin_c']['p50']:.0f}"
    N["REV_EOH_HYB_BOTH_PCT"] = f"{100 * e['hybrid_both_running_share_of_heating_hh']:.0f}"
    cd = e["cold_days"]
    N["REV_EOH_COLD_DAYS"] = str(len(cd))
    from datetime import date as _date
    N["REV_EOH_COLDEST_DATE"] = _date.fromisoformat(cd[0]["date"]).strftime("%-d %B %Y")
    N["REV_EOH_COLDEST_C"] = f"{cd[0]['median_home_mean_temp_c']:.1f}".replace("-", "−")
    N["REV_EOH_COLD_HOMES_MIN"] = str(min(c["homes"] for c in cd))
    N["REV_EOH_COLD_TMEAN_MAX_C"] = f"{max(c['median_home_mean_temp_c'] for c in cd):.1f}".replace("-", "−")
    N["REV_EOH_ADMD_P50_KW"] = f"{e['cold_day_admd_kw_per_home']['p50']:.2f}"
    N["REV_EOH_ADMD_MAX_KW"] = f"{max(max(v) for v in e['cold_day_profiles_kw_per_home'].values()):.2f}"
    N["REV_EOH_WINTER_COINC_MAX_KW"] = f"{e['winter_coincident_mean_kw_max']:.2f}"
    N["REV_EOH_IPEAK_P50_KW"] = f"{e['cold_day_individual_peak_kw_median']['p50']:.1f}"
    N["REV_EOH_CF_ALL"] = f"{e['cold_day_cf_all']['p50']:.2f}"
    N["REV_EOH_CF34"] = f"{e['cold_day_cf34']['p50']:.2f}"
    N["REV_EOH_CF10"] = f"{e['cold_day_cf10']['p50']:.2f}"
    N["REV_EOH_COLDEST_PEAK_HH"] = f"{e['coldest_day_peak_hh'] // 2:02d}:{30 * (e['coldest_day_peak_hh'] % 2):02d}"
    iw = e["internal_winter"]
    N["REV_EOH_INT_HOMES"] = str(iw["homes"])
    N["REV_EOH_INT_SETBACK_P50_K"] = f"{iw['setback_eve_minus_night_k']['p50']:.1f}"
    N["REV_EOH_INT_SETBACK_OVER2K_PCT"] = f"{100 * iw['share_setback_over_2k']:.0f}"
    N["REV_EOH_INT_EVE_P50_C"] = f"{iw['evening_mean_c']['p50']:.1f}"
    N["REV_EOH_INT_NIGHT_P50_C"] = f"{iw['night_min_c']['p50']:.1f}"
    N["REV_EOH_HEAT_0006_PCT"] = f"{100 * e['share_hp_heat_0000_0600']:.0f}"
    N["REV_EOH_FLOW_AT_0C_P50"] = f"{e['flow_temp_at_0_2c_per_home']['p50']:.0f}"
    N["REV_EOH_FLOW_AT_0C_P10"] = f"{e['flow_temp_at_0_2c_per_home']['p10']:.0f}"
    N["REV_EOH_FLOW_AT_0C_P90"] = f"{e['flow_temp_at_0_2c_per_home']['p90']:.0f}"
    N["REV_EOH_FLOW_AT_M4C"] = f"{e['flow_temp_by_outdoor']['-4']:.0f}"
    if "spf_mine_vs_esc" in e:                      # the open per-home summaries from ESC's USmart platform
        N["REV_EOH_ESC_HYBRIDS"] = str(e["esc_hybrid_vs_boiler_meter"]["esc_hybrids"])
        N["REV_EOH_ESC_SPFH4_P50"] = f"{e['esc_spfh4_included']['p50']:.2f}"
        N["REV_EOH_ESC_SPFH4_N"] = str(e["esc_spfh4_included"]["n"])
        N["REV_EOH_VS_ESC_N"] = str(e["spf_mine_vs_esc"]["n"])
        N["REV_EOH_VS_ESC_MAD"] = f"{e['spf_mine_vs_esc']['median_abs_diff']:.2f}"
        N["REV_EOH_VS_ESC_CORR"] = f"{e['spf_mine_vs_esc']['corr']:.2f}"
        N["REV_EOH_DESIGN_FLOW_P50"] = f"{e['design_flow_temp_c']['p50']:.0f}"
        N["REV_EOH_DESIGN_FLOW_P10"] = f"{e['design_flow_temp_c']['p10']:.0f}"
        N["REV_EOH_DESIGN_FLOW_P90"] = f"{e['design_flow_temp_c']['p90']:.0f}"
        N["REV_EOH_DESIGN_FLOW_N"] = str(e["design_flow_temp_c"]["n"])
        N["REV_EOH_HP_SIZE_P50"] = f"{e['hp_size_kw']['p50']:.0f}"
        N["REV_EOH_FLOOR_P50"] = f"{e['floor_area_m2']['p50']:.0f}"
if (UK / "eoh_schedules.json").exists():            # the trial's heating schedules as a habits library (eoh_schedules.py)
    q = json.load(open(UK / "eoh_schedules.json"))
    N["REV_H_LIB_DAYS"] = f"{q['home_days']:,}"
    N["REV_H_LIB_HOMES"] = str(q["homes"])
    N["REV_H_LIB_ON_PCT"] = f"{100 * q['on_share']:.0f}"
    N["REV_H_LIB_HOURS_P50"] = f"{q['hours_on_per_day']['p50']:.0f}"
    N["REV_H_LIB_HOURS_P10"] = f"{q['hours_on_per_day']['p10']:.0f}"
    N["REV_H_LIB_HOURS_P90"] = f"{q['hours_on_per_day']['p90']:.0f}"
    N["REV_H_LIB_ALLDAY_PCT"] = f"{100 * q['share_days_on_all_day']:.0f}"
    N["REV_H_LIB_OFFNIGHT_PCT"] = f"{100 * q['share_days_off_overnight']:.0f}"
    N["REV_H_LIB_OVERNIGHT_HOMES_PCT"] = f"{100 * q['share_homes_mostly_overnight']:.0f}"
    N["REV_H_LIB_THR_W"] = f"{2000 * q['threshold_kwh_per_hh']:.0f}"
if (UK / "efus.json").exists():                     # Energy Follow-Up Survey 2011, SN 7471 (safeguarded; aggregates)
    u = json.load(open(UK / "efus.json"))
    j = u["patterns"]["Jan_WD"]
    N["REV_EFUS_HOMES"] = str(u["homes"])
    N["REV_EFUS_JAN_HOMES"] = str(j["homes_with_pattern"])
    N["REV_EFUS_HOURS_P50"] = f"{j['hours_heated']['p50']:.1f}"
    N["REV_EFUS_HOURS_MEAN"] = f"{j['hours_heated']['mean']:.1f}"
    N["REV_EFUS_OVER16H_PCT"] = f"{100 * j['share_over_16h']:.0f}"
    N["REV_EFUS_OVERNIGHT_PCT"] = f"{100 * j['share_overnight']:.0f}"
    N["REV_EFUS_TWO_PERIODS_PCT"] = f"{100 * j['periods_share']['2']:.0f}"
    N["REV_EFUS_ONE_PERIOD_PCT"] = f"{100 * j['periods_share']['1']:.0f}"
    N["REV_EFUS_DROP_P50_K"] = f"{j['overnight_drop_living_k']['p50']:.1f}"
    N["REV_EFUS_DROP_P90_K"] = f"{j['overnight_drop_living_k']['p90']:.1f}"
    N["REV_EFUS_LIVING_END_P50_C"] = f"{j['living_room_at_last_end_c']['p50']:.1f}"
    N["REV_EFUS_LIVING_START_P50_C"] = f"{j['living_room_at_p1_start_c']['p50']:.1f}"
    iv = u["interview"]
    N["REV_EFUS_INT_N"] = f"{iv['n']:,}"
    N["REV_EFUS_TIMER_PCT"] = f"{100 * iv['ch_control']['1']:.0f}"
    N["REV_EFUS_INT_HOURS_P50"] = f"{iv['MainHrsWkday']['p50']:.0f}"
    N["REV_EFUS_INT_24H_PCT"] = f"{100 * iv['MainHrsWkday']['share_24h']:.0f}"
if (UK / "fp2023.json").exists():                   # EHS Fuel Poverty Dataset 2023, SN 9466 (safeguarded; aggregates)
    f = json.load(open(UK / "fp2023.json"))
    N["REV_FP_N"] = f"{f['n']:,}"
    N["REV_FP_HH_M"] = f"{f['households_weighted'] / 1e6:.1f}"
    N["REV_FP_GAS_PCT"] = f"{100 * f['share_Mainfueltype']['1']:.0f}"
    N["REV_FP_LILEE_PCT"] = f"{100 * f['share_fpLILEEflg']['1']:.1f}"
    N["REV_FP_LILEE_GAS_PCT"] = f"{100 * f['share_fpLILEEflg_by_fuel']['1']:.1f}"
    N["REV_FP_HEAT_GAS_P50"] = f"{f['heat_cost_gbp_gas']['p50']:,.0f}"
    N["REV_FP_HEAT_GAS_P10"] = f"{f['heat_cost_gbp_gas']['p10']:,.0f}"
    N["REV_FP_HEAT_GAS_P90"] = f"{f['heat_cost_gbp_gas']['p90']:,.0f}"
    N["REV_FP_SPACE_GAS_P50"] = f"{f['space_heat_cost_gbp_gas']['p50']:,.0f}"
    N["REV_FP_HEAT_SHARE_P50"] = f"{f['heat_share_of_ahc_income_pct']['p50']:.1f}"
    N["REV_FP_HEAT_SHARE_P90"] = f"{f['heat_share_of_ahc_income_pct']['p90']:.1f}"
    N["REV_FP_OVER10_PCT"] = f"{100 * f['share_heat_over_10pct_ahc']:.0f}"
    N["REV_FP_D1_HEAT_SHARE"] = f"{f['by_ahc_decile']['1']['heat_share_ahc_pct']:.0f}"
    N["REV_FP_D2_HEAT_SHARE"] = f"{f['by_ahc_decile']['2']['heat_share_ahc_pct']:.0f}"
    N["REV_FP_D10_HEAT_SHARE"] = f"{f['by_ahc_decile']['10']['heat_share_ahc_pct']:.1f}"
    N["REV_FP_D1_HEAT_GBP"] = f"{f['by_ahc_decile']['1']['heat_cost_gbp']:,}"
    N["REV_FP_D10_HEAT_GBP"] = f"{f['by_ahc_decile']['10']['heat_cost_gbp']:,}"
    N["REV_FP_D1_GAS_PCT"] = f"{100 * f['by_ahc_decile']['1']['gas_share']:.0f}"
    N["REV_FP_D1_LILEE_PCT"] = f"{100 * f['by_ahc_decile']['1']['lilee_rate']:.0f}"
    N["REV_FP_D1_AHC_P50"] = f"{f['by_ahc_decile']['1']['ahc_income_p50']:,}"
    N["REV_FP_AHC_EQ_P10"] = f"{f['ahc_eq_income_gbp']['p10']:,.0f}"
if (UK / "hbai.json").exists():                     # IFS HBAI 1961-1993, SN 3300 (safeguarded; aggregates)
    h = json.load(open(UK / "hbai.json"))
    ov = [y for y in h if "ons_p10_nominal" in h[y]]
    r = [h[y]["ons_p10_nominal"] / h[y]["bhc_p10_ind_gbp_year"] for y in ov]
    N["REV_HBAI_FIRST"], N["REV_HBAI_LAST"] = min(h), max(h)
    N["REV_HBAI_OVERLAP_YEARS"] = str(len(ov))
    N["REV_HBAI_P10_MAXDIFF_PCT"] = f"{100 * max(abs(v - 1) for v in r):.0f}"
    N["REV_HBAI_P10_RATIO"] = f"{np.mean(r):.3f}"
    N["REV_HBAI_BU_1977"] = f"{h['1977']['benefit_units']:,}"
    N["REV_HBAI_P10_1962_GBP"] = f"{h['1962']['bhc_p10_ind_gbp_year']:,}"
# the model's own boiler share for the C-COP hybrid, for comparison with the trial's hybrids (national.csv)
nat = R / "national.csv"
if nat.exists():
    import csv as _csv
    bs = {}
    for row in _csv.DictReader(open(nat)):
        if row["ctrl"] in ("ccop", "biv0") and row["boiler_share_median"] not in ("", "nan"):
            bs.setdefault((row["tariff"], row["ctrl"]), {})[row["year"]] = float(row["boiler_share_median"])
    for (t, c), d in bs.items():
        N[f"REV_MODEL_GAS_{c.upper()}_{t.upper()}"] = f"{100 * np.median(list(d.values())):.0f}"
        tr = [d[y] for y in ("2020", "2021", "2022") if y in d]
        if tr:
            N[f"REV_MODEL_GAS_{c.upper()}_{t.upper()}_TRIAL"] = f"{100 * np.mean(tr):.0f}"

p = R / "numbers_results.json"
old = json.load(open(p))
old = {k: v for k, v in old.items() if not k.startswith("REV_")}
old.update(N)
json.dump(dict(sorted(old.items())), open(p, "w"), indent=1, ensure_ascii=False)
print(f"{len(N)} REV_ numbers merged")
for k in sorted(N):
    print(k, N[k])
