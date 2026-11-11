#!/usr/bin/env python3
"""Hostile review (9 Nov 2026), critical issue 3: a weather-conditioned national baseline.

The main runs add each historic winter's heat-pump demand to the national demand Britain actually carried in the same
calendar half-hour of 2025-26 (NESO ND). That baseline does not know the historic winter was cold, although ND itself
rises in cold weather (existing electric heating, lighting, longer evening peaks). This fits ND's temperature response
on 2016-26 and moves the 2025-26 baseline by the difference between each historic winter's temperatures and 2025-26's:

    ND(t) = year effect + slot x day-type + season x slot-block + sum_b [a_b HDD(T_now) + c_b HDD(T_24h)] x block_b + e
    base_Y(t) = ND_2025(t) + temperature terms(T_Y on that calendar half-hour) - temperature terms(T_2025)

T is Britain's temperature: the 79 towns, each region weighted by its domestic gas meters (the same weights as the
heat). HDD = max(15.5 - T, 0). T_24h is the exponentially weighted temperature over about a day (thermal inertia of
buildings). Day types follow the 2025-26 calendar the baseline keeps. Two bounds on the cold tail, which lies outside
the 2016-26 range in the hardest winters: "linear" extrapolates the fitted slope; "capped" holds HDD at the coldest
value seen in 2016-26.

Then every national peak of the paper is recomputed on the conditioned baseline, from the stored per-tariff heat
(data/model/v3fp2), with SD-Power redispatched against a cap recomputed the same way (flat-tariff C-COP peak).
    .venv/bin/python scripts/article/review_baseline.py  -> docs/article/results/review_baseline.json
"""
import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np

import sys

