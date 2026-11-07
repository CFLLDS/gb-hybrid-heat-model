# GB hybrid heat model

The model, data preparation, analysis and article build behind **LDS Public Class No. 1: "Hiding the wiring again:
software-defined power, hybrid heating, and the cost, carbon and flexibility of keeping the boiler. Evidence from 86
British winters"** by Craig Lewis, LDS Consultancy.

It simulates one monitored house and 32,000 sampled homes in each of 79 towns across Great Britain, every half-hour
of every heating year from 1940–41 to 2025–26 (ERA5 weather), priced on the actual 2025–26 regional tariffs and grid
carbon, under ten heating controllers: all gas, all heat pump, fixed bivalent switches at 0, 2 and 5 °C, a price-aware
C-COP controller, two carbon-aware variants, a peak-avoiding variant and SD-Power dispatch (a cap on GB total demand).

## Layout

| Folder | What it holds |
|---|---|
| `model/` | the JAX model (`gbmodel/`), its entry point `gb_v2.py`, the SD-Power second pass, run scripts |
| `data_prep/` | fetch and build every input from public sources (ERA5 via Open-Meteo, Octopus, NESO, DESNZ) |
| `data/` | small inputs: towns and design temperatures, gas meters per region, national demand |
| `results/` | the analysed results tables the article quotes |
| `analysis/` | results, flexibility events, validation, and the number register |
| `article/` | the article's chapters, figures, literature register (every source with the quotes read from it), claims ledger and build |
| `tests/` | known-answer tests for the controllers |

## Reproduce

1. `python data_prep/gb_history_data.py` builds `history.npz` (86 years of hourly ERA5 temperature for 79 towns; or
   download it from this repository's release assets). `gb_year_data.py`, `gb_base_demand.py` and `gb_national_scale.py`
   build the prices, carbon, national demand and gas-meter weights.
2. `python model/gb_v2.py --weather 1962 --data data --out out/v2/1962` runs one heating year (about 3 minutes on an
   NVIDIA DGX Spark; much longer on a CPU, where `--stock 2000` gives a quicker, noisier run). `run_history.sh` runs all
   years; `run_pass2.sh` adds SD-Power dispatch.
3. `python analysis/analysis.py`, `analysis/flex_events.py`, `analysis/article_numbers.py`, then `article/build.py` to
   rebuild the article; every number in it comes from the outputs, and `article/ledger.py` lists what backs each claim.

Tests: `python -m pytest tests/`.

## Licence

Code: MIT (`LICENSE`). Article text, figures and results: CC BY 4.0 (`LICENSE-TEXT`). Input data keep their own
licences: ERA5 (Copernicus, via Open-Meteo, CC BY 4.0), NESO data (NESO Open Data Licence), DESNZ and ONS statistics
(Open Government Licence v3.0), Octopus tariff data (published rates), heatpumpmonitor.org (public system data).

## Cite

See `CITATION.cff`.
