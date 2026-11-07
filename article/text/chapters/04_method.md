## 4. Method

The model is a half-hourly simulation of heat demand and heat supply for one monitored house and a sampled housing stock in __TOWNS__ towns across Great Britain, run through every heating year from __FIRST_YEAR__ to __LAST_YEAR__. It is written in Python with JAX [@JAX2018] and runs on a single NVIDIA DGX Spark, where one heating year for every town, home, tariff and controller takes about __SECONDS_PER_YEAR__ seconds. This section describes its inputs, its physics, the controllers it compares, how results are counted and scaled, and how it was validated.

{{fig:pipeline}}

### 4.1 Weather: every heating year since 1940

Outdoor temperature comes from the ERA5 reanalysis [@Hersbach2020], served hourly by the Open-Meteo historical weather API [@OpenMeteo_Historical; @Zippenfenig2023]. ERA5 begins in 1940 [@ECMWF_ERA5_1940], so the first complete heating year is 1 November 1940 to 31 October 1941. For each of the __TOWNS__ towns, from Penzance in the south-west to Wick in the far north, the model takes hourly 2-metre temperature for every heating year from 1940–41 to 2025–26, __N_YEARS__ years in all, and interpolates it to half-hours. Each year is run as a whole: mild autumn and spring days, summer days with only hot water to make, and cold snaps all count in proportion.

Each town also has a design temperature: the cold its heat pumps are sized for. MCS heat-loss calculations may use either a 99% or a 99.6% external design temperature from CIBSE Guide A; this model uses the colder, 99.6% basis [@MCS_DesignTemps, Table 2, column B] for the nearest of 14 listed locations, corrected by −0.6 °C per 100 m of altitude. Across the towns it ranges from __DESIGN_RANGE__.

### 4.2 Prices and carbon: one real year, matched by calendar day

Half-hourly tariffs and regional grid carbon do not exist for most of the weather record, so every weather year is priced on one real year: 1 November 2025 to 31 October 2026. Each simulated day takes the actual prices and carbon intensity of the *same calendar day* in that year, in the town's own electricity region: 1 December 1962 is priced as 1 December 2025. A leap-year 29 February borrows 28 February. The model therefore asks a precise question: *what would today's tariffs and today's grid have cost, and emitted, in the weather of each past year?* It does not reconstruct the prices of the past.

Four electricity tariffs are compared:

