# GB hybrid heat model

The model, data preparation, analysis and article build behind **LDS Public Class No. 1: "Hiding the wiring again:
software-defined power, hybrid heating, and the cost, carbon and flexibility of keeping the boiler. Evidence from 86
British winters"** by Craig Lewis, LDS Consultancy. Version 1.0 of the paper (11 November 2026, DOI
https://doi.org/10.5281/zenodo.24133414) is at https://energy.ldsconsultancy.net/class/ and, as a PDF, among this release's assets.

It simulates one monitored house and 32,000 sampled homes in each of 79 towns across Great Britain, every half-hour of
every heating year from 1940-41 to 2025-26 (ERA5 weather), priced on the actual 2025-26 regional tariffs and grid
carbon, under ten heating controllers: all gas, all heat pump, fixed bivalent switches at 0, 2 and 5 C, a measured
switching rule from the Electrification of Heat trial, a price-aware C-COP controller, two carbon-aware variants, a
peak-avoiding variant and SD-Power dispatch (a cap on GB total demand). Model v4 (`scripts/spark/gbmodel`) produced
every number in the paper; each run's `run.json` records its arguments and the code version.

## Layout (the same paths as the private working repository, so every script runs unchanged)

| Path | What it holds |
|---|---|
| `scripts/spark/gbmodel/` | the JAX model: configuration, stock, physics, thermal store, controllers, diversity, run loop |
| `scripts/spark/gb_v2.py` | the entry point (one heating year, one town set); `gb_v4.sh` is the whole pipeline, stages A-G |
| `scripts/spark/v4x/` | the later stages: calibration (`cal*.sh`), weather-matched market (`matched.sh`), stage G digests (`rev4g.sh`, `rev4post.sh`), the trial-validation runs (`val.sh`), the feeder case (`feeder_runs.sh`), the three-day trace (`trace2010.sh`); stage H is `gb_h.sh` |
| `scripts/spark/gb_*_data.py`, `gb_base_demand.py`, `gb_national_scale.py`, `gb_v3_*.py`, `gb_wind.py`, `gb_wmatch.py` | data preparation from public sources (ERA5 via Open-Meteo, Octopus, NESO, DESNZ, ONS, heatpumpmonitor.org) |
| `scripts/spark/ukds/` | the UK Data Service studies: habits library and boiler-share curve from the Electrification of Heat trial, aggregates from EFUS 2011, Fuel Poverty 2023 and HBAI |
| `scripts/spark/gb_coincidence.py`, `feeder_case.py`, `lcl_*.py`, `ideal_gas.py`, `gb_feedback.py`, `gb_stagger.py` | the coincidence, feeder, Low Carbon London, ideal-gas-habits, price-feedback and stagger experiments |
| `scripts/article/` | results (`analysis.py`), sensitivities, burden, flexibility events, the review tests (`review_*.py`), validation against measured systems and the trial, the number register (`article_numbers.py`), the article build (`build.py`), figures, the claims ledger and the PDF |
| `scripts/article/crosscheck.py` | the independent second implementation in plain numpy (imports nothing from the model); `docs/article/crosscheck.json` is its last pass |
| `docs/article/sd_power_hybrid/` | the chapters (Markdown with `__NAME__` number slots and `[@Key]` citations), template, figures and the house animation |
| `docs/article/sources.json`, `docs/article/lit/` | every source cited, with the passages read from it; the literature syntheses |
| `docs/article/numbers.json`, `numbers_meta.json` | every number the prose quotes, and where each comes from |
| `docs/article/results/` | the results tables and digests the numbers are computed from (`diversity/`, `ukds/`) |
| `data/model/gb/` | small inputs: towns, region weights, national base demand, historic prices, stock metadata, the trial's habits library |
| `data/historic_energy_prices/` | the 1961-2025 price and income series and how they were built |
| `tests/` | known-answer tests for the controllers, inputs and thermal store (`python -m pytest tests/`) |

## Release assets

