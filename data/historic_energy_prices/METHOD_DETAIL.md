# UK domestic gas and electricity prices, 1946 to 2025: method detail

This file holds every detail and judgement call. `METHOD.md` is the one-page
summary.

LDS Consulting Limited. Built by `build_series.py` from the unedited files in
`raw/` (listed with URLs and download dates in `raw/SOURCES.md`) and the hand
transcription of ten Hansard written answers in
`transcriptions/hansard_tables.csv`. Every transcribed value is checked
against the saved page text on each run. Nothing in the outputs is typed in by
hand.

**What each value is.** Annual pence per kWh, money of the day (nominal) and
2025 prices (real), for each fuel and year, with the source, whether it is an
actual price, an index-spliced value or an estimate, and a confidence grade.

**One measure throughout (client decision).** Every value in the main series
is an all-in price per kWh with the standing charge and VAT included
(`avg_revenue_inc_standing`). Before 2010 the actual values are average revenue
per kWh: domestic spending, or revenue, divided by kWh bought. From 2010 they
are DESNZ typical bill divided by typical consumption: (UK average variable
unit price x typical kWh + average fixed cost) / typical kWh, from Tables
2.2.4 and 2.3.4, at the current DESNZ typical consumption (3,400 kWh
electricity, 11,200 kWh gas). For 2014 to 2025 this equals the published bill
in Tables 2.2.1 and 2.3.1 divided by that consumption, exactly. For 2010 to
2013, where DESNZ publishes bills only at the older 3,600 kWh and 13,600 kWh,
the same formula is applied at 3,400 and 11,200 kWh so that the consumption
basis does not change inside the series; the published historic bills give
values 0.6% to 0.7% (electricity) and 3.0% to 3.9% (gas) lower, recorded in the
reconciliation sheet. The DESNZ unit rate excluding the standing charge is
kept in its own column, `unit_rate_ex_standing_p_per_kwh`, for 2010 on only;
it is 10% to 19% (electricity) and 10% to 22% (gas) below the all-in price.
Older electricity values are labelled "average revenue per kWh (standing charge
blended)" in the notes, not "unit rate". With one measure there is no false
step at 2010 (real electricity 2009 to 2010 -5.0%, gas -3.2%), and the 2010 to
2012 overlap between DESNZ and the fact file, which was over 10% when DESNZ
unit rates were used, is shown to be a difference of measure: on the same
all-in basis the two agree within 3.4% (within 5.2% against the published
historic bills).

**Electricity actual years.** 1948 to 1977: HC Deb 17 May 1978, GB average net
selling value at 1977 money. 1978 to 1988: HC Deb 16 Feb 1990, Electricity
Council revenue per kWh, money of the day (England and Wales, financial years).
1989 to 1991: HC Deb 9 Nov 1992, average price including standing charges at
1991 prices. 1992 to 2009: housing energy fact file 2013 (below). 2010 to
2025: DESNZ 2.2.1 and 2.2.4 (all-in).

**Gas actual years.** 1950, 1959, 1960 and 1969 to 1977: HC Deb 21 Feb 1979,
GB average net selling value in pence per therm (financial years). 1964 and
1965: HC Deb 26 Apr 1966 (national average revenue per therm from domestic
sales, 1964-65, 26.36d) and HC Deb 19 Jan 1967 (average income from domestic
sales, 1965-66, 25.56d), converted from old pence at 2.4d to the new penny and
graded medium (the 1967 "average" may be an unweighted mean of the boards).
1978 to 2009: housing energy fact file 2013. 2010 to 2025: DESNZ 2.3.1 and
2.3.4 (all-in).

**Housing energy fact file.** The DECC United Kingdom housing energy fact file
2013 (BRE), Table 3c, gives average household gas and electricity prices for
1970 to 2012 in 2011 prices. They are implicit prices: household spending
divided by household consumption (DUKES), so they include the standing charge
and VAT. They were converted back to money of the day with the RPI column
printed in the same table, which exactly undoes the published deflation. They
agree with the Hansard values within 8.2% wherever both exist (gas 1970 to
1977, electricity 1970 to 1991). The 2011 edition (GB, 2009 prices) is kept for
reconciliation only; it differs from the 2013 edition by up to 4.8%.

