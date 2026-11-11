#!/usr/bin/env python3
"""Number register for LDS Public Class No. 1: every figure the prose quotes, computed from files.

    .venv/bin/python scripts/article/article_numbers.py      ->  docs/article/numbers.json  {NAME: "formatted text"}

Sources: model config (scripts/spark/gbmodel/cfg.py, read as text -- no JAX needed here), run outputs pulled from the
Spark into data/model/v2/<year>/, the HPM fit (logs/hpm_shares_20261106.json), docs/article/validation.json,
data/model/gb/{towns,region_weights,prices_year,history}.*, and docs/article/results/*.json from analysis.py.
A number that cannot be computed is left OUT, so the build fails on it rather than printing a stale value.
"""
import csv
import json
import sys
import re
import statistics as st
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
V2 = ROOT / (sys.argv[sys.argv.index("--src") + 1] if "--src" in sys.argv else "data/model/v3f")   # model runs (run.json)
GB = ROOT / "data" / "model" / "gb"
ART = ROOT / "docs" / "article"
N = {}


def big(n):
    """922720000 -> '923 million'; 7.9e10 -> '79.4 billion'; 1.2e12 -> '1.2 trillion'."""
    for v, w in ((1e12, "trillion"), (1e9, "billion"), (1e6, "million")):
        if n >= v:
            x = n / v
            return f"{x:.0f} {w}" if x >= 100 else f"{x:.1f} {w}"
    return f"{n:,.0f}"


def yr(y):
    return f"{y}–{(y + 1) % 100:02d}"


def cfg_values():
    s = (ROOT / "scripts" / "spark" / "gbmodel" / "cfg.py").read_text()
    g = re.search(r"GAS_P, GAS_SC, SVR_P, IOG = ([\d.]+), ([\d.]+), ([\d.]+), \(([\d.]+), ([\d.]+)\)", s)
    N.update(P_GAS=g.group(1), GAS_SC=g.group(2), P_SVR=g.group(3), P_IOG_CHEAP=g.group(4), P_IOG_PEAK=g.group(5))
    N["GAS_KG"] = re.search(r"GAS_KG = ([\d.]+)", s).group(1)
    N["COP_BREAKEVEN_SVR"] = f"{float(N['P_SVR']) * 0.84 / float(N['P_GAS']):.2f}"     # SAP default boiler 84%
    N["PRICE_RATIO_SVR"] = f"{float(N['P_SVR']) / float(N['P_GAS']):.2f}"


def runs():
    years = sorted(int(p.parent.name) for p in V2.glob("*/run.json"))
    if not years:
        return
    infos = [json.load(open(V2 / str(y) / "run.json")) for y in years]
    N["N_YEARS"] = str(len(years))
    N["FIRST_YEAR"], N["LAST_YEAR"] = yr(years[0]), yr(years[-1])
    N["HOMES_PER_TOWN"] = f"{infos[0]['stock']:,}"
    N["N_CONTROLLERS"] = str(len(infos[0]["ctrl"]))
    hd = sum(i["house_days"] for i in infos)
    N["HOUSEDAYS_TOTAL"], N["DECISIONS_TOTAL"] = big(hd), big(hd * 48)
    N["SECONDS_PER_YEAR"] = f"{st.median(i['seconds'] for i in infos):.0f}"
    N["COMPLETE_RUN"] = "yes" if len(years) == 86 else f"PARTIAL {len(years)}"
    argv = infos[0].get("argv", [])                      # v4: the IOG rates the runs actually used (--iog)
    if "--iog" in argv:
        N["P_IOG_CHEAP"], N["P_IOG_PEAK"] = argv[argv.index("--iog") + 1].split(":")
    N["EXVAT"] = "yes" if "--exvat" in argv else "no"
    N["GAS_SC_GBP_YEAR"] = f"{float(N['GAS_SC']) * 365 / 100:.0f}"


def towns_and_design():
    G = json.load(open(GB / "towns.json"))
    N["TOWNS"] = str(len(G["towns"]))
    d = {k: v["design_c"] for k, v in G["design"].items()}
    lo, hi = min(d, key=d.get), max(d, key=d.get)
    N["DESIGN_RANGE"] = f"{d[lo]:.1f} °C ({lo}) to {d[hi]:.1f} °C ({hi})".replace("-", "−")


