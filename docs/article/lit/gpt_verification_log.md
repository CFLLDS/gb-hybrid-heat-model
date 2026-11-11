# Verification log: ChatGPT hybrid-heating literature list (2026-11-07)

Input: `tmp/Hybrid_Heating_Literature_Base_2026-11-07.md` (30 references, leads and datasets). It was treated as unverified claims.
Downloads: `data/model/gb/sources/verify_gpt/` (raw PDF/HTML plus extracted `.txt`); Crossref records for DOIs are in `leads/`.
Register output: `docs/article/lit/gpt_verified.json`, holding VERIFIED and VERIFIED_WITH_CORRECTIONS sources only.

Method: each source was fetched, the text extracted, and each quote matched verbatim by script after normalising whitespace, curly quotes, ligatures and line-break hyphenation. Two-column PDFs were matched in non-layout mode. The key numbers in the "Use and evidence" text were searched for in the source.

**Result: 26 VERIFIED, 4 VERIFIED_WITH_CORRECTIONS, 0 NOT_FOUND, 0 BLOCKED.** All 30 quotes appear verbatim at or near the stated locator, so no quote had to be replaced (no `quote_corrected`). Where the register adds a second claim, that claim's quote was also matched verbatim.

## The 30 references

| # | Key | Status | Corrections / notes |
|---|---|---|---|
| 1 | Boardman2010_FP08 | VERIFIED | Live parliament.uk page returns HTTP 403, so it was read from an Internet Archive snapshot. Memo dated February 2010, HC 424 (2009-10). Quote is in para. 1; the 10% threshold is in the same sentence. |
| 2 | Hills2012 | VERIFIED | CASE report 72, March 2012. Quote at PDF p. 12, printed p. 9, Recommendation 2, as stated. |
| 3 | DESNZ2026_FuelPoverty | VERIFIED | Published 26 Mar 2026, republished 7 Aug 2026 (calculation error corrected). 2.36 m (9.4%) LILEE and 7.63 m (30.4%) over 10% AHC confirmed (p. 1; Annex D table p. 83). Quote in section 2.1, p. 10. Full title adds "(2024 and 2025 data)". |
| 4 | NEA_EAS2024_Monitor | VERIFIED | 136 Call for Evidence respondents confirmed. Quote at PDF p. 4 ("Our approach"). |
| 5 | ONS2012_EWM | VERIFIED | 26,080 excess winter deaths in 2010/11 confirmed. "Extending through 1962/63" is loose wording: the series runs 1950/51-2011/12, so it includes 1962/63. |
| 6 | NICE2015_NG6 | VERIFIED | Page fetched directly. The para. 1.1 lag is "up to 2 or 3 weeks". |
| 7 | Rivers2026 | VERIFIED | Author Will Rivers (Carbon Trust). Report RAF026/2526, May 2026. Cover credits DESNZ (2026), with Ipsos UK on the team. Quote at PDF p. 7, printed p. 4. "20 technical audits" means concurrent audits in 20 of the 29 interviewed homes. ">1,100 installations" confirmed. |
| 8 | Zhou2024 | VERIFIED | The Edinburgh repository PDF returned 403, so the full text was read via Europe PMC (PMC10837618, CC BY). iScience 27(2) 108854 confirmed. 67.26 to 65.16 (Scotland) and 47.68 to 46.85 (England) are in Table 1, under "crisis" = 2022 prices, with all off-gas heating replaced by heat pumps. |
| 9 | Xu2025 | VERIFIED | AAE 17 (2025) 100201 confirmed. Abstract quote verbatim. Ratio range 3.25-5 confirmed; "most notable increase in inequality occurs between the price ratios of 3.5 and 4" (national level). 2019 vs 2022 contrast confirmed. |
| 10 | Rijksoverheid2024_hybrid | VERIFIED | Page dated 31-10-2024 (Ministerie BZK). Quote is its opening sentence. |
| 11 | dena2026_hybrid | **VERIFIED_WITH_CORRECTIONS** | The given URL (`Factsheet_65ProzentEE_10_...`) returns **404**, and there is no Wayback copy. The current edition is `Factsheet_Waermeerzeugung-GModG_06_Waermepumpe-Hybridsystem.pdf`, **Stand 08/2026**. It cites the new **Gebäudemodernisierungsgesetz (GModG, §§42-46, from 29.07.2026)**, not the GEG 65% rule. Quote, 30%/40% sizing, EUR 28,000 and EUR 6,000 are unchanged in that edition. Re-dated to 2026 and re-keyed from dena2025_hybrid. Do not cite it as a September 2025 snapshot. |
| 12 | DiMatteo2026 | VERIFIED | Energy Eng. 123(2) article 1, DOI confirmed. Quote in section 3.2, p. 32. Close to 30% PES, 35.3%, 25.8% and EUR 15,175 confirmed in section 3.3, Table 10, p. 33. |
| 13 | SSEF2024_hybrid_demo | **VERIFIED_WITH_CORRECTIONS** | Quote is on **p. 11** of 113, not p. 12. 174 participants with working meter sets confirmed. COP about 3.8. 75% gas saving is the mean of 168 participants (range 31-97%). EUR 1,000/yr is at the June 2024 tariff of EUR 1.33/m3. Ref. 2021-53403. |
| 14 | Davila2023_HHP | VERIFIED | The paper is authored "Camila Dávila"; ORBi lists "Davila Valdebenito, Camila". HPC 2023, Edinburgh, 3-6 Sept. Quote in Conclusions. 2021-2022 monitoring and tariff-setting changes confirmed. |
| 15 | Zadoks2026 | VERIFIED | arXiv 2609.02174, submitted 2 Sep 2026, preprint. 471 networks, 39% / 134% for an extra 20% of adoption confirmed. Added: optimal thresholds of 50% (ToU) and 40% (RTP), and the >50% cost reduction below them. |
| 16 | Bernard2024 | VERIFIED | NBER WP 33036, October 2024 version read (whether it was later revised was not checked). The 50% is a peak-demand fall with a 60% peak price rise, own-price elasticity -0.8 (p. 34). Centre for Net Zero / Octopus conflict disclosed. |
| 17 | EFUS2011_Report4 | VERIFIED | BRE 286733a, December 2013. Quote in section 4.3, printed p. 53. 18-21 C interquartile range confirmed. |
| 18 | EST2008_DHW | **VERIFIED_WITH_CORRECTIONS** | "Approximately 120 monitored homes" is imprecise: **124 recruited, 119 with usable data, 7 more dropped in analysis**. 122 ±18 L/day, 16.8 ±2.2 MJ/day and 51.9 ±1.3 C confirmed (p. 2). |
| 19 | Orr2009_boilers | VERIFIED | June 2009, GaC3563. Quote in section 7.1.2, printed p. 25. 60 boilers, 43 full datasets (31 combis) and regular boilers at 85.3% (SD 2.5%) confirmed. |
| 20 | DESNZ2023_HEM_FHS | VERIFIED | December 2023 consultation. 60 W, 104 W and 74 W confirmed in section 3.1.2, p. 15. |
| 21 | Ofgem2025_RIIO3_FD | VERIFIED | Published 4 Dec 2025. Quote at para. 7.2, PDF p. 89. New gas-distribution assets depreciated by 2050, existing-asset policy unchanged, gas transmission keeps its 45-year profile: all confirmed. |
| 22 | DESNZ2025_Midstream | VERIFIED | Policy paper published 30 June 2025. Quote in the "Balancing infrastructure..." section. Stranding language confirmed. |
| 23 | DeltaEE2018_costs | VERIFIED | Final report July 2018, BEIS RP 2020/028. GBP 8,750 (8 kW) and GBP 11,500 (12.5 kW), excluding VAT and distribution, confirmed on p. 9. |
| 24 | HHGB2025 | VERIFIED | PDF dated November 2025. GBP 4,000-7,000 hybrid range confirmed on p. 10; footnote 14 reads "Heat Pump Installers, Engagement, 2025". |
| 25 | Fell2015 | VERIFIED | ERSS 9, 72-84. N = 2002 and five tariffs confirmed. |
| 26 | EU2019_944 | VERIFIED | Article 11(3) verbatim (consolidated text 2024-07-16). |
| 27 | Chard2021_InvoLVe | VERIFIED | June 2021. Quote on p. 43. |
| 28 | Hansard1950_gas | VERIFIED | HC Deb 14 Jul 1950 vol 477 cc137-8W. 1946 = 1s 1d/therm confirmed. |
| 29 | Hansard1977_fuel | **VERIFIED_WITH_CORRECTIONS** | Given URL returned 403. Confirmed via the historic-hansard mirror and the Hansard API. Citation completed as **vol 924 cc636-7W**. Gas 10.6 and electricity 23.3 p/therm for 1966 confirmed. Gas figures are for years ending 31 March of the following year. |
| 30 | IFS_LSPI | VERIFIED | Live page returned 403, so it was read from an Internet Archive snapshot of 2025-12-29. Quote verbatim. Workbook cells not audited. |

