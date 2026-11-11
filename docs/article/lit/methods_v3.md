# Methods v3: how comparable studies handled our five weaknesses

Compiled 7 November 2026. Every source cited here was downloaded and read on that date. Verbatim quotes, page locators and full Harvard references are in `methods_v3.json`; sources we could not fetch are listed there under `not_verified`. This note does not repeat `hybrid_peak.md` or `controls_flex.md`. Watson et al., Love et al., Freedom, Péan et al. and Strbac et al. are cited from those files.

## 1. Thermal mass and pre-heating

**What others did.** DESNZ's Home Energy Model (HEM), which replaces SAP, uses the full BS EN ISO 52016-1 heat balance. Each opaque element has five nodes, and air plus furniture are given a default 10,000 J/K per m² of floor area (DESNZ 2025, pp. 6, 9). The Python core is open, but it is far too heavy for 32,000 homes × 86 winters × 17,520 half-hours.

The national flexibility studies all use a first-order (1R1C) model:

- **Canet and Qadrdan (2023)**, Cardiff, England and Wales. Heat loss is EPC annual heat demand divided by heating degree-hours, for 16 dwelling categories in each of 34,753 LSOAs. Capacity is floor area × SAP 2012 "medium" (250 kJ/m²K) (p. 5).
- **Halloran, Lizana and McCulloch (2024)**, Oxford. They fit the same structure to DESNZ LSOA gas data. Median regional heat loss is 0.21 kW/K (1st–99th percentile 0.12–0.41), median capacity is 6.5 kWh/K, and the median time constant is 30.6 h.

The same Oxford paper reports a time constant of 22.8 h from the EPC-based method and 44.4 h from indoor-temperature fits in 742 Electrification of Heat homes, which skew towards larger houses (pp. 5–6). Two independent GB checks agree:

- **Crawley et al. (2022)** measured a mean 1.5 K fall in 3 h at a 15 K inside–outside difference in 193 homes. Our derived first-order time constant is about 28.5 h. Flats cooled more slowly than houses (1.43 K against 1.7 K).
- **Cornwall Insight's model for Nesta** assumes a 3 K fall over 5 h at a 20 K difference, which we derive as about 31 h (Cornwall Insight 2024, p. 8).

The practical consequence is in Halloran et al.: the median "heat-free" time is 5.9 h on a 20th-percentile winter day but only 3.6 h on extreme cold days (p. 1). Kelly, Tuohy and Hawkes (2014) show the cost of forcing a heat pump fully off-peak without fabric help: a 1,000 L buffer, and over 60% more electricity. The Imperial/EDRC brief (Yan et al. 2026) and the Catapult's Living Lab note (ESC 2026) back tariff-driven pre-heating but publish no parameters. We found no open 2R2C parameter set for GB dwelling types: the CREST paper could not be fetched.

**Recommendation.**

