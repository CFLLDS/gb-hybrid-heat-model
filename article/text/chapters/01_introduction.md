<div class="abstract" markdown="1">
## Abstract

__ABSTRACT__

<p class="keywords"><b>Keywords:</b> hybrid heat pump; bivalent control; software-defined power; demand flexibility; grid carbon intensity; peak demand; ERA5; Great Britain</p>
</div>

<nav class="toc noprint" markdown="1">
**Contents**

1. [Introduction: the wiring is back](#1-introduction-the-wiring-is-back)
2. [What we know, and what we do not](#2-what-we-know-and-what-we-do-not)
3. [Research questions](#3-research-questions)
4. [Method](#4-method)
5. [Results](#5-results)
6. [Discussion](#6-discussion)
7. [Limitations](#7-limitations)
8. [Conclusions and recommendations](#8-conclusions-and-recommendations)
</nav>

## 1. Introduction: the wiring is back

In a short film that still circulates among energy people, an Olympic track cyclist tries to power a domestic toaster. He is one of the strongest sprinters of his generation. The toaster needs about 700 watts. By the end he is spent and the bread is barely brown [@Lewis2026Olympian]. The point of the film is not the cyclist. It is how completely the electricity system has hidden from us the work it does. For a century the engineers who built Britain's grid "hid the wiring": they made supply so large, so central and so reliable that a household never had to think about where its power came from, when, or at what cost [@Lewis2026Olympian].

Electrification is pulling the wiring back into the home. A household that replaces its gas boiler with a heat pump, adds a battery, takes a half-hourly tariff and puts panels on the roof has, without meaning to, become a systems integrator. It now owns decisions the grid used to make for it: which source of heat to use, when to store energy and when to spend it, and how to trade comfort against cost against carbon, every half-hour. Most households are not equipped to make those decisions and should not have to be. This paper is about the software that could make them instead, and about one specific decision where that software matters more than anywhere else: whether to keep the gas boiler.

### The hybrid question

A hybrid heating system pairs an air-source heat pump with a gas boiler, usually the one already on the wall. British policy has moved firmly against it. The Climate Change Committee's Seventh Carbon Budget does not consider fossil-fuel hybrids at all [@CCC2025_7CB, p. 163]; the National Energy System Operator's 2025 Future Energy Scenarios state that natural-gas hybrids are "no longer installed, as they are not net zero compliant" [@NESO2025_FES_Pathways, p. 103]; and the Boiler Upgrade Scheme will not fund any system that combines a heat pump with fossil-fuel heating [@Ofgem_BUS_installers]. Yet the same scenarios still have roughly 19.5 million homes with a gas boiler in 2035, even in the fastest pathway [@NESO2025_FES_Workbook, sheet F.45]. The boiler is not leaving most British homes this decade. The practical question is what it should be allowed to do while it is there.

The case for the hybrid has always rested on an assumption about its control. In the Sixth Carbon Budget the CCC assumed that hybrids "can operate in heat pump mode up to 80% of the time" and found that at 50% they become "significantly less cost effective" [@CCC2020_6CB_Buildings, p. 29]. That 80% was an input, fixed outside the model. It was not the result of any controller responding to prices, weather or the state of the grid. The whole-system studies that found hybrids the cheapest route to decarbonised heat assumed near-ideal dispatch: little gas off-peak, all gas at the peak [@Strbac2018]. The largest recent field trial found something different. In the Electrification of Heat demonstration the heat pumps inside hybrids supplied a median of only 40% of space heating, at a median efficiency of 2.50, and their switch to the boiler "generally corresponded to a certain external temperature" [@ESC2024]. Manufacturers' controllers ship with exactly that kind of rule: a fixed outdoor changeover temperature, set once at commissioning, against tariffs that now change every half-hour [@Vaillant2024Top10; @Daikin2026IRG].

The gap between the hybrid that was modelled and the hybrid that was installed is a gap in software. That is the subject of this paper.

### Software-defined power

I use the term **SD-Power**, a working name for the next stage of LDS's Levant platform [@Lewis2026Olympian], for a software layer that hides the wiring again. It borrows its structure from software-defined wide-area networking (SD-WAN), which solved a similar problem for corporate networks fifteen years ago. SD-WAN is defined as "an overlay connectivity service that optimizes transport of IP Packets over one or more Underlay Connectivity Services by recognizing applications … and determining forwarding behavior by applying Policies to them" [@MEF2021_70_1, s. 3]. It did not make cheap internet links better. It made them usable, by putting a controller in charge of which link carried which traffic [@Lewis2026Olympian].

Mapped onto a home, SD-Power has three layers:

- **the underlay**: the physical home and its connections: meter, tariff, heat pump, boiler, battery, and the thermal mass of the building itself;
- **the overlay**: a description of each home's flexibility, expressed the same way whoever made the equipment;
- **the controller**: one place where the decision is made, each half-hour, about which source serves which demand.

The analogy breaks in one important place. SD-WAN puts applications first; SD-Power must put people first. Comfort is the floor, not the variable [@Lewis2026Olympian]. The controller may choose how heat is made, never whether the house is warm. Its success is measured not in raw efficiency but in what I have called the *commercial coefficient of performance* (C-COP): useful heat per penny, relative to what the same heat would cost from gas.

A hybrid is the simplest possible SD-Power system: two underlays (a heat pump and a boiler), one demand (heat), and a single decision to make each half-hour. If software cannot add value there, it is unlikely to add value anywhere in the home. If it can, the question is how much, for whom, in which weather, and at what cost to the climate and the grid.

### What this paper does

This paper builds a national model of that decision and runs it through every heating year in the modern weather record. It simulates __HOMES_PER_TOWN__ sampled homes in each of __TOWNS__ towns from Penzance to Wick, half-hour by half-hour, through __N_YEARS__ real heating years from __FIRST_YEAR__ to __LAST_YEAR__: __HOUSEDAYS_TOTAL__ house-days and __DECISIONS_TOTAL__ heating decisions per tariff. Every simulated day is priced on the actual regional half-hourly tariffs and grid carbon intensity of the same calendar day in 2025–26. The heat pumps are calibrated to __HPM_SYSTEMS__ measured British systems on heatpumpmonitor.org and bounded below by the national field-trial median. One monitored house, my own in Poole, anchors the calibration and serves as a case study.

The model compares the controllers a hybrid could run: the fixed outdoor-temperature switch that ships today, a price-aware C-COP controller, a carbon-aware variant that adds a price on CO₂, and an SD-Power dispatch that also keeps Britain's total electricity demand under a cap by sending a share of homes to gas when the system is stretched. It reports what each does to the household bill, to emissions under average and marginal grid carbon, and to the winter electricity peak scaled to Britain's gas-heated homes.

The contribution is threefold. First, it replaces the assumed hybrid of the policy literature with a controlled one, and measures the difference. Second, it turns one or two "cold years" into a distribution of __N_YEARS__, so that statements about hard winters become statements of probability. Third, it reports the household's bill, the climate's carbon and the grid's peak for the *same* control rule, which is the test the whole-system literature has assumed but not carried out.

The rest of the paper is organised as follows. Section 2 reviews the evidence on hybrid trials, peak demand, carbon accounting and control. Section 3 states the research questions and hypotheses, which were written down before the national results existed. Section 4 describes the model and how it was validated. Section 5 presents the results, closing with the monitored house. Section 6 discusses what they mean for policy and for who should hold the controller; Section 7 sets out the limitations; Section 8 concludes.
