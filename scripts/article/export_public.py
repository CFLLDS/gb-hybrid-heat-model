#!/usr/bin/env python3
"""Assemble the PUBLIC repository CFLLDS/gb-hybrid-heat-model from this private one (Craig, 7 Nov 2026: open source,
"credibility in the club"; 11 Nov 2026: "build the reproduction package", release v1.0.0). Code MIT, text CC BY 4.0.

Files are copied to the SAME relative paths they have here, so every script runs unchanged (each finds the repo root
as parents[2] of its own path). Writes a fresh tree to ../gb-hybrid-heat-model (or --dest), then scans every file for
secrets and private details and FAILS if it finds any. Never copies state/, logs/ (except the one HPM fit file), keys,
the house's minute logs or anything outside the explicit list below. Large inputs and the model's per-winter outputs
are NOT copied into the tree: --assets packs them into <dest>/release/ as the tarballs attached to the GitHub release.
UK Data Service: SN 9209 (Electrification of Heat) is open and its derived habits library is included; SN 7471, 9466
and 3300 are safeguarded and only the aggregates in docs/article/results/ukds/ leave this machine.
    .venv/bin/python scripts/article/export_public.py [--dest DIR] [--assets]
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEST = Path(sys.argv[sys.argv.index("--dest") + 1]) if "--dest" in sys.argv else ROOT.parent / "gb-hybrid-heat-model"
VERSION, DATE = "1.0.0", "2026-11-11"
SPARK_PY = ["gb_v2.py", "gb_sdp_phi.py", "gb_trace.py", "gb_feedback.py", "gb_coincidence.py", "gb_stagger.py",
            "gb_spf_cal.py", "gb_wind.py", "gb_wmatch.py", "gb_v3_stock.py", "gb_v3_calibrate.py", "gb_v3_prices.py",
            "gb_v3_epc_check.py", "gb_div_digest.py", "gb_h_digest.py", "gb_v4_digest.py", "review_spark.py",
            "ideal_gas.py", "feeder_case.py", "lcl_base.py", "lcl_dtou.py", "gb_history_data.py", "gb_year_data.py",
            "gb_base_demand.py", "gb_national_scale.py", "gb_hist_pack.py", "probe.py"]
SPARK_SH = ["gb_v4.sh", "gb_v3_final.sh", "gb_v3_pre.sh", "gb_div.sh", "gb_h.sh", "gb_review.sh", "gb_sens.sh",
            "gb_v2_history.sh", "gb_v21_pass2.sh", "gb_history_run.sh", "run_queue.sh"]
ARTICLE_PY = ["analysis.py", "article_numbers.py", "build.py", "burden.py", "crosscheck.py", "figures.py", "flex_events.py",
              "hbai_income.py", "hybrid_house.py", "ledger.py", "make_pdf.py", "pdf_paginate.py", "review_adopt.py",
              "review_baseline.py", "review_climate.py", "review_numbers.py", "review_sdp.py", "sensitivity.py",
              "sources_merge.py", "three_days.py", "validation.py", "validation_eoh.py", "export_public.py"]
FILES = ([f"scripts/spark/{f}" for f in SPARK_PY + SPARK_SH] + ["scripts/spark/gbmodel", "scripts/spark/ukds",
         "scripts/spark/v4x", "scripts/spark/Dockerfile"]
         + [f"scripts/article/{f}" for f in ARTICLE_PY]
         + ["tests/test_gb_controllers.py", "tests/test_gb_inputs.py", "tests/test_gb_thermal.py"]
         + ["docs/article/sd_power_hybrid/chapters", "docs/article/sd_power_hybrid/template.html",
            "docs/article/sd_power_hybrid/figures", "docs/article/sd_power_hybrid/house", "docs/article/lit",
            "docs/article/sources.json", "docs/article/numbers.json", "docs/article/numbers_meta.json",
            "docs/article/validation.json", "docs/article/crosscheck.json", "docs/article/data/trace_2010.json",
            "docs/article/results"]
         + [f"data/model/gb/{f}" for f in ("towns.json", "region_weights.json", "base_demand.json", "hist_prices.json",
                                            "stock_v3_meta.json", "eoh.json", "eoh_schedules.npz", "ideal_schedules.npz")]
         + ["data/model/results", "data/historic_energy_prices", "logs/hpm_shares_20261106.json"])
# release assets: the inputs the scripts read that are too large for the tree, and the per-winter model outputs
ASSET_INPUTS = ([f"data/model/gb/{f}" for f in ("history.npz", "stock_v3.npz", "weather.json", "weather_year.json",
                                                 "weather_year2010.json", "prices_year.json", "prices_current.json",
                                                 "carbon_year.json", "carbon_winter.json", "wind.json", "years")]
                + ["data/historic_energy_prices/raw"])
ASSET_OUTPUTS = [f"data/model/{d}" for d in ("v4", "v4p2", "v4p2c", "v4pre", "v4_half", "v4_levy", "v4_matched")]
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "build", "raw", "*.xlsx~")
SCRUB = [(re.compile(r"dna@100\.110\.154\.69:?\S*"), "<your-gpu-host>:<path>"),
         (re.compile(r"\b100\.\d+\.\d+\.\d+\b"), "<host>"), (re.compile(r"\b192\.168\.\d+\.\d+\b"), "<lan-host>")]
DENY = re.compile(r"(api[_-]?key\s*[=:]\s*['\"][A-Za-z0-9]{12,}|gho_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|BEGIN [A-Z ]*PRIVATE KEY|"
                  r"password\s*[=:]\s*['\"][^'\"]{4,}|bearer\s+[A-Za-z0-9._\-]{20,}|[A-Za-z0-9._-]+@ldsconsultancy\.com|tailscale|"
                  r"state/octopus\.key|cflha\.|\.spark_vllm)", re.I)
TEXT = {".py", ".sh", ".md", ".json", ".html", ".csv", ".txt", ".cff", ".js", ".css", ""}


def copy():
    if DEST.exists():
        for p in DEST.iterdir():
            if p.name not in (".git", "release"):
                shutil.rmtree(p) if p.is_dir() else p.unlink()
    DEST.mkdir(parents=True, exist_ok=True)
    for rel in FILES:
        s, d = ROOT / rel, DEST / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        if s.is_dir():
            shutil.copytree(s, d, ignore=IGNORE)
        elif s.exists():
            shutil.copy2(s, d)
        else:
            print(f"missing (skipped): {rel}")
    for p in list(DEST.rglob("results_v2_backup_*")):
        shutil.rmtree(p)


def scrub_and_scan():
    bad = []
    for p in DEST.rglob("*"):
        if p.is_file() and p.suffix in TEXT and ".git" not in p.parts and "release" not in p.parts and p.name != "export_public.py":
            t = p.read_text(errors="ignore")
            for rx, rep in SCRUB:
                t = rx.sub(rep, t)
            p.write_text(t)
            for m in DENY.finditer(t):
                bad.append(f"{p.relative_to(DEST)}: …{t[max(0, m.start() - 30):m.end() + 10]!r}")
    return bad


def assets():
    rel = DEST / "release"
    rel.mkdir(exist_ok=True)
    for name, paths in (("inputs", ASSET_INPUTS), ("model_outputs_v4", ASSET_OUTPUTS)):
        have = [p for p in paths if (ROOT / p).exists()]
        out = rel / f"{name}.tar.gz"
        subprocess.run(["tar", "--exclude=__pycache__", "-czf", str(out), "-C", str(ROOT)] + have, check=True)
        print(f"{out.name}: {out.stat().st_size / 1e6:.0f} MB from {len(have)} paths")
    pdf = ROOT / "docs" / "article" / "sd_power_hybrid" / "build" / "paper_draft.pdf"
    if pdf.exists():
        shutil.copy2(pdf, rel / "hiding_the_wiring_again_v1.0.pdf")


def ukds_lines():
    src = json.load(open(ROOT / "docs" / "article" / "sources.json"))
    src = src.get("sources", src)
    rows = (("UKDS9209", "Electrification of Heat Demonstration Project: Heat Pump Performance Data, 2020-2022", "open (OGL)",
             "the habits library `data/model/gb/eoh_schedules.npz`, the boiler-share curve `eoh.json` and the aggregates in `docs/article/results/ukds/`"),
            ("UKDS7471", "Energy Follow-Up Survey, 2011", "safeguarded", "aggregates only (`efus.json`)"),
            ("UKDS9466", "Fuel Poverty Dataset, 2023", "safeguarded", "aggregates only (`fp2023.json`)"),
            ("UKDS3300", "Households Below Average Income, 1961-1991 (Family Expenditure Survey)", "safeguarded", "aggregates only (`hbai.json`)"))
    return "\n".join(f"| {t} | https://doi.org/{src[k]['doi']} | {lic} | {what} |" for k, t, lic, what in rows)


README = """# GB hybrid heat model

