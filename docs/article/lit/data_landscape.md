# Data landscape for model v3

Accessed 2026-11-07. Every entry in `data_landscape.json` (34 records) comes from a page or API we fetched, and each one carries a `verified_quote`. Where we could not confirm something, the entry says UNVERIFIED. Nothing was registered for, applied for or submitted.

**Who has to act** is marked in each line:

- **[OPEN]**: download it now, with no account.
- **[LOGIN]**: Craig needs a free account.
- **[UKDS-EUL]**: free UK Data Service registration plus acceptance of the End User Licence.
- **[SECURE]**: an application to the UKDS SecureLab.
- **[PAY]**: costs money.

## Headline

**Craig must:**

1. Create a GOV.UK One Login account for EPC data.
2. Register with the UK Data Service, for SERL statistical data and EHS.
3. Optionally apply for SERL Secure Access.

Nothing has to be bought. The paid property APIs add little over EPC and NEED, which are free.

## (a) Realistic housing stock

1. **NEED anonymised data 2026 [OPEN]**. This is the top pick. It has 4 million dwelling records (a 50k version also exists), and each record has:
   - type, age band, floor-area band, region and EPC band;
   - flags and dates for loft insulation, cavity wall insulation and PV;
   - main heating fuel;
   - **metered annual gas and electricity for 2005-2024**.

   It replaces sampled ranges with an empirical joint distribution, and it gives measured gas use to calibrate heat loss against.
   - Catch: England & Wales only. Location is region, not town. Data is annual.
2. **EPC bulk data, England & Wales [LOGIN]**. You need a GOV.UK One Login account, and there is no fee. Data runs from 2008 and includes:
   - floor area;
   - wall, roof and glazing descriptions;
   - heating system;
   - the local authority, which lets us build per-town stock.

   Catches:
   - the register is "not a true representation" of the whole stock;
   - certificates are duplicated;
   - address fields are restricted to energy-efficiency purposes.
3. **Scottish domestic EPC to Q3 2026 [OPEN]**. Covers the Scottish towns. It contains current certificates from Q4 2016.
4. **OS Open UPRN [OPEN]**. Coordinates for about 40 million UPRNs. We can geolocate EPC records to towns with it, so AddressBase is not needed. AddressBase reaches end of life in Autumn 2027.
5. **Canet et al. 2022 LSOA heat demand (UKERC EDC) [OPEN]**. Gives stock and heat demand per LSOA, plus ASHP and boiler half-hourly profiles. Use it as a comparator and benchmark.
6. **English Housing Survey stock data, e.g. 2022 SN 9314 [UKDS-EUL]**. Weighted national distributions. Since 2014 the Safeguarded version holds derived variables only. We did not verify whether it includes heat loss. The raw physical survey needs a Special Licence.
7. **Paid APIs: not recommended.** All prices exclude VAT.
   - **Homedata [PAY]**: 100 tokens = £1. Most calls cost 1 token; a full profile costs 50. The first top-up is matched 100%. It is EPC, Land Registry and OS joined on the UPRN, for England & Wales only, and redistribution is restricted.
   - **PropertyData [PAY]**: from £30/month for 2,000 credits, up to £200/month for 50,000.

   Neither adds stock attributes beyond EPC + NEED, and neither prices national coverage sensibly. GetTheData has no bulk stock data.

## (b) Thermal mass

1. **SMETER TEST Phase 2 [OPEN, CC BY 4.0]**. 30 homes with:
   - co-heating-measured heat transfer coefficients (HTCs) and airtightness;
   - floor plans;
   - 30-minute gas, electricity and room temperatures, plus local weather.

   We can fit each home's time constant and effective capacitance against a known HTC. The catch is that it is 30 homes from one housing association.
2. **SAP 10.2 Tables 1e/1f [OPEN]**. Heat capacity (kappa) per construction, and the TMP = Σκ·A / total floor area (TFA) definition. Map EPC construction descriptions onto these values.
3. **HEM-TP-07 (DESNZ, Oct 2025, OGL) [OPEN]**. The thermal-mass method used in the Home Energy Model, the government's dynamic model.
4. Our own fits from HeatpumpMonitor and the house's cool-downs remain the measured cross-check.

## (c) Price history

