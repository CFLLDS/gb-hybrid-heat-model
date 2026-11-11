# Controls, demand-side flexibility and the SD-WAN analogy

*Literature strand for "Hiding the wiring again". Sources accessed 7 November 2026. Full quotes, locators and references are in `controls_flex.json`.*

## 1. What a hybrid controller is asked to decide

A hybrid must decide continuously which heat source to run, yet the formal anchor for that decision is capacity, not cost. Commission Regulation (EU) No 813/2013 defines the bivalent temperature as the outdoor temperature at which the heat pump's declared capacity "equals the part load for heating and below which the declared capacity for heating requires supplementary capacity" (European Commission 2013, Annex I(39)). For the average European climate it sets this at no warmer than +2 °C against a design temperature of −10 °C (European Commission 2013, Annex III, Table 4). In Britain, MCS now admits hybrids under MIS 3005-D if the heat pump covers at least 55% of the design heat load at a 55 °C flow temperature. Its only control requirement is that "the controls' philosophy shall be capable of prioritising the heat pump" (MCS 2024). Nothing in either instrument requires the switching rule to respond to price, carbon or grid conditions.

## 2. What manufacturers ship

Each controller offers some price-aware mode, but the economics are frozen into static parameters set once by an installer or householder.

- **Vaillant.** The sensoCOMFORT hybrid manager offers "triVAI" (tariff-based) or "Bivalence pt" (outdoor temperature). Its factory setting is bivalence point, with heating changeover at 0 °C, domestic hot water at −7 °C, and the "alternative point", where the heat pump stops altogether, set to Off (Vaillant Group UK 2024, pp. 17–18). Vaillant's own guidance, counter-intuitively, recommends the tariff mode "if minimal information present".
- **Daikin.** The integrated Altherma H Hybrid offers an "Economical" mode, which chooses gas or electricity "based on energy prices", or an "Ecological" mode, which uses a fixed primary energy factor of 2.5 for electricity (Daikin Europe 2026, p. 146). With a third-party boiler the logic reverts to a temperature rule: a bivalent ON temperature bounded by installer parameters [C‑03] and [C‑03]+[C‑04], with a fixed 3 K hysteresis. [C‑03] is read off a chart from a break-even COP of (electricity price ÷ gas price) × boiler efficiency. The worked example gives a COP of 3 and a changeover of 2.5 °C (Daikin Europe 2026, pp. 162–163). The UK user guide has householders re-enter prices after any tariff change, with three electricity price bands on a timer (Daikin UK 2021, p. 6).
- **Mitsubishi Electric.** The Ecodan FTC4 offers Ambient, Cost or CO2 priority. Each mode falls back to an outdoor-temperature changeover, and prices and emission factors are entered by hand. Switching can also be forced by "external input from power supplier" (Mitsubishi Electric n.d., p. 2).
- **Ideal.** The Logic Air Hybrid describes its strategy as "Bivalent Point/Tariff", with the heat pump as system master (Ideal Heating 2026).

No default could be verified for Worcester Bosch, Ideal or Mitsubishi (see `not_verified`). The verified default (Vaillant 0 °C) and worked example (Daikin 2.5 °C) sit near the regulatory +2 °C ceiling: fixed numbers set at commissioning, against prices that now change every half-hour.

## 3. Predictive and price-responsive control

Péan, Salom and Costa-Castelló (2019) classify supervisory heat-pump control into rule-based control (RBC) and model predictive control (MPC), "given the clear differences in their concept and complexity". They find that in MPC "the monetary objective (reduction of the energy costs) has been the most utilized". They also find the building's own thermal mass "more cost-effective than water buffer tanks" as flexible storage (Péan, Salom and Costa-Castelló 2019, abstract). (Only the abstract was read.)

The most directly relevant GB evidence comes from the Freedom Project, run by Western Power Distribution and Wales & West Utilities with PassivSystems in 75 Bridgend homes. It set predictive optimisation of running costs, with pre-heating ahead of occupancy, against "traditional hybrid systems that simply switch fuel based on external temperature" (WPD and WWU 2018, p. 6). Three findings matter here. First, on mains gas "fuel switching was determined economically … rather than because the heat pump no longer had enough heating capacity", and 5 kW heat pumps were enough for most homes (p. 22). Second, optimised hybrids reached a median SPF of 3.60, because the controller used the heat pump only when it was efficient to do so (p. 22), which matters for any commercial-COP metric. Third, and most important for grid-aware dispatch, heat-pump demand "can be reliably reduced to less than 20W per home within a few minutes … without impacting occupant comfort", with the gas network absorbing the shift. A 54-home portfolio was capped to within 0.1–0.2 kW per home (pp. 15, 22). The predictive controller made "quantitative trade-offs between storing heat in the fabric … the additional heat losses incurred and any discomfort" (p. 25). That is close to a comfort-constrained cost minimisation. But Freedom was a single 2017–18 winter, and its authors concede that the pre-warming strategy was not tested head-to-head against outdoor-temperature switching (p. 22).

For heat-pump-only homes, Nesta and the Centre for Net Zero ran a randomised trial in February 2024: 30 events across 43 households, each holding heat pumps down for four hours. They reported a statistically significant 32% (0.123 kWh) reduction in consumption during the flexibility period, with temperatures kept within a comfortable range and householders "happy with the automation" (Nesta 2024).

## 4. GB demand flexibility in practice

The ESO's Demand Flexibility Service (DFS) is the largest GB test of household turn-down.

