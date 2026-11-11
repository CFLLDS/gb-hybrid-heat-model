#!/usr/bin/env python3
"""Extend the poorest-tenth and median income series back from 1977 to 1961 with the IFS Households Below Average Income
microdata (UKDS SN 3300, Family Expenditure Survey 1961-1993, safeguarded; only the aggregates in
docs/article/results/ukds/hbai.json leave the Spark: scripts/spark/ukds/hbai_p10.py).

HBAI gives weekly disposable household income, equivalised on the McClements scale (childless couple = 1), at January
prices of each year, individual-weighted; the ONS HDII series the paper uses (income_series.csv) is equivalised on the
modified OECD scale and runs from 1977. Over the 17 overlapping years the two agree to within a few per cent, so the
HBAI years 1961-1976 are spliced on with the mean ONS/HBAI ratio of 1977-1993 and deflated to 2025 money with the same
CPI deflator as the rest of the file (taken from the gdhi_per_head rows, which carry both nominal and real values).
Rows are written with source_id IFS_HBAI_SN3300, value_type index_spliced and confidence medium; existing rows are kept.
    .venv/bin/python scripts/article/hbai_income.py
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INC = ROOT / "data" / "historic_energy_prices" / "income" / "income_series.csv"
HB = ROOT / "docs" / "article" / "results" / "ukds" / "hbai.json"
MEAS = {"p10_equivalised_household_income": "bhc_p10_ind_gbp_year", "median_equivalised_household_income": "bhc_p50_ind_gbp_year"}


def main():
    rows = list(csv.DictReader(open(INC)))
    hb = json.load(open(HB))
    defl = {int(r["year"]): float(r["real_gbp_2025"]) / float(r["nominal_gbp"]) for r in rows if r["measure"] == "gdhi_per_head"}
    out = [r for r in rows if r["source_id"] != "IFS_HBAI_SN3300"]
    report = {}
    for meas, key in MEAS.items():
        ons = {int(r["year"]): float(r["nominal_gbp"]) for r in out if r["measure"] == meas}
        overlap = [y for y in range(1977, 1994) if y in ons and str(y) in hb]
        ratio = sum(ons[y] / hb[str(y)][key] for y in overlap) / len(overlap)
        spread = max(abs(ons[y] / hb[str(y)][key] - 1) for y in overlap)
        report[meas] = {"overlap_years": len(overlap), "ons_over_hbai_mean": round(ratio, 4), "max_abs_diff_pct": round(100 * spread, 1)}
        for y in range(1961, 1977):
            if str(y) not in hb:
                continue
            nominal = hb[str(y)][key] * ratio
            out.append({"year": str(y), "measure": meas, "nominal_gbp": f"{nominal:.2f}", "real_gbp_2025": f"{nominal * defl[y]:.2f}",
                        "source_id": "IFS_HBAI_SN3300", "value_type": "index_spliced", "confidence": "medium",
                        "notes": f"Per household, equivalised (McClements, childless couple = 1), UK, individual-weighted, from FES microdata "
                                 f"(IFS HBAI 1961-1993, UKDS SN 3300), annualised x52 at January prices, scaled by {ratio:.4f} (the mean "
                                 f"ONS HDII / HBAI ratio over 1977-1993, max difference {100 * spread:.1f}%)"})
    out.sort(key=lambda r: (int(r["year"]), r["measure"]))
    with open(INC, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(out)
    print(json.dumps(report, indent=1))
    print("rows", len(out), "added", len(out) - len(rows) + sum(1 for r in rows if r["source_id"] == "IFS_HBAI_SN3300"))


if __name__ == "__main__":
    main()
