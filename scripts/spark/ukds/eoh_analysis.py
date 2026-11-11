"""Electrification of Heat (UKDS SN 9209, open) half-hourly data: aggregates for the paper.

Per home: 12-month realised performance (heat out / whole-system electricity, SPFH4-like, and without the immersion
and back-up heaters), by heat pump type and hybrid or not. Hybrids: share of heat from the boiler by outdoor
temperature. Cold days: coincident electrical demand per home (ADMD), coincidence factors for groups of 10, 34 and
all homes, the mean diurnal profile. Internal temperature habits: evening-to-night setback. Flow temperature by
outdoor temperature. Aggregates only; writes /w/work/eoh_results.json.
"""
import json

import numpy as np
import pandas as pd

P = "/w/work/eoh_hh.parquet"
rng = np.random.default_rng(9209)
df = pd.read_parquet(P).sort_values(["Property_ID", "Timestamp"]).reset_index(drop=True)
df["Property_ID"] = df["Property_ID"].astype(str)
E = {"hp": "Heat_Pump_Energy_Output", "sys": "Whole_System_Energy_Consumed", "boil": "Boiler_Energy_Output",
     "imm": "Immersion_Heater_Energy_Consumed", "bku": "Back-up_Heater_Energy_Consumed", "pump": "Circulation_Pump_Energy_Consumed"}
g = df.groupby("Property_ID", sort=False)
for k, c in E.items():
    d = g[c].diff()
    same = g["Timestamp"].diff() == pd.Timedelta("30min")
    d = d.where(same)
    d = d.where((d >= 0) & (d <= 25))                    # meter noise, resets, impossible jumps (> 50 kW for 30 min)
    df[k] = d.astype("float32")
