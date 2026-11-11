#!/usr/bin/env python3
"""A local-network constrained case (independent review, 10 Nov 2026, item 3): heat pumps and hybrids on low-voltage
feeders, with heterogeneous homes, measured base loads and mixed tariffs, against the feeder's own capacity.

Homes: the model's 4,000 sampled Birmingham homes (real stock heat loss, MCS-sized units) on the town's 12 coldest
days of a winter, each home's half-hourly electricity under every tariff x controller from gb_coincidence.py
--save-e (all-electric hp; hybrid C-COP ccop; hybrid under national SD-Power dispatch sdp, pass-2 shares).
Base load: each home takes one Low Carbon London flat-tariff home's measured winter-weekday profiles (lcl_base.py),
a different day for each model day. Feeders: the homes shuffled into feeders of N, so each feeder mixes leaky and
tight homes; tariffs by mix (all Agile; a quarter on each of SVR, Agile, Cosy, IOG).
Capacity: a feeder "built for its homes" carries its own pre-heat-pump peak (the base loads' highest half-hour
over the window) plus a headroom of h kW per home; h is swept, with 1.5 kW the WinDebut diversified peak for a
gas-heated property and 1.7-2.4 kW NESO's planning allowance per heat pump (BEIS2022_LVCapacity; NESO2026_CPA).
Local dispatch: when a feeder would exceed its capacity, hybrids on it (those running the heat pump) are sent to
gas one home at a time, in random order, until it does not; applied to C-COP (local only) and on top of national
SD-Power (both). Conflicts: half-hours in which the feeder is over its limit while the national cap is not binding
(national dispatch silent), and in which national dispatch sheds homes while the feeder has room.
    python feeder_case.py --e /work/out/feeder_e_1962_Birmingham.npz --base /lcl/lcl_base.npz --n 100 --out f.json
"""
import json
import sys

import numpy as np

