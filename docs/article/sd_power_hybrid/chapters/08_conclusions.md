## 8. Conclusions and recommendations

This paper set out to replace the assumed hybrid of British energy policy with a controlled one, and to measure, for the same control rule, what it does to the household's bill, the climate's carbon and the grid's peak, across every winter since 1940. Its contribution is not a general case for hybrid heating. It is that a household's choice of heat source interacts with heat-pump efficiency, tariff design, carbon and the national peak, and that flexible control has to be judged separately from the heating it controls. Five conclusions follow from the results. Each is stated no more strongly than the evidence supports.

**1. Whether keeping the boiler lowers the running cost is decided by prices more than by place or weather.** In this design the tariff explains __VAR_TARIFF_PCT__% of the variation in the hybrid's winning share, the winter __VAR_YEAR_PCT__% and the town __VAR_TOWN_PCT__%; the share is a property of the four tariffs chosen, and falls to __VAR_TARIFF_NOIOG_PCT__% without IOG, so it is not a general law. Underneath the tariff is the electricity-to-gas price ratio, which the 2026 levy changes brought below the break-even point for a typical home, and the gas standing charge of about £__GAS_SC_GBP_YEAR__ a year that a hybrid must save more than to win. At today's prices the all-electric heat pump is the cheaper one to run for most homes on a flat tariff in most winters; on tariffs with dear daytime electricity, the hybrid is, so long as the all-electric home cannot store heat to avoid the dear hours (with pre-heating, __REV_PRE_HYB_IOG__% on IOG). On Agile, whose price follows the wholesale market, the headline runs understate the hybrid's case: over twelve test winters it wins __REV4_WM_HYB_CAL_AGILE__% of homes when each historic day is priced on the same date in 2025–26, but __REV4_WM_HYB_AGILE__% when it is priced on a recent day as cold. How well the heat pump is commissioned matters as much: over twelve test winters the hybrid's winning share on SVR runs from __REV_COP_HI_HYB_SVR__% for a stock as well tuned as the best-monitored systems to __REV_COP_LO_HYB_SVR__% at the national field-trial median, against __REV_COP_MID_HYB_SVR__% in the central case, so where heat pumps are well commissioned the all-electric home is the cheaper to run for almost every household on a flat tariff.

**2. Software control is worth having, but its objective matters more than its existence.** A price-aware controller saves every hybrid household money against a fixed changeover temperature, the factory setting of many hybrids, on every tariff, and in the same breath burns more gas. On a flat tariff the saving is mostly the value of setting the changeover point correctly, a commissioning task; software adds what no fixed setting can only where prices move within the day. Controllers that compare stored prices already capture much of that saving on flat and fixed time-of-use tariffs; what is new is following half-hourly prices, keeping prices current, pricing carbon and coordinating homes. Given a carbon price at the government's appraisal value, it removes most of that penalty for tens of pounds a year.

**3. Smart heating, left to itself, herds.** Price-aware controllers in millions of homes, seeing the same price, synchronise, and when they share one dynamic tariff they move the peak rather than remove it; pre-heating moves it further. In the model, a synchronised stress case, coordinated dispatch that sends a small share of homes to gas when Britain's total demand would exceed a cap removes the herd above that cap, by construction: __HERD_EXCESS_AGILE_GW__ GW from the worst-winter peak on Agile, for about £__SDP_COST_AGILE_MEAN__ a home a year in fuel. That is an idealised result against a chosen cap, in a stress case whose homes are far more synchronised than real ones; spreading their timing by up to two hours leaves __REV_STAG_W120_HERD_AGILE_GW__ GW, and over twelve winters heating habits measured in real homes shrink the herd from __REV_DSDP_B_AGILE_IDEAL_GW__ to __REV_DSDP_D_AGILE_IDEAL_GW__ GW, with __REV_DSDP_AGILE_GWH_CUT_PCT__% less heat moved to gas. Delivered with imperfect participation, forecasts and compliance, dispatch scheduled ahead still takes about __REV_SDP_AGILE_SCHEDULED_REAL_GW__ GW off but breaches the cap in every winter, by up to __REV_SDP_AGILE_SCHEDULED_REAL_MAXOVER_GW__ GW; dispatch in reaction takes __REV_SDP_AGILE_REALISTIC_GW__ GW. The herd is far smaller when homes are spread across tariffs, and the £__SDP_COST_AGILE_MEAN__ is the household's extra fuel only, not the cost of communications, incentives, verification or the network.

