"""Build annual UK household income series, 1946 to the latest year, for
setting domestic energy costs against income.

Reads only files in income/raw/ and ../raw/ (Bank of England Millennium
dataset, ONS CPI and the 2013 housing energy fact file), and writes
income_series.csv, household_size.csv, income_series.xlsx and
build_log.txt next to this script. Real values use the same CPI deflator as
../build_series.py, rebased to the latest full year.

Run with:  python -I build_income.py
"""
import csv
import datetime as dt
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
sys.path.insert(0, PARENT)
import build_series as bs  # noqa: E402  (shared readers, deflator inputs and xlsx cleaning)

import openpyxl  # noqa: E402
from openpyxl.styles import Font  # noqa: E402

RAW = os.path.join(HERE, "raw")
FIRST_YEAR = 1946
LOG = []


def log(msg=""):
    LOG.append(msg)
    print(msg)


def ons_csv(fname):
    out, title = {}, ""
    with open(os.path.join(RAW, fname), newline="") as f:
        for r in csv.reader(f):
            if len(r) >= 2 and r[0] == "Title":
                title = r[1]
            if len(r) >= 2 and re.fullmatch(r"(19|20)\d\d", r[0]) and r[1].strip():
                out[int(r[0])] = float(r[1])
    return out, title


def boe_household_gdi_per_head():
    """BoE Millennium A57 'Spliced gross disposable income' (GBP mn; Sefton and
    Weale before 1948, ONS RPHQ from 1948) divided by A1 population (GB+NI, 000s)."""
    path = os.path.join(bs.RAW, "a-millennium-of-macroeconomic-data-for-the-uk.xlsx")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)

    def column(sheet, label):
        ws = wb[sheet]
        head = list(ws.iter_rows(min_row=1, max_row=8, values_only=True))
        c = next(c for c in range(len(head[0]))
                 if any(str(r[c]).strip() == label for r in head if c < len(r) and r[c] is not None))
        out = {}
        for r in ws.iter_rows(min_row=9, values_only=True):
            if isinstance(r[0], (int, float)) and 1900 <= r[0] <= 2100 and isinstance(r[c], (int, float)):
                out[int(r[0])] = float(r[c])
        return out, c
    gdi, cg = column("A57. Household saving", "Spliced gross disposable income")
    pop, cp = column("A1. Headline series", "Population (GB+NI)")
    wb.close()
    log(f"BoE: A57 column {cg} spliced GDI {min(gdi)}-{max(gdi)}; A1 column {cp} population {min(pop)}-{max(pop)}")
    return {y: gdi[y] * 1e6 / (pop[y] * 1e3) for y in gdi if y in pop}


def hdii_series():
    """ONS Effects of taxes and benefits (HDII) FYE2025: Table 1 median and
    Table 3 decile points of equivalised household disposable income, in
    2024/25 prices (CPIH); Table 31 CPIH deflator to undo the deflation."""
    path = os.path.join(RAW, "hdiifye2025.xlsx")

    def table(name):
        return bs.sheet_rows(path, name)
    t1, t3, t31 = table("Table 1"), table("Table 3"), table("Table 31")
    h1 = next(i for i, r in enumerate(t1) if r[0] == "Year")
    assert t1[h1 - 1][1] == "All people" and t1[h1][2] == "Median", t1[h1]
    h3 = next(i for i, r in enumerate(t3) if r[0] == "Year")
    assert t3[h3][1] == "2nd" and t3[h3][5] == "6th", t3[h3]
    h31 = next(i for i, r in enumerate(t31) if r[0] == "Year")
    defl = {str(r[0]): float(r[1]) for r in t31[h31 + 1:] if r[0] is not None and isinstance(r[1], (int, float))}
    med, p10 = {}, {}
    for r in t1[h1 + 1:]:
        if r[0] is not None and isinstance(r[2], (int, float)):
            med[str(r[0])] = float(r[2])
    for r in t3[h3 + 1:]:
        if r[0] is not None and isinstance(r[1], (int, float)):
            p10[str(r[0])] = float(r[1])
            # the 6th decile point is the median: confirms column '2nd' is the 10th percentile
            assert abs(float(r[5]) - med[str(r[0])]) < 1, r
    return med, p10, defl


