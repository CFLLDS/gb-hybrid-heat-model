## 7. Limitations

Every model is a simplification, and the conclusions of this paper are only as strong as the simplifications allow. The most important are set out here, roughly in order of how much they could change the answer.

### 7.1 Today's prices on yesterday's weather

Every weather year is priced on the actual tariffs and grid carbon of 2025–26, matched by calendar day. This isolates the effect of weather, which is the point, but it means the model does not know what the prices *would* have been in a hard winter. In reality a cold snap raises wholesale prices: Agile would have been dearer on the coldest days of 2010–11 than on the same calendar days of 2025–26, which were mild. The model therefore understates the price of electricity exactly when a hybrid's boiler is most valuable, and so understates the hybrid's advantage in hard winters. The direction of this bias is known; its size is not.

### 7.2 Every home a price-taker

The model assumes that what each home does has no effect on the prices it faces. That is reasonable for one home and unreasonable for __GB_GAS_METERS__. If every gas-heated home in Britain ran a price-aware hybrid on Agile, the herd described in Section 5 would itself raise the prices of the half-hours it piles into, and part of the herd would dissolve. The herd peaks reported here are therefore an upper bound on what uncoordinated price response would produce. The case for SD-Power does not rest on the herd being as large as modelled; it rests on not having to rely on prices to undo a problem the prices created.

### 7.3 No thermal mass, no pre-heating

Each half-hour stands alone: heat is supplied when the home needs it, and nothing is stored in the building's fabric or in hot water ahead of a cheap window. This is the most important limit on the all-electric case. Real heat pumps on time-of-use tariffs pre-heat into cheap periods and coast through dear ones, which the case-study house does every night [@HPM454]. The model's all-heat-pump costs on Intelligent Octopus Go, Cosy and Agile are therefore pessimistic, and its comparisons on those tariffs favour the hybrid more than a well-run all-electric home would. On SVR, a flat tariff, pre-heating gains nothing and the comparison is fair. The same limit applies to SD-Power: a controller that could pre-heat ahead of a stress period would shed less to gas.

### 7.4 Weather at the town, not the house

ERA5 represents each town by a grid cell about 31 km across [@Hersbach2020]. Near the coast that cell includes sea air. Across the __TOWNS__ towns, ERA5's coldest 0.4% of hours over 1991–2020 is on average __ERA5_DESIGN_BIAS__ °C warmer than the station-based design temperatures used to size the heat pumps, and up to __ERA5_DESIGN_BIAS_MAX__ °C warmer at coastal towns. Over the 2025–26 heating season the archive also ran 0.4–0.9 °C warmer than the case-study house's own outdoor sensor. Two consequences follow. Heat pumps are sized for colder weather than the model then gives them, which is conservative for the all-electric case. And the coastal towns' weather is probably milder in the model than at the houses, which understates how often the hybrid wins there.

### 7.5 A sampled stock, not a surveyed one

The __HOMES_PER_TOWN__ homes in each town are drawn from ranges chosen to span British homes, not from a housing survey. Their results show the spread of outcomes and the direction of effects; the exact shares ("the hybrid wins for 61% of homes") depend on those ranges and should be read as indicative. The heat-pump efficiency level, drawn between the national field-trial median and the tuned systems on heatpumpmonitor.org, is the most influential of them; Section 5 reports how the main results move across it.

### 7.6 Gas meters are not gas-heated homes

National figures scale each region by its domestic gas meters, __GB_GAS_METERS__ in 2024 [@DESNZ2025_MSOA_Gas]. Some meters serve cooking only or empty homes; in England and Wales there are about 0.81 homes heated by mains gas alone per domestic meter [@ONS2021_TS046]. National peaks and totals on a gas-heated-homes basis are about a fifth lower than those reported on a meter basis, and both are given where it matters. Neither basis is a forecast of adoption: every national figure assumes *all* gas-heated homes adopt the controller in question, to show what each controller does to the system, not how many homes will choose it.

### 7.7 What is not counted

The comparison is of running costs only. Equipment, installation, maintenance and grants are excluded; so is the cost of keeping the gas network open for hybrid homes, which a full system comparison would have to include and which is significant [@Strbac2018]. Hot-water use follows a fixed daily pattern. Comfort is held as a floor in every case, so the model says nothing about homes that under-heat to save money, which are precisely the homes National Energy Action exists to help. The air-to-air results on the companion map use manufacturer efficiency, not measured data.

### 7.8 One controller rule, perfectly informed

The C-COP controller knows the current price and its heat pump's current efficiency exactly. Real controllers estimate both. The savings reported for software over a fixed switch are therefore an upper bound on what a real controller would capture, although the fixed-switch baselines are themselves generous: they assume an installer chose a sensible changeover temperature, and the Electrification of Heat trial found some hybrids with control faults that overused the boiler [@ESC2024].
