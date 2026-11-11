# Hybrid heat pumps, peak demand and flexibility: a review of the GB evidence

*Strand A: hybrid field trials. Strand B: peak electricity demand from electrified heat and the flexibility value of hybrids. All sources were read in full on 7 November 2026. Verbatim quotes and locators are in `hybrid_peak.json`.*

## 1. Why the peak, not the annual total, is the binding constraint

The GB literature agrees that electrifying domestic heat is governed less by annual energy than by the coincident cold-weather peak. The early whole-system estimates came from Sansom's synthesised half-hourly heat model. It put the UK's 2010 building heat peak "just above 330 GWth" and found that DECC Pathway 3 would add 57 GW of electrical heat peak in a normal winter and about 74 GW in a cold one, "a near doubling of electricity peak demand" (Sansom and Strbac 2012). The figure most often carried into policy was a 277 GW domestic heat peak attributed to Sansom.

Watson, Lomas and Buswell (2019) revised this using half-hourly gas data from more than 6,000 homes in the Energy Demand Research Project. They estimated a peak GB domestic heat demand of 159–170 GW and a maximum ramp of 60 GW/h, respectively about 40% and 50% below Sansom. The difference arises mainly because cold-day profiles are flatter than the single "peaky" profile used earlier. In a follow-up based on roughly 600 Renewable Heat Premium Payment (RHPP) heat pumps, Watson et al. (2021) showed that heat-pump heating patterns flatten demand further. In a cold year, peak heat falls to 157 GW and the ramp to 21 GW/h, even though annual heat rises 8% to 422 TWh. Watson's thesis converts this into electricity: 100% heat pumps would produce a 75 GW heat-pump electricity peak and take total GB demand from about 60 GW to 130 GW. Making all hot water and 20% of space heating flexible would bring that down to 109 GW (Watson 2019).

Love et al. (2017) supply the main empirical diversity figure. Across 696 RHPP heat pumps, After Diversity Maximum Demand (ADMD) was 1.7 kWe per site, and it occurred in the morning, whereas the national peak is in the evening. On first-order upscaling, 20% household uptake adds 7.5 GW (14%) to the evening peak.

Three points of agreement emerge. The heat peak is smaller than first feared. It is still large enough to roughly double system peak at full electrification. And its size depends heavily on how households operate heating. The disagreements are about method rather than sign. Sansom synthesised demand from assumed profiles; Watson and Love used measured profiles from samples that are not representative. RHPP homes were largely off-gas and social housing, a point Love et al. acknowledge. None of these studies runs more than a handful of weather years. Watson et al. use 2010 as the "cold" year, and the Imperial work tests adequacy against a stylised 1-in-20 cold week. The distribution of peaks across many winters is therefore asserted rather than measured.

## 2. What hybrids are claimed to do for the peak

The modelling literature is close to unanimous that a gas boiler kept for the coldest hours is a cheap way to avoid peak capacity. For the CCC, Strbac et al. (2018) found the Hybrid pathway cheapest in 2050 at GBP 81.6 bn/yr, against GBP 87.8 bn for Electric and GBP 89.6 bn for hydrogen at 30 MtCO2/yr. They also stress that the three are "within 10%" and that the ranking could change. The Electric pathway needs "about 100 GW" more firm generation, and the hybrid boiler "can efficiently reduce the need for distribution network reinforcement".

Vivid Economics and Imperial (2019) assume that hybrids "contribute little to the peakiness of electricity demand" because they "switch to gas mode during periods of high electricity demand". On that basis they estimate up to GBP 50 bn of extra distribution spend by 2035 for rapid EV and hybrid uptake, about 4% of total system cost. Element Energy (2017), modelling for BEIS, likewise found that hybrids "have the potential to significantly reduce the peak electricity demand compared to a standalone HP". That comparison assumes the standalone heat pump uses resistive backup, which makes it something of a straw man.

The system operator's framing is consistent with this. ESO's FES 2024 material notes that unmanaged electrified heat and transport "coincide with the morning and evening peaks", and it puts aggregated consumer flexibility at 70 GW (ESO 2024). FES 2025 now models heat-pump flexibility as within-day *load shifting* at constant daily energy (NESO 2025), not as *fuel switching*.