def to_calendar(series, defl):
    """Year labels are calendar years to 1993 and financial years ('1994/95')
    after. Returns {calendar year: (nominal GBP, note)}; nominal = 2024/25
    prices / CPIH deflator. Calendar Y = 1/4 FY(Y-1/Y) + 3/4 FY(Y/Y+1) where
    both exist; otherwise the FY starting in Y is used alone."""
    cal, fy = {}, {}
    for lab, v in series.items():
        nom = v / defl[lab]
        if "/" in lab:
            fy[int(lab[:4])] = (nom, lab)
        else:
            cal[int(lab)] = (nom, f"calendar year {lab}")
    out = dict(cal)
    for y in sorted(fy):
        if y in out:
            continue
        if y - 1 in fy:
            out[y] = (0.25 * fy[y - 1][0] + 0.75 * fy[y][0], f"calendarised 1/4 {fy[y - 1][1]} + 3/4 {fy[y][1]}")
        else:
            out[y] = (fy[y][0], f"financial year {fy[y][1]} used for calendar {y}")
    return out


def household_size():
    """Average household size (persons): ONS 2011 Census bulletin text for 1961
    (UK, 3.0), DECC housing energy fact file 2013 Table 4a population /
    households for 1970-1995, ONS Families and households (LFS) Table 5 from
    1996."""
    out = {}
    txt = open(os.path.join(RAW, "ons_census2011_uk_households_bulletin.html"), encoding="utf-8").read()
    m = re.search(r"In 1961 the average household size for the UK was (\d\.\d) people per household", txt)
    out[1961] = (float(m.group(1)), "ONS_CENSUS2011_BULLETIN", "actual", "medium",
                 "UK census 1961, stated to one decimal place in the ONS 2011 Census bulletin")
    rows = bs.sheet_rows(os.path.join(bs.RAW, "uk_housing_fact_file_2013_tables.xlsx"), "4a - Housing stock- population")
    h = bs.find_header(rows)
    cp, ch = bs.col_index(rows[h], "Population"), bs.col_index(rows[h], "Households")
    for r in rows[h + 1:]:
        y = bs.year_of(r[0])
        if y and 1970 <= y <= 1995 and isinstance(r[cp], (int, float)) and isinstance(r[ch], (int, float)):
            out[y] = (r[cp] / r[ch], "HEFF_2013", "actual", "medium",
                      "fact file Table 4a: population / households (millions); the table notes 1972-1980 households are interpolated")
    rows = bs.sheet_rows(os.path.join(RAW, "familiesandhouseholdsuk2025.xlsx"), "5")
    hi = next(i for i, r in enumerate(rows) if r[0] and str(r[0]).startswith("Number of households"))
    ai = next(i for i, r in enumerate(rows) if r[0] and str(r[0]).startswith("Average household size"))
    for j, lab in enumerate(rows[hi]):
        m = re.match(r"(\d{4}) Estimate", str(lab or ""))
        if m:
            out[int(m.group(1))] = (float(rows[ai][j]), "ONS_FAMILIES_HOUSEHOLDS", "actual", "high",
                                    "ONS Families and households, Table 5 (Labour Force Survey)")
    # fill 1946-1960 (held at 1961) and 1962-1969 (log-linear between 1961 and 1970)
    for y in range(FIRST_YEAR, 1961):
        out[y] = (out[1961][0], "ONS_CENSUS2011_BULLETIN", "estimate", "low",
                  "held at the 1961 census value; no fetched source gives earlier UK household size")
    a, b = out[1961][0], out[1970][0]
    for y in range(1962, 1970):
        v = a * (b / a) ** ((y - 1961) / 9)
        out[y] = (v, "ONS_CENSUS2011_BULLETIN+HEFF_2013", "estimate", "low",
                  "interpolated (constant growth rate) between 1961 and 1970")
    return out


