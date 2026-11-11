"""Build an annual UK domestic gas and electricity unit price series, 1946 to the
latest full year, in pence per kWh (nominal and real).

Reads only files in raw/ and transcriptions/hansard_tables.csv, and writes
historic_energy_prices.csv, historic_energy_prices.xlsx and
build_log.txt next to this script. No number is typed in by hand except the
Hansard tables, which are transcribed in transcriptions/hansard_tables.csv and
checked against the saved page text in raw/ on every run.

Run with:  python -I build_series.py
"""
import csv
import datetime as dt
import io
import math
import os
import re
import sys
import zipfile

import openpyxl
import xlrd
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Font

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
TRANS = os.path.join(HERE, "transcriptions", "hansard_tables.csv")
FIRST_YEAR = 1946
GC_FIRST, GC_LAST = 1958, 1966  # years the Gas Council all-gas revenue index is used (client decision)
MEDIUM_OVERRIDE = {("gas", 1967), ("gas", 1968)}  # left on the fuel and light index, graded medium (client decision)
THERM_KWH = 29.3071
GAP_LIMIT = 10.0  # % difference that must be put to the client before choosing
AUTHOR = "LDS Consulting Limited"

LOG = []


def log(msg=""):
    LOG.append(msg)
    print(msg)


# ---------------------------------------------------------------- readers
def year_of(cell):
    """Year from a cell such as 2024, '2025 p' or '2023r'."""
    if cell is None:
        return None
    m = re.match(r"^\s*((?:19|20)\d\d)\b", str(cell))
    return int(m.group(1)) if m else None


def sheet_rows(path, sheet):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows = [list(r) for r in wb[sheet].iter_rows(values_only=True)]
    wb.close()
    return rows


def find_header(rows, first="Year"):
    for i, r in enumerate(rows):
        if r and isinstance(r[0], str) and r[0].strip() == first:
            return i
    raise ValueError("header row not found")


def col_index(header, startswith):
    for j, h in enumerate(header):
        if isinstance(h, str) and h.strip().startswith(startswith):
            return j
    raise ValueError("column not found: " + startswith)


def desnz_unit_table(fname, sheet):
    """UK, all payment methods ('Overall'): variable unit price (p/kWh) and
    fixed cost (GBP/yr); direct debit unit price for the Ofgem cross-check."""
    rows = sheet_rows(os.path.join(RAW, fname), sheet)
    h = find_header(rows)
    hdr = rows[h]
    cu = col_index(hdr, "Overall: Average variable unit price")
    cf = col_index(hdr, "Overall: Average fixed cost")
    cd = col_index(hdr, "Direct debit: Average variable unit price")
    out = {}
    for r in rows[h + 1:]:
        y = year_of(r[0])
        if y and isinstance(r[1], str) and r[1].strip() == "United Kingdom":
            out[y] = {"unit": float(r[cu]) * 100, "fixed": float(r[cf]),
                      "dd_unit": float(r[cd]) * 100}
    return out


def desnz_bill_table(fname, sheet, colname):
    rows = sheet_rows(os.path.join(RAW, fname), sheet)
    title = str(rows[0][0])
    m = re.search(r"consumption of ([\d,]+)\s*kWh", title)
    kwh = float(m.group(1).replace(",", ""))
    h = find_header(rows)
    c = col_index(rows[h], colname)
    out = {}
    for r in rows[h + 1:]:
        y = year_of(r[0])
        if y and r[c] not in (None, ""):
            out[y] = float(r[c])
    return out, kwh


def ons_annual(fname):
    out, title = {}, ""
    with open(os.path.join(RAW, fname), newline="") as f:
        for r in csv.reader(f):
            if len(r) < 2:
                continue
            if r[0] == "Title":
                title = r[1]
            if re.fullmatch(r"(19|20)\d\d", r[0]) and r[1].strip():
                out[int(r[0])] = float(r[1])
    return out, title


def qep_annual():
    """DESNZ QEP table 2.1.2, CPI current price indices for gas and electricity."""
    rows = sheet_rows(os.path.join(RAW, "table_211_213.xlsx"), "2.1.2")
    h = find_header(rows)
    cg = col_index(rows[h], "Current price indices: Gas")
    ce = col_index(rows[h], "Current price indices: Electricity")
    gas, elec = {}, {}
    for r in rows[h + 1:]:
        y = year_of(r[0])
        if y and r[cg] is not None:
            gas[y], elec[y] = float(r[cg]), float(r[ce])
    return gas, elec