Measured all-electric flexibility is modest. In EQUINOX trial two, over 1,000 heat-pump homes on two-hour evening events delivered an average 0.6 kW turn-down per opted-in home (48% of their peak), with only 47% opting in per event (National Grid Electricity Distribution and Guidehouse 2024). This is the benchmark against which a hybrid's ability to drop to zero should be judged.

## 3. What the field trials actually found

**FREEDOM (Bridgend, 2017–18)** remains the only GB trial built around *smart, price- and constraint-aware* hybrid control. It ran 75 homes with small (5–8 kW) ASHPs added beside new combi boilers, and made no emitter or fabric changes (Wales & West Utilities, Western Power Distribution and PassivSystems 2018). It showed that fleet electricity demand could be cut "immediately and indefinitely" within 1–2 minutes. Whole-home load was held under a 0.75 kW per home cap, slightly above baseload peak, to within 0.1–0.2 kW, while still delivering about 50% of heat from the heat pump.

Two FREEDOM findings bear directly on the present article. First, at 2017–18 prices cost-optimal control "strongly favour[ed] gas". Heat-pump share reached about 50% only when gas prices were raised by 50%, whereas LPG homes moved about 80% of their heat to the heat pump. Second, the optimiser's preferred strategy was "continuously varying, gentle heat pump operation with bursts of gas boiler use". The report contrasts this with conventional switching on external temperature, which it calls "a relatively poor strategy". FREEDOM's network modelling put upgrade costs at about GBP 50 per customer per year for 100% ASHPs, against under GBP 5 for smart hybrids. Imperial's whole-system analysis for the project valued responsive hybrids at GBP 7.4–9.3 bn/yr over pure ASHPs. These are modelled, not observed, figures from a project that had commercial partners among its authors.

**The Electrification of Heat (EoH) demonstration** is the largest recent dataset. Its final median ASHP SPFH4 is 2.78 (n = 428; the interim figure was 2.80), against 2.44 under RHPP. Heat pumps *within* hybrids performed worse: median SPFH4 2.50 (n = 94), with the boiler excluded and not metered. They supplied a median of only 40% of space heating (IQR 30–56%), and SPF fell as their share fell (Energy Systems Catapult 2023; 2024).

The control method matters. Although EoH hybrids are described as "cost-optimal", the boiler takeover point "generally corresponded to a certain external temperature". In other words they ran a fixed bivalent point, and some had control faults that overused the boiler. This fits the 30–96% spread in heat-pump share that Element Energy (2017) compiled from earlier trials. It also fits Element Energy's modelled finding that emissions savings fall from 55% to 18% under twice-daily heating.

The Carbon Trust's evidence review for BEIS had already recommended a "floating (variable) bivalent point based on lowest cost, lowest emissions or lowest energy". It also recorded stakeholder estimates of only 0–5% running-cost savings over a good boiler (Carbon Trust and Rawlings 2016). The modellers note the same risk. In Imperial's optimised hybrid world, boilers supply only about 14% of heat at 30 Mt, and emissions "could increase substantially" if consumers use the boiler more than the model assumes (Strbac et al. 2018).

## 4. Tensions in the evidence

1. **Optimised versus deployed.** Whole-system studies credit hybrids with near-ideal dispatch: little gas off-peak and all gas at peak. Field hybrids under fixed-temperature switching deliver 40% heat-pump heat and a depressed SPF. The flexibility value is therefore asserted for a control regime that the largest trial did not use.
2. **Peak avoidance versus carbon and bills.** A switch tuned to prices may push heat onto gas when GB tariffs are skewed against electricity, as FREEDOM found at 2017–18 ratios. A switch tuned to carbon or peak avoidance may cost the household money. Element Energy (2017) explicitly flags this trade-off, but nobody quantifies it nationally across tariff regimes.
3. **Flexibility valued per kW.** No source reviewed gives an authoritative GB £/kW figure for avoided peak. The usable figures are FREEDOM's per-customer GBP 50 vs <GBP 5 a year, Vivid's GBP 50 bn total, and the LV substation unit costs in Delta-EE's Peak Heat cost–benefit analysis (Jamieson and Pieterse 2022). The last of these implies roughly GBP 200–380 per kVA of added transformer capacity, which is this review's derivation, not the source's. That analysis also shows that heat-pump-only flexibility (hot water, temperature, buffers) defers rather than avoids reinforcement.
4. **Representativeness.** RHPP (off-gas, social), FREEDOM (75 Bridgend homes, one winter) and EoH (homes pre-screened as suitable) are all small or selected samples of the on-gas stock in which a hybrid would actually be installed.

