## 3. Research questions

The questions and hypotheses below were written down on 7 November 2026. They are not a pre-registration: no registry holds them, and they were written after two earlier versions of the national model had produced public hybrid maps (Section 4.10), so the authors had seen national results for an earlier stock and controller set. They were written before any result of the model used here existed (version 3, whose stock, inputs and physics version 4 keeps; Section 4.10), and are reported as written, whether or not the results support them. The amendment below, made the same day, records the one change prompted by those earlier national results.

**RQ1: Cost and weather.** Across __N_YEARS__ real heating years, __TOWNS__ towns and a sampled housing stock, when does an orchestrated hybrid cost a household less over a year than an all-electric heat pump?

> *H1.* The weather year and the tariff matter more than location: the same town will favour the hybrid in hard winters and the heat pump in mild ones, and the tariff will move the answer more than moving from the south coast to the Midlands.

**RQ2: Software or hardware switching.** Does a price-aware software controller (C-COP) beat the fixed outdoor-temperature switch that hybrid controllers ship with today?

> *H2.* Yes, on both cost and carbon, because a fixed changeover temperature cannot follow half-hourly prices or the seasonal swings in the electricity-to-gas price ratio.

*Note added in revision (November 2026).* RQ2's premise is too broad as written: a fixed changeover temperature is the factory setting of many hybrids, not all. Daikin's integrated hybrid can compare stored gas and electricity prices (Section 1). The question and hypothesis are left as they were set; Section 5.2 reports what the distinction means for the results.

**RQ3: Carbon.** What does keeping the boiler cost in carbon, against an all-electric heat pump, under average and marginal grid intensity, today and on the grids projected for 2030 and 2035? Does a carbon-aware controller close the gap, and at what carbon price?

> *H3.* A cost-optimal hybrid emits more than an all-electric heat pump on today's average grid, and the gap widens as the grid decarbonises. A controller that prices carbon at the government's appraisal value closes most of it at a modest cost to the household.

**RQ4: Grid flexibility.** Scaled to Britain's gas-heated homes, what does an all-electric heat-pump stock do to the winter evening peak, against a hybrid stock and against hybrids dispatched by SD-Power to use gas during grid stress? How does that vary across __N_YEARS__ winters, including the hardest on record?

> *H4.* Hybrid stock removes most of the heat-driven increase in the coldest evening peaks, and SD-Power dispatch removes nearly all of it, at a small cost in carbon because the hours involved are few.

<div class="box" markdown="1">
#### Amendment, 7 November 2026

The national results of the earlier versions showed something the original design of RQ4 did not anticipate: on dynamic tariffs, price-aware control in every home synchronises, and the stock's heat-pump demand peaks *at the cheap times*, overnight and at dawn, not in the evening. The SD-Power dispatch was originally defined as "gas during the 16:00–19:00 peak on the coldest days", which those results showed to be the wrong target. It was redefined as a cap on Britain's total demand (Section 4.6). The new definition was fixed before the full run; one year (2010–11) was run first to check that it had been implemented correctly. H4 is tested against the redefined controller. The original definition and its results are kept in the model's history.
</div>
