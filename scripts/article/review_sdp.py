#!/usr/bin/env python3
"""Hostile review (9 Nov 2026), critical issues 1 and 2, from the stored v3 outputs (no model rerun).

SD-Power dispatch in the paper is a perfect operator: it knows Britain's demand in advance, every home takes part and
every instruction is obeyed, against a cap set at the flat-tariff hybrid's own peak. This replays the dispatch on the
national half-hourly demand of every winter (data/model/v3fp2/<Y>/flex_region.npz, gas-meter weighted as
gb_sdp_phi.py) with the imperfections the review lists, and reports what is DELIVERED, not what was requested:

  participation p      only a share p of homes can be dispatched (the shed share is capped at p)
  forecast error       the operator sets the shed share from forecasts: base x (1 + e_b), heat x (1 + e_h), e ~ N(0, s)
                       independently per half-hour (NESO day-ahead ND error is ~2-3% MAPE; heat-pump load less known)
  compliance c         a share c of instructed homes actually switch
  lag                  the shed share is set from the half-hour before (one-slot dispatch latency)
  fixed caps           exogenous caps (GW) the same in every winter, instead of the endogenous flat-tariff peak

Shedding a random share phi of homes cuts the heat-pump demand by phi (homes are interchangeable in expectation); the
replay of the ideal case is checked against the model's own sdp controller. Peak rebound: the headline model stores no
heat, so a shed home does not catch up afterwards; that is a property of the model, stated, not a finding.

Also tariff diversity (issue 2): Britain's heat demand when homes are spread across tariffs, from the per-tariff arrays.
    .venv/bin/python scripts/article/review_sdp.py   -> docs/article/results/review_sdp.json
"""
import json
from pathlib import Path

import numpy as np

import sys

ROOT = Path(__file__).resolve().parents[2]
_a = lambda k, d: Path(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d                      # noqa: E731
SRC = _a("--src", ROOT / "data" / "model" / "v3fp2")          # on the Spark: --src /work/out/v3fp2 --gb /work/data/gb
GB = _a("--gb", ROOT / "data" / "model" / "gb")
OUT = _a("--out", ROOT / "docs" / "article" / "results" / "review_sdp.json")
SEED = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 9112026


def price_day(d, py=2025):
    y = py if d[5:] >= "11" else py + 1
    md = d[5:]
    if md == "02-29" and not (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)):
        md = "02-28"
    return f"{y}-{md}"


def load_year(y, W, S):
    f = np.load(SRC / str(y) / "flex_region.npz")
    regs, tar, ctrl = list(f["regions"]), list(f["tariffs"]), list(f["ctrl"])
    w = np.array([W[r] for r in regs], float)
    e = f["e"].astype(np.float64)                                          # (R, days, T, C, 48) kWh per home per slot
    gw = lambda t, c: (e[:, :, tar.index(t), ctrl.index(c)] * w[:, None, None]).sum(0) * 2 / 1e6   # noqa: E731
    dates = [str(d) for d in f["dates"]]
    base = np.array([[S[f"{price_day(d)}T{s // 2:02d}:{30 * (s % 2):02d}Z"] / 1000 for s in range(48)] for d in dates])
    return {"base": base.ravel(), **{f"{c}_{t}": gw(t, c).ravel() for t in ("svr", "agile", "cosy", "iog")
                                     for c in ("ccop", "sdp", "hp")}}


def noise(n, sd, rho, rng):
    """Forecast error series: independent (rho 0) or AR(1) with lag-one correlation rho, marginal sd."""
    z = rng.standard_normal(n)
    if not rho:
        return sd * z
    e = np.empty(n)
    e[0] = z[0]
    k = np.sqrt(1 - rho * rho)
    for i in range(1, n):
        e[i] = rho * e[i - 1] + k * z[i]
    return sd * e