The model, data preparation, analysis and article build behind **LDS Public Class No. 1: "Hiding the wiring again:
software-defined power, hybrid heating, and the cost, carbon and flexibility of keeping the boiler. Evidence from 86
British winters"** by Craig Lewis, LDS Consultancy. Version 1.0 of the paper (11 November 2026) is at
https://energy.ldsconsultancy.net/class/ and, as a PDF, among this release's assets.

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
%(ukds)s

The three safeguarded studies are used under the UK Data Service End User Licence and cannot be redistributed: no
record from them is here, only the aggregate statistics the paper quotes. Anyone registered with the service can
rerun `scripts/spark/ukds/` on their own copies.

## Cite

See `CITATION.cff`. Lewis, C. (2026) Hiding the wiring again: software-defined power, hybrid heating, and the cost,
carbon and flexibility of keeping the boiler. Evidence from 86 British winters. LDS Public Class No. 1, version 1.0.
"""

MIT = """MIT License

Copyright (c) 2026 LDS Consulting Limited

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

CCBY = """The article text, figures and results tables in this repository (docs/article/, including the literature
syntheses and results) are licensed under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
To view a copy, visit https://creativecommons.org/licenses/by/4.0/

Attribution: Lewis, C. (2026) Hiding the wiring again. LDS Public Class No. 1, version 1.0. LDS Consultancy.
"""