Nothing turned out to be non-existent, and no quote failed. The substantive problems were the dena edition (dead URL, superseded law) and the loose DHW sample size. The other corrections are page locators and fuller citations.

## Unverified leads

| Lead | Verdict |
|---|---|
| Sun et al. 2019, Applied Energy 247:525-536 | CONFIRMED to exist (Crossref: authors, volume, pages). Full text not read, so not in the register. |
| Muratori & Rizzoni 2016, IEEE TPWRS 31(2):1108-1117 | CONFIRMED to exist (Crossref). Full text not read. |
| Klein, Huchtemann & Müller 2014, Energy & Buildings 69:193-201 | CONFIRMED to exist (Crossref). Full text not read. |
| Di Perna et al. 2015, Applied Thermal Eng. 76:86-97 | CONFIRMED to exist (Crossref). Full text not read. |
| Boardman 1991 book | Only cited inside FP 08 ("Boardman 1991, p 227"). Not inspected. |
| Continuous 1946-2025 price/income panel | Correctly flagged as a gap. Not a source. |
| Gas decommissioning cost estimate | Correctly flagged as a gap. Midstream (2025) and Ofgem (2025) give no per-household figure. |

## Datasets

| Dataset | URL | Access terms (confirmed) |
|---|---|---|
| DESNZ long-term fuel poverty trends (LILEE, 2010-2025) | https://www.gov.uk/government/statistics/fuel-poverty-trends-2026 | XLSX and ODS, published 26 Mar 2026, Open Government Licence v3.0 |
| Hills Review chart data | https://assets.publishing.service.gov.uk/media/5a78f123e5274a277e690aa2/4665-data-used-charts-final-fuel-pov-rpt.xls | XLS on GOV.UK, OGL v3.0. Not audited |
| ONS EWM 2012 reference tables | https://www.ons.gov.uk/.../excesswintermortalityinenglandandwales/2012-11-29 (XLS links on page, including ewm-reference-tables.xls) | Free download, ONS/OGL. England and Wales only |
| IFS living standards spreadsheet | https://ifs.org.uk/living-standards-poverty-and-inequality-uk | Free spreadsheet download. Live site returns 403 to scripts; confirmed via Wayback. Terms not checked |
| BoE "A millennium of macroeconomic data" v3.1 (to 2016) | https://www.bankofengland.co.uk/statistics/research-datasets | Free XLSX (28 MB). Columns not checked |
| EFUS 2011 reports | https://www.gov.uk/government/statistics/energy-follow-up-survey-efus-2011 | 11 PDF reports, OGL. Microdata access not established |
| Delta-ee installation cost data | https://assets.publishing.service.gov.uk/media/5f6d9379e90e077514e06719/delta-ee-cost-domestic-heating-measures-final-cost.ods | ODS on GOV.UK, OGL |
| Dutch hybrid demonstration report | https://media.greenchoice.nl/media/g2xg0uem/eindrapportage-demonstratieproject-hybride-warmtepompen-aug2024.pdf | Public PDF with participant table (p. 30). Raw time series not public as far as could be seen. No licence stated |
| Xu et al. code and data | https://github.com/cambridge-cares/TheWorldAvatar (cited in the paper) | Public GitHub repository. Licence not checked |