def dispatch(base, heat, cap, p=1.0, s_b=0.0, s_h=0.0, c=1.0, lag=0, rng=None, rho=0.0, outage=None):
    """Delivered total demand when the operator sheds a share of homes to hold base + heat at cap.
    rho: lag-one autocorrelation of the forecast errors (half-hourly). outage (q, s): on each day independently with
    probability q, a block of s of the dispatched homes is unreachable for the whole day (common-mode failure)."""
    bf = base * (1 + noise(base.size, s_b, rho, rng)) if s_b else base
    hf = heat * (1 + noise(heat.size, s_h, rho, rng)) if s_h else heat
    phi = np.where(bf + hf > cap, np.clip(1 - (cap - bf) / np.maximum(hf, 1e-9), 0, 1), 0.)
    if lag:
        phi = np.r_[np.zeros(lag), phi[:-lag]]
    phi = np.minimum(phi, p) * c
    if outage:
        q, sh = outage
        down = np.repeat(rng.random(base.size // 48) < q, 48)
        phi = np.where(down, phi * (1 - sh), phi)
    return base + heat * (1 - phi), phi


def longest_run(mask):
    best = cur = 0
    for m in mask:
        cur = cur + 1 if m else 0
        best = max(best, cur)
    return best


def score(tot, cap, ideal_phi, phi, heat):
    """Peak removed and cap compliance are separate metrics (review, 9 Nov): peak, half-hours over the cap, worst
    breach, longest excursion (half-hours), energy above the cap, energy dispatched to gas (heat-pump electricity not
    drawn) requested and delivered, and the share of home-half-hours dispatched."""
    over = tot - cap
    m = over > 0.05
    return {"peak_gw": round(float(tot.max()), 1), "hh_over_cap": int(m.sum()),
            "max_over_gw": round(float(max(over.max(), 0)), 1), "longest_over_hh": longest_run(m),
            "over_cap_gwh": round(float(np.maximum(over, 0).sum() / 2), 2),
            "shed_requested_gwh": round(float((ideal_phi * heat).sum() / 2), 0),
            "shed_delivered_gwh": round(float((phi * heat).sum() / 2), 0),
            "home_hh_dispatched_pct": round(100 * float(phi.mean()), 3)}


def main():
    W = json.load(open(GB / "region_weights.json"))["homes"]
    S = json.load(open(GB / "base_demand.json"))["series"]
    years = sorted(int(p.name) for p in SRC.iterdir() if (p / "flex_region.npz").exists())
    rng = np.random.default_rng(SEED)
    R = {"years": len(years), "seed": SEED, "source": str(SRC), "check": {}, "by_year": {}}
    cases = {"ideal": {}, "p75": {"p": .75}, "p50": {"p": .5}, "p25": {"p": .25},
             "fc_small": {"s_b": .02, "s_h": .05}, "fc_large": {"s_b": .03, "s_h": .15},
             "comply90": {"c": .9}, "comply70": {"c": .7}, "lag1": {"lag": 1},
             "realistic": {"p": .75, "s_b": .02, "s_h": .10, "c": .9, "lag": 1},
             # review 9 Nov (P0-C): temporally correlated forecast error, common-mode outages, scheduled + margin
             "fc_small_ar": {"s_b": .02, "s_h": .05, "rho": .95}, "fc_large_ar": {"s_b": .03, "s_h": .15, "rho": .95},
             "outage_2pct_30": {"outage": (.02, .3)}, "outage_5pct_50": {"outage": (.05, .5)},
             "scheduled_real": {"p": .75, "s_b": .02, "s_h": .10, "c": .9, "rho": .95, "outage": (.02, .3)}}
    fixed = [55, 60, 65, 70, 75]
    mixes = {"all_agile": {"agile": 1}, "even4": {"svr": .25, "agile": .25, "cosy": .25, "iog": .25},
             "svr_heavy": {"svr": .6, "agile": .1, "cosy": .15, "iog": .15},
             "agile_half": {"svr": .5, "agile": .5}}
    worst = {}
    for y in years:
        d = load_year(y, W, S)
        b = d["base"]
        cap = float((b + d["ccop_svr"]).max())
        Y = {"cap_gw": round(cap, 1), "base_peak_gw": round(float(b.max()), 1)}
        for t in ("agile", "cosy", "iog"):
            h = d[f"ccop_{t}"]
            tot0 = b + h
            ideal_tot, ideal_phi = dispatch(b, h, cap)
            model_sdp = b + d[f"sdp_{t}"]
            if json.load(open(SRC / str(y) / "run.json")).get("sdp_phi"):      # pass-2 winters only (v4: 12 of 86)
                R["check"].setdefault(t, []).append(abs(float(ideal_tot.max() - model_sdp.max())))
            T = {"ccop_peak_gw": round(float(tot0.max()), 1), "model_sdp_peak_gw": round(float(model_sdp.max()), 1)}
            for name, kw in cases.items():
                tot, phi = dispatch(b, h, cap, rng=rng, **kw)
                T[name] = score(tot, cap, ideal_phi, phi, h)
            for fc in fixed:
                tot, phi = dispatch(b, h, fc)
                T[f"fixed{fc}"] = {**score(tot, fc, phi, phi, h), "shed_hh_share_pct":
                                   round(100 * float(phi.sum() / phi.size), 2)}
            Y[t] = T
        Y["mix"] = {}
        for m, sh in mixes.items():
            h = sum(v * d[f"ccop_{k}"] for k, v in sh.items())
            Y["mix"][m] = {"ccop_peak_gw": round(float((b + h).max()), 1),
                           "herd_over_cap_gw": round(float(max((b + h).max() - cap, 0)), 1)}
        R["by_year"][y] = Y
        print(y, Y["agile"]["ccop_peak_gw"], Y["agile"]["ideal"]["peak_gw"], Y["agile"]["realistic"]["peak_gw"], flush=True)
    R["check"] = {t: {"max_abs_peak_diff_gw": round(max(v), 2)} for t, v in R["check"].items()}
    # worst-winter summary (the paper's 35 GW is max over years of ccop minus max over years of sdp, Agile)
    for t in ("agile", "cosy", "iog"):
        by = R["by_year"]
        c0 = max(by[y][t]["ccop_peak_gw"] for y in years)
        worst[t] = {"ccop_max_gw": c0, "herd_removed_gw": {}}
        for name in list(cases) + [f"fixed{fc}" for fc in fixed]:
            pk = max(by[y][t][name]["peak_gw"] for y in years)
            worst[t]["herd_removed_gw"][name] = round(c0 - pk, 1)
            worst[t].setdefault("winters_over_cap", {})[name] = sum(by[y][t][name]["hh_over_cap"] > 0 for y in years)
            worst[t].setdefault("median_hh_over_cap", {})[name] = float(np.median([by[y][t][name]["hh_over_cap"] for y in years]))
            worst[t].setdefault("max_over_gw", {})[name] = max(by[y][t][name]["max_over_gw"] for y in years)
            worst[t].setdefault("longest_over_hh", {})[name] = max(by[y][t][name]["longest_over_hh"] for y in years)
            worst[t].setdefault("over_cap_gwh_median", {})[name] = float(np.median([by[y][t][name]["over_cap_gwh"] for y in years]))
            worst[t].setdefault("dispatched_gwh_median", {})[name] = float(np.median([by[y][t][name]["shed_delivered_gwh"] for y in years]))
            worst[t].setdefault("home_hh_pct_median", {})[name] = float(np.median([by[y][t][name]["home_hh_dispatched_pct"] for y in years]))
            worst[t].setdefault("delivered_pct", {})[name] = round(100 * sum(by[y][t][name]["shed_delivered_gwh"] for y in years)
                                                                    / max(sum(by[y][t][name]["shed_requested_gwh"] for y in years), 1), 1)
        for fc in fixed:
            worst[t].setdefault("fixed_shed_hh_share_pct_median", {})[fc] = float(np.median([by[y][t][f"fixed{fc}"]["shed_hh_share_pct"] for y in years]))
    worst["mix"] = {m: {"ccop_max_gw": max(R["by_year"][y]["mix"][m]["ccop_peak_gw"] for y in years),
                        "herd_over_cap_max_gw": max(R["by_year"][y]["mix"][m]["herd_over_cap_gw"] for y in years)}
                    for m in mixes}
    worst["cap_max_gw"] = max(R["by_year"][y]["cap_gw"] for y in years)
    R["worst"] = worst
    OUT.write_text(json.dumps(R, indent=1))
    print(json.dumps({"check": R["check"], "worst": worst}, indent=1))


if __name__ == "__main__":
    main()