CFF = f"""cff-version: 1.2.0
message: "If you use this model or its results, please cite it as below."
title: "Hiding the wiring again: software-defined power, hybrid heating, and the cost, carbon and flexibility of keeping the boiler. Evidence from 86 British winters (model, data and article)"
authors:
  - family-names: Lewis
    given-names: Craig
    affiliation: LDS Consultancy
version: "{VERSION}"
date-released: "{DATE}"
license: MIT
repository-code: "https://github.com/CFLLDS/gb-hybrid-heat-model"
url: "https://energy.ldsconsultancy.net/class/"
"""

GITIGNORE = """out/
release/
__pycache__/
*.pyc
docs/article/sd_power_hybrid/build/
# release assets (inputs.tar.gz, model_outputs_v4.tar.gz) unpack to these paths
data/model/gb/history.npz
data/model/gb/history_parts/
data/model/gb/stock_v3*.npz
data/model/gb/weather*.json
data/model/gb/prices_*.json
data/model/gb/carbon_*.json
data/model/gb/wind.json
data/model/gb/years/
data/model/gb/sources/
data/model/v4*/
data/historic_energy_prices/raw/
"""


if __name__ == "__main__":
    copy()
    (DEST / "README.md").write_text(README % {"ukds": ukds_lines()})
    (DEST / "LICENSE").write_text(MIT)
    (DEST / "LICENSE-TEXT").write_text(CCBY)
    (DEST / "CITATION.cff").write_text(CFF)
    (DEST / "requirements.txt").write_text("jax\nnumpy\npandas\npyarrow\nopenpyxl\nrequests\nmarkdown\npytest\n")
    (DEST / ".gitignore").write_text(GITIGNORE)
    bad = scrub_and_scan()
    n = sum(1 for p in DEST.rglob("*") if p.is_file() and ".git" not in p.parts and "release" not in p.parts)
    if bad:
        print("SECRET/PRIVATE SCAN FAILED:\n  " + "\n  ".join(bad[:30]))
        sys.exit(1)
    print(f"exported {n} files to {DEST}; scan clean")
    if "--assets" in sys.argv:
        assets()
