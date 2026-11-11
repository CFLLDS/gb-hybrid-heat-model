# Data hunt: older prices, hybrid costs, hybrid data, Scotland

Accessed 2026-11-07. Adds to `data_landscape.md`. All 21 records in `data_hunt.json` were fetched and carry a located quote; samples are in `data/model/gb/sources/hunt/`. Nothing was registered, submitted or paid for.

## Priorities

### 1. Electric Insights mirror: half-hourly GB day-ahead price from 2009 [OPEN, licence unclear]

**Use this for 2009-2016.** A GitHub repository (Bourn) holds yearly CSVs of Drax Electric Insights data, 2009 to mid-2022, with 30-minute `day_ahead_price` and `imbalance_price` plus demand, fuel mix and carbon.

We checked the 2010 file:

- It has 17,520 unique half-hours, but 23,426 rows, so duplicates must be dropped.
- The day-ahead price averages £41.5/MWh.
- In January 2010 the price averaged £30/MWh at 04:00 and £70/MWh at 17:30. The evening peak is clearly there.

It covers the 2010-11 hard winter. Catches: no licence file; the exchange (APX or N2EX) is not named; a few 0.0 gaps. **Action:** cross-check against MID and OPSD over 2015-16, and cite Drax/Electric Insights.

### 2. Elexon system prices reach back to 6 Nov 2015 [OPEN]

The Insights API serves SSP/SBP from **2015-11-06**; every earlier date we tried (2001 to 2015-11-05) is empty. That is 11 months before MID, but it is the cash-out price, not day-ahead.

### 3. Other price sources, all weaker

- **OPSD:** hourly GB day-ahead price from ENTSO-E, 2015-01-02 to 2020-09-30.
- **LCCC IMRP actuals:** hourly GB day-ahead price under the OGL, but only from 2016-06-30.
- **UKDS SN 5247 (Green & Evans), 1996-2004:** Pool-era E&W data, undocumented; may hold 2001-04 prices.
- **Dead ends:**
  - CAFIM "APX" is the Dutch exchange and needs a login.
  - Bodmer's UK price database has no download link we could find.
  - The Nord Pool historical-data URLs return 404.
  - BSC Portal access now matters only for 2001-2008.

**Recommended price stack:**

| Years | Source |
|---|---|
| 2001-08 | NESO demand only. Price is a gap unless SN 5247 or Elexon fills it |
| 2009-16 | Electric Insights |
| Nov 2015 onwards | Elexon SSP, as an imbalance cross-check |
| Oct 2016 onwards | Elexon MID |
| 2018 onwards | Octopus Agile |

### 4. Hybrid installed costs

| Source | £ (as published) | Year | What it includes |
|---|---|---|---|
| EoH Install Report Table 4 | **10,200 ± 3,300** (n=147; 8,000-27,300) | installs 2020-22 | heat pump, extra measures, labour; boiler mostly retained; mostly 4 kW E.ON |
| EoH Table 5 | 6,700 ± 2,600 | 2020-22 | heat pump + labour only |
| Element Energy for BEIS | HHP 6,725 (5 kW HP), 6,170 (2 kW); boiler 1,570; full HP 8,975 | £2016 | modelled, typical semi |
| Carbon Trust for BEIS | product <2,000-7,000; installed 4,000-10,000 | 2016 | quotes |
| Nesta | 8,000 / 12,100 / 16,000 (small/medium/large) | Feb 2025 | method not read |
| Worcester Bosch | 5,000-8,000 | undated | manufacturer guide |
| BEE merchant, Vaillant aroTHERM plus 3.5 kW hybrid kit | 3,590.81 ex VAT (list 4,613.00) | Nov 2026 | kit only |

Delta-ee (2018) has no hybrid line (installers price boiler + heat pump). No Which? figure; Daikin and Ideal list prices unpublished; Checkatrade 403.

**Recommendation:** EoH **£10,200** as the measured central case, £8,000 as low; Element Energy for the increment over a £1,570 boiler.

### 5. Measured hybrid data

- **EoH SN 9050 [OPEN, OGL]: best.** Hybrids have **a separate boiler space-heating heat meter** plus heat-pump heat and electricity. Interim median heat-pump share of hybrid space heat: **39%** (cost-optimised control). Boiler hot water and gas input unmetered. Use it to validate our HP/boiler split against outdoor temperature.
- **Freedom (75 Bridgend homes, 2017-18):** report open, no public dataset; **no boiler heat meter** ("virtual heat meter").
- **ESC Living Lab Eden 5 (hybrids, Oct 2019-Sep 2020):** uSmart, licence unknown; host unreachable, size unverified.
- **RHPP SN 8151:** UKDS EUL, 700 heat pumps 2013-15; no hybrids mentioned.

### 6. Scotland

- **Census 2022 UV407 [OPEN, OGL]:**
  - Scotland has 2,509,269 households.
  - **1,841,697 have mains gas as their only central heating type.** Another 153,976 have two or more types.
  - Against 2,150,344 DESNZ domestic gas meters for 2022, that gives **0.856 heated homes per meter**, or 0.928 if every multi-type home counts.
  - At Intermediate Zone level, 1,012 zones matched on unique names. Their median is 0.866, and the deciles run from 0.77 to 0.94.
  - Catches: the census IZ file is keyed by name, not code, and the figures are perturbed.
- **SHCS LA tables [OPEN]:** 2016-18 (downloaded) and 2022-24 (26 May 2026): per-council gas grid, heating, insulation, % EPC F/G and B/C, mean SAP. Survey-based.
- **Home Analytics:** EST site blocked us; treat as licensed, not open.

## What Craig needs to do

1. **Nothing to pay.**
2. **UKDS account** (already needed for SERL and EHS) to download:
   - SN 5247, to see whether 2001-04 Pool prices are inside;
   - SN 8151, optionally.

   EoH SN 9050 is open.
3. **Optional email to Drax/Electric Insights** for permission to cite and redistribute the 2009-16 day-ahead series.
4. **Elexon:** ask about pre-2009 MID only if 2001-08 prices are essential.
5. **Optional:** fill in ESC's download form (or email communications@es.catapult.org.uk) for the EoH final reports and Living Lab Eden 5 details.

## References (accessed 7 November 2026)

Full URLs and locators are in `data_hunt.json`. Bourn (2022) *Electric Insights* [GitHub]; Carbon Trust (2016) *Domestic Hybrid Heat Pumps*, BEIS; Delta-ee (2018) *Cost of installing heating measures*, BEIS RP 2020/028; Element Energy (2017) *Hybrid Heat Pumps: Final report*, BEIS; Elexon (2026) *Insights API*; ESC (2022) *EoH Home Surveys and Install Report*; ESC (2023) *EoH Interim Performance Report 1*; ESC (2024) SN 9050, UKDS; Green and Evans (2005) SN 5247, UKDA; LCCC (2026) *IMRP actuals*; NRS (2024) *Census 2022 UV407*; Nesta (2025) *Hybrid heat pumps*; OPSD (2020) *Time series*; Scottish Government (2019; 2026) *SHCS LA tables*; WWU and WPD (2018) *Freedom Final Report*; Worcester Bosch (n.d.) *Hybrid heat pump cost*.