def rpi_fuel_light():
    """ONS ad hoc 1643: RPI fuel and light group, monthly, Jan 1956 to Jan 1987,
    in three base periods (HKBL Jan 1956, HKDA Jan 1962, CBAG Jan 1974). The
    segments are linked at their common month and averaged to calendar years,
    then joined to the ONS annual series CHBG (Jan 1987=100) at Jan 1987."""
    rows = sheet_rows(os.path.join(RAW, "rpifuelandlightindicesandweights.xlsx"),
                      "Fuel and Light (RPI)")
    segs = {}
    for name, (cl, cv) in {"CBAG": (0, 1), "HKDA": (3, 4), "HKBL": (6, 7)}.items():
        assert rows[0][cv] == name, name
        s = {}
        for r in rows[2:]:
            if r[cl] and r[cv] is not None:
                y, mon = str(r[cl]).split()
                s[(int(y), mon)] = float(r[cv])
        segs[name] = s
    k62 = segs["HKBL"][(1962, "Jan")] / segs["HKDA"][(1962, "Jan")]
    monthly = dict(segs["HKBL"])
    for key, v in segs["HKDA"].items():
        monthly.setdefault(key, v * k62)
    k74 = monthly[(1974, "Jan")] / segs["CBAG"][(1974, "Jan")]
    for key, v in segs["CBAG"].items():
        monthly.setdefault(key, v * k74)
    annual = {}
    for y in range(1956, 1987):
        vals = [v for (yy, _), v in monthly.items() if yy == y]
        assert len(vals) == 12, y
        annual[y] = sum(vals) / 12
    jan87 = monthly[(1987, "Jan")]  # = 100 on the CHBG base
    chbg, _ = ons_annual("chbg_mm23.csv")
    for y, v in chbg.items():
        annual[y] = v * jan87 / 100.0
    return annual


def boe_series():
    """Bank of England Millennium dataset, sheet A1: CPI (2015=100) and GDP
    deflator at market prices (2013=100), annual."""
    path = os.path.join(RAW, "a-millennium-of-macroeconomic-data-for-the-uk.xlsx")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["A1. Headline series"]
    head = list(ws.iter_rows(min_row=1, max_row=8, values_only=True))
    ccpi = cgdp = None
    for c in range(len(head[0])):
        labs = [str(r[c]).strip() for r in head if c < len(r) and r[c] is not None]
        if ccpi is None and "Consumer price index" in labs:
            ccpi = c
        if cgdp is None and "GDP deflator at market prices" in labs:
            cgdp = c
    cpi, gdp = {}, {}
    for r in ws.iter_rows(min_row=9, values_only=True):
        y = r[0]
        if isinstance(y, (int, float)) and 1900 <= y <= 2100:
            if isinstance(r[ccpi], (int, float)):
                cpi[int(y)] = float(r[ccpi])
            if isinstance(r[cgdp], (int, float)):
                gdp[int(y)] = float(r[cgdp])
    wb.close()
    log(f"BoE A1: CPI column {ccpi}, GDP deflator column {cgdp}; "
        f"CPI {min(cpi)}-{max(cpi)}, GDP deflator {min(gdp)}-{max(gdp)}")
    return cpi, gdp


def ofgem_cap_unit_rates():
    """Ofgem default tariff cap model v1.24, sheet '1b Historical level tables',
    'Other Payment Method' (direct debit) GB average. Implied unit rate =
    (level at typical consumption - level at nil) / typical kWh, plus 5% VAT.
    Typical consumption is 3,100 kWh (single-rate electricity) and 12,000 kWh
    (gas), as named in the model's calculation sheets."""
    rows = sheet_rows(os.path.join(RAW, "Default_tariff_cap_level_v1.24.xlsx"),
                      "1b Historical level tables")
    kwh = {"electricity": 3100.0, "gas": 12000.0}
    block_lab = {"electricity": "Electricity: Single-Rate", "gas": "Gas"}
    # the first block in the sheet is 'Other Payment Method'
    lab_row = next(i for i, r in enumerate(rows) if r[1] and str(r[1]).startswith("Electricity: Single-Rate"))
    nil_row = next(i for i, r in enumerate(rows) if i > lab_row and r[1] == "Nil consumption")
    typ_row = next(i for i, r in enumerate(rows) if i > nil_row and r[1] == "Typical consumption")

    def total_after(start):
        return next(i for i, r in enumerate(rows) if i > start and r[1] == "Total_GB average")
    nil_tot, typ_tot = total_after(nil_row), total_after(typ_row)
    months = {m: i + 1 for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}
    out = {}
    for fuel in ("electricity", "gas"):
        c0 = next(j for j, v in enumerate(rows[lab_row]) if v and str(v).startswith(block_lab[fuel]))
        monthly = {}
        j = c0 + 1
        while j < len(rows[nil_row]):
            p = rows[nil_row][j]
            if p is None:
                j += 1
                if j < len(rows[nil_row]) and rows[nil_row][j] in (None, "Nil consumption"):
                    break
                continue
            m = re.match(r"(\w{3})\w* (\d{4}) - (\w{3})\w* (\d{4})", str(p))
            if not m:
                break
            rate = (rows[typ_tot][j] - rows[nil_tot][j]) / kwh[fuel] * 100 * 1.05
            y, mo = int(m.group(2)), months[m.group(1)]
            y2, mo2 = int(m.group(4)), months[m.group(3)]
            while (y, mo) <= (y2, mo2):
                monthly[(y, mo)] = rate
                mo += 1
                if mo == 13:
                    y, mo = y + 1, 1
            j += 1
        for y in sorted({k[0] for k in monthly}):
            vals = [monthly[(y, mm)] for mm in range(1, 13) if (y, mm) in monthly]
            if len(vals) == 12:
                out[(fuel, y)] = sum(vals) / 12
    return out