## 5. The gap this article can fill

No published GB study combines the following:

- **(i) Many weather years.** Existing peak estimates rest on one to three years (2003, 2010) or a stylised 1-in-20 week. An 86-year ERA5 record allows the *distribution* of cold-spell peaks and the frequency of the hybrid's peak-shaving role to be estimated rather than assumed.
- **(ii) A stock-wide sample calibrated to measured heat pumps.** Watson's and Love's profiles come from RHPP; Imperial's from assumed COPs. Calibration to heatpumpmonitor.org systems, set against EoH's 2.78 median, tests whether optimistic or field-typical performance drives the result.
- **(iii) A head-to-head of control rules.** The literature contrasts "smart" with "fixed bivalent" switching qualitatively (FREEDOM; Carbon Trust and Rawlings 2016), and EoH shows that deployed hybrids use a fixed bivalent point. No study isolates, at national scale, how much cost, carbon and peak benefit a price-ratio rule (heat pump when gas price ÷ boiler efficiency exceeds electricity price ÷ COP) adds over a fixed bivalent temperature. Nor has anyone shown how that benefit varies by town, tariff and winter severity.
- **(iv) Reconciling the household and system views.** The article can report the household bill, the carbon outcome and the coincident peak contribution of the same control rule. That would test directly whether the whole-system modellers' assumed hybrid dispatch is achievable by a household optimising its own bill.

If C-COP control drives heat-pump share well above EoH's 40% while still handing the coldest half-hours to gas, the article would supply the missing empirical-scale link between FREEDOM's single-winter demonstration and the 2050 system-cost claims of Strbac et al. (2018). If it does not, for example because GB price ratios push too much heat onto gas, the article would quantify the trade-off that Element Energy (2017) and Strbac et al. (2018) warn about but do not measure.

## References

Carbon Trust and Rawlings Support Services (2016) *Evidence Gathering – Low Carbon Heating Technologies: Domestic Hybrid Heat Pumps*. London: BEIS.

Element Energy (2017) *Hybrid Heat Pumps: Final report for BEIS*. Cambridge: Element Energy.

Energy Systems Catapult (2023) *Electrification of Heat Demonstration Project: Interim Heat Pump Performance Data Analysis Report*. Birmingham: ESC for DESNZ.

Energy Systems Catapult (2024) *Electrification of Heat Demonstration Project: Heat Pump Performance Data Analysis Report*. Birmingham: ESC for DESNZ.

ESO (2024) *Future Energy Scenarios: ESO Pathways to Net Zero – Energy consumer and demand side flexibility* [slides], 18 July.

Jamieson, T. and Pieterse, R. (2022) *Peak Heat WP5: Cost Benefit Analysis*. Delta Energy & Environment for Western Power Distribution.

Love, J. et al. (2017) 'The addition of heat pump electricity load profiles to GB electricity demand', *Applied Energy*, 204, pp. 332–342. doi:10.1016/j.apenergy.2017.07.026.

National Grid Electricity Distribution and Guidehouse (2024) *EQUINOX: Learning from trialling novel commercial methods* (Deliverable 4).

NESO (2025) *Modelling Methods: How we model FES*. July 2025.

Sansom, R. and Strbac, G. (2012) 'The impact of future heat demand pathways on the economics of low carbon heating systems', BIEE 9th Academic Conference, Oxford.

Strbac, G. et al. (2018) *Analysis of Alternative UK Heat Decarbonisation Pathways*. Imperial College London for the CCC.

Vivid Economics and Imperial College London (2019) *Accelerated electrification and the GB electricity system*. Report for the CCC.

Wales & West Utilities, Western Power Distribution and PassivSystems (2018) *Freedom Project Final Report*.

Watson, S.D. (2019) *Predicting the additional GB electricity demand resulting from a widespread uptake of domestic heat pumps*. PhD thesis, Loughborough University.

Watson, S.D., Lomas, K.J. and Buswell, R.A. (2019) 'Decarbonising domestic heating: What is the peak GB demand?', *Energy Policy*, 126, pp. 533–544. doi:10.1016/j.enpol.2018.11.001.

Watson, S.D., Lomas, K.J. and Buswell, R.A. (2021) 'How will heat pumps alter national half-hourly heat demands?', *Energy and Buildings*, 238, 110777. doi:10.1016/j.enbuild.2021.110777.
