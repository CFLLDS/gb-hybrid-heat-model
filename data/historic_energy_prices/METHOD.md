# UK domestic gas and electricity prices, 1946 to 2025: method

LDS Consulting Limited. Full detail and every judgement call are in
`METHOD_DETAIL.md`; sources, URLs and download dates are in `raw/SOURCES.md`.

**What the dataset is.** One value per fuel per year, 1946 to 2025, in pence
per kWh, in money of the day and in 2025 prices. Each row states its source,
whether it is an actual price, an index-spliced value or an estimate, and a
confidence grade. `build_series.py` rebuilds everything from the unedited downloads in
`raw/`; only the Hansard tables are hand-transcribed, and each value is
checked against the saved page text on every run.

**One measure throughout.** Every value is an all-in price per kWh: standing
charge and VAT included. Before 2010 this is average revenue (domestic
spending divided by kWh bought). From 2010 it is the DESNZ typical bill
divided by typical consumption. The DESNZ unit rate without the standing
charge is given in a separate column from 2010.

**Where the actual prices come from.**
- 2010 to 2025, both fuels: DESNZ annual domestic energy price statistics.
- 1970 to 2009: the DECC/BRE housing energy fact file 2013, which divides
  household spending by household consumption. It fills electricity 1992 to
  2009 and gas 1978 to 2009, and agrees with the Hansard figures within 8.2%
  where both exist.
- Electricity 1948 to 1991: government answers to Parliament (Hansard, 1977
  to 1992) giving average revenue per kWh.
- Gas 1950, 1959, 1960, 1964, 1965 and 1969 to 1977: Hansard answers giving
  average revenue per therm, converted at 29.3071 kWh per therm.

**Conversions.** Tables published in constant prices were converted back to
money of the day with the deflator they used: CPI for the 1977 and 1978
answers, the GDP deflator for the 1992 answer, and the RPI printed in the fact
file for the fact file. Financial years become calendar years as one quarter
plus three quarters. Gas before 1972 is flagged as town gas and was converted
only from therms, never from cubic feet.

**Filling gaps.** Where no actual price exists, the nearest actual year is
carried forward or back with the fuel's own price index. If none exists, the
fuel and light group index is used, and failing that, general CPI. No
electricity year needs this. Gas does for 1951 to 1958, 1961 to 1963 and
1966 to 1968. For 1958 to 1966 the index is the Gas Council's average revenue
per therm. It covers all gas sold, not domestic sales only, so it tracks how
prices moved, not their level. Each filled year's note gives how far the chain
misses the next actual year: -5.3%, +2.8% and +15.1% for the three gaps. No
smoothing is applied.

**Before 1948.** Parliament was told in 1977 and 1978 that no domestic average
prices exist before 1948. Electricity 1946 to 1947 and gas 1946 to 1949 are
therefore estimates, back-cast with general CPI and graded low.

**Real terms.** Bank of England CPI to 2016, joined to ONS CPI from 2016, and
rebased to 2025.

**Checks.** Overlapping sources were compared year by year, and none differs
by more than 10%. The DESNZ unit prices reproduce the DESNZ bill tables
exactly. Ofgem price cap levels agree within 7% except in 2022 to 2023, when
the Energy Price Guarantee held prices below the cap.
All checks are in the xlsx reconciliation sheet.

**Main limits.** Gas 1966 to 1968 rests partly on a general fuel index and
misses its closing anchor by 15%. Electricity 1978 to 1988 covers England and
Wales only. Revenue-based prices blend tariffs, so they match no single tariff.