**4. The hybrid is a bridge with a carbon cost that rises as the grid gets cleaner.** On today's grid it emits __KG_GAP_CCOP_HP_NOW_SVR__ kg a year more than a heat pump, on the 2035 grid __KG_GAP_CCOP_HP_2035_SVR__ kg. Where it has a case, it rests on what coordinated control lets it save the electricity system at the peak and on the insurance it gives households against a bad winter, a bad price ratio or a poorly performing heat pump, not on its own emissions.

**5. The choice of fuel has been a hedge against bad years.** At the prices of each winter since 1961, a typical home with a C-COP hybrid would have paid less to heat than with an all-electric heat pump in __BURDEN_P10_CCOP_LOWEST_YEARS__ of __BURDEN_P10_YEARS__ winters, and never more than with gas alone, which it can always fall back on; measured against the income at the upper boundary of the poorest tenth, it had the lowest worst-year burden of the three. This is a finding about exposure to fuel prices, not a model of fuel-poor homes, their housing or their circumstances.

### Recommendations

These follow from the results and the limitations together. They are offered as evidence for decisions others must make, and are addressed to the bodies that make them.

**For the Department for Energy Security and Net Zero and Ofgem, in the load-control licence.**

- Specify what a licensed controller of a hybrid may optimise, not only who may hold it. A default objective that prices carbon at the government's appraisal value, with the household able to choose otherwise, would remove most of the hybrid's carbon penalty.
- Provide for coordinated dispatch against a system-level cap, scheduled ahead of the published prices that trigger herding, and treat a randomised start delay as insufficient protection against herding by automated heating on dynamic tariffs.
- Do not let the cost of a carbon-aware default fall on households in fuel poverty.

**For the National Energy System Operator and network operators.**

- Count a hybrid's switch to gas in a stress period as flexibility, and pay for it, through the Demand Flexibility Service, local flexibility markets or their successors. The schemes that pay households today reward batteries, not heat.
- Plan for automated domestic heat to synchronise on dynamic tariffs, and treat uncoordinated peaks from price-responsive heat as a planning case.

**For policy on prices.**

- Recognise that rebalancing policy costs between electricity and gas decides, almost alone, whether hybrids pay households, and that the 2026 changes have already moved Britain to the break-even point.

**For manufacturers and installers.**

- Ship hybrids with price-aware control that reads the tariff itself, half-hourly where the tariff is, rather than a fixed changeover temperature or prices typed in by the householder, with a carbon setting and an interface for coordinated dispatch.
- Commission heat pumps, in hybrids and alone, to the performance of the best-monitored systems, and measure it: on a flat tariff that decides, more than any other input here, whether keeping the boiler pays.
- Make the affordability case for a hybrid, as for a heat pump, at standard rates, with time-of-use savings as an addition that depends on automation, as the Committee on Fuel Poverty recommends [@Rivers2026CFP, p. 6].

**For research.**

- Model the feedback of a herd on the prices that cause it with a market, not a fixed slope: the simple feedback run here moves the herd between half-hours without settling, which says little about where a market would settle.
- Test the herd against measured half-hourly demand from many homes on time-of-use tariffs; the modelled homes are far more synchronised than real ones.
- Measure the efficiency level of the installed stock, home by home: it decides the household verdict on flat and dynamic tariffs more than any other input.
- Cost the gas network that hybrid homes would keep open, and decide who pays as its customers fall.
- Test coordinated dispatch in occupied homes at scale, as Freedom did for 75 homes [@Sun2019SmartHHP].
- Validate the half-hourly shape and diversity of heat-pump demand against measured data from many homes; every national peak here rests on them.
- Model fuel poverty with households stratified by income and housing, under a stated fuel-poverty definition, rather than a typical home set against low incomes.
- Compare hybrids and all-electric heat pumps over their whole life, with equipment, installation, servicing and replacement, not running costs alone.

The model, its inputs, every number in this paper and the independent check of its arithmetic are published with it, so that each of these conclusions can be tested, and corrected, by others.