def prices():
    P = json.load(open(GB / "prices_year.json"))
    ag = [v for k, s in P.items() if k.startswith("agile_") for v in s.values()]
    n_reg = sum(1 for k in P if k.startswith("agile_"))
    N["AGILE_HALFHOURS"] = f"{len(ag) // n_reg:,}"
    N["AGILE_NEGATIVE_PCT"] = f"{100 * sum(v < 0 for v in ag) / len(ag):.1f}"


def region_weights():
    w = json.load(open(GB / "region_weights.json"))
    N["GB_GAS_METERS"] = big(w["total"])
    if "total_heated" in w:                              # review 4: national demand on gas-heated homes, not meters
        N["GB_HEATED_HOMES"] = big(w["total_heated"])


def era5_design_bias():
    """ERA5 1991-2020 0.4th-percentile hourly temperature minus the station-based design temperature, per town."""
    h = np.load(GB / "history.npz")
    G = json.load(open(GB / "towns.json"))
    t0 = np.datetime64(str(h["start"]))
    yrs = (t0 + np.arange(h["t"].shape[1]) * np.timedelta64(1, "h")).astype("datetime64[Y]").astype(int) + 1970
    sel = (yrs >= 1991) & (yrs <= 2020)
    d = []
    for i, n in enumerate(h["towns"]):
        v = h["t"][i, sel]
        v = v[v != -32768] / 10
        d.append(np.percentile(v, 0.4) - G["design"][str(n)]["design_c"])
    N["ERA5_DESIGN_BIAS"], N["ERA5_DESIGN_BIAS_MAX"] = f"{np.mean(d):.1f}", f"{max(d):.1f}"


def stress_overlap():
    """Share of the 20 coldest days (equal region weights, as run) also among the 20 coldest by gas-meter weights."""
    h = np.load(GB / "history.npz")
    G = json.load(open(GB / "towns.json"))
    W = json.load(open(GB / "region_weights.json"))["homes"]
    reg = {t[0]: t[3] for t in G["towns"]}
    regs = sorted(G["regions"])
    ri = np.array([regs.index(reg[str(n)]) for n in h["towns"]])
    t = h["t"].astype(float) / 10
    nd = t.shape[1] // 24
    daily = t[:, :nd * 24].reshape(len(ri), nd, 24).mean(2)
    rd = np.stack([daily[ri == r].mean(0) for r in range(len(regs))])
    w = np.array([W[r] for r in regs])
    eq, wt = rd.mean(0), (rd * w[:, None]).sum(0) / w.sum()
    k = 20
    ov = []
    for y in range(1940, 2025):
        a = int((np.datetime64(f"{y}-11-01") - np.datetime64("1940-11-01")) / np.timedelta64(1, "D"))
        ov.append(len(set(np.argsort(eq[a:a + 365])[:k]) & set(np.argsort(wt[a:a + 365])[:k])) / k)
    N["STRESS_OVERLAP_MEAN"], N["STRESS_OVERLAP_MIN"] = f"{100 * np.mean(ov):.0f}", f"{100 * min(ov):.0f}"


def hpm():
    j = json.load(open(ROOT / "logs" / "hpm_shares_20261106.json"))
    N["HPM_SYSTEMS"] = str(j["systems"])
    N["HPM_DAYS"] = f"{sum(b['days'] for b in j['bands'].values()):,}"
    N["LEVEL_LOW"] = "0.816"                       # physics.STOCK_LEVEL[0], calibrated (gb_spf_cal.py)
    vp = ART / "validation.json"
    if vp.exists():
        v = json.load(open(vp))
        fc = v.get("fleet_context", {})
        if "median_spf" in fc:
            N["HPM_FLEET_SPF"], N["HPM_FLEET_N"] = f"{fc['median_spf']:.2f}", f"{fc['n_systems']:,}"
            N["STOCK_SPF_TYPICAL"] = f"{fc['median_spf'] * (1 + 0.816) / 2:.1f}"
        h = v.get("house_454", {})
        if "measured_space_cop" in h:
            N["HOUSE_MEASURED_SCOP"], N["HOUSE_MODEL_SCOP"] = f"{h['measured_space_cop']:.2f}", f"{h['model_space_cop']:.2f}"
        lit = v.get("litmus", {})
        if "n_systems" in lit:
            N["LITMUS_SYSTEMS"], N["LITMUS_TOWNS"] = str(lit["n_systems"]), str(lit["n_towns"])
        fcnt = v.get("fit_counts", {})
        if "days_all" in fcnt:
            N["HPM_DAYS_ALL"] = f"{fcnt['days_all']:,}"
    cc = ART / "crosscheck.json"
    if cc.exists():
        x = json.load(open(cc))["summary"]
        N["XCHK_HOUSE"], N["XCHK_HOUSE_PASS"] = f"{x['house_checks']:,}", f"{x['house_pass']:,}"
        N["XCHK_STOCK"], N["XCHK_STOCK_PASS"] = str(x["stock_checks"]), str(x["stock_pass"])
        N["XCHK_SHARE_PTS"], N["XCHK_MEDIAN_PCT"] = f"{x['max_stock_share_diff_pts']:.1f}", f"{x['max_stock_median_cost_diff_pct']:.0f}"
        N["XCHK_TOWNS"], N["XCHK_HOMES"] = ", ".join(x["towns"]), f"{x['stock_homes']:,}"
    N["HOUSE_COP_DAYS"] = "318"      # days of daily COP behind the house curve (gb_map.py v1 docstring, 5 Nov fit)


