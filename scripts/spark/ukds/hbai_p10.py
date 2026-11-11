"""IFS Households Below Average Income 1961-1993 (UKDS SN 3300, safeguarded, FES-based): weighted percentiles of
equivalised disposable household income per year, nominal, January prices of the year (within-year deflator), annualised
x52. Individual-weighted (BUGF_2, the HBAI convention) and benefit-unit-weighted (BUGF_1). Compared with the ONS HDII
series the paper already uses (income_series.csv, nominal) where both exist. Aggregates only."""
import json

import numpy as np
import pandas as pd

def wq(x, w, q):
    m = np.isfinite(x) & np.isfinite(w) & (w > 0)
    x, w = x[m], w[m]
    o = np.argsort(x)
    cw = np.cumsum(w[o]) / w[o].sum()
    return float(x[o][np.searchsorted(cw, q)])

R = {}
for y in range(61, 94):
    f = f"/w/x/UKDA-3300-tab/tab/ifs{y}.tab"
    try:
        d = pd.read_csv(f, sep="\t")
    except FileNotFoundError:
        continue
    d.columns = [c.lower() for c in d.columns]
    yr = 1900 + y
    bhc = d.hbhci.astype(float) / d.hes_bhc.astype(float) * d.wyd_bhc.astype(float)
    ahc = d.hahci.astype(float) / d.hes_ahc.astype(float) * d.wyd_ahc.astype(float)
    row = {"benefit_units": int(len(d)), "households": int(d.hrn.nunique())}
    for wname, wcol in (("ind", "bugf_2"), ("bu", "bugf_1")):
        w = d[wcol].astype(float).values
        for lab, x in (("bhc", bhc.values), ("ahc", ahc.values)):
            for q, qn in ((.1, "p10"), (.5, "p50")):
                row[f"{lab}_{qn}_{wname}_gbp_year"] = round(52 * wq(x, w, q))
    row["bhc_p10_over_p50_ind"] = round(row["bhc_p10_ind_gbp_year"] / row["bhc_p50_ind_gbp_year"], 3)
    R[str(yr)] = row
    print(yr, row["bhc_p10_ind_gbp_year"], row["bhc_p50_ind_gbp_year"], row["bhc_p10_over_p50_ind"], flush=True)
# comparison with the ONS series already in the paper (nominal)
try:
    inc = pd.read_csv("/w/work/income_series.csv")
    for meas in ("p10_equivalised_household_income", "median_equivalised_household_income"):
        s = inc[inc.measure == meas].set_index("year").nominal_gbp
        for yr in R:
            if int(yr) in s.index:
                R[yr][f"ons_{meas.split('_')[0]}_nominal"] = round(float(s[int(yr)]))
except Exception as e:  # noqa: BLE001
    print("no ONS comparison:", e)
json.dump(R, open("/w/work/hbai_results.json", "w"), indent=1)
print({y: (r["bhc_p10_ind_gbp_year"], r.get("ons_p10_nominal")) for y, r in R.items() if "ons_p10_nominal" in r})
