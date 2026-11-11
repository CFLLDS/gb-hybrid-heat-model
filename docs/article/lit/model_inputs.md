# Model inputs: evidence for the sampled home parameters

Compiled 2026-11-07. Every source was downloaded and read; quotes, locators and Harvard references are in `model_inputs.json`. Figures marked "derived" are our arithmetic on the source's numbers.

## 1. Is the DESNZ calibration target weather-corrected? Yes, but not to a Met Office normal

DESNZ sub-national domestic gas (the MSOA/LSOA, LA and regional series) is **weather corrected**: "Gas consumption figures have been weather corrected" (DESNZ 2026, Table 1, p. 6). The correction belongs to Xoserve and is applied to each meter's Annual Quantity (AQ): "Xoserve adjust the AQ using a weather correction factor which accounts for regional temperature and wind speed and incorporates trends" (DESNZ 2026, s. 2.2).

- **Normal used.** The AQ is consumption "for a 365-day year, under seasonal normal weather conditions" (DECC 2014). That is the gas industry's own seasonal normal composite weather variable (CWV, temperature plus wind) for each LDZ. It is "based on historical weather adjusted for forecast warming of the UK climate". The basis in the 2020 methodology "represents the average climate conditions expected in 2015-2020" and is built from daily history since October 1960 (National Grid 2020, App. A1.2, A1.4). The basis is reviewed "every five years or so" (DECC 2014). Whether a newer basis applied to the 2024/25 AQs is **not verified**.
- **Reference period.** The "2024" data cover **mid-May 2024 to mid-May 2025** (DESNZ workbook cover sheet; booklet Table 2).
- **Meter basis.** AQs come from two reads 6–18 months apart. Stale AQs are carried forward (2 million meters in 2019/20). "Domestic" means AQ below 73,200 kWh, so some small businesses are counted (DESNZ 2026, s. 2.1.2).
- **Size of the correction.** DESNZ also publishes non-weather-corrected LA/regional tables for 2015–2024. For GB in 2024 the mean domestic gas per meter is 11,359 kWh weather corrected and 10,745 kWh actual, so the corrected figure is 5.7% higher (2024/25 was milder than seasonal normal). Across 2015–2024 the ratio ran from 0.963 to 1.062 (derived).

**Consequence for `gb_v3_calibrate.py`.** Its docstring says DESNZ gas "is compared with 1991-2020 normal weather". That is wrong. Calibrate either (a) the weather-corrected target against a normal-climate weather year, or (b) the target × (non-corrected ÷ corrected) for the region (GB 0.946) against actual May 2024–May 2025 weather. The non-corrected series stops at LA level, so MSOA targets need the LA or regional ratio.

## 2–5. Parameters