1. Add one lumped capacity per sampled home, C = 250 kJ/m²K × floor area (Canet and Qadrdan 2023, after SAP). Run SAP's "low" and "high" levels as sensitivities. Those two values were not read in this pass, so take them from SAP 2012 Table 1e before use.
2. Keep the existing heat-transfer coefficient H, so that τ = C/H.
3. Accept the stock only if its median τ falls between 23 and 44 h and is near 31 h. A flat-versus-house gap should appear unprompted.
4. Let the C-COP controller pre-heat inside a comfort band capped at 3 K (Halloran et al.'s window). Add a test that reproduces Crawley's 1.5 K / 3 h / ΔT 15 K result.
5. Report the extra kWh that pre-heating costs, since Kelly et al. show it is not free.

A 1R1C model is a known simplification: it ignores the fast air node and emitter mass. Name it as a limitation rather than adding a second node without GB data to fit it.

## 2. Price response and herding

**What others did.** The rebound or "avalanche" peak is well documented:

- **Kelly et al. (2014).** Shifting 50 simulated GB heat-pump homes wholly to Economy 10 off-peak raised the network peak by over 50% (p. 1).
- **Georges et al. (2016)**, Belgian stock RC model. Uncoordinated price response at 58% heat-pump penetration raised peak demand by 31%. Sending each home a copy of the price signal shifted by up to 1.5 h cut that to 19%, with unchanged savings (p. 9).
- **Element Energy (2014) for DECC.** Found "a distinct demand peak at the beginning of the night-time tariff rate" in the CLNR trial. It recommended staggering tariff periods (p. 7).
- **Pimm, Cockerill and Taylor (2018).** Found the same mechanism for batteries at LV substations.
- **Semmelmann et al. (2025).** Name it the "avalanche effect", test rotating and segmented grid charges, and publish open code.
- **De Paola, Angeli and Strbac (2018)**, the Imperial formal treatment. Price is an increasing function of aggregate demand, and the population schedule is a fixed point (a Nash equilibrium of a continuum of devices) that "avoids rebound peaks" (p. 6).

The only GB measurement of household price response for heat pumps is **Bernard et al. (2024)**, on Cosy Octopus. Its implied own-price elasticities are –2.5 off-peak and –0.8 at peak, and evening-peak use halved. The authors work at Octopus's Centre for Net Zero. **We found no study that quantifies national-scale herding on Agile in GB.** That is a gap the paper can name.

**Recommendation.** Add two layers and report both.

- **(a) Endogenous price.** Follow De Paola et al. Set W′ₜ = Wₜ + β·ΔDₜ, where ΔDₜ is the fleet's change in GB demand. Iterate the fleet schedule until it is consistent with the prices it produces. The slope β should be fitted by us, by regressing N2EX price on NESO demand. No published GB β was read.
- **(b) Diversity.** Give each home a random tariff-edge offset of 0–90 min (Georges et al.), plus the ≤10-minute randomised delay that SSES mandates (`controls_flex.md`).

Calibrate the ToU response so that a Cosy-like tariff halves the fleet's 16:00–19:00 use (Bernard et al. 2024). Report a "herding ratio": peak demand with price-following ÷ peak without. SD-Power's demand cap already bounds the worst case. The new result is how much of the C-COP saving survives once prices respond to the fleet.

## 3. Realistic housing stock

**What others did.** **Canet et al. (2022)** built LSOA-level stock data for England and Wales from the full EPC register: 16 categories (dwelling form × heating system), annual heat demand before and after efficiency measures, and floor area. Code is on GitHub and data on the UKERC Energy Data Centre.

EPC numbers are biased, however:

- **Few et al. (2023).** In 1,374 SERL homes, EPCs over-predict energy use by 8% in band C, rising to 48% in bands F–G. The gap persists in homes that match SAP's occupancy assumptions.
- **SMETER trial (BEIS 2022).** Against co-heating tests in 30 occupied homes (HTC 127–269 W/K), the expert RdSAP heat-transfer coefficient was almost unbiased (NMBE –2.8%, CVRMSE 18.2%), and the best smart-meter method reached a CVRMSE of 13.4%.

Taken together, the shape of the HTC from EPC inputs is usable, but energy use and the poor-band tail need correcting. Halloran et al. (2024) avoid EPCs by inverting metered LSOA gas against degree-days.

SERL (Webborn et al. 2021) links half-hourly gas and electricity to EPC inputs and ERA5 weather for over 13,000 homes. It is free to accredited researchers only.

**Recommendation.**

1. Draw each town's dwelling-form mix, floor-area distribution and EPC-derived heat demand from Canet et al.'s LSOA dataset, aggregated to the town's LSOAs.
2. Convert heat demand to HTC by dividing by SAP-region degree-hours, as Canet and Qadrdan (2023) do.
3. Deflate the HTC by band using Few et al.'s gaps. Then scale it per LSOA so that modelled annual gas matches DESNZ LSOA/MSOA metered gas, which is already in `region_data.json`. This is Halloran et al.'s method.
4. Validate the half-hourly shape against the SERL Statistical Data release and HeatpumpMonitor.

Canet's data cover England and Wales only. Scottish towns need EPC Scotland or Home Analytics, which we have not verified.

## 4. Capital costs and gas-network costs

**What others did.**

**Installed ASHP cost.**

- The BUS median is £13,041 in real terms, down 11% since 2022 (Shepheard 2026).
- By archetype, from MCS installs matched to EPCs (2021 to mid-2023, 2023 prices): flats £9,700, semi-detached and terraced houses £12,000, detached houses £14,000 (Kavan 2024).

**Hybrids.** No current official figure exists.

- The Delta-ee study for BEIS found that installers price a hybrid as "the sum of the cost of a gas boiler and a heat pump", sharing one cylinder and set of emitters.
- Its 2018 component costs (ex VAT) are an 8 kW ASHP at £8,750 excluding emitters and a regional combi swap at £2,700 (Delta-ee 2018, pp. 9, 11).
- The Carbon Trust (2016) gives hybrid product prices from under £2,000 to over £7,000.

**Gas network.**

- Gas-related regulated asset value (RAV, the investment consumers have not yet paid for) is about £26.1bn, written off over 45-year asset lives.
- Ofgem's own method divides depreciation plus return by forecast gas demand. In most FES scenarios this puts charges rising "significantly in the mid-2030s" (Ofgem 2023, pp. 67–70).
- Regen reads Ofgem's chart as about 10p/kWh by 2040 and 40p/kWh by 2050 (Hodgson 2024).
- Decommissioning could cost £46–74bn (Arup, cited by Salmon and Watson 2025).
- **Davis and Hausman (2021)** give the empirical shape for US utilities: losing 15% of customers adds about $30 a year to each remaining bill, and losing 90% adds over $1,500.

**Recommendation.**

1. Annuitise capex using Nesta's archetype medians for ASHPs. Price a hybrid as a smaller ASHP plus a combi, from Delta-ee's components inflated to 2025, and test against BUS medians.
2. Add an endogenous gas standing charge. Each year, per-customer network cost = (depreciation + return on £26.1bn RAV) ÷ remaining connected customers, using Ofgem's footnote-73 method.
3. Run it under each scenario's disconnection rate.

This is where hybrids differ structurally. They keep customers connected, which slows the spiral, but those customers then carry the standing charge. The paper should show both sides.

## 5. Multiple price years

**What others did.** **We found no published study that runs GB heat-pump or hybrid economics across many historical retail price years.** The nearest methods are:

- **Lyden et al. (2024).** Applied the Octopus Agile formula to PyPSA-GB wholesale prices for 2020 and 2035. Only the abstract was read.
- **Stute et al. (2024).** Kept one year's price shape (2019) and rescaled its mean and standard deviation to scenario levels.

The Agile formula is published: min(D × W + P, 95p). In 2019, the regional multiplier D was 2.0–2.4 and the 16:00–19:00 peak adder P was 11–14p (Steele 2019). D and P change over time, and the Octopus API exposes current values per region.

Open wholesale archives are short:

- **NESO's N2EX file.** Hourly, starting 20 September 2021 (our download).
- **Elexon's market-index data.** Half-hourly, starting between September and November 2016 (our probe).

**Recommendation.**

1. Reconstruct Agile for each heating year from 2016-17 to 2025-26 from Elexon market-index prices. Hold today's regional D and P fixed, so that only wholesale variation enters.
2. Scale Cosy, IOG and SVR by each year's Ofgem cap ratio to the 2025-26 cap, and take gas from the same caps.
3. Run two designs: matched weather-and-price years for 2016–2025, and the full 86 weather years × N price years grid, so that the paper can separate price-year from weather-year effects.
4. Use Stute-style rescaling only for stress cases, such as 2022 crisis prices with today's shape.

## Comparable published studies

| Study | Resolution | Weather years | Stock basis | Open code / data | Dataset links |
|---|---|---|---|---|---|
| Watson, Lomas and Buswell 2019, 2021 (see `hybrid_peak.json`) | half-hourly | a few, with 2010 as cold year | EDRP gas, RHPP heat pumps | no / no | — |
| Deakin et al. 2021 | hourly (daily gas proxy) | 30 winters, 1990–2020, MERRA-2 | NDM gas demand as heat proxy | not stated / no | MERRA-2 |
| Charitopoulos et al. 2023 | hourly, 13 LDZs | gas data 2015–2018 | LDZ gas demand | on request / yes | doi:10.5281/zenodo.6022815 |
| Canet et al. 2022; Canet and Qadrdan 2023 | half-hourly profiles | typical year | full EPC register, LSOA × 16 categories | yes / yes | github.com/AlexandreLab/UKERC-data; UKERC EDC |
| Halloran, Lizana and McCulloch 2024 | daily (1R1C) | 2010–2022 | DESNZ LSOA gas, EPC, EoH | yes (GeoHeatFlex, MIT) / public inputs | DESNZ sub-national gas; EoH (UKDS) |
| Zeyen, Hagenmeyer and Brown 2021 | hourly, Europe incl. GB, hybrids | one year (+ SI sensitivity) | 9 building categories × 7 construction periods | yes (PyPSA-Eur-Sec) / yes | ERA5 |
| Ruhnau, Hirth and Praktiknjo 2019 (When2Heat) | hourly, 16 countries | 2008–2018, ERA-Interim | population-weighted, gas load profiles | yes / yes | data.open-power-system-data.org/when2heat |
| Kelly, Tuohy and Hawkes 2014 | ESP-r dynamic simulation | one cold week | 1 detached house × 50, randomised use | no / no | — |
| Georges et al. 2016 | RC stock model (time step not checked) | not checked | Belgian stock, 58% heat pumps | no / no | — |
| Semmelmann et al. 2025 | LV grid simulation (time step not checked) | not checked | empirical household and heat-pump load | yes / yes | github.com/leloq/dynamic-tariffs-in-distribution-grids |
| Bernard et al. 2024 | smart-meter panel | 2022–2024 (observed) | Octopus heat-pump customers | no / no | — |
| Lyden et al. 2024 (abstract only) | power-system model | 2020, 2035 snapshots | — | PyPSA-GB is open (not checked) / — | — |

None of these combines more than about 30 weather years with a priced, stock-resolved hybrid controller. That is the paper's opening, provided the five fixes above are made.