ROOT = Path(__file__).resolve().parents[2]
_a = lambda k, d: Path(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d                      # noqa: E731
GB = _a("--gb", ROOT / "data" / "model" / "gb")              # on the Spark: --gb /work/data/gb --src /work/out/v3fp2
SRC = _a("--src", ROOT / "data" / "model" / "v3fp2")
OUT = _a("--out", ROOT / "docs" / "article" / "results" / "review_baseline.json")
BLOCKS = [(0, 12), (12, 24), (24, 32), (32, 40), (40, 48)]               # slots: night, morning, day, peak, evening
FIT_YEARS = list(range(2016, 2026))

# England & Wales bank holidays 2016-2026 (gov.uk), plus Christmas-New Year treated as holidays
BH = {"2016-12-26", "2016-12-27", "2017-01-02", "2017-04-14", "2017-04-17", "2017-05-01", "2017-05-29", "2017-08-28",
      "2017-12-25", "2017-12-26", "2018-01-01", "2018-03-30", "2018-04-02", "2018-05-07", "2018-05-28", "2018-08-27",
      "2018-12-25", "2018-12-26", "2019-01-01", "2019-04-19", "2019-04-22", "2019-05-06", "2019-05-27", "2019-08-26",
      "2019-12-25", "2019-12-26", "2020-01-01", "2020-04-10", "2020-04-13", "2020-05-08", "2020-05-25", "2020-08-31",
      "2020-12-25", "2020-12-28", "2021-01-01", "2021-04-02", "2021-04-05", "2021-05-03", "2021-05-31", "2021-08-30",
      "2021-12-27", "2021-12-28", "2022-01-03", "2022-04-15", "2022-04-18", "2022-05-02", "2022-06-02", "2022-06-03",
      "2022-08-29", "2022-09-19", "2022-12-26", "2022-12-27", "2023-01-02", "2023-04-07", "2023-04-10", "2023-05-01",
      "2023-05-08", "2023-05-29", "2023-08-28", "2023-12-25", "2023-12-26", "2024-01-01", "2024-03-29", "2024-04-01",
      "2024-05-06", "2024-05-27", "2024-08-26", "2024-12-25", "2024-12-26", "2025-01-01", "2025-04-18", "2025-04-21",
      "2025-05-05", "2025-05-26", "2025-08-25", "2025-12-25", "2025-12-26", "2026-01-01", "2026-04-03", "2026-04-06",
      "2026-05-04", "2026-05-25", "2026-08-31"}


def gb_weights():
    G = json.load(open(GB / "towns.json"))
    W = json.load(open(GB / "region_weights.json"))["homes"]
    towns = G["towns"]
    per = {}
    for t in towns:
        per[t[3]] = per.get(t[3], 0) + 1
    return [t[0] for t in towns], np.array([W[t[3]] / per[t[3]] for t in towns], float)


def hourly_gb(y, names, w, H):
    """Britain's hourly temperature, heating year y (1 Nov y .. 31 Oct y+1), gas-meter weighted."""
    if y == 2025:
        Wd = json.load(open(GB / "weather_year.json"))
        M = np.array([[np.nan if v is None else v for v in Wd[n].values()] for n in names], float)
    else:
        t0 = np.datetime64(str(H["start"]))
        i0 = int((np.datetime64(f"{y}-11-01T00:00") - t0) / np.timedelta64(1, "h"))
        i1 = int((np.datetime64(f"{y + 1}-11-01T00:00") - t0) / np.timedelta64(1, "h"))
        ix = {str(n): i for i, n in enumerate(H["towns"])}
        M = np.array([H["t"][ix[n], i0:i1] for n in names], float)
        M = np.where(M == -32768, np.nan, M / 10)
    ww = np.where(np.isnan(M), 0, w[:, None])
    return np.nansum(np.nan_to_num(M) * ww, 0) / ww.sum(0)


def to_slots(h):
    """Hourly -> half-hourly (linear), length 2n."""
    x = np.arange(2 * len(h)) / 2
    return np.interp(x, np.arange(len(h)), h)


def ewma(x, hl_slots=24):
    a = 1 - 0.5 ** (1 / hl_slots)
    out = np.empty_like(x)
    m = x[0]
    for i, v in enumerate(x):
        m = m + a * (v - m)
        out[i] = m
    return out


def temp_feats(T, T24, cap=None, quad=False):
    """Heating degrees now and over ~a day, per slot block; quad adds their squares (a non-linear cold response)."""
    hd, hd24 = np.maximum(15.5 - T, 0), np.maximum(15.5 - T24, 0)
    if cap is not None:
        hd, hd24 = np.minimum(hd, cap[0]), np.minimum(hd24, cap[1])
    slot = np.arange(len(T)) % 48
    cols = []
    for a, b in BLOCKS:
        m = ((slot >= a) & (slot < b)).astype(float)
        cols += [hd * m, hd24 * m] + ([hd * hd * m, hd24 * hd24 * m] if quad else [])
    return np.stack(cols, 1)


def cal_feats(dates48, slot):
    """slot x day-type dummies, and day-of-year harmonics per slot block."""
    dt = np.array([2 if d in BH else min(date.fromisoformat(d).weekday() - 4, 2) if date.fromisoformat(d).weekday() >= 5
                   else 0 for d in dates48])                        # 0 weekday, 1 Sat, 2 Sun/holiday
    X = np.zeros((len(slot), 48 * 3))
    X[np.arange(len(slot)), slot * 3 + dt] = 1
    doy = np.array([date.fromisoformat(d).timetuple().tm_yday for d in dates48]) / 365.25 * 2 * np.pi
    harm = []
    for a, b in BLOCKS:
        m = ((slot >= a) & (slot < b)).astype(float)
        for k in (1, 2, 3):
            harm += [np.sin(k * doy) * m, np.cos(k * doy) * m]
    return np.c_[X, np.stack(harm, 1)]


def nd_year(y):
    p = GB / "base_demand.json" if y == 2025 else GB / "years" / str(y) / "base_demand.json"
    S = json.load(open(p))["series"]
    d0 = date(y, 11, 1)
    n = (date(y + 1, 11, 1) - d0).days
    dates = [str(d0 + timedelta(i)) for i in range(n)]
    return np.array([S[f"{d}T{s // 2:02d}:{30 * (s % 2):02d}Z"] / 1000 for d in dates for s in range(48)]), dates


def main():
    names, w = gb_weights()
    _h = np.load(GB / "history.npz")
    H = {"t": _h["t"], "start": _h["start"], "towns": _h["towns"]}           # decompress once
    temps, cal, nds, dts = {}, {}, {}, {}
    for y in FIT_YEARS:
        nd, dates = nd_year(y)
        T = to_slots(hourly_gb(y, names, w, H))[:len(nd)]
        temps[y] = (T, ewma(T))
        d48 = np.repeat(dates, 48)
        cal[y] = cal_feats(d48, np.tile(np.arange(48), len(dates)))
        nds[y], dts[y] = nd, np.array([int(d[5:7]) for d in d48])
    Tall = np.concatenate([temps[y][0] for y in FIT_YEARS])
    T24all = np.concatenate([temps[y][1] for y in FIT_YEARS])
    hd_cap = (float(np.maximum(15.5 - Tall, 0).max()), float(np.maximum(15.5 - T24all, 0).max()))

    def design(ys, quad, rows=None):
        X = [np.c_[temp_feats(*temps[y], quad=quad), cal[y]][rows[y] if rows else slice(None)] for y in ys]
        Y = [nds[y][rows[y] if rows else slice(None)] for y in ys]
        yr = np.concatenate([np.full(len(v), y) for v, y in zip(Y, ys)])
        FE = np.stack([(yr == y).astype(float) for y in ys[1:]], 1)
        return np.c_[np.vstack(X), FE], np.concatenate(Y), yr

    fits = {}
    for spec, quad in (("linear", False), ("quad", True)):
        Xf, Y, _ = design(FIT_YEARS, quad)
        beta = np.linalg.lstsq(Xf, Y, rcond=None)[0]
        res = Y - Xf @ beta
        nT = len(BLOCKS) * (4 if quad else 2)
        F = {"r2": round(float(1 - res.var() / Y.var()), 4), "rmse_gw": round(float(res.std()), 3), "bT": beta[:nT],
             "quad": quad}
        # leave-one-winter-out: train on the other years + this year's Apr-Oct (identifies its level), score Dec-Feb
        cv = {}
        for h in FIT_YEARS:
            rows = {y: slice(None) for y in FIT_YEARS if y != h}
            rows[h] = np.isin(dts[h], [4, 5, 6, 7, 8, 9, 10])
            ys = [y for y in FIT_YEARS if y != h] + [h]
            Xt, Yt, _ = design(ys, quad, rows)
            b = np.linalg.lstsq(Xt, Yt, rcond=None)[0]
            win = np.isin(dts[h], [12, 1, 2])
            Xh = np.c_[temp_feats(*temps[h], quad=quad), cal[h]][win]
            pred = Xh @ b[:Xh.shape[1]] + b[-1]                     # the held-out year's level is the last FE column
            err = pred - nds[h][win]
            Th = temps[h][0][win]
            cold = Th <= np.percentile(Th, 5)
            top = np.argsort(nds[h][win])[-20:]
            cv[h] = {"rmse_gw": round(float(np.sqrt((err ** 2).mean())), 3), "bias_gw": round(float(err.mean()), 3),
                     "cold5_bias_gw": round(float(err[cold].mean()), 3), "cold5_rmse_gw": round(float(np.sqrt((err[cold] ** 2).mean())), 3),
                     "top20_bias_gw": round(float(err[top].mean()), 3), "coldest_c": round(float(Th.min()), 1)}
        F["cv"] = cv
        F["cv_summary"] = {k: round(float(np.mean([cv[h][k] for h in cv])), 3) for k in ("rmse_gw", "bias_gw", "cold5_bias_gw", "cold5_rmse_gw", "top20_bias_gw")}
        F["cv_summary"]["top20_bias_worst_gw"] = round(float(max((cv[h]["top20_bias_gw"] for h in cv), key=abs)), 3)
        if not quad:                                                 # block bootstrap by week for the temperature coefficients
            rng = np.random.default_rng(9112026)
            nwk = len(Y) // 336 + 1
            boots = []
            for _ in range(60):
                pick = rng.integers(0, nwk, nwk)
                idx = np.concatenate([np.arange(k * 336, min((k + 1) * 336, len(Y))) for k in pick])
                boots.append(np.linalg.lstsq(Xf[idx], Y[idx], rcond=None)[0][:nT])
            boots = np.array(boots)
            F["temp_coef_gw_per_k"] = {f"{a}-{b}": [round(float(beta[2 * i]), 3), round(float(beta[2 * i + 1]), 3)]
                                       for i, (a, b) in enumerate(BLOCKS)}
            F["temp_coef_boot_sd"] = {f"{a}-{b}": [round(float(boots[:, 2 * i].std()), 3), round(float(boots[:, 2 * i + 1].std()), 3)]
                                      for i, (a, b) in enumerate(BLOCKS)}
        del Xf
        fits[spec] = F
        print(spec, json.dumps({k: v for k, v in F.items() if k not in ("bT", "cv")}), flush=True)
    fit = {k: v for k, v in fits["linear"].items() if k not in ("bT",)}
    fit["quad"] = {k: v for k, v in fits["quad"].items() if k not in ("bT",)}
    fit["fit_coldest_gb_c"] = [round(float(Tall.min()), 1), round(float(T24all.min()), 1)]
    fit["spec"] = ("ND (GW, half-hourly, 2016-26) on: HDD(15.5 - T) and HDD of the ~24 h EWMA temperature, each by 5 slot "
                   "blocks (quad: plus their squares); 48 slots x 3 day types (weekday, Saturday, Sunday/bank holiday); "
                   "3 day-of-year harmonics by block; year fixed effects. T = 79 towns weighted by regional gas meters.")
    nd25, dates25 = nd_year(2025)
    T25 = to_slots(hourly_gb(2025, names, w, H))[:len(nd25)]
    T25_24 = ewma(T25)
    pidx = {d: i for i, d in enumerate(dates25)}
    W = json.load(open(GB / "region_weights.json"))["homes"]
    years = sorted(int(p.name) for p in SRC.iterdir() if (p / "flex_region.npz").exists())
    out = {"fit": fit, "by_year": {}, "method": __doc__.split("\n\n")[1].strip()}
    for y in years:
        f = np.load(SRC / str(y) / "flex_region.npz")
        regs, tar, ctrl = list(f["regions"]), list(f["tariffs"]), list(f["ctrl"])
        ww = np.array([W[r] for r in regs], float)
        e = f["e"].astype(np.float64)
        gw = lambda t, c: ((e[:, :, tar.index(t), ctrl.index(c)] * ww[:, None, None]).sum(0) * 2 / 1e6).ravel()  # noqa: E731
        dates = [str(d) for d in f["dates"]]
        from review_sdp import price_day                                          # same calendar mapping as the model
        pi = np.array([pidx[price_day(d)] for d in dates])
        sl = (pi[:, None] * 48 + np.arange(48)).ravel()
        Ty = to_slots(hourly_gb(y, names, w, H))[:len(dates) * 48]
        Ty24 = ewma(Ty)
        base0 = nd25[sl]
        Y_ = {"base_fixed_peak": round(float(base0.max()), 1)}
        for var, spec, cap in (("linear", "linear", None), ("capped", "linear", hd_cap), ("quad", "quad", None),
                               ("quad_capped", "quad", hd_cap)):
            bT, q = fits[spec]["bT"], fits[spec]["quad"]
            adj = temp_feats(Ty, Ty24, cap, q) @ bT - temp_feats(T25[sl], T25_24[sl], cap, q) @ bT
            base = base0 + adj
            V = {"base_peak": round(float(base.max()), 1), "adj_at_base_peak": round(float(adj[base.argmax()]), 2)}
            capv = float((base + gw("svr", "ccop")).max())
            V["cap"] = round(capv, 1)
            for t in ("svr", "agile", "cosy", "iog"):
                for c in ("hp", "ccop"):
                    V[f"{c}_{t}"] = round(float((base + gw(t, c)).max()), 1)
                h = gw(t, "ccop")
                phi = np.where(base + h > capv, np.clip(1 - (capv - base) / np.maximum(h, 1e-9), 0, 1), 0.)
                V[f"sdp_{t}"] = round(float((base + h * (1 - phi)).max()), 1)
            V["heat_only_hp_peak"] = round(float(gw("svr", "hp").max()), 1)
            Y_[var] = V
        for t in ("svr", "agile", "cosy", "iog"):                              # the paper's numbers on the fixed base
            for c in ("hp", "ccop", "sdp"):
                Y_.setdefault("fixed", {})[f"{c}_{t}"] = round(float((base0 + gw(t, c)).max()), 1)
        out["by_year"][y] = Y_
        print(y, Y_["base_fixed_peak"], Y_["linear"]["base_peak"], Y_["fixed"]["hp_svr"], Y_["linear"]["hp_svr"],
              Y_["fixed"]["ccop_agile"], Y_["linear"]["ccop_agile"], Y_["linear"]["sdp_agile"], flush=True)
    s = {}
    by = out["by_year"]
    for var in ("fixed", "linear", "capped", "quad", "quad_capped"):
        g = (lambda y, k: by[y][var][k]) if var != "fixed" else (lambda y, k: by[y]["fixed"][k])
        s[var] = {k: {"mean": round(float(np.mean([g(y, k) for y in years])), 1), "max": max(g(y, k) for y in years)}
                  for k in ["hp_svr", "ccop_svr", "ccop_agile", "ccop_cosy", "ccop_iog", "sdp_agile", "sdp_cosy", "sdp_iog"]}
        s[var]["herd_excess_agile"] = round(s[var]["ccop_agile"]["max"] - s[var]["sdp_agile"]["max"], 1)
        s[var]["herd_excess_iog"] = round(s[var]["ccop_iog"]["max"] - s[var]["sdp_iog"]["max"], 1)
    for var in ("linear", "capped", "quad", "quad_capped"):
        s[var]["base_peak"] = {"mean": round(float(np.mean([by[y][var]["base_peak"] for y in years])), 1),
                               "max": max(by[y][var]["base_peak"] for y in years)}
    s["fixed"]["base_peak"] = {"mean": round(float(np.mean([by[y]["base_fixed_peak"] for y in years])), 1),
                               "max": max(by[y]["base_fixed_peak"] for y in years)}
    out["summary"] = s
    OUT.write_text(json.dumps(out, indent=1))
    print(json.dumps(s, indent=1))


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    main()