ARG = lambda k, d: type(d)(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d       # noqa: E731
E_PATH, BASE, OUT = ARG("--e", ""), ARG("--base", "/lcl/lcl_base.npz"), ARG("--out", "feeder_case.json")
N, SEED = ARG("--n", 100), ARG("--seed", 9112026)
HEAD = [0.0, 0.5, 1.0, 1.5, 1.7, 2.4]                        # kW per home above the feeder's pre-heat-pump peak
MIXES = {"agile": {"agile": 1.0}, "even4": {"svr": .25, "agile": .25, "cosy": .25, "iog": .25}}
rng = np.random.default_rng(SEED)

f = np.load(E_PATH)
E = f["e"].astype(np.float32) * 2.0                        # (T, C, B, slots) kW
tar, ctrl, dates = list(f["tariffs"]), list(f["ctrl"]), list(f["dates"])
T, C, B, S = E.shape
D = S // 48
lb = np.load(BASE)
kw, home = lb["kw"].astype(np.float32), lb["home"]
starts = np.r_[0, np.cumsum(np.bincount(home))]
# base load: one London home per model home, one of its days per model day
pick = rng.integers(0, home.max() + 1, B)
base = np.empty((B, S), np.float32)
for d in range(D):
    row = starts[pick] + rng.integers(0, starts[pick + 1] - starts[pick])
    base[:, d * 48:(d + 1) * 48] = kw[row]
# feeders
order = rng.permutation(B)
F = B // N
fid = np.full(B, -1)
fid[order[:F * N]] = np.repeat(np.arange(F), N)
sel = fid >= 0
base_f = np.stack([base[fid == i].sum(0) for i in range(F)])          # (F, S)
p0 = base_f.max(1)                                                     # pre-heat-pump peak per feeder


def heat_kw(c, mix):
    """Each home's electricity for heat (kW) under controller c with tariffs drawn by mix: (B, S)."""
    u = rng.random(B)
    out = np.zeros((B, S), np.float32)
    lo = 0.0
    for t, share in mix.items():
        m = (u >= lo) & (u < lo + share)
        out[m] = E[tar.index(t), ctrl.index(c)][m]
        lo += share
    return out


def feeder_sum(x):
    return np.stack([x[fid == i].sum(0) for i in range(F)])


def local_dispatch(h_kw, cap):
    """Send hybrids on an overloaded feeder to gas, one home at a time in random order, until it fits.
    Returns the feeder loads after dispatch (F, S) and the share of home-slots sent to gas."""
    h2 = h_kw.copy()
    shed = 0
    for i in range(F):
        homes = np.where(fid == i)[0]
        for s in range(S):
            load = base_f[i, s] + h2[homes, s].sum()
            if load <= cap[i]:
                continue
            on = homes[h2[homes, s] > 0]
            for j in rng.permutation(on):
                load -= h2[j, s]
                h2[j, s] = 0.0
                shed += 1
                if load <= cap[i]:
                    break
    return base_f + feeder_sum(h2), shed / max(1, (h_kw[sel] > 0).sum())


def metrics(load, cap):
    over = load - cap[:, None]
    m = over > 1e-6
    days = m.reshape(F, D, 48).any(2)
    return {"feeder_days_over_pct": round(100 * float(days.mean()), 1),
            "feeder_slots_over_pct": round(100 * float(m.mean()), 2),
            "feeders_ever_over_pct": round(100 * float(m.any(1).mean()), 1),
            "max_over_pct_of_cap": round(100 * float((over / cap[:, None]).max()), 1),
            "peak_kw_per_home_mean": round(float(load.max(1).mean() / N), 3)}


R = {"source": E_PATH, "dates": dates, "homes": int(F * N), "feeders": F, "homes_per_feeder": N,
     "base": {"peak_kw_per_home_mean": round(float(p0.mean() / N), 3), "kwh_day_per_home": round(float(base.sum(1).mean() / 2 / D), 2)},
     "scenarios": {}}
hp = heat_kw("hp", {"svr": 1.0})
load_hp = base_f + feeder_sum(hp)
R["hp_diversified_kw_per_home"] = round(float(((load_hp.max(1) - p0) / N).mean()), 3)
R["hp_peak_kw_per_home_mean"] = round(float(load_hp.max(1).mean() / N), 3)
sdp_active = (E[tar.index("agile"), ctrl.index("sdp")] < E[tar.index("agile"), ctrl.index("ccop")] - 1e-4).any(0)   # (S,)
R["national_shed_slots"] = int(sdp_active.sum())
for mname, mix in MIXES.items():
    u = rng.random(B)                                                  # one tariff draw: ccop and sdp share it
    cc = np.zeros((B, S), np.float32)
    sd = np.zeros((B, S), np.float32)
    lo = 0.0
    for t, share in mix.items():
        m = (u >= lo) & (u < lo + share)
        cc[m] = E[tar.index(t), ctrl.index("ccop")][m]
        sd[m] = E[tar.index(t), ctrl.index("sdp")][m]
        lo += share
    load_cc, load_sd = base_f + feeder_sum(cc), base_f + feeder_sum(sd)
    for h in HEAD:
        cap = p0 + h * N
        key = f"{mname}_h{h:g}"
        loc, shed_loc = local_dispatch(cc, cap)
        both, shed_both = local_dispatch(sd, cap)
        over_cc = (load_cc - cap[:, None]) > 1e-6
        nat = sdp_active[None, :] & np.ones((F, 1), bool)
        R["scenarios"][key] = {
            "all_electric": metrics(load_hp, cap),
            "hybrid_ccop": metrics(load_cc, cap),
            "hybrid_national": metrics(load_sd, cap),
            "hybrid_local": {**metrics(loc, cap), "home_slots_to_gas_pct": round(100 * shed_loc, 2)},
            "hybrid_both": {**metrics(both, cap), "home_slots_to_gas_pct": round(100 * shed_both, 2)},
            "conflict_feeder_slots": {"feeder_over_national_silent_pct": round(100 * float((over_cc & ~nat).mean()), 2),
                                      "national_sheds_feeder_fine_pct": round(100 * float((~over_cc & nat).mean()), 2),
                                      "both_pct": round(100 * float((over_cc & nat).mean()), 2)}}
        print(key, R["scenarios"][key]["all_electric"]["feeders_ever_over_pct"], R["scenarios"][key]["hybrid_ccop"]["feeders_ever_over_pct"],
              R["scenarios"][key]["hybrid_national"]["feeders_ever_over_pct"], R["scenarios"][key]["hybrid_local"]["feeders_ever_over_pct"],
              R["scenarios"][key]["hybrid_local"]["home_slots_to_gas_pct"], flush=True)
json.dump(R, open(OUT, "w"), indent=1)
print("done", OUT)
