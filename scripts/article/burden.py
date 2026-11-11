#!/usr/bin/env python3
"""Heating energy burden: each winter's heating bill at THAT winter's real prices, as a share of household income.

    .venv/bin/python scripts/article/burden.py [--src data/model/v3f]

Bill: the model's "hist" tariff (gb_v3_final.sh): flat electricity and gas unit rates plus the gas standing charge
for the heating year, 2025 money (data/model/gb/hist_prices.json). It covers space heating and hot water only; the
electricity standing charge and all non-heating electricity are left out because they are common to every
controller. So this is a HEATING burden, not the official whole-home fuel-poverty measure (LIHC/LILEE, or
Boardman's 10% of income on all energy), and the article reports it as such.

Income (data/historic_energy_prices/income/income_series.csv), real 2025 money on the SAME CPI deflator as the prices,
so the ratio is the same in nominal terms:
  gdhi_per_household                    1946-2025, ONS CRXS per head x household size (low confidence before 1961)
  median_equivalised_household_income   1977-2025, ONS HDII
  p10_equivalised_household_income      1977-2025, ONS HDII (the poorest tenth)
A heating year (Nov Y - Oct Y+1) takes the mean of calendar years Y and Y+1, as the prices do; 2025-26 uses 2025.
National bill = mean over towns of each town's mean (or median) bill, each town weighted by its share of its region's
domestic gas meters (as analysis.py).
Writes docs/article/results/burden.csv and merges BURDEN_* numbers into results/numbers_results.json (run after
analysis.py, which rewrites that file).
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / (sys.argv[sys.argv.index("--src") + 1] if "--src" in sys.argv else "data/model/v3f")
GB = ROOT / "data" / "model" / "gb"
OUT = ROOT / "docs" / "article" / "results"
INC = ROOT / "data" / "historic_energy_prices" / "income" / "income_series.csv"
CTRL = ["gas", "hp", "biv0", "biv2", "biv5", "ccop"]
MEASURES = {"gdhi_hh": "gdhi_per_household", "median_eq": "median_equivalised_household_income",
            "p10_eq": "p10_equivalised_household_income"}


def town_weights():
    G = json.load(open(GB / "towns.json"))
    W = json.load(open(GB / "region_weights.json"))["homes"]
    reg = {t[0]: t[3] for t in G["towns"]}
    per = {}
    for r in reg.values():
        per[r] = per.get(r, 0) + 1
    return {t: W[r] / per[r] for t, r in reg.items()}


def income():
    inc = {}
    for r in csv.DictReader(open(INC)):
        inc.setdefault(r["measure"], {})[int(r["year"])] = (float(r["real_gbp_2025"]), r["confidence"])
    return inc


def heating_year_income(series, y):
    a, b = series.get(y), series.get(y + 1)
    if a and b:
        return (a[0] + b[0]) / 2, min(a[1], b[1], key=["low", "medium", "high"].index)
    return a if a else (None, None)


def main():
    tw = town_weights()
    inc = income()
    prices = json.load(open(GB / "hist_prices.json"))["years"]
    rows = []
    for d in sorted(SRC.glob("*/stock_summary.csv"), key=lambda p: int(p.parent.name)):
        y = int(d.parent.name)
        hist = [r for r in csv.DictReader(open(d)) if r["tariff"] == "hist"]
        if not hist:
            continue
        wsum = sum(tw[r["town"]] for r in hist)
        nat = lambda col: sum(float(r[col]) * tw[r["town"]] for r in hist) / wsum          # noqa: E731
        row = {"year": y, "heating_year": f"{y}–{(y + 1) % 100:02d}", "elec_unit_p": prices[str(y)]["elec_unit_p"],
               "gas_unit_p": prices[str(y)]["gas_unit_p"], "gas_sc_p_day": prices[str(y)]["gas_sc_p_day"],
               "hybrid_beats_hp_pct": round(nat("hybrid_beats_hp_pct"), 1), "hp_beats_gas_pct": round(nat("hp_beats_gas_pct"), 1)}
        for c in CTRL:
            row[f"{c}_gbp_mean"] = round(nat(f"{c}_gbp_year_mean"), 1)
            row[f"{c}_gbp_median"] = round(nat(f"{c}_gbp_year_median"), 1)
        for k, m in MEASURES.items():
            v, conf = heating_year_income(inc.get(m, {}), y)
            row[f"income_{k}"] = round(v, 0) if v else ""
            row[f"income_{k}_confidence"] = conf or ""
            for c in CTRL:
                row[f"burden_{k}_{c}_pct"] = round(100 * row[f"{c}_gbp_median"] / v, 2) if v else ""
        rows.append(row)
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "burden.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} heating years -> results/burden.csv")

    # headline numbers for the prose
    N = {}
    by = {r["year"]: r for r in rows}
    p10 = [r for r in rows if r["burden_p10_eq_gas_pct"] != ""]
    for c in ("gas", "hp", "ccop"):
        worst = max(p10, key=lambda r: r[f"burden_p10_eq_{c}_pct"])
        N[f"BURDEN_P10_{c.upper()}_MAX_PCT"] = f"{worst[f'burden_p10_eq_{c}_pct']:.1f}"
        N[f"BURDEN_P10_{c.upper()}_MAX_YEAR"] = worst["heating_year"]
        N[f"BURDEN_P10_{c.upper()}_MIN_PCT"] = f"{min(r[f'burden_p10_eq_{c}_pct'] for r in p10):.1f}"
        for y in (1962, 1977, 2010, 2022, 2025):
            if y in by and by[y][f"burden_p10_eq_{c}_pct"] != "":
                N[f"BURDEN_P10_{c.upper()}_{y}_PCT"] = f"{by[y][f'burden_p10_eq_{c}_pct']:.1f}"
        since77 = [r for r in p10 if r["year"] >= 1977]  # the ONS-measured years, for the worst winter within living memory
        worst77 = max(since77, key=lambda r: r[f"burden_p10_eq_{c}_pct"])
        N[f"BURDEN_P10_{c.upper()}_MAX77_PCT"] = f"{worst77[f'burden_p10_eq_{c}_pct']:.1f}"
        N[f"BURDEN_P10_{c.upper()}_MAX77_YEAR"] = worst77["heating_year"]
    N["BURDEN_P10_FIRST_YEAR"] = min(p10, key=lambda r: r["year"])["heating_year"]
    for y in (1962, 2025):
        if y in by:
            N[f"BURDEN_GDHI_GAS_{y}_PCT"] = f"{by[y]['burden_gdhi_hh_gas_pct']:.1f}"
    # the hybrid as insurance for the poorest tenth: in how many winters is C-COP the lowest burden of the three?
    N["BURDEN_P10_CCOP_LOWEST_YEARS"] = str(sum(r["ccop_gbp_median"] <= min(r["gas_gbp_median"], r["hp_gbp_median"]) for r in p10))
    N["BURDEN_P10_YEARS"] = str(len(p10))
    last = max(p10, key=lambda r: r["year"])           # review 4: state the income point and the bill basis
    N["BURDEN_P10_INCOME_2025"] = f"£{last['income_p10_eq']:,.0f}"
    N["BURDEN_GAS_MEDIAN_2025"] = f"{last['gas_gbp_median']:,.0f}"
    p = OUT / "numbers_results.json"
    R = json.load(open(p)) if p.exists() else {}
    R = {k: v for k, v in R.items() if not k.startswith("BURDEN_")}
    R.update(N)
    json.dump(R, open(p, "w"), indent=1, ensure_ascii=False)
    for k, v in N.items():
        print(f"  {k:32} {v}")


if __name__ == "__main__":
    main()