def fact_file_prices(fname, sheet):
    """Housing energy fact file Table 3c: average household fuel prices, p/kWh in
    constant prices (RPI-deflated), implicit = household spending / household
    consumption. Returns {fuel: {year: nominal p/kWh}}, converted back to money
    of the day with the RPI column printed in the same table, plus the base."""
    path = os.path.join(RAW, fname)
    if fname.lower().endswith(".xls"):
        sh = xlrd.open_workbook(path).sheet_by_name(sheet)
        rows = [sh.row_values(i) for i in range(sh.nrows)]
    else:
        rows = sheet_rows(path, sheet)
    h = find_header(rows)
    hdr = rows[h]
    cg, ce = col_index(hdr, "Gas"), col_index(hdr, "Electricity")
    cr = col_index(hdr, "Retail Price Index")
    base = re.search(r"\((\d{4}) = 100", hdr[cr]).group(1)
    out = {"gas": {}, "electricity": {}}
    for r in rows[h + 1:]:
        y = year_of(int(r[0]) if isinstance(r[0], float) else r[0])
        if not y or not isinstance(r[cr], (int, float)):
            continue
        for fuel, c in (("gas", cg), ("electricity", ce)):
            if isinstance(r[c], (int, float)):
                out[fuel][y] = (r[c] * r[cr] / 100.0, r[c])
    return out, base


def hansard_rows():
    with open(TRANS, newline="") as f:
        rows = list(csv.DictReader(f))
    # check every transcribed value against the saved page text
    bad = 0
    for r in rows:
        txt = open(os.path.join(RAW, r["source_id"].lower() + ".txt"), encoding="utf-8").read()
        lines = [ln.strip(" |") for ln in txt.splitlines()]
        per = r["period"].replace("-", "\u2013")
        alts = {r["value"], r["value"].replace(".", "\u2013"), r["value"].replace(".", " "), r["value"] + "d."}
        if r["row_label"] == "(prose)":
            ok = any((r["period"] in ln or per in ln) and (r["value"] + "d") in ln for ln in lines)
        else:
            # '--' in a label stands for the long dash printed in the source
            lab = r["row_label"].replace("--", "\u2014").replace("-", "\u2013")
            ok = any((ln == lab or ln == "1" + lab) and alts & set(lines[i + 1:i + 4])
                     for i, ln in enumerate(lines))
            if lab != per:
                ok = ok and any(per in ln for ln in lines)
        if not ok:
            bad += 1
            log(f"TRANSCRIPTION NOT FOUND IN PAGE TEXT: {r}")
    log(f"Hansard transcriptions: {len(rows)} values, {len(rows) - bad} found in the saved page text")
    if bad:
        sys.exit("transcription check failed")
    return rows


_HZ = []


def hansard_rows_cache():
    if not _HZ:
        _HZ.extend(hansard_rows())
    return _HZ


def calendarise(fy):
    """Financial years (April to March) to calendar years. Calendar year Y is
    0.25 x FY(Y-1/Y) + 0.75 x FY(Y/Y+1) when both exist; otherwise the FY that
    starts in Y stands alone and the year is noted as such."""
    out = {}
    for y in sorted(fy):
        if y - 1 in fy:
            out[y] = (0.25 * fy[y - 1] + 0.75 * fy[y], "calendarised 1/4 FY%d-%02d + 3/4 FY%d-%02d" % (
                y - 1, y % 100, y, (y + 1) % 100))
        else:
            out[y] = (fy[y], "financial year %d-%02d used for calendar %d (previous FY not available)" % (
                y, (y + 1) % 100, y))
    return out