| Parameter | Current assumption | Evidence | Recommended distribution | Source |
|---|---|---|---|---|
| Boiler seasonal efficiency η (gross CV) | U(0.85, 0.92), mean 0.885 | Measured over a year in 43 homes: combi 82.5% (SD 4.0, range 68.6–89.7); regular 85.3% (SD 2.5) at the boiler, about 80.3% with cylinder losses; rated SEDBUK about 90.4%. SAP default for a post-1998 condensing boiler is 84% (gross) | **N(0.84, 0.035) truncated [0.72, 0.91]**, applied to space heat + hot water | EST 2009 (Orr et al.); SAP 10.2 Table 4b, Table E4 |
| Hot water (heat out of the boiler) | U(2, 8) kWh/day, two 2-h reheats | 122 L/day mean (±18); volume = 46 + 26N L/day; 16.8 MJ = **4.67 kWh/day at the tap**; temperature rise 36.7 K; combi homes 142 L vs regular 116 L. SAP 2012: 25N + 36 L/day, ΔT 37 K, +15% distribution loss. SAP 10.2 gives about 6.4–7.1 kWh/day at the tap for 70–90 m² (derived) | **4.18·(46+26N)·36.7/3600 × 1.15 × LN(0, 0.4)**: mean about 5.3 kWh/day at N = 2.4, 5–95% range about 2.5–10. Reheat timing 08–10 and 18–23 (regular boilers, 2.6 h/day) | EST 2008; SAP 2012 App. J, Table 1d; SAP 10.2 App. J |
| Indoor temperature (`tset`, constant 24 h, whole house) | U(19, 21.5), mean 20.25 | Thermostat set point: mean 20.4, median 20, IQR 19–21 (EFUS 2011 IQR 18–21). **Measured** winter living-room means 18.3–19.3 (EPC A–D 18.6–19.3; F–G 17.2; pre-1919 17.7); bedrooms 0.5 K and halls 0.4 K cooler; coldest 10% below 15.7. SAP: 21 °C living, elsewhere 21 − 0.5·HLP (not a flat 18), heated 07–09 and 16–23 | **N(18.8, 1.0) truncated [16, 21.5]**, about 1 K lower for EPC E–G or pre-1919. Keep U(19, 21) only if `tset` is a thermostat set point with intermittent heating and setback | EFUS 2017 heating-patterns, thermal-comfort and fuel-poverty reports; SAP 10.2 Table 9 |
| Mean internal gains | U(250, 700) W | SAP 10.2 typical gains: metabolic 60N, cooking 35+7N, losses −40N, appliances 207.8(TFA·N)^0.4714 kWh/yr, lighting (App. L), water-heating gains. Totals about **360 W (50 m²), 465 (70), 545 (90), 620 (120)** (derived) | **SAP total for the record's floor area × U(0.75, 1.25)** | SAP 10.2 s. 5, Table 5, App. L |
| Gains daily profile | 0.7 / 1.1 / 0.8 / 1.3 / 1.0 | No published profile fetched. The SAP heating periods (07–09, 16–23) and EST hot-water timing match its morning and evening peaks | Keep the profile, but label it an assumption | none (not verified) |

## Where the current assumptions sit outside the evidence

1. **η is about 4 points too high.** Every measured mean (80–85%) and the SAP default (84%) fall at or below the bottom of U(0.85, 0.92). Because the stock is calibrated to metered gas, a higher η implies more delivered heat per kWh of gas, so the HTC multiplier comes out about 5% high. That inflates heat demand and therefore the heat-pump electricity that a hybrid displaces.
2. **`tset` is about 1.5 K too warm as a 24-hour whole-house mean.** EFUS's 19–21 is a reported thermostat setting; measured living-room means are about 19, and the rest of the house is cooler. The calibration absorbs the annual level through HTC, but a warm `tset` raises the balance point. That puts too much heat into the shoulder months and too little into cold days relative to the mean, which matters for COP weighting and peak.
3. **The weather normal is misstated.** The target is a gas-industry seasonal normal (2015–20 climate, temperature plus wind), not 1991–2020. Matching it with a single price-year's weather (2025–26 or the 2010–11 switch) is not like-for-like. Use the corrected/non-corrected ratio, or normal-year weather.
4. **Hot-water spread.** The mean of U(2, 8) is close to the evidence (about 5.3 kWh/day). But the floor of 2 is below what even a one-person home draws on SAP or EST equations, the ceiling of 8 cuts off large households, and the value is not tied to occupancy.
5. **Gains** are consistent in level for a 70–90 m² home but should scale with floor area. Their profile is unsourced.

## Not verified

The seasonal-normal basis that applied to the 2024/25 AQs; the CV basis of DESNZ kWh (gross by convention); newer in-use boiler studies (no Boiler Plus efficiency evaluation found; the 2010 TPI-extension tables were not read); the PCDB distribution; EFUS 2011 primary reports; CIBSE TM59 or Guide A profiles; EoH and HeatpumpMonitor hot-water energy; a labelling inconsistency between SAP 10.2 equations L16 and L16a (typical gains used here). Details are in `not_verified` in the JSON.