| Asset | Unpack at | Holds |
|---|---|---|
| `inputs.tar.gz` | repository root | the large inputs: 86 years of hourly ERA5 temperature for 79 towns (`history.npz`), the sampled stock (`stock_v3.npz`), weather, prices, carbon and wind by year, the 2016-24 price years, and the raw documents behind the historic price series |
| `model_outputs_v4.tar.gz` | repository root | the per-winter outputs of model v4 that the analysis reads: `data/model/v4/<year>/{stock_summary.csv, town_summary.csv, run.json, flex_region.npz}` for all 86 winters, plus the SD-Power second pass (`v4p2`, `v4p2c`), pre-heating (`v4pre`), half-sized hybrids (`v4_half`), levy cases (`v4_levy`) and the weather-matched market (`v4_matched`) |
| `hiding_the_wiring_again_v1.0.pdf` | | the paper, version 1.0 |

The 8,000-home stage G and H runs (price feedback, efficiency levels, weekday calendar, measured habits, measured
switching) and the validation and feeder runs are about 12 GB; their digests are in `docs/article/results/`, the
scripts that made them are here, and the raw outputs are available on request.

## Reproduce

1. **The article from its numbers** (no data needed): `python scripts/article/build.py` writes
   `docs/article/sd_power_hybrid/build/index.html`; `python scripts/article/ledger.py` lists what backs each sentence.
2. **Every number from the outputs**: unpack both tarballs at the repository root, then
   `python scripts/article/analysis.py --src data/model/v4`, `sensitivity.py --set v4`, `burden.py --src data/model/v4`,
   `flex_events.py --src data/model/v4`, `review_sdp.py`, `review_baseline.py`, `review_climate.py`, `review_adopt.py`,
   `validation.py`, `validation_eoh.py`, then `review_numbers.py`, `article_numbers.py --src data/model/v4` and
   `build.py`. `article_numbers.py` leaves out any number it cannot compute, so the build fails on it rather than
   printing a stale value. `crosscheck.py --src data/model/v4` reruns the second implementation.
3. **The outputs from the model**: `scripts/spark/Dockerfile` builds the image (NVIDIA PyTorch 25.09 base, JAX 0.12);
   `gb_v4.sh` runs stages A-G (12 sensitivity winters with the SD-Power second pass, the other 74 winters, 8,000-home
   reviews; about 7 minutes a winter on an NVIDIA DGX Spark, far longer on a CPU, where `--stock 2000` gives a
   quicker, noisier run), then `gb_h.sh`, `v4x/val.sh` and `v4x/feeder_runs.sh`. The data-preparation scripts
   rebuild every input in `inputs.tar.gz` from the public sources they name.

## Data licences

Code: MIT (`LICENSE`). Article text, figures and results: CC BY 4.0 (`LICENSE-TEXT`). Input data keep their own
licences: ERA5 (Copernicus, via Open-Meteo, CC BY 4.0), NESO data (NESO Open Data Licence), DESNZ and ONS statistics
(Open Government Licence v3.0), Octopus tariff data (published rates), heatpumpmonitor.org (public system data), Low
Carbon London (UK Power Networks, CC BY). The four UK Data Service studies:

| Study | DOI | Access | In this repository |
|---|---|---|---|
| Electrification of Heat Demonstration Project: Heat Pump Performance Data, 2020-2022 | https://doi.org/10.5255/UKDA-SN-9209-1 | open (OGL) | the habits library `data/model/gb/eoh_schedules.npz`, the boiler-share curve `eoh.json` and the aggregates in `docs/article/results/ukds/` |
| Energy Follow-Up Survey, 2011 | https://doi.org/10.5255/UKDA-SN-7471-3 | safeguarded | aggregates only (`efus.json`) |
| Fuel Poverty Dataset, 2023 | https://doi.org/10.5255/UKDA-SN-9466-1 | safeguarded | aggregates only (`fp2023.json`) |
| Households Below Average Income, 1961-1991 (Family Expenditure Survey) | https://doi.org/10.5255/UKDA-SN-3300-2 | safeguarded | aggregates only (`hbai.json`) |

The three safeguarded studies are used under the UK Data Service End User Licence and cannot be redistributed: no
record from them is here, only the aggregate statistics the paper quotes. Anyone registered with the service can
rerun `scripts/spark/ukds/` on their own copies.

## Cite

See `CITATION.cff`. Lewis, C. (2026) Hiding the wiring again: software-defined power, hybrid heating, and the cost,
carbon and flexibility of keeping the boiler. Evidence from 86 British winters. LDS Public Class No. 1, version 1.0.
https://doi.org/10.5281/zenodo.24133414