# ---------------------------------------------------------------- build
def main():
    build_time = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)

    # deflators
    boe_cpi, boe_gdp = boe_series()
    d7bt, _ = ons_annual("d7bt_mm23.csv")
    k16 = boe_cpi[2016] / d7bt[2016]
    deflator = {y: v for y, v in boe_cpi.items() if y <= 2016}
    for y, v in d7bt.items():
        if y > 2016:
            deflator[y] = v * k16
    log(f"Deflator: BoE CPI to 2016, ONS D7BT after 2016 (ratio at 2016 = {k16:.6f}); "
        f"BoE 2016 {boe_cpi[2016]:.3f}, D7BT 2016 {d7bt[2016]:.3f}")

    # anchors
    e224 = desnz_unit_table("table_224__1_.xlsx", "2.2.4")
    g234 = desnz_unit_table("table_234__1_.xlsx", "2.3.4")
    last_year = min(max(e224), max(g234), max(d7bt))
    log(f"Latest full year with DESNZ prices and CPI: {last_year}")

    # indices
    dobx, dobx_t = ons_annual("dobx_mm23.csv")
    doby, doby_t = ons_annual("doby_mm23.csv")
    qep_gas, qep_elec = qep_annual()
    rpifl = rpi_fuel_light()
    log(f"Indices: {dobx_t} {min(dobx)}-{max(dobx)}; {doby_t} {min(doby)}-{max(doby)}; "
        f"QEP CPI {min(qep_gas)}-{max(qep_gas)}; RPI fuel and light {min(rpifl)}-{max(rpifl)}")
    et = {1978: 100.0}
    for r in sorted((r for r in hansard_rows_cache() if r["source_id"] == "HANSARD_1989_11_08"),
                    key=lambda r: int(r["period"])):
        y = int(r["period"])
        et[y] = et[y - 1] * (1 + float(r["value"]) / 100)
    log(f"Energy Trends domestic gas price index (from HC Deb 8 Nov 1989 % changes), 1978=100: {min(et)}-{max(et)}")
    gc_fy = {int(r["period"][:4]): float(r["value"]) for r in hansard_rows_cache()
             if r["source_id"] in ("HANSARD_1966_08_01", "HANSARD_1968_07_17")}
    gc = {y: v for y, (v, _) in calendarise(gc_fy).items() if GC_FIRST <= y <= GC_LAST}
    log(f"Gas Council all-gas average revenue index (calendarised): {min(gc)}-{max(gc)}")
    index_chain = {
        "electricity": [("ONS_RPI_ELEC", dobx, "RPI electricity (DOBX)"),
                        ("DESNZ_QEP_212", qep_elec, "QEP CPI electricity"),
                        ("ONS_RPI_FUEL_LIGHT", rpifl, "RPI fuel and light group"),
                        ("BOE_MILLENNIUM", deflator, "all-items CPI")],
        "gas": [("ONS_RPI_GAS", doby, "RPI gas (DOBY)"),
                ("DESNZ_QEP_212", qep_gas, "QEP CPI gas"),
                ("HANSARD_1989_11_08", et, "Energy Trends domestic gas price index"),
                ("HANSARD_1966_08_01+HANSARD_1968_07_17", gc, "Gas Council average revenue on all gas sold"),
                ("ONS_RPI_FUEL_LIGHT", rpifl, "RPI fuel and light group"),
                ("BOE_MILLENNIUM", deflator, "all-items CPI")],
    }

    hz = hansard_rows_cache()

    def hz_series(src, fuel):
        return [r for r in hz if r["source_id"] == src and r["fuel"] == fuel]

    # candidate actual values per fuel, in priority order
    cands = {"electricity": [], "gas": []}  # (priority, year, nominal, measure, source, conf, note)
    # DESNZ from 2010: all-in price = (unit price x typical kWh + fixed cost) / typical kWh, at the
    # current DESNZ typical consumption, which reproduces the published bill / consumption exactly
    bills = {}
    for fuel, fn, unit_t, usid, bsid in (("electricity", "table_221__1_.xlsx", e224, "DESNZ_224", "DESNZ_221"),
                                         ("gas", "table_231__1_.xlsx", g234, "DESNZ_234", "DESNZ_231")):
        sh = "2.2.1" if fuel == "electricity" else "2.3.1"
        now, kwh_now = desnz_bill_table(fn, sh, "Overall: All Tariffs")
        hist, kwh_hist = desnz_bill_table(fn, sh + " (Historic)", "Overall: UK")
        bills[fuel] = (now, kwh_now, hist, kwh_hist, sh)
        for y, v in unit_t.items():
            allin = v["unit"] + v["fixed"] / kwh_now * 100
            how = (f"published bill / {kwh_now:,.0f} kWh (table {sh})" if y in now else
                   f"computed from table {usid[-3]}.{usid[-2]}.{usid[-1]} at {kwh_now:,.0f} kWh, the method DESNZ uses for its "
                   f"2014-2021 bills (table {sh} starts in 2014 on this basis)")
            cands[fuel].append((1, y, allin, "avg_revenue_inc_standing", bsid + "+" + usid, "high",
                                f"All-in price per kWh (standing charge and VAT included): UK, all payment methods, "
                                f"{how}. Unit rate excluding the standing charge is in its own column"))
    for r in hz_series("HANSARD_1978_05_17", "electricity"):
        y = int(r["period"])
        nom = float(r["value"]) * deflator[y] / deflator[1977]
        cands["electricity"].append((2, y, nom, "avg_revenue_inc_standing", "HANSARD_1978_05_17",
                                     "high" if y == 1977 else "medium",
                                     "GB average net selling value (revenue / kWh), published at 1977 money %s; converted to money of the day with the CPI deflator" % r["value"]
                                     if y != 1977 else "GB average net selling value (revenue / kWh); 1977 money equals money of the day"))
    for r in hz_series("HANSARD_1977_07_06", "electricity"):
        y = int(r["period"])
        nom = float(r["value"]) * deflator[y] / deflator[1976]
        cands["electricity"].append((3, y, nom, "avg_revenue_inc_standing", "HANSARD_1977_07_06", "medium",
                                     "GB average net selling value at 1976 money %s; converted with the CPI deflator" % r["value"]))
    fy90 = {int(r["period"][:4]): float(r["value"]) for r in hz_series("HANSARD_1990_02_16", "electricity")}
    for y, (v, how) in calendarise(fy90).items():
        cands["electricity"].append((4, y, v, "avg_revenue_inc_standing", "HANSARD_1990_02_16", "high",
                                     "Electricity Council revenue per kWh sold to domestic customers (England and Wales), money of the day; " + how))
    for r in hz_series("HANSARD_1992_11_09", "electricity"):
        y = int(r["period"])
        nom = float(r["value"]) * boe_gdp[y] / boe_gdp[1991]
        cands["electricity"].append((5, y, nom, "avg_revenue_inc_standing", "HANSARD_1992_11_09",
                                     "high" if y == 1991 else "medium",
                                     "average price per unit incl. standing charges at 1991 prices %s; converted to money of the day with the GDP deflator (the deflator the answer used)" % r["value"]
                                     if y != 1991 else "average price per unit incl. standing charges; 1991 prices equal money of the day"))
    for r in hz_series("HANSARD_1979_02_21", "electricity"):
        y = int(r["period"])
        cands["electricity"].append((6, y, float(r["value"]), "avg_revenue_inc_standing", "HANSARD_1979_02_21", "high",
                                     "GB average net selling value, current prices"))
    fy79 = {int(r["period"][:4]): float(r["value"]) / THERM_KWH for r in hz_series("HANSARD_1979_02_21", "gas")}
    for y, (v, how) in calendarise(fy79).items():
        cands["gas"].append((2, y, v, "avg_revenue_inc_standing", "HANSARD_1979_02_21", "high",
                             "GB average net selling value, pence per therm / 29.3071; " + how))
    # housing energy fact files (implicit household prices, standing charge and VAT included)
    for prio, fname, sheet, sid in ((5.5, "uk_housing_fact_file_2013_tables.xlsx", "3c - Energy prices", "HEFF_2013"),
                                    (7, "great-britains-energy-fact-file-2011.xls", "3c - Energy Prices", "HEFF_2011")):
        ff, ffbase = fact_file_prices(fname, sheet)
        for fuel in ("gas", "electricity"):
            for y, (nom, real) in ff[fuel].items():
                cands[fuel].append((prio, y, nom, "avg_revenue_inc_standing", sid, "high",
                                    "implicit average household price (household spending / household consumption, "
                                    "standing charge and VAT included), published at %s prices %.4f; converted to money "
                                    "of the day with the RPI column printed in the same table" % (ffbase, real)))
    # 1960s domestic average revenue, old pence (d) per therm; 240d = GBP 1, so 2.4d = 1 new penny
    fy6x = {}
    for sid in ("HANSARD_1966_04_26", "HANSARD_1967_01_19"):
        for r in hz_series(sid, "gas"):
            fy6x[int(r["period"][:4])] = (float(r["value"]) / 2.4 / THERM_KWH, sid, r["value"])
    for y, (v, how) in calendarise({k: v[0] for k, v in fy6x.items()}).items():
        sid = fy6x[y][1]
        cands["gas"].append((3, y, v, "avg_revenue_inc_standing", sid, "medium",
                             "domestic average revenue per therm, %sd (old pence) / 2.4 / 29.3071; %s%s" % (
                                 fy6x[y][2], how, "; FY1964-65 from HC Deb 26 Apr 1966" if y == 1965 else "")))

    # choose the highest-priority value per year; record every overlap
    recon = []  # dict rows
    stops = []
    actual = {"electricity": {}, "gas": {}}
    for fuel, lst in cands.items():
        by_year = {}
        for c in lst:
            by_year.setdefault(c[1], []).append(c)
        for y, cs in sorted(by_year.items()):
            if y < FIRST_YEAR or y > last_year:
                continue
            cs.sort(key=lambda c: c[0])
            keep = cs[0]
            actual[fuel][y] = keep
            for other in cs[1:]:
                diff = (other[2] - keep[2]) / keep[2] * 100
                recon.append({"fuel": fuel, "year": y, "check": "source overlap",
                              "kept_source": keep[4], "kept_p_per_kwh": keep[2],
                              "other_source": other[4], "other_p_per_kwh": other[2],
                              "pct_difference": diff, "over_10pct": abs(diff) > GAP_LIMIT,
                              "note": "other minus kept, as % of kept"})
                if abs(diff) > GAP_LIMIT:
                    stops.append(f"{fuel} {y}: {keep[4]} {keep[2]:.4f} vs {other[4]} {other[2]:.4f} p/kWh ({diff:+.1f}%)")

    # index chaining
    def step_ratio(fuel, y0, y1):
        """Index ratio I(y1)/I(y0) for adjacent years using the best index that
        covers both years."""
        for sid, idx, name in index_chain[fuel]:
            if y0 in idx and y1 in idx:
                return idx[y1] / idx[y0], sid, name
        raise KeyError((fuel, y0, y1))

    def chain(fuel, anchor_year, target):
        val, used = actual[fuel][anchor_year][2], []
        step = 1 if target > anchor_year else -1
        y = anchor_year
        while y != target:
            r, sid, name = step_ratio(fuel, y, y + step)
            val *= r
            used.append((sid, name))
            y += step
        return val, used

    final = {"electricity": {}, "gas": {}}
    closures = []  # (fuel, from_year, to_year, chained value) where the measure changes
    for fuel in ("electricity", "gas"):
        anchors = sorted(actual[fuel])
        for y in range(FIRST_YEAR, last_year + 1):
            if y in actual[fuel]:
                p, _, nom, meas, sid, conf, note = actual[fuel][y]
                if fuel == "electricity" and not sid.startswith("DESNZ"):
                    note = "Average revenue per kWh (standing charge blended). " + note
                ut = e224 if fuel == "electricity" else g234
                final[fuel][y] = dict(nominal=nom, value_type="actual", measure=meas, source_id=sid,
                                      confidence=conf, notes=note,
                                      unit_rate=ut[y]["unit"] if sid.startswith("DESNZ") else None)
                continue
            left = max((a for a in anchors if a < y), default=None)
            right = min((a for a in anchors if a > y), default=None)
            if left is None or (right is not None and right - y < y - left):
                a = right
            else:
                a = left
            val, used = chain(fuel, a, y)
            names = []
            for _, n in used:
                if n not in names:
                    names.append(n)
            sids = []
            for s, _ in used:
                if s not in sids:
                    sids.append(s)
            anchor = actual[fuel][a]
            before_first = left is None
            if before_first:
                vtype = "estimate"
                conf = "low"
            else:
                vtype = "index_spliced"
                weak = any(n in ("all-items CPI", "RPI fuel and light group") for n in names)
                conf = "low" if weak else "medium"
                if (fuel, y) in MEDIUM_OVERRIDE:
                    conf = "medium"
            note = (f"chained from the {a} {anchor[4]} value with {', '.join(names)}"
                    f" (nearest actual anchor)")
            if "Gas Council average revenue on all gas sold" in names:
                note += "; caveat: the Gas Council index covers ALL gas sold, not domestic sales only"
            if (fuel, y) in MEDIUM_OVERRIDE:
                note += "; graded medium by client decision although the fuel and light group index is used"
            if "all-items CPI" in names:
                note += "; no fuel-specific index exists for these years, so the all-items CPI was used"
            if before_first:
                note += ("; no domestic average price exists before %d, so this is a back-cast estimate" % a)
            if fuel == "electricity" and anchor[3] == "avg_revenue_inc_standing":
                note = "Average revenue per kWh (standing charge blended), " + note
            final[fuel][y] = dict(nominal=val, value_type=vtype, measure=anchor[3],
                                  source_id=anchor[4] + "+" + "+".join(sids), confidence=conf, notes=note,
                                  unit_rate=None)
        # chain closure across each run of filled years between two anchors
        for a0, a1 in zip(anchors, anchors[1:]):
            if a1 - a0 > 1:
                fwd, used = chain(fuel, a0, a1)
                act = actual[fuel][a1][2]
                diff = (fwd - act) / act * 100
                names = sorted({n for _, n in used})
                if actual[fuel][a0][3] != actual[fuel][a1][3]:
                    closures.append((fuel, a0, a1, fwd))
                for yy in range(a0 + 1, a1):
                    final[fuel][yy]["notes"] += (f"; gap {a0 + 1}-{a1 - 1}: chaining {a0} forward to {a1} "
                                                 f"misses the {a1} actual by {diff:+.1f}%")
                recon.append({"fuel": fuel, "year": a1, "check": "chain closure",
                              "kept_source": actual[fuel][a1][4], "kept_p_per_kwh": act,
                              "other_source": f"{actual[fuel][a0][4]} {a0} chained forward with {', '.join(names)}",
                              "other_p_per_kwh": fwd, "pct_difference": diff, "over_10pct": abs(diff) > GAP_LIMIT,
                              "note": (f"years {a0 + 1}-{a1 - 1} filled from the nearest anchor; "
                                       f"anchor measures: {actual[fuel][a0][3]} -> {actual[fuel][a1][3]}")})

    # town gas flag
    for y, r in final["gas"].items():
        if y < 1972:
            r["notes"] = "Town gas era (sold by the therm; converted from therms only). " + r["notes"]

    # real terms
    base = last_year
    for fuel in final:
        for y, r in final[fuel].items():
            r["real"] = r["nominal"] * deflator[base] / deflator[y]

    # cross-checks and the 2010 measure decision
    for fuel, unit in (("electricity", e224), ("gas", g234)):
        now, kwh_now, hist, kwh_hist, sh = bills[fuel]
        usid = "DESNZ_224" if fuel == "electricity" else "DESNZ_234"
        for y in sorted(unit):
            allin = final[fuel][y]["nominal"]
            d = (unit[y]["unit"] - allin) / allin * 100
            recon.append({"fuel": fuel, "year": y, "check": "measure decision (2010 on)",
                          "kept_source": final[fuel][y]["source_id"] + " all-in", "kept_p_per_kwh": allin,
                          "other_source": usid + " unit rate excluding standing charge (kept as an extra column)",
                          "other_p_per_kwh": unit[y]["unit"], "pct_difference": d, "over_10pct": "n/a (two measures by design)",
                          "note": "client decision: the main series is all-in from 2010 so every year is one measure; "
                                  "this resolves the 2010-2012 DESNZ against fact file overlap, which was a difference of measure"})
            if y in now:
                implied = (now[y] - unit[y]["fixed"]) / kwh_now * 100
                dd = (implied - unit[y]["unit"]) / unit[y]["unit"] * 100
                recon.append({"fuel": fuel, "year": y, "check": "bill / consumption cross-check",
                              "kept_source": usid, "kept_p_per_kwh": unit[y]["unit"],
                              "other_source": f"table {sh}: (bill GBP {now[y]:.2f} - fixed GBP {unit[y]['fixed']:.2f}) / {kwh_now:,.0f} kWh",
                              "other_p_per_kwh": implied, "pct_difference": dd, "over_10pct": abs(dd) > GAP_LIMIT,
                              "note": "cross-check only"})
            elif y in hist:
                ph = hist[y] / kwh_hist * 100
                dd = (ph - allin) / allin * 100
                recon.append({"fuel": fuel, "year": y, "check": "all-in basis 2010-2013",
                              "kept_source": final[fuel][y]["source_id"] + f" at {kwh_now:,.0f} kWh", "kept_p_per_kwh": allin,
                              "other_source": f"table {sh} (Historic): published bill GBP {hist[y]:.2f} / {kwh_hist:,.0f} kWh",
                              "other_p_per_kwh": ph, "pct_difference": dd, "over_10pct": abs(dd) > GAP_LIMIT,
                              "note": "the historic bill uses a higher typical consumption, so the fixed cost is spread "
                                      "thinner; the main series uses one consumption basis for all years from 2010"})
    ofg = ofgem_cap_unit_rates()
    for (fuel, y), rate in sorted(ofg.items()):
        if y < 2019 or y > last_year:
            continue
        unit = e224 if fuel == "electricity" else g234
        if y not in unit:
            continue
        d = unit[y]["dd_unit"]
        diff = (rate - d) / d * 100
        recon.append({"fuel": fuel, "year": y, "check": "Ofgem price cap cross-check",
                      "kept_source": ("DESNZ_224" if fuel == "electricity" else "DESNZ_234") + " direct debit",
                      "kept_p_per_kwh": d, "other_source": "OFGEM_CAP, direct debit, GB average, calendar-year mean incl. 5% VAT",
                      "other_p_per_kwh": rate, "pct_difference": diff, "over_10pct": abs(diff) > GAP_LIMIT,
                      "note": "cross-check only; the cap is a ceiling and excludes the Energy Price Guarantee (Oct 2022 to Jun 2023)"})

    # ------------------------------------------------------------ outputs
    cols = ["year", "fuel", "nominal_p_per_kwh", "real_p_per_kwh", "real_base_year", "value_type",
            "measure", "unit_rate_ex_standing_p_per_kwh", "source_id", "confidence", "notes"]
    data = []
    for fuel in ("electricity", "gas"):
        for y in range(FIRST_YEAR, last_year + 1):
            r = final[fuel][y]
            ur = round(r["unit_rate"], 4) if r["unit_rate"] is not None else None
            data.append([y, fuel, round(r["nominal"], 4), round(r["real"], 4), base, r["value_type"],
                         r["measure"], ur, r["source_id"], r["confidence"], r["notes"]])
    with open(os.path.join(HERE, "historic_energy_prices.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(data)

    sources = read_sources()
    write_xlsx(os.path.join(HERE, "historic_energy_prices.xlsx"), cols, data, sources, recon, base,
               build_time)

    # summary
    log("")
    log(f"{'fuel':12} {'first':>5} {'last':>5} {'actual':>6} {'spliced':>7} {'estimate':>8}  real min (year)    real max (year)")
    for fuel in ("electricity", "gas"):
        rs = [d for d in data if d[1] == fuel]
        n = {k: sum(1 for d in rs if d[5] == k) for k in ("actual", "index_spliced", "estimate")}
        mn = min(rs, key=lambda d: d[3])
        mx = max(rs, key=lambda d: d[3])
        log(f"{fuel:12} {rs[0][0]:>5} {rs[-1][0]:>5} {n['actual']:>6} {n['index_spliced']:>7} {n['estimate']:>8}  "
            f"{mn[3]:7.2f} ({mn[0]})     {mx[3]:7.2f} ({mx[0]})")
    log("")
    log("Reconciliation rows over 10%:")
    for r in recon:
        if r["over_10pct"] is True:
            log(f"  {r['check']}: {r['fuel']} {r['year']}: kept {r['kept_source']} {r['kept_p_per_kwh']:.4f}, "
                f"other {r['other_source']} {r['other_p_per_kwh']:.4f} ({r['pct_difference']:+.1f}%)")
    if stops:
        log("")
        log("STOP: source overlaps over 10% (higher-priority source kept pending a decision):")
        for s in stops:
            log("  " + s)
    with open(os.path.join(HERE, "build_log.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(LOG) + "\n")


def read_sources():
    """Parse the source table in raw/SOURCES.md."""
    out = []
    with open(os.path.join(RAW, "SOURCES.md"), encoding="utf-8") as f:
        for ln in f:
            if ln.startswith("| ") and not ln.startswith("| source_id") and not ln.startswith("| ---"):
                cells = [c.strip() for c in ln.strip().strip("|").split("|")]
                if len(cells) >= 6:
                    out.append(cells[:6])
    return out


# ---------------------------------------------------------------- xlsx
def write_xlsx(path, cols, data, sources, recon, base, build_time):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "data"
    ws.append(cols)
    for d in data:
        ws.append(d)
    for c in ws[1]:
        c.font = Font(bold=True)
    ws.freeze_panes = "A2"
    for col, wdt in zip("ABCDEFGHIJK", (7, 12, 18, 16, 14, 14, 26, 20, 44, 11, 120)):
        ws.column_dimensions[col].width = wdt

    s = wb.create_sheet("sources")
    s.append(["source_id", "title", "URL", "download date", "years covered", "used for"])
    for r in sources:
        s.append(r)
    for c in s[1]:
        c.font = Font(bold=True)
    for col, wdt in zip("ABCDEF", (24, 60, 70, 34, 22, 50)):
        s.column_dimensions[col].width = wdt

    rc = wb.create_sheet("reconciliation")
    rcols = ["fuel", "year", "check", "kept_source", "kept_p_per_kwh", "other_source", "other_p_per_kwh",
             "pct_difference", "over_10pct", "note"]
    rc.append(rcols)
    for r in sorted(recon, key=lambda r: (r["check"], r["fuel"], r["year"])):
        rc.append([r[k] if not isinstance(r[k], float) else round(r[k], 4) for k in rcols])
    for c in rc[1]:
        c.font = Font(bold=True)
    for col, wdt in zip("ABCDEFGHIJ", (12, 7, 30, 30, 15, 70, 15, 14, 11, 80)):
        rc.column_dimensions[col].width = wdt

    ch = wb.create_sheet("chart")
    ch.append(["year", "electricity real p/kWh (%d prices)" % base, "gas real p/kWh (%d prices)" % base])
    years = sorted({d[0] for d in data})
    real = {(d[1], d[0]): d[3] for d in data}
    for y in years:
        ch.append([y, real[("electricity", y)], real[("gas", y)]])
    chart = LineChart()
    chart.title = "UK domestic energy prices, real p/kWh (%d prices), %d to %d" % (base, years[0], years[-1])
    chart.y_axis.title = "pence per kWh (%d prices)" % base
    chart.x_axis.title = "year"
    chart.add_data(Reference(ch, min_col=2, max_col=3, min_row=1, max_row=len(years) + 1), titles_from_data=True)
    chart.set_categories(Reference(ch, min_col=1, min_row=2, max_row=len(years) + 1))
    chart.x_axis.tickLblSkip = 5
    chart.x_axis.delete = False
    chart.y_axis.delete = False
    chart.height, chart.width = 11, 24
    ch.add_chart(chart, "E2")

    for w in wb.worksheets:
        w.sheet_properties.tabColor = None
    buf = io.BytesIO()
    wb.save(buf)
    clean_xlsx(buf.getvalue(), path, build_time)

    # re-open and check
    wb2 = openpyxl.load_workbook(path)
    n = wb2["data"].max_row - 1
    assert n == len(data), (n, len(data))
    log(f"xlsx re-opened: {n} data rows (expected {len(data)}), sheets {wb2.sheetnames}")


def clean_xlsx(blob, path, build_time):
    """Rewrite document properties and give every zip entry the build time."""
    stamp = build_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:creator>{AUTHOR}</dc:creator><cp:lastModifiedBy>{AUTHOR}</cp:lastModifiedBy>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{stamp}</dcterms:created>'
            f'<dcterms:modified xsi:type="dcterms:W3CDTF">{stamp}</dcterms:modified>'
            '</cp:coreProperties>')
    app = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
           'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
           '<Application>Microsoft Excel</Application><DocSecurity>0</DocSecurity>'
           '<ScaleCrop>false</ScaleCrop><Company>' + AUTHOR + '</Company>'
           '<LinksUpToDate>false</LinksUpToDate><SharedDoc>false</SharedDoc>'
           '<HyperlinksChanged>false</HyperlinksChanged><AppVersion>16.0300</AppVersion></Properties>')
    local = build_time.astimezone()
    date_time = (local.year, local.month, local.day, local.hour, local.minute, local.second)
    src = zipfile.ZipFile(io.BytesIO(blob))
    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            if info.filename == "docProps/custom.xml":
                continue
            data = src.read(info.filename)
            if info.filename == "docProps/core.xml":
                data = core.encode("utf-8")
            elif info.filename == "docProps/app.xml":
                data = app.encode("utf-8")
            elif info.filename == "[Content_Types].xml":
                data = re.sub(rb'<Override[^>]*PartName="/docProps/custom.xml"[^>]*/>', b"", data)
            elif info.filename == "_rels/.rels":
                data = re.sub(rb'<Relationship[^>]*Target="/?docProps/custom.xml"[^>]*/>', b"", data)
            zi = zipfile.ZipInfo(info.filename, date_time=date_time)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o600 << 16
            dst.writestr(zi, data)
    os.replace(tmp, path)


if __name__ == "__main__":
    main()