def main():
    build_time = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    bs.LOG.clear()
    boe_cpi, _ = bs.boe_series()
    d7bt, _ = bs.ons_annual("d7bt_mm23.csv")
    k16 = boe_cpi[2016] / d7bt[2016]
    defl = {y: v for y, v in boe_cpi.items() if y <= 2016}
    defl.update({y: v * k16 for y, v in d7bt.items() if y > 2016})
    crxs, crxs_t = ons_csv("crxs_ukea.csv")
    crxx, crxx_t = ons_csv("crxx_ukea.csv")
    last = min(max(crxs), max(defl))
    base = last
    log(f"ONS CRXS '{crxs_t}' {min(crxs)}-{max(crxs)}; CRXX '{crxx_t}' {min(crxx)}-{max(crxx)}; base year {base}")

    def real(y, nom):
        return nom * defl[base] / defl[y]

    rows, recon = [], []

    # ---- measure 1: gross disposable income per head (households)
    boe = boe_household_gdi_per_head()
    s0 = min(crxs)
    k = crxs[s0] / boe[s0]
    log(f"Splice at {s0}: CRXS {crxs[s0]:.1f} / BoE {boe[s0]:.1f} = {k:.4f} ({(1 / k - 1) * 100:+.1f}% BoE vs ONS)")
    for y in sorted(boe):
        if y in crxs:
            diff = (boe[y] * k - crxs[y]) / crxs[y] * 100
            recon.append(["gdhi_per_head", y, "splice overlap", "ONS_CRXS", round(crxs[y], 2),
                          f"BOE_MILLENNIUM x {k:.4f}", round(boe[y] * k, 2), round(diff, 2),
                          abs(diff) > 10, "BoE households+NPISH GDI / population, scaled at the splice year"])
    recon.insert(0, ["gdhi_per_head", s0, "splice ratio", "ONS_CRXS", round(crxs[s0], 2), "BOE_MILLENNIUM (unscaled)",
                     round(boe[s0], 2), round((boe[s0] - crxs[s0]) / crxs[s0] * 100, 2),
                     abs((boe[s0] - crxs[s0]) / crxs[s0] * 100) > 10,
                     "raw gap at the splice year: BoE series is households+NPISH (old RPHQ basis), ONS CRXS is households only"])
    gdhi = {}
    for y in range(FIRST_YEAR, last + 1):
        if y in crxs:
            gdhi[y] = (crxs[y], "ONS_CRXS", "actual", "high",
                       "ONS CRXS, households (S.14) gross disposable income per head, current prices, seasonally adjusted")
        else:
            conf = "low" if y < 1948 else "medium"
            gdhi[y] = (boe[y] * k, "BOE_MILLENNIUM+ONS_CRXS", "index_spliced", conf,
                       f"BoE Millennium A57 spliced gross disposable income / A1 population, scaled by {k:.4f} to ONS CRXS at {s0}"
                       + ("; before 1948 the BoE series is Sefton and Weale (1995) on a pre-ESA95 basis" if y < 1948 else
                          "; 1948 on the BoE series is ONS RPHQ (households and NPISH)"))
    for y, (nom, sid, vt, conf, note) in gdhi.items():
        rows.append([y, "gdhi_per_head", round(nom, 2), round(real(y, nom), 2), sid, vt, conf,
                     "Per head. " + note])
    # cross-check: real growth with our CPI against ONS CVM (household consumption deflator)
    for y in (1955, 1975, 1995, 2015):
        ours = real(last, crxs[last]) / real(y, crxs[y])
        onsg = crxx[last] / crxx[y]
        d = (ours - onsg) / onsg * 100
        recon.append(["gdhi_per_head", y, f"real growth {y}-{last}", "ONS_CRXX (CVM)", round(onsg, 4),
                      "CRXS deflated with this project's CPI", round(ours, 4), round(d, 2), "n/a",
                      "growth factor, not GBP: ONS deflates with the household consumption deflator, this series with CPI"])

    # ---- household size and per household
    hs = household_size()
    with open(os.path.join(HERE, "household_size.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["year", "persons_per_household", "source_id", "value_type", "confidence", "notes"])
        for y in range(FIRST_YEAR, last + 1):
            v, sid, vt, conf, note = hs[y]
            w.writerow([y, round(v, 3), sid, vt, conf, note])
    for y, (nom, sid, vt, conf, note) in gdhi.items():
        size = hs[y]
        c = {"high": 2, "medium": 1, "low": 0}
        conf2 = min(conf, size[3], key=lambda x: c[x])
        vt2 = "actual" if vt == "actual" and size[2] == "actual" else ("estimate" if "estimate" in (vt, size[2]) else "index_spliced")
        rows.append([y, "gdhi_per_household", round(nom * size[0], 2), round(real(y, nom * size[0]), 2),
                     sid + "+household_size:" + size[1], vt2, conf2,
                     f"Per household: gdhi_per_head x average household size {size[0]:.3f} ({size[2]})"])

    # ---- measures 2 and 3: median and 10th percentile, equivalised household disposable income
    med, p10, cpih = hdii_series()
    for name, ser, lab in (("median_equivalised_household_income", med, "median"),
                           ("p10_equivalised_household_income", p10, "10th percentile (lowest decile point)")):
        cal = to_calendar(ser, cpih)
        for y in range(min(cal), last + 1):
            if y in cal:
                nom, how = cal[y]
                rows.append([y, name, round(nom, 2), round(real(y, nom), 2), "ONS_HDII_FYE2025", "actual", "high",
                             f"Per household, equivalised to a two-adult household without children (modified OECD scale); "
                             f"UK {lab} across individuals; published in 2024/25 prices (CPIH), converted to money of the day "
                             f"with the CPIH deflator in Table 31; {how}"])
            else:
                prev = max(a for a in cal if a < y)
                nom = cal[prev][0] * crxs[y] / crxs[prev]
                rows.append([y, name, round(nom, 2), round(real(y, nom), 2), "ONS_HDII_FYE2025+ONS_CRXS", "index_spliced",
                             "medium", f"Per household, equivalised as above; carried forward from {prev} with the "
                             f"growth in ONS CRXS gross disposable income per head (no {y}/{(y + 1) % 100:02d} survey yet)"])

    rows.sort(key=lambda r: (r[1], r[0]))
    cols = ["year", "measure", "nominal_gbp", "real_gbp_%d" % base, "source_id", "value_type", "confidence", "notes"]
    with open(os.path.join(HERE, "income_series.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)

    # ---- xlsx
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "income"
    ws.append(cols)
    for r in rows:
        ws.append(r)
    hsw = wb.create_sheet("household_size")
    hsw.append(["year", "persons_per_household", "source_id", "value_type", "confidence", "notes"])
    for y in range(FIRST_YEAR, last + 1):
        v, sid, vt, conf, note = hs[y]
        hsw.append([y, round(v, 3), sid, vt, conf, note])
    rc = wb.create_sheet("reconciliation")
    rc.append(["measure", "year", "check", "kept_source", "kept_value", "other_source", "other_value",
               "pct_difference", "over_10pct", "note"])
    for r in recon:
        rc.append(r)
    sw = wb.create_sheet("sources")
    sw.append(["source_id", "title", "URL", "download date", "years covered", "used for"])
    with open(os.path.join(RAW, "SOURCES.md"), encoding="utf-8") as f:
        for ln in f:
            if ln.startswith("| ") and not ln.startswith("| source_id") and not ln.startswith("| ---"):
                cells = [c.strip() for c in ln.strip().strip("|").split("|")]
                if len(cells) >= 6:
                    sw.append(cells[:6])
    for w_ in wb.worksheets:
        for c in w_[1]:
            c.font = Font(bold=True)
        w_.freeze_panes = "A2"
    buf = io.BytesIO()
    wb.save(buf)
    out = os.path.join(HERE, "income_series.xlsx")
    bs.clean_xlsx(buf.getvalue(), out, build_time)
    wb2 = openpyxl.load_workbook(out)
    n = wb2["income"].max_row - 1
    assert n == len(rows), (n, len(rows))
    log(f"xlsx re-opened: {n} income rows (expected {len(rows)}), sheets {wb2.sheetnames}")

    # ---- summary
    log("")
    log(f"{'measure':38} {'first':>5} {'last':>5} {'actual':>6} {'spliced':>7} {'estimate':>8}")
    for m in sorted({r[1] for r in rows}):
        rs = [r for r in rows if r[1] == m]
        n = {t: sum(1 for r in rs if r[5] == t) for t in ("actual", "index_spliced", "estimate")}
        log(f"{m:38} {rs[0][0]:>5} {rs[-1][0]:>5} {n['actual']:>6} {n['index_spliced']:>7} {n['estimate']:>8}")
    with open(os.path.join(HERE, "build_log.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
