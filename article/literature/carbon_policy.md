# Carbon accounting and UK policy: synthesis

*Strand: carbon and policy. All sources accessed 7 November 2026. Full references, verbatim quotes and locators are in `carbon_policy.json`.*

## 1. Where hybrids sit in UK decarbonisation policy

UK policy has moved from cautiously including the gas hybrid heat pump to leaving it out of its central pathways. The Climate Change Committee's Sixth Carbon Budget gave hybrids a real near-term role. The CCC listed their benefits as public acceptability, installation without a distressed purchase, and suitability for hard-to-treat homes. Its modelling assumed that hybrids "can operate in heat pump mode up to 80% of the time", a figure taken from Imperial College London analysis (CCC 2020, p. 29). A sensitivity at 50% heat-pump operation made hybrids "significantly less cost effective". The Committee made two conditions explicit: standards for smart controls, and rebalancing of gas and electricity prices (CCC 2020, p. 63). Two features of that assumption matter for this article. First, the 80% share is fixed exogenously. It is not the outcome of a dispatch rule responding to prices, weather or grid carbon. Second, the CCC itself reported Energy Systems Catapult evidence that hybrid performance is "highly variable and dependent on household heating behaviours" (CCC 2020, p. 29).

The government's Heat and Buildings Strategy took the same cautious position. It said hybrids "could play a transitional role in the 2020s and 2030s" but that it was "too early to rule hybrid systems in or out" for 2050 (HM Government 2021, p. 85). It also stated that natural gas hybrids "are not compatible with Net Zero" and that the evidence base was too thin "to make firm conclusions about the potential carbon reductions that they can offer" (p. 85). The Strategy noted that hybrid controls "can be used to optimise on the basis of cost or efficiency" (p. 84). This is close to the article's software-defined controller, but the Strategy did not quantify it.

The Seventh Carbon Budget closes that door in its central case. Hybrids are 6% of heat pumps installed by 2040, but the CCC states: "We do not consider fossil fuel or hydrogen hybrids". Its most common hybrid is a heat pump paired with point-of-use hot water (CCC 2025, p. 163). The Balanced Pathway assumes heat pump installations rise from 60,000 in 2023 to about 450,000 in 2030 and 1.5 million in 2035. It also assumes the sale of new gas boilers ends in 2035 (p. 163). NESO's Future Energy Scenarios 2025 take the same line. In the net-zero pathways, "hybrid natural gas heat pump systems are no longer installed, as they are not net zero compliant", and gas boiler installations stop in 2035 (NESO 2025a, p. 103). The FES data workbook has no ASHP-plus-natural-gas hybrid category at all. Its hybrids are ASHP with BioLPG, with resistive back-up, or with hydrogen (NESO 2025b, sheet F.45).

The workbook also shows why the retained boiler is a live question in practice. Even in Holistic Transition about 19.5 million homes still have a gas boiler in 2035, against 24.4 million in 2024 (NESO 2025b, F.45). FES nonetheless lists hybrid heat pumps as a distinct source of peak demand flexibility (NESO 2025a, Fig. 54). Subsidy policy follows the pathways. The Boiler Upgrade Scheme excludes any system that "combines a heat pump with fossil fuel heating" (Ofgem n.d.).

## 2. Carbon accounting parameters