1. **Elexon Insights API [OPEN]**. Covers MID, system prices and FUELHH, with an open licence and attribution required. **Our probe found MID only from October 2016 and FUELHH from January 2016**, so the API does **not** reach 2001.
2. **Older MID and system prices** now sit behind a **BSC Portal login**. Whether non-BSC-parties can get one, and how far back MID goes, are UNVERIFIED. This is **Craig's call to Elexon**.
3. **Nord Pool (N2EX) [PAY]**. Price not published. Only worth it if the BSC Portal route fails.
4. **Octopus API [OPEN]**. Agile half-hourly rates from **21 Feb 2018** (verified) for all regions, no key needed.
5. **Agile formula [OPEN]**. Octopus publishes `D + (W × X)` with a £1 cap. D and X are higher from 16:00 to 19:00. Fit D and X per region on 2018-2026 MID against the Agile API, then back-cast "Agile-equivalent" prices to 2016. Wholesale data reaching further back is still needed.
6. **Ofgem price cap levels and annexes [OPEN]**. Flat retail rates from 2019. Annex 2/3/4 cover the wholesale, network and policy components. Pre-2019 retail prices would need DESNZ QEP tables, which we did not fetch.

## (d) Carbon and demand, more years

1. **NESO Historic Demand Data [OPEN, NESO Open Data Licence]**. Half-hourly national demand **from 2001** (we verified the 2001 file). It covers every weather year, including 2010-11.
2. **NESO historic generation mix and carbon intensity [OPEN]**. Half-hourly national carbon intensity and fuel mix **from 1 Jan 2009**.
3. **Carbon Intensity API, regional [OPEN, CC BY 4.0]**. The page says regional data starts 2017-09-26. Our probe got regional data from May 2018. Earlier regional values would need to be reconstructed from national figures.

## (e) Capital costs

1. **BUS statistics [OPEN]**. Monthly, latest September 2026. Gives the installed cost of BUS ASHPs.
2. **MCS Data Dashboard [OPEN, but manual]**. Free, with an "Installation Cost" section and exports. It is a JavaScript app, so the exports have to be clicked by hand. Bespoke data goes through an MCS request form; Craig must ask MCS.
3. **DESNZ/Delta-EE 2020 cost study [OPEN]**. Component costs for ASHPs and boilers, which lets us build a hybrid from smaller-ASHP plus boiler costs. Prices are 2020, so they need inflating.
4. **HeatpumpMonitor**. Only 51 systems have an installation cost, so it is a weak source here.

## (f) Gas network costs

1. **Ofgem cap Annex 3 (gas) [OPEN]**. Network cost allowance per region inside the gas standing charge and unit rate. This is the most direct source.
2. **RIIO-GD2 PCFM / AIP [OPEN]**. Allowed revenue per gas distribution network (GDN). We found it via search only and did not open the model.
3. **DUoS charging statements**. UNVERIFIED: the DNO pages we tried returned 404. Use Ofgem Annex 3 (electricity) instead.

## (g) Validation homes and heat pumps

1. **Electrification of Heat, SN 9050 / 9209 / 9210 [OPEN via UKDS]**. Monitored heat pumps from about 742 files' worth of homes, Nov 2020 to Sep 2023. SN 9209 is at 30-minute resolution. This is the top pick for validation.
2. **HeatpumpMonitor public JSON [OPEN, CC BY 4.0]**. 864 systems, 765 of them with measured heat loss. Only 3 are flagged hybrid.
3. **SERL Statistical Data SN 8963 [UKDS-EUL]**. Aggregated half-hourly gas and electricity by dwelling type, heating system and weather for 2020-2023, from about 13,000 homes. It validates demand shapes without needing SecureLab.
4. **SERL Observatory SN 8666 [SECURE]**. Half-hourly per-home data. It needs:
   - a UKDS SecureLab application;
   - an organisational countersignature on the user agreement;
   - training;
   - access from an approved device or a SafePod.

   This is optional and slow, and it is Craig's application to make. serl.ac.uk blocked our fetch, so we did not read SERL's own eligibility rules.
5. **RHPP SN 8151**. About 700 heat pumps from 2013-15. The access level is unverified. Lower priority.
6. **Low Carbon London [OPEN]**. Electricity only, 2011-14. Low priority.

## Acquisition order for v3

1. Open downloads today:
   - NEED 4M;
   - NESO demand 2001-2026 and generation mix 2009+;
   - Elexon API 2016+;
   - Octopus Agile 2018+;
   - Ofgem cap annexes;
   - SMETER;
   - EoH 9050/9209;
   - HeatpumpMonitor;
   - OS Open UPRN;
   - BUS;
   - the Delta-EE study;
   - Canet LSOA data.
2. Craig: create a GOV.UK One Login account, then do the EPC bulk download for England & Wales.
3. Craig: register with UKDS, then get SERL SN 8963 and EHS stock data.
4. Craig: ask Elexon about BSC Portal access to pre-2016 MID and system prices. Only if that is refused, request a Nord Pool quote.
5. Optional: apply for SERL Secure Access (SN 8666).