df["date"] = df.Timestamp.dt.floor("D")
df["hh"] = (df.Timestamp.dt.hour * 2 + df.Timestamp.dt.minute // 30).astype("int16")
pid = df.Property_ID
gshp = set(df.loc[df.Brine_Flow_Temperature.notna(), "Property_ID"].unique())
boil_tot = df.groupby("Property_ID")["boil"].sum()
hyb = set(boil_tot[boil_tot > 300].index)                 # boiler meter that actually delivers heat
R = {"homes": int(pid.nunique()), "gshp_homes": len(gshp), "hybrid_homes": len(hyb),
     "span": [str(df.Timestamp.min()), str(df.Timestamp.max())], "rows": int(len(df))}
print(R, flush=True)

def pct(x, q=(10, 25, 50, 75, 90)):
    x = np.asarray([v for v in x if np.isfinite(v)])
    return {} if len(x) == 0 else {f"p{p}": round(float(np.percentile(x, p)), 3) for p in q} | {"n": int(len(x)), "mean": round(float(x.mean()), 3)}

# 1. twelve-month performance, windows Oct Y to Sep Y+1 (data ends 28 Sep 2023)
spf = {}
for y in (2021, 2022):
    w = df[(df.Timestamp >= f"{y}-10-01") & (df.Timestamp < f"{y + 1}-10-01")]
    a = w.groupby("Property_ID").agg(hp=("hp", "sum"), sys=("sys", "sum"), imm=("imm", "sum"), bku=("bku", "sum"), boil=("boil", "sum"),
                                     n_hp=("hp", "count"), n_sys=("sys", "count"))
    full = 365 * 48
    ok = a[(a.n_hp >= 0.9 * full) & (a.n_sys >= 0.9 * full) & (a.sys > 500)]
    h4 = ok.hp / ok.sys
    h2 = ok.hp / (ok.sys - ok.imm.fillna(0) - ok.bku.fillna(0)).clip(lower=1)
    rows = {"all_h4": pct(h4), "all_excl_imm_backup": pct(h2),
            "ashp_nonhybrid_h4": pct(h4[[i not in gshp and i not in hyb for i in h4.index]]),
            "gshp_h4": pct(h4[[i in gshp for i in h4.index]]),
            "hybrid_hp_only_h4": pct(h4[[i in hyb for i in h4.index]]),
            "heat_kwh_year": pct(ok.hp + ok.boil.fillna(0)), "hp_elec_kwh_year": pct(ok.sys),
            "imm_share_of_elec": pct((ok.imm.fillna(0) / ok.sys) * 100)}
    spf[f"{y}-{y + 1}"] = rows
    print(y, rows["all_h4"], flush=True)
R["spf_12m"] = spf

# 2. hybrids: boiler share by outdoor temperature (winter months), and each home's own crossover
hw = df[pid.isin(hyb) & (df.Timestamp.dt.month.isin([11, 12, 1, 2, 3]))].copy()
hw["tb"] = (np.floor(hw.External_Air_Temperature / 2) * 2)
hb = hw.groupby("tb").agg(hp=("hp", "sum"), boil=("boil", "sum"), n=("hp", "count"))
hb = hb[(hb.index >= -8) & (hb.index <= 16) & (hb.n > 2000)]
R["hybrid_boiler_share_by_temp"] = {str(int(t)): round(float(r.boil / (r.hp + r.boil)), 3) for t, r in hb.iterrows()}
per = hw.groupby(["Property_ID", "tb"]).agg(hp=("hp", "sum"), boil=("boil", "sum"))
per["share"] = per.boil / (per.hp + per.boil)
cross = {}
for h, s in per.groupby(level=0):
    s = s.droplevel(0).sort_index()
    s = s[(s.index >= -8) & (s.index <= 16)]
    if len(s) < 5:
        continue
    above = s[s.share > 0.5]
    cross[h] = float(above.index.max()) if len(above) else -99.0   # warmest 2-degree bin where gas carries most of the heat
wint = hw.groupby("Property_ID").agg(hp=("hp", "sum"), boil=("boil", "sum"))
R["hybrid_winter_boiler_share_per_home"] = pct((wint.boil / (wint.hp + wint.boil)) * 100)
cv = np.array(list(cross.values()))
R["hybrid_crossover_bin_c"] = pct(cv[cv > -99]) | {"never_gas_majority": int((cv == -99).sum())}
both = hw[(hw.hp > 0.1) & (hw.boil > 0.1)]
R["hybrid_both_running_share_of_heating_hh"] = round(float(len(both) / max(1, ((hw.hp > 0.1) | (hw.boil > 0.1)).sum())), 3)
print("hybrid", R["hybrid_boiler_share_by_temp"], R["hybrid_crossover_bin_c"], flush=True)

# 3. cold days: coincident demand of heat-pump homes (whole-system electricity, kW)
df["kw"] = df["sys"] * 2
dayT = df.groupby(["date", "Property_ID"])["External_Air_Temperature"].mean().groupby(level=0).median()
dayN = df.groupby("date")["sys"].count() / 48
cand = dayT[(dayN > 250)].sort_values()
cold = []
for d, t in cand.items():
    if all(abs((d - c).days) > 1 for c in cold):
        cold.append(d)
    if len(cold) == 12:
        break
R["cold_days"] = [{"date": str(d.date()), "median_home_mean_temp_c": round(float(dayT[d]), 2), "homes": int(dayN[d])} for d in cold]
nh = df[~pid.isin(hyb)]
prof = {}
cf_all, cf10, cf34, admd, ipk = [], [], [], [], []
for d in cold:
    w = nh[nh.date == d]
    m = w.pivot_table(index="Property_ID", columns="hh", values="kw")
    m = m.dropna(thresh=46).fillna(0)
    if len(m) < 50:
        continue
    tot = m.mean(0)                                    # kW per home, coincident
    prof[str(d.date())] = [round(float(v), 3) for v in tot.values]
    admd.append(float(tot.max()))
    ipk.append(float(m.max(1).median()))
    cf_all.append(float(m.sum(0).max() / m.max(1).sum()))
    for n, store in ((10, cf10), (34, cf34)):
        vals = []
        for _ in range(300):
            s = m.iloc[rng.choice(len(m), n, replace=False)]
            vals.append(s.sum(0).max() / s.max(1).sum())
        store.append(float(np.mean(vals)))
R["cold_day_admd_kw_per_home"] = pct(admd)
R["cold_day_individual_peak_kw_median"] = pct(ipk)
R["cold_day_cf_all"] = pct(cf_all)
R["cold_day_cf10"] = pct(cf10)
R["cold_day_cf34"] = pct(cf34)
R["cold_day_profiles_kw_per_home"] = prof
# the single coldest day: peak hour
if prof:
    k0 = list(prof)[0]
    R["coldest_day_peak_hh"] = int(np.argmax(prof[k0]))
# winter-long per-home p99 electrical kW, and the all-home coincident winter peak
wn = nh[nh.Timestamp.dt.month.isin([12, 1, 2])]
R["winter_home_p99_kw"] = pct(wn.groupby("Property_ID")["kw"].quantile(0.99))
R["winter_home_max_kw"] = pct(wn.groupby("Property_ID")["kw"].max())
coinc = wn.groupby("Timestamp")["kw"].agg(["mean", "count"])
coinc = coinc[coinc["count"] > 250]
R["winter_coincident_mean_kw_max"] = round(float(coinc["mean"].max()), 3)
R["winter_coincident_mean_kw_max_at"] = str(coinc["mean"].idxmax())
print("cold days", R["cold_day_admd_kw_per_home"], R["cold_day_cf34"], flush=True)

# 4. internal temperature habits on winter days (non-hybrid): evening mean minus night minimum, per home
wt = wn[wn.Internal_Air_Temperature.notna()]
pt = wt.groupby(["Property_ID", "hh"])["Internal_Air_Temperature"].mean().unstack()
pt = pt.dropna(thresh=40)
eve = pt.loc[:, 34:43].mean(1)                            # 17:00 to 21:30
night = pt.loc[:, 0:11].min(1)                             # 00:00 to 05:30
morn = pt.loc[:, 14:19].mean(1)                            # 07:00 to 09:30
R["internal_winter"] = {"evening_mean_c": pct(eve), "night_min_c": pct(night), "setback_eve_minus_night_k": pct(eve - night),
                        "share_setback_over_2k": round(float(((eve - night) > 2).mean()), 3),
                        "share_setback_over_1k": round(float(((eve - night) > 1).mean()), 3),
                        "daily_mean_c": pct(pt.mean(1)), "homes": int(len(pt)),
                        "mean_profile_c": [round(float(v), 2) for v in pt.mean(0).values]}
# heat pump running overnight: share of HP heat delivered 00:00-06:00 on winter days
hn = wn.groupby("hh")["hp"].sum()
R["share_hp_heat_0000_0600"] = round(float(hn.loc[0:11].sum() / hn.sum()), 3)
R["winter_mean_hp_heat_profile_kw_per_home"] = [round(float(v), 3) for v in (wn.groupby("hh")["hp"].mean() * 2).values]
print("internal", R["internal_winter"]["setback_eve_minus_night_k"], flush=True)

# 5. flow temperature when heating, by outdoor temperature (ASHP, non-hybrid)
fl = nh[(~nh.Property_ID.isin(gshp)) & (nh.hp > 0.25) & nh.Heat_Pump_Heating_Flow_Temperature.notna()].copy()
fl["tb"] = np.floor(fl.External_Air_Temperature / 2) * 2
ft = fl.groupby("tb")["Heat_Pump_Heating_Flow_Temperature"].agg(["median", "count"])
R["flow_temp_by_outdoor"] = {str(int(t)): round(float(r["median"]), 1) for t, r in ft.iterrows() if -8 <= t <= 16 and r["count"] > 2000}
# per-home median flow at 0 to 2 C
f0 = fl[(fl.tb == 0)].groupby("Property_ID")["Heat_Pump_Heating_Flow_Temperature"].median()
R["flow_temp_at_0_2c_per_home"] = pct(f0)
# 6. the open per-home summaries from ESC's USmart platform (x/eoh_performance_summary.csv, x/eoh_property_design_installation.csv)
try:
    ps = pd.read_csv("/w/x/eoh_performance_summary.csv", na_values=["null", ""]).set_index("Property_ID")
    pdi = pd.read_csv("/w/x/eoh_property_design_installation.csv", na_values=["null", ""], low_memory=False)
    pdi = pdi[pdi.HP_Installed.notna()].drop_duplicates("Property_ID").set_index("Property_ID")
    R["esc_hp_installed"] = ps.HP_Installed.value_counts().to_dict()
    R["esc_hybrid_vs_boiler_meter"] = {"esc_hybrids": int((ps.HP_Installed == "Hybrid").sum()),
                                      "boiler_meter_hybrids": len(hyb),
                                      "both": int(sum(1 for h in hyb if ps.HP_Installed.get(h) == "Hybrid"))}
    inc = ps[ps.Included_SPF_analysis == True]  # noqa: E712
    R["esc_spfh4_included"] = pct(inc.SPFH4_selected_window) | {"spfh2_p50": round(float(inc.SPFH2_selected_window.median()), 3)}
    for typ in ("ASHP", "HT_ASHP", "GSHP", "Hybrid"):
        R[f"esc_spfh4_{typ}"] = pct(inc[inc.HP_Installed == typ].SPFH4_selected_window)
    # our twelve-month figure against ESC's selected window, same homes
    mine = {}
    for y in (2021, 2022):
        w = df[(df.Timestamp >= f"{y}-10-01") & (df.Timestamp < f"{y + 1}-10-01")]
        a = w.groupby("Property_ID").agg(hp=("hp", "sum"), sys=("sys", "sum"), n_hp=("hp", "count"), n_sys=("sys", "count"))
        a = a[(a.n_hp >= 0.9 * 365 * 48) & (a.n_sys >= 0.9 * 365 * 48) & (a.sys > 500)]
        for h, r in a.iterrows():
            mine.setdefault(h, []).append(r.hp / r.sys)
    both = [(np.mean(v), inc.SPFH4_selected_window[h]) for h, v in mine.items() if h in inc.index and np.isfinite(inc.SPFH4_selected_window[h])]
    if both:
        m, e_ = np.array(both).T
        R["spf_mine_vs_esc"] = {"n": len(both), "median_abs_diff": round(float(np.median(np.abs(m - e_))), 3), "median_mine": round(float(np.median(m)), 3),
                               "median_esc": round(float(np.median(e_)), 3), "corr": round(float(np.corrcoef(m, e_)[0, 1]), 3)}
    # design values of the installed homes
    ins = pdi[pdi.index.isin(ps.index)]
    R["design_flow_temp_c"] = pct(ins.MCS_Flow_Temp[(ins.MCS_Flow_Temp > 25) & (ins.MCS_Flow_Temp < 80)])
    R["design_flow_temp_c_by_type"] = {t: pct(ins[(ins.HP_Installed == t)].MCS_Flow_Temp[(ins.MCS_Flow_Temp > 25) & (ins.MCS_Flow_Temp < 80)]) for t in ("ASHP", "HT_ASHP", "Hybrid")}
    hl = pd.to_numeric(ins.MCS_Hloss, errors="coerce")
    hl = hl.where(hl < 100, hl / 1000)                     # mostly entered in W, a few in kW
    hl = hl[(hl > 1) & (hl < 30)]
    R["design_heat_loss_kw"] = pct(hl)
    R["hp_size_kw"] = pct(ins.HP_Size_kW[(ins.HP_Size_kW > 2) & (ins.HP_Size_kW < 30)])
    R["floor_area_m2"] = pct(ins.Total_Floor_Area[(ins.Total_Floor_Area > 20) & (ins.Total_Floor_Area < 500)])
    R["house_sap"] = pct(pd.to_numeric(ins.House_SAP, errors="coerce").dropna())
    # coldest-day coincident demand per kW of design heat loss (non-hybrid homes with a design figure)
    if prof:
        d0 = pd.Timestamp(list(prof)[0])
        w = nh[nh.date == d0]
        m = w.pivot_table(index="Property_ID", columns="hh", values="kw").dropna(thresh=46).fillna(0)
        hl_m = hl.reindex(m.index).dropna()
        m2 = m.loc[hl_m.index]
        R["coldest_day_admd_per_kw_design_loss"] = round(float(m2.mean(0).max() / hl_m.mean()), 3)
        R["coldest_day_admd_homes_with_design"] = int(len(m2))
        R["coldest_day_individual_peak_over_design_loss_p50"] = round(float((m2.max(1) / hl_m).median()), 3)
    print("esc", R["esc_hybrid_vs_boiler_meter"], R.get("spf_mine_vs_esc"), R["design_flow_temp_c"], flush=True)
except FileNotFoundError as e:
    print("no USmart summaries:", e)
json.dump(R, open("/w/work/eoh_results.json", "w"), indent=1)
print("done")