- **SVR**, the price-cap standard variable rate: a flat __P_SVR__p/kWh all day;
- **Intelligent Octopus Go (IOG)**: __P_IOG_CHEAP__p/kWh from 23:30 to 05:30 and __P_IOG_PEAK__p/kWh otherwise;
- **Cosy** (Octopus's heat-pump tariff): the actual regional half-hourly rates, with cheap windows and a 16:00–19:00 peak [@OctopusCosy; @OctopusAPI];
- **Agile** (Octopus): a new price every half-hour that follows the wholesale market [@OctopusAgile; @OctopusAPI], __AGILE_HALFHOURS__ actual prices per region over the year, of which __AGILE_NEGATIVE_PCT__% were negative.

Gas is __P_GAS__p/kWh with a standing charge of __GAS_SC__p a day. The SVR and gas prices are the Ofgem cap for the Southern region, Direct Debit, October to December 2026, applied to every town; the GB average for the same period was 26.32p and 7.97p [@Ofgem2026_Cap_OctDec]. The gas standing charge is paid every day of the year by any home that keeps a boiler, and by no all-electric home.

Grid carbon is the regional half-hourly intensity from the National Energy System Operator's Carbon Intensity API for the same calendar day [@CarbonIntensityAPI; @Bruce2024_CI_Regional]. Gas emits __GAS_KG__ kg CO₂ per kWh burned [@DESNZ2025_GHG_CF].

### 4.3 Heat demand

Each home's space-heating demand in each half-hour is its heat loss at the outdoor temperature less its internal gains:

<div class="eq">q_space(t) = max( UA × (T_set − T_out(t)) − G × g(t), 0 ) × 0.5 h</div>

where UA is the home's heat-loss coefficient (W/K), T_set its set point, G its mean internal gains and g(t) a daily gains profile (0.7 overnight, 1.1 06:00–09:00, 0.8 during the day, 1.3 16:00–21:00, 1.0 late evening). Hot water is made in two two-hour reheats, 06:00–08:00 and 17:30–19:30. The model has no thermal mass: each half-hour stands alone and heat is supplied when it is needed (see Section 7).

### 4.4 Heat pump efficiency and capacity

A heat pump's coefficient of performance (COP) is modelled as a share of the ideal Carnot COP at its flow temperature:

<div class="eq">COP(t) = share(T_out) × level × (T_flow + 273.15) / max(T_flow − T_out, 5), clipped to 1.3–7</div>

The Carnot share captures everything the ideal cycle leaves out, including defrost. For the housing stock it was fitted to __HPM_SYSTEMS__ British air-source systems on heatpumpmonitor.org [@HPM_org] that report space heating separately: __HPM_DAYS_ALL__ system-days over the winters of 2024–25 and 2025–26 passed the quality filters, of which __HPM_DAYS__ fall inside the fitted temperature bands. Those systems hold a share of about 0.34–0.36 from −10 °C to 12 °C, falling to 0.31 when mild (Figure 2).

{{fig:share_fit}}

But the systems on heatpumpmonitor.org are, by self-selection, well installed and well tuned: their median seasonal performance factor is __HPM_FLEET_SPF__ across __HPM_FLEET_N__ British systems, against 2.78 in the national Electrification of Heat trial [@ESC2024]. Each sampled home therefore draws a *level* uniformly between the trial median and the tuned fleet (×__LEVEL_LOW__ to ×1.0 of the fitted share), so the typical sampled home sits at about SPF __STOCK_SPF_TYPICAL__.

Flow temperature follows weather compensation, from 25 °C at 16 °C outside to the home's design flow temperature at its design outdoor temperature. Hot water is made at 48 °C. Output is capped by the unit's capacity, which falls in the cold, using a measured manufacturer table (Daikin ERGA06, 35 °C and 45 °C flow) scaled to each unit's size.

### 4.5 The housing stock

Each town samples __HOMES_PER_TOWN__ homes. Their parameters are drawn independently:

<div class="tablebox" markdown="1">

| Parameter | Distribution |
|---|---|
| Heat-loss coefficient UA | log-normal, median 180 W/K, σ = 0.45, clipped to 60–450 W/K |
| Set point | uniform 19–21.5 °C |
| Mean internal gains | uniform 250–700 W |
| Hot water | uniform 2–8 kWh a day |
| Radiator design flow temperature | uniform 40–55 °C |
| Heat-pump efficiency level | uniform ×__LEVEL_LOW__–×1.0 of the fitted Carnot share |
| Boiler seasonal efficiency | uniform 85–92% |
| Heat-pump size | MCS: smallest of 4–20 kW covering 100–120% of the design heat loss at the town's design temperature and the home's design flow |

</div>

These ranges are drawn to show the spread of British homes, not their exact national shares; they are not a housing survey (Section 7). Each home is sized as an MCS installer would size it, to meet its full design heat loss at the town's design temperature [@MCS2024MIS3005D].

The same __HOMES_PER_TOWN__ homes are run through every day of every year, under every tariff and every controller. Each comparison is therefore *paired*: when the model reports that one controller beats another for some share of homes, it is the same homes, on the same days, in the same weather. A home's result is its whole-year bill, not any single day.

### 4.6 The controllers

Each half-hour, each controller decides which source supplies the heat. The all-heat-pump case is the benchmark: it uses only the heat pump, and any demand beyond its capacity is charged as direct electric heat at COP 1, so that the all-electric case is never flattered. Every hybrid is capacity-limited: when the heat pump is chosen but cannot meet the demand, the boiler tops up.

<div class="tablebox" markdown="1">

| Controller | Heat pump runs in a half-hour when… | Represents |
|---|---|---|
| All gas | never | the boiler alone |
| All heat pump | always | an all-electric home |
| Fixed bivalent, 0 °C | T_out ≥ 0 °C | Vaillant's factory default [@Vaillant2024Top10] |
| Fixed bivalent, 2 °C | T_out ≥ 2 °C | the EU bivalent ceiling [@EU2013Reg813]; close to Daikin's worked example [@Daikin2026IRG] |
| Fixed bivalent, 5 °C | T_out ≥ 5 °C | a cautious installer setting |
| **C-COP** | p_gas / η > p_elec(t) / COP(t) | software choosing heat per penny |
| C-COP + carbon (£40/t) | (p_gas + λ·k_gas)/η > (p_elec + λ·c(t)) / COP | the traded carbon price [@DESNZ2026_TradedCarbonValues] |
| C-COP + carbon (£312/t) | as above, λ = £312/t | the government appraisal value [@DESNZ2026_DataTables] |
| C-COP, peak off | C-COP, and never 16:00–19:00 | a simple network peak rule |
| **SD-Power dispatch** | C-COP, except that a random share of homes use gas when Britain's total demand would exceed a cap | software that also serves the grid |

</div>

Here η is the boiler's efficiency, k_gas the gas emission factor, c(t) the half-hourly grid intensity and λ the carbon price. The C-COP rule is the decision a household optimising its own bill would make each half-hour with perfect knowledge of the current price and its heat pump's current efficiency: run the heat pump whenever its heat is cheaper than the boiler's. It is the controller studied in this paper's case-study house, where it is measured as the *commercial COP*.

**SD-Power dispatch** is the one controller that looks beyond the home. A price-aware controller in every home sees the same price at the same moment. On a flat tariff that is harmless, because C-COP hands the coldest hours to gas. On a dynamic tariff it is not: every home switches to its heat pump in the same cheap half-hour, and the stock's demand moves together, a problem regulation already anticipates with a randomised delay of up to ten minutes for smart heating [@DESNZ2025SSES, p. 7]. SD-Power dispatch is therefore defined against Britain's whole electricity system. For each half-hour of each weather year the model adds the stock's C-COP heat-pump demand, scaled to Britain's gas-heated homes, to the national demand the system actually carried in the same half-hour of 2025–26 [@NESO_HistoricDemand]. It sets a cap: the highest total that C-COP would produce in that year on a flat tariff. Wherever a tariff would push the total above the cap, a random share of homes, just large enough to hold the total at the cap, uses gas instead for that half-hour. This is the portfolio cap the Freedom project demonstrated in 54 homes [@FREEDOM2018, pp. 15, 22], applied nationally. It needs two passes of the model: the first measures the demand, the second dispatches against it. In every other respect the two passes are identical, and the second reproduces the first exactly for every other controller.

### 4.7 Counting, carbon and scaling

For each home, tariff and controller the model records the year's cost, gas and electricity use, the heat supplied by the boiler, and emissions on the average grid. Because electricity and gas use are recorded separately, emissions under any other constant factor can be recomputed without rerunning the model: the government's long-run marginal factor for 2025, 2030 and 2035 [@DESNZ2026_DataTables], the empirical short-run marginal range [@Hawkes2010; @Hawkes2014], and the 2030 and 2035 grids of the Future Energy Scenarios [@NESO2025_FES_Workbook].

Town results are reported as the share of the __HOMES_PER_TOWN__ homes for which each option is cheapest over the year, with the median home's annual cost. National electricity demand is the mean per-home demand in each half-hour, averaged over the towns of each of Britain's 14 electricity regions and weighted by that region's gas-heated homes (__GB_GAS_METERS__ domestic gas meters in 2024, assigned to the regions small area by small area [@DESNZ2025_MSOA_Gas; @NESO2024_DNO_Areas; @ONS2021_MSOA_Centroids; @ScotGov2022_IZ_Centroids]). Gas meters are not quite gas-heated homes: in England and Wales the census counts 0.81 homes heated by mains gas alone per domestic meter [@ONS2021_TS046], so national figures are also given on that basis. Peaks are the largest half-hour of each heating year under each controller, assuming every gas-heated home adopts it.

### 4.8 The monitored house

One real house anchors the calibration: my own, a three-storey house in Poole with a 6 kW Daikin Altherma monobloc on all-microbore pipework, a heat loss of 171.7 W/K measured from a year of its own data, and its own measured Carnot share (from __HOUSE_COP_DAYS__ days of daily COP), which falls from 0.35 in the cold to 0.21 in mild weather because the unit cannot turn down below about 1.5 kW and cycles. The model moves this house, unchanged, to each of the __TOWNS__ towns. It has no backup heater; any shortfall is charged at COP 1.

### 4.9 Validation

The model was tested against measured data at three levels before any national result was produced.

**The house against itself.** Run through its own year of weather and its own heating schedule, the model predicts a space-heating seasonal COP of __HOUSE_MODEL_SCOP__ against __HOUSE_MEASURED_SCOP__ measured on heatpumpmonitor.org over the same period. An earlier version over-predicted mild-weather efficiency by about a fifth; the measured 12–16 °C point was added to the house curve to correct it.

**The efficiency model against real systems.** Using each system's own flow and outdoor temperatures, the stock's efficiency model was tested on __LITMUS_SYSTEMS__ heat pumps within 25 km of __LITMUS_TOWNS__ of the map towns, from the coldest to the mildest, over two winters. Below 6 °C it matched within 5%; in mild weather real systems did 10–20% better, which is why the stock uses the fleet's fitted curve rather than the case-study house's.

**v1 against v2.** The national model was first built for a public map [@LDSMap2026]. The version used here reproduces that model's results to the third decimal place on SVR, IOG and Cosy. On Agile it corrects an error: the first version compared heat-per-penny as a ratio, which on the __AGILE_NEGATIVE_PCT__% of half-hours with negative prices chose gas when electricity was being given away. The correction raises the hybrid's Agile results, and all Agile figures here use it.

The controllers themselves are covered by known-answer tests: C-COP switches exactly at heat-per-penny parity, uses the heat pump at negative prices, the fixed bivalent rules ignore price, an extreme carbon price moves the choice to the lower-carbon source, grid-stress half-hours go to gas only under SD-Power dispatch, and only homes with a boiler pay the gas standing charge.

### 4.10 Reproducibility

The model, its inputs and its tests are held in LDS's repository; every number in this paper is generated from the model outputs by a script and inserted at build time, so the text cannot drift from the results. Each year's run records its arguments, software versions and timing. The full run covered __HOUSEDAYS_TOTAL__ house-days and __DECISIONS_TOTAL__ half-hourly decisions per tariff for each of __N_CONTROLLERS__ controllers.
