"""Fuel Poverty 2023 EHS dataset (UKDS SN 9466, safeguarded): weighted aggregates only. Writes /w/work/fp2023_results.json."""
import json

import numpy as np
import pandas as pd

d = pd.read_csv("/w/x/UKDA-9466-tab/tab/fuel_poverty_2023_ukda_eul.tab", sep="\t")
w = d.aagph2223.astype(float).values
R = {"n": int(len(d)), "households_weighted": int(w.sum())}

def wq(x, w, q):
    m = np.isfinite(x)
    x, w = x[m], w[m]
    o = np.argsort(x)
    cw = np.cumsum(w[o]) / w[o].sum()
    return float(x[o][np.searchsorted(cw, q)])

def summ(x, w, nd=0):
    x = np.asarray(x, float)
    m = np.isfinite(x)
    return {"n": int(m.sum()), "mean": round(float((x[m] * w[m]).sum() / w[m].sum()), nd), "p10": round(wq(x, w, .1), nd),
            "p25": round(wq(x, w, .25), nd), "p50": round(wq(x, w, .5), nd), "p75": round(wq(x, w, .75), nd), "p90": round(wq(x, w, .9), nd)}

def shares(col, mask=None):
    v = d[col]
    m = v.notna() if mask is None else (v.notna() & mask)
    return {str(k): round(float(w[m & (v == k)].sum() / w[m].sum()), 4) for k in sorted(v[m].unique())}

for c in ("Mainfueltype", "CentralHeating", "boiler", "Ongas", "EPC", "FPEERband", "tenure4x", "DWtype", "gorehs", "fpLILEEflg", "fpvuln", "BHCflg10", "AHCflg10"):
    R[f"share_{c}"] = shares(c)
gas = d.Mainfueltype == 1          # check code in the dictionary before using
R["gas_main_fuel_code_assumed"] = 1
R["share_EPC_gas"] = shares("EPC", gas)
R["share_fpLILEEflg_by_fuel"] = {str(k): round(float(w[(d.Mainfueltype == k) & (d.fpLILEEflg == 1)].sum() / w[d.Mainfueltype == k].sum()), 4) for k in sorted(d.Mainfueltype.dropna().unique())}
heat = (d.spahcost + d.wathcost).astype(float)
ahc = (d.fpfullinc - d.HousingCosts).astype(float)
R["heat_cost_gbp"] = summ(heat, w)
R["heat_cost_gbp_gas"] = summ(heat[gas], w[gas])
R["space_heat_cost_gbp_gas"] = summ(d.spahcost[gas], w[gas])
R["fuel_cost_all_gbp"] = summ(d.fuelexpn, w)
R["full_income_gbp"] = summ(d.fpfullinc, w)
R["ahc_income_gbp"] = summ(ahc, w)
R["ahc_eq_income_gbp"] = summ(d.AHCIncomeEQ_LILEE, w)
R["heat_share_of_ahc_income_pct"] = summ(100 * heat / ahc.clip(lower=1), w, 1)
R["heat_share_of_full_income_pct"] = summ(100 * heat / d.fpfullinc.clip(lower=1), w, 1)
R["share_heat_over_10pct_ahc"] = round(float(w[(100 * heat / ahc.clip(lower=1)) > 10].sum() / w.sum()), 4)
R["share_heat_over_10pct_ahc_gas"] = round(float(w[gas & ((100 * heat / ahc.clip(lower=1)) > 10)].sum() / w[gas].sum()), 4)
by = {}
for dec in sorted(d.EqAHCincDeciles_LILEE.dropna().unique()):
    m = d.EqAHCincDeciles_LILEE == dec
    by[str(int(dec))] = {"heat_cost_gbp": round(float((heat[m] * w[m]).sum() / w[m].sum())), "heat_share_ahc_pct": round(wq((100 * heat / ahc.clip(lower=1))[m].values, w[m], .5), 1),
                         "lilee_rate": round(float(w[m & (d.fpLILEEflg == 1)].sum() / w[m].sum()), 3), "gas_share": round(float(w[m & gas].sum() / w[m].sum()), 3),
                         "epc_d_or_worse": round(float(w[m & (d.EPC >= 2)].sum() / w[m].sum()), 3), "epc_f_g": round(float(w[m & (d.EPC >= 4)].sum() / w[m].sum()), 3),
                         "ahc_income_p50": round(wq(ahc[m].values, w[m], .5)), "heat_cost_gas_gbp": round(float((heat[m & gas] * w[m & gas]).sum() / w[m & gas].sum()))}
R["by_ahc_decile"] = by
R["share_FloorArea_band"] = shares("FloorArea")           # 1 <50, 2 50-69, 3 70-89, 4 90-109, 5 110+ m2
R["share_FloorArea_band_gas"] = shares("FloorArea", gas)
R["sap12"] = summ(d.SAP12, w, 1)
R["sap12_gas"] = summ(d.SAP12[gas], w[gas], 1)
json.dump(R, open("/w/work/fp2023_results.json", "w"), indent=1)
print(json.dumps(R, indent=0)[:6000])