| Winter | Participants | Delivered | Spend | Price |
|---|---|---|---|---|
| 2022/23 | over 1.6 million households and businesses, 31 providers, 22 events | about 3,300 MWh | about £11.1m | average £3,000/MWh (tests), £4,559/MWh (live) |
| 2023/24 | 2.6 million meters (99% domestic), 48 providers, 14 tests and 2 live events | over 3.7 GWh, peak over 400 MW | £11.9m | average accepted bid £1,110.9/MWh in competitive tests |

Sources: National Grid ESO (2023, pp. 3–4) for 2022/23; National Grid ESO (2024, p. 4) for 2023/24.

Over 99% of participants were "Manually Initiated", and the ESO infers that 91% of domestic delivery came from reductions of 1 kW or less: "manual flexing/reducing actions as opposed to any significant level of EV/heat pump participation" (National Grid ESO 2024, pp. 4, 25). Octopus's Saving Sessions, which ran through DFS, illustrate the same consumer-led model. In the first session, over 200,000 households cut demand by 108 MW, an average reduction of 59% (Octopus Energy 2022). Across 13 sessions in 2022/23, Octopus customers shifted 1.86 GWh and were paid £5.3m (Martins 2023). Households respond to price signals, but almost entirely by hand; automated dispatch of heat, which Freedom showed to be straightforward for hybrids, barely featured.

Under market-wide half-hourly settlement (MHHS), Elexon expected about 80% of meters (around 25.9 million) to be migrated by October 2026 (Elexon 2026). The final programme milestone cuts reconciliation to seven months from 1 October 2026 and to four months from 1 April 2027 (MHHS Programme 2026). DESNZ expects MHHS to push suppliers towards "more dynamic, price-sensitive tariffs and services" (DESNZ 2026, p. 7).

## 5. Who holds the controller: SSES

The Smart Secure Electricity Systems (SSES) programme is the regulatory answer to SD-Power's central question. Its April 2025 response (DESNZ 2025):

- It estimates 10–12 GW of consumer-led flexibility is possible by 2030 (p. 6).
- It mandates smart functionality for electric heating, with ETSI EN 303 645 cyber security and an aggregate randomised delay of up to 10 minutes against herding (p. 7).
- It creates a single load control licence covering both the sending of control signals and the contracting with consumers (p. 8).
- For hybrids specifically, it attaches the mandate to the "common controller, or 'master controller'", leaving the gas boiler out of scope (p. 18).
- It requires suppliers to publish machine-readable time-of-use tariff data under the Retail Energy Code by mid-to-late 2026 (p. 9).

The 2026 licensing response sets the timetable (DESNZ 2026). Regulations will be laid in autumn 2026, applications open in March 2027, and holding a licence becomes mandatory in March 2028 (p. 9). Device smart-functionality requirements apply from 31 December 2027 (p. 7). Load controllers managing 300 MW or more also fall under the NIS Regulations (DESNZ 2025, p. 8). The consumer's right to override is placed on the manufacturer's interface rather than written in as a licence term (DESNZ 2026, p. 52). Citizens Advice (2026) warns that "essential services such as heating must not become difficult to manage or understand" under automation. It flags people "who need predictable warmth", which is in substance the comfort-floor argument.

## 6. The SD-WAN definition

MEF 70.1 defines an SD-WAN service as "an overlay connectivity service that optimizes transport of IP Packets over one or more Underlay Connectivity Services by recognizing applications (Application Flows) and determining forwarding behavior by applying Policies to them" (MEF Forum 2021, s.3). The provider "monitors the performance of the available forwarding options and modifies how packets in each Application Flow are forwarded" (s.6). Cost (flat-rate or usage-based) is an explicit attribute of each underlay, and disparate underlays deliver "cost benefits, resiliency, and differentiated transport" (pp. 16–17). Notably, the standard defines only the externally visible service. Management and orchestration, and so the controller itself, are expressly outside its normative scope (s.6.1).

## 7. The gap

The literature and the market leave three gaps open.

1. **The deployed rule is fixed.** Shipped controllers use a fixed temperature or static price ratio. The MPC literature (Péan, Salom and Costa-Castelló 2019) and Freedom show that predictive, cost-aware control is feasible, but no GB study verified here quantifies, across many homes and winters, what fixed bivalent switching leaves behind in cost and carbon against a half-hourly price-aware controller.
2. **Gas fallback is unquantified as a grid asset.** Freedom showed that grid-aware fuel switching works physically. Yet GB flexibility markets still deliver almost entirely through manual action, and no source verified here values the gas fallback as a grid asset alongside its carbon cost.
3. **Regulation does not specify the controller's objective.** SSES specifies who may hold the controller and how securely, not what it should optimise. In particular, it does not say whether comfort is a hard constraint or a tradeable variable.

The article fills these gaps. It compares a price- and grid-aware controller with fixed bivalent switching across 86 British winters, with comfort held as a floor and outcomes measured in heat per penny.

## 8. How SD-Power maps onto, and departs from, the formal SD-WAN definition

**Where it maps.** Heat sources (heat pump, boiler, fabric) are underlays with explicit cost attributes, as in MEF. The controller monitors prices, COP and carbon, and re-steers continuously, with policy set by class of demand.

**Where it departs.**

- **Comfort is a constraint.** MEF policies tune how flows are forwarded; the comfort floor decides whether demand is served at all, closer to an admission guarantee.
- **Heat can be stored.** Packets cannot be; heat can be pre-loaded into the fabric, so the controller schedules over time as well as across paths. That makes it MPC rather than path selection.
- **The controller is the point.** MEF leaves orchestration non-normative; SD-Power's argument is about who holds the controller, which SSES licensing governs.
- **"Overlay" differs.** In MEF it is the subscriber's virtual network; in SD-Power it is a vendor-neutral description of each home's flexibility, closer to the SSES interoperability standard.