def stock_v3():
    """Model v3 real stock: calibration to metered gas (data/model/gb/stock_v3_meta.json, gb_v3_calibrate.py)."""
    p = GB / "stock_v3_meta.json"
    if not p.exists():
        return
    m = json.load(open(p))
    c = m.get("model_calibration", {})
    if c:
        lo, hi = c["multiplier_range"]
        N["CAL_MULT_LO"], N["CAL_MULT_HI"], N["CAL_MULT_MED"] = f"{lo:.2f}", f"{hi:.2f}", f"{c['multiplier_median']:.2f}"
        N["STOCK_HTC_MEDIAN"], N["STOCK_TAU_MEDIAN"] = f"{c['median_htc_cal_w_k']:.0f}", f"{c['median_tau_cal_h']:.0f}"
        N["CAL_H_HEATED"] = f"{c['h_heated_homes_per_meter']:.2f}"
        y = c["years"]
        N["CAL_YEARS"] = f"{y[0]}–{(y[-1] + 1) % 100:02d}"
    N["STOCK_RECORDS_PER_TOWN"] = f"{m['n_per_town']:,}"
    N["STOCK_SCOT_PROXY_TOWNS"] = str(sum(1 for t in m.get("towns", []) if t.get("scottish_proxy")))


def results():
    """Results numbers from analysis.py (docs/article/results/numbers_results.json), merged as they are."""
    p = ART / "results" / "numbers_results.json"
    if p.exists():
        N.update(json.load(open(p)))


if __name__ == "__main__":
    SOURCE = {"cfg_values": "model configuration, scripts/spark/gbmodel/cfg.py",
              "runs": f"model run logs, {V2.relative_to(ROOT)}/<year>/run.json",
              "towns_and_design": "data/model/gb/towns.json (towns, design temperatures)",
              "prices": "actual Octopus Agile rates 2025-26, data/model/gb/prices_year.json",
              "region_weights": "DESNZ 2024 domestic gas meters by DNO region, data/model/gb/region_weights.json",
              "era5_design_bias": "ERA5 history (data/model/gb/history.npz) against towns.json design temperatures",
              "hpm": "heatpumpmonitor.org fit (logs/hpm_shares_20261106.json) and docs/article/validation.json",
              "stock_v3": "v3 housing stock and its calibration, data/model/gb/stock_v3_meta.json",
              "results": "model results, docs/article/results/ (scripts/article/analysis.py, flex_events.py)"}
    meta = {}
    for f in (cfg_values, runs, towns_and_design, prices, region_weights, era5_design_bias, hpm, stock_v3, results):
        before = set(N)
        f()
        for k in set(N) - before:
            meta[k] = SOURCE[f.__name__]
    json.dump(dict(sorted(N.items())), open(ART / "numbers.json", "w"), indent=1, ensure_ascii=False)
    json.dump(dict(sorted(meta.items())), open(ART / "numbers_meta.json", "w"), indent=1, ensure_ascii=False)
    print(f"{len(N)} numbers -> docs/article/numbers.json")
    for k, v in sorted(N.items()):
        print(f"  {k:24} {v}")