**Converting real-terms tables back to money of the day.** The 1977 and 1978
answers are in constant money. They were converted to nominal with the
deflator below (CPI), as the brief asks: nominal = real x CPI(year) / CPI(base
year). The 1992 answer states it used the GDP deflator, so it was converted
with the Bank of England GDP deflator instead; using CPI to undo a GDP
deflator would mix two inflation measures. The base-year values (1977, 1991)
need no conversion and are graded high; converted years are graded medium.
The 1979 answer gives electricity at current prices for 1950, 1960 and 1970 to
1977, which tests the conversion: the converted values differ from it by 0% to
6.4% (largest in 1950, where the 1978 answer used the old "purchasing power of
the pound" index rather than CPI).

**Financial to calendar years.** Gas (1979 answer) and electricity (1990
answer) are April to March. Calendar year Y = 1/4 x FY(Y-1/Y) + 3/4 x FY(Y/Y+1)
when both exist. Where the earlier year is missing (gas 1950, 1959, 1964,
1969; electricity 1974) the financial year starting in Y is used alone and the note
says so.

**Therms.** Gas was sold by the therm; 1 therm = 29.3071 kWh, and only therm
figures were converted. Before conversion to natural gas, town gas had about
half the calorific value per cubic foot, so no conversion from cubic feet was
made. All gas years before 1972 are flagged "town gas era".

**Priority where sources overlap.** DESNZ, then the Hansard answers (for
electricity: 1978, 1977, 1990, 1992, then 1979), then the 2013 fact file, then
the 2011 fact file. The lower-priority value is recorded in the reconciliation
sheet with the % difference. No source overlap exceeds 10% (largest 8.3%,
electricity 1974, where only one financial year was available).

**Filling gaps by index splicing.** Where a year has no actual value, the
nearest actual year (the anchor) is chained year by year with the fuel's own
price index, choosing for each year-to-year step the best index covering both
years: (1) ONS RPI component (electricity DOBX, gas DOBY, from 1987); (2) DESNZ
QEP CPI fuel component (from 1990); for gas only, (2a) the Energy Trends
domestic gas price index, taken from the annual % changes for 1979 to 1988 in
HC Deb 8 Nov 1989; for gas 1958 to 1966 only (client decision), (2b) the Gas
Council average revenue per therm on ALL gas sold (HC Deb 1 Aug 1966 and 17 Jul
1968), calendarised in the same way as other financial-year data; (3) RPI fuel and light group (ONS ad hoc 1956 to 1987,
linked at Jan 1962, Jan 1974 and Jan 1987, then CHBG); (4) all-items CPI. The
ONS RPI components start in 1987, so gas 1956 to 1957 and 1967 to 1968 use
the fuel and light group (which also contains coal, coke, oil and
electricity), and gas 1951 to 1955 uses all-items CPI. Values from steps (3)
or (4) are graded low and from (1), (2), (2a) or (2b) medium, except gas 1967
and 1968, graded medium by client decision. Caveat on (2b): it covers all gas
sold, including industrial and commercial sales, not domestic sales only. In
1964-65 and 1965-66 domestic revenue per therm was 14% to 17% above the
all-sales figure, so the index tracks the movement, not the level. A spliced value inherits the
measure of its anchor, so a gap filled from both ends changes measure at its
midpoint.

**Chain closure.** Chaining from one anchor to the next shows how well the
index tracks the actual price; each spliced year's note gives its gap's miss.
No electricity year is spliced. Gas is spliced in 1951 to 1958 (miss -5.3%),
1961 to 1963 (+2.8%, Gas Council index) and 1966 to 1968 (+15.1%: the Gas
Council index covers 1965 to 1966 and the fuel and light group 1966 to 1969).
No smoothing is applied, so the 1966 to 1968 gap keeps a step between 1967
and 1968 (real -10%) where the two ends meet.

**1946 and 1947.** Hansard (1977 and 1978) states that there are no GB average
domestic selling values before 1948. The RPI fuel and light index starts in
1956, so electricity 1946 to 1947 and gas 1946 to 1949 are back-cast from the
first actual year with all-items CPI, graded low and typed "estimate". This
holds the real price flat over those years by construction. A fuel-specific
alternative exists but was not used: DESNZ's Electricity since 1920 gives the
average net selling value to all consumers (domestic and non-domestic), which
moved from 0.4671p (1946) to 0.4679p (1947) to 0.4850p (1948).

**DESNZ Electricity since 1920.** Every sheet was checked. It has no domestic
price or revenue series; its price sheet is for all consumers, so it is not
used for values.

**Deflator.** Bank of England Millennium dataset CPI (2015=100) to 2016,
extended with ONS D7BT (2015=100) after 2016, spliced at 2016 by ratio
(BoE 100.660, ONS 100.700). Real values are in 2025 prices, the latest full
calendar year in both DESNZ and CPI.

**Cross-checks.** DESNZ bill tables 2.2.1 and 2.3.1: (bill minus fixed cost) /
stated consumption reproduces the 2.2.4 and 2.3.4 unit prices exactly in every
year, as DESNZ builds the bills from them. Ofgem cap (direct debit, GB
average, implied unit rate from the typical and nil consumption levels, plus
5% VAT, calendar-year mean): within 7% in 2019 to 2021 and 2024; 15% to 45%
higher in 2022 to 2023, as expected, because the Energy Price Guarantee held
actual prices below the cap from October 2022 to June 2023.

**Hansard and archive search.** Used: the 1966, 1967 and 1989 domestic gas
answers and the Gas Council all-gas revenue (1966 and 1968 answers); the 1989
% changes now fill no year, because the fact file covers 1978 on. Not used:
domestic gas in 1970 terms deflated by RPI excluding fuels (HC Deb 1 Mar
1982), a deflator not in this dataset; a domestic gas price index, 1980=100
(HC Deb 23 Apr 1986), which duplicates the 1989 % changes; and tariff examples
at fixed consumption (400 therms, 125 therms, 18,000 kWh, including HC Deb 25
Jun 1984), which are not average prices. A 1982-83 domestic average revenue of
37.9 (HC Deb 30 Nov 1983) prints no unit. DECC's Gas since 1882 workbook has no
prices. DESNZ QEP tables start in 1990, with no earlier separate gas and
electricity indices. No readable Gas Council or British Gas annual report was
found online. The QEP March 2013 page cited by the fact file returns 404; it
was not needed.

**Remaining limits.** Gas 1966 to 1968 still misses its closing anchor by
15.1%. Electricity 1946 to 1947 and gas 1946 to 1949 are estimates. Values
before 1972 for gas are town gas. Electricity 1978 to 1988 is England and Wales
(Electricity Council), not GB.