**Gas.** The 2025 government conversion factor for mains natural gas is 0.18296 kgCO2e/kWh (gross CV; AR5 GWP100; it includes the grid's small biogas content). The equivalent for the 100% mineral blend is 0.18494 (DESNZ 2025, 'Fuels'). The appraisal guidance treats the marginal and average gas factors as "identical" and constant over time (DESNZ 2026a, para 3.28). Its October 2026 Table 2a quotes 0.1830 kgCO2e/kWh (DESNZ 2026c).

**Electricity, average versus marginal.** The government's rule is clear. Average factors are "for the purposes of emissions footprinting", and the long-run marginal emissions factor (LRMEF) is for "analysing sustained changes in energy consumption" (DESNZ 2026b, para 2.9; DESNZ 2026a, para 3.29). The LRMEF, however, assumes a change "distributed evenly through the day and year": it is a time-weighted annual average (DESNZ 2026b, para 2.14). It comes from the BID3 Net Zero reference case and is smoothed with a power-law fit (paras 2.17–2.20). The guidance accepts that a heat pump shifts demand in time relative to a boiler. Yet it asks analysts to treat peak effects only as "non-monetised costs/benefits" (DESNZ 2026a, paras 3.18–3.19). DESNZ also says Table 1 is a "conservative estimate" for electrification, and that changes above about 10–20 TWh/yr need bespoke analysis (DESNZ 2026b, para 2.21).

The academic literature has long shown that short-run marginal factors differ from average ones in GB. Hawkes (2010) estimated an empirical marginal factor of 0.69 kgCO2/kWh (±10%) for 2002–09, "higher than commonly applied system-average or assumed 'long term marginal' emissions rates". Hawkes (2014) put the long-run marginal factor at 0.26–0.53 kgCO2/kWh for the following decade, approaching zero by 2035, and found that it "can diverge very significantly from the short-run". Thomson, Harrison and Chick (2017) found that average factors generally understated marginal displacement over 2009–14. In 2010 wind's displacement factor was 21% above the average. Pimm et al. (2019) estimated regional marginal factors from 28.8 to 468.5 gCO2/kWh across GB zones in 2018. They argue that marginal factors, not average ones, should be used to judge interventions such as demand response.

The half-hourly average series most models use is NESO's Carbon Intensity API. It counts generation CO2 only, using fixed fuel factors (CCGT 394, OCGT 651, coal 937, biomass 120 gCO2/kWh) and including imports and losses. It excludes unmetered embedded generation (Bruce et al. 2024). These fuel factors trace back to Staffell (2017).

**Future grids.** The FES 2025 workbook gives "CO2 intensity of generation" by pathway. NESO warns that these values ignore constraint redispatch, so "real world values will be higher" (NESO 2025b, ES1 note). In the net-zero pathways, negative BECCS emissions push headline intensities below zero by 2035. Allocating those negative emissions to a heat pump's marginal kWh would be questionable, so the excluding-BECCS series is the more defensible input for heat attribution. The CCC's Balanced Pathway has supply intensity falling from 131 gCO2e/kWh in 2023 to 7 in 2040 (CCC 2025, PDF p. 211).

**Carbon prices.** The Green Book requires all emission changes, including those inside the UK ETS, to be valued at the Data Table 3 appraisal values (DESNZ 2026a, para 3.39). The ETS allowance price is relevant only to the Financial Case (para 3.44). Central appraisal values are therefore roughly seven to eleven times the 2025 traded values (£312 against £29–44). The UK ETS auction reserve price is £28, rising to £29.01 in 2027 (DESNZ 2026e). The OBR records the UKA price falling from £73 in 2022 to £35 in 2024 (OBR 2026).

### Parameter tables

**Table A. Carbon values (£/tCO2e)**

| Series | 2025 | 2026 | 2030 | 2035 | Source |
|---|---|---|---|---|---|
| Appraisal, low (2025 £) | 156.10 | 158.47 | 168.35 | 181.57 | DESNZ 2026c, Table 3 |
| Appraisal, central | 312.19 | 316.95 | 336.70 | 363.13 | DESNZ 2026c, Table 3 |
| Appraisal, high | 468.29 | 475.42 | 505.05 | 544.70 | DESNZ 2026c, Table 3 |
| Traded, market trajectory (2025 £) | 44 | 42 | 50 | 70 | DESNZ 2026d, Table 1 |
| Traded, low / central / high | 22 / 29 / 37 | 22 / 38 / 47 | 25 / 50 / 66 | 45 / 70 / 92 | DESNZ 2026d |
| UK ETS auction reserve price (nominal) | n/a | 28 (29.01 in 2027) | n/a | n/a | DESNZ 2026e |

**Table B. Emission factors (kgCO2e/kWh)**

| Factor | 2025 | 2026 | 2030 | 2035 | Source |
|---|---|---|---|---|---|
| Natural gas, gross CV | 0.18296 | (0.1830) | constant | constant | DESNZ 2025; DESNZ 2026c |
| Electricity, reporting (generation + T&D) | 0.177 + 0.0185 = 0.1955 | n/a | n/a | n/a | DESNZ 2025 |
| LRMEF, domestic, consumption-based | 0.211 | 0.191 | 0.095 | 0.039 | DESNZ 2026c, Table 1 |
| Grid average, domestic, consumption-based | 0.146 | 0.125 | 0.072 | 0.025 | DESNZ 2026c, Table 1 |
| Empirical short-run marginal factor, GB 2002–09 | 0.69 ± 10% | | | | Hawkes 2010 |
| Long-run marginal factor, GB, decade from 2014 | 0.26–0.53 | | | ≈0 | Hawkes 2014 |
| Regional marginal factor, GB 2018 | 0.029–0.469 | | | | Pimm et al. 2019 |

**Table C. FES 2025 CO2 intensity of generation (gCO2/kWh; 2024 = 117.9)**

| Pathway | 2030 incl. BECCS | 2030 excl. BECCS | 2035 incl. BECCS | 2035 excl. BECCS |
|---|---|---|---|---|
| Holistic Transition | 4.1 | 14.3 | −30.2 | 5.6 |
| Electric Engagement | 5.6 | 15.6 | −42.6 | 9.9 |
| Hydrogen Evolution | 9.3 | 24.0 | −12.2 | 5.2 |
| Falling Behind | 79.9 | 79.9 | 23.2 | 31.0 |
| Ten Year Forecast | 35.7 | 49.4 | 23.1 | 30.2 |

Source: NESO 2025b, sheet ES1. These are generation-based figures. Add about 10% for T&D losses to approximate consumption, using the DESNZ 2025 ratio of 0.0185/0.177.

**Table D. Price cap, Direct Debit, GB average (p/kWh; p/day)**

| Period | Elec. unit | Elec. SC | Gas unit | Gas SC | Elec:gas ratio | Source |
|---|---|---|---|---|---|---|
| Oct–Dec 2025 | 26.35 | 53.68 | 6.29 | 34.03 | 4.19 | Ofgem 2025a |
| Jan–Mar 2026 | 27.69 | 54.75 | 5.93 | 35.09 | 4.67 | Ofgem 2025b |
| Apr–Jun 2026 | 24.67 | 57.21 | 5.74 | 29.09 | 4.30 | Ofgem 2026a |
| Oct–Dec 2026 (electricity VAT 0%) | 26.32 | 54.83 | 7.97 | 29.68 | 3.30 | Ofgem 2026b |

## 3. Levy rebalancing: what has actually happened

Before the Budget, policy costs were 16% of a typical electricity bill but only 5.5% of a gas bill. Nesta put the unit-price ratio at 3.9, against an ASHP running-cost break-even of about 4.1. Removing all levies from electricity would cut the ratio to 3.1, and full rebalancing onto gas to 2.4 (Shepheard et al. 2024). The CCC's pathway assumes a fall from about 4 to 2.2–2.6 by 2040 (CCC 2025, p. 107). In 2021 the government committed to "shift or rebalance energy levies … away from electricity to gas over this decade" (HM Government 2021, p. 21).

What has been decided by November 2026 is a move onto taxation, not onto gas. From April 2026 the Exchequer meets 75% of domestic Renewables Obligation costs for 2026/27–2028/29, and ECO/GBIS are no longer levied on bills, saving about £150 on average (DESNZ 2025b; Ofgem 2026c). VAT on household electricity has been removed from 1 October 2026 to 31 March 2027 (DESNZ 2026f; Ofgem 2026b). The MCS Foundation finds these measures "go some way" but "do not fully resolve" the imbalance (Russon and Wakelin 2026, p. 36). The cap ratio has moved accordingly. It peaked at 4.67 in Q1 2026 and fell to 3.30 in Q4 2026, helped as much by a rise in wholesale gas prices as by the levy changes (Table D). For a price-aware hybrid controller, this volatility in the ratio from quarter to quarter is itself a model input. It is also a reason not to fix the switching point.

## 4. The gap

Four things are missing from the literature and from official accounting.

1. **No price-dispatched hybrid in official carbon accounting.** The CCC's only quantified gas-hybrid case uses a fixed 80% (or 50%) heat-pump share (CCC 2020). The government admitted in 2021 that it could not estimate hybrid carbon savings (HM Government 2021). Both the CCC 2025 pathway and FES 2025 then drop gas hybrids altogether. No source reviewed derives the heat-pump share from a controller responding to half-hourly tariffs, weather and carbon.
2. **Flat marginal factors for a weather-correlated load.** The appraisal LRMEF is time-weighted and assumes evenly spread demand (DESNZ 2026b). Yet the guidance itself says heat pumps reshape demand (DESNZ 2026a). The academic evidence shows marginal factors diverge from average ones in time and space (Hawkes 2010, 2014; Thomson et al. 2017; Pimm et al. 2019). None of this work examines the cold, still, high-demand half-hours in which a hybrid's boiler-or-heat-pump decision is made, nor how often they occur across many weather years.
3. **Future-grid intensities are not tied to switching.** FES 2025 publishes pathway intensities, including negative values driven by BECCS, and notes that they are biased low (NESO 2025b). However, no study maps them onto the dispatch of a retained boiler, with or without a carbon price.
4. **Policy contingency.** The electricity-to-gas price ratio, which the CCC treats as a precondition for hybrids, is now moved by fiscal choices: Exchequer funding of RO costs and temporary VAT relief. Rebalancing onto gas has not happened. The cost-optimal and carbon-optimal switching points therefore diverge in ways that no published GB study has quantified across decades of weather.

The article's GB model fills this gap. It covers 79 towns over 86 ERA5 winters, uses a price-aware and carbon-aware controller, and reports results under both average and marginal intensity for today's grid and for FES 2030 and 2035.
