#!/bin/bash
# Model v3 FINAL runs: real stock calibrated in the model's own terms (htc_cal, gb_v3_calibrate.py) + sourced inputs
# (gbmodel/inputs.py). Each winter at today's 2025-26 tariffs AND, where the 80-year series has it, at that year's
# own prices (tariff "hist": unit rates + gas standing charge split from the all-in series, data/gb/hist_prices.json). Then SD-Power pass 2, matched weather+price years
# 2016-2024, the sensitivities, and pre-heating on 12 years spanning winter severity.
cd /work
COMMON="--data /work/data/gb --stock-v3 cal --inputs sourced"
YEARS="2025 2010 1962 1946 1981 2009 1978 1985 1986 1990 $(seq 1940 2024)"
SENS="1962 2025 1941 1945 1950 1965 1974 1981 1992 1998 2004 2024"
hist() { python -c "import json,sys;y=json.load(open('/work/data/gb/hist_prices.json'))['years'].get('$1');print(f\"--hist-price {y['elec_unit_p']}:{y['gas_unit_p']}:{y['gas_sc_p_day']}\" if y else '')"; }
for Y in $YEARS; do
  [ -f out/v3f/$Y/run.json ] && continue
  echo "== p1 $Y $(date +%T)"
  python v3/scripts/gb_v2.py --weather $Y $COMMON $(hist $Y) --out /work/out/v3f/$Y 2>&1 | grep -E "^done|Error|Traceback"
done
echo P1DONE
for Y in $YEARS; do
  [ -f out/v3fp2/$Y/run.json ] && continue
  echo "== p2 $Y $(date +%T)"
  python v3/scripts/gb_sdp_phi.py --flex out/v3f/$Y/flex_region.npz --data data/gb --out out/v3f/$Y/sdp_phi.npz
  python v3/scripts/gb_v2.py --weather $Y $COMMON $(hist $Y) --sdp-phi /work/out/v3f/$Y/sdp_phi.npz --out /work/out/v3fp2/$Y 2>&1 | grep -E "^done|Error|Traceback"
done
echo P2DONE
for Y in 2016 2017 2018 2019 2020 2021 2022 2023 2024; do
  [ -f out/v3f_matched/$Y/run.json ] && continue
  echo "== matched $Y $(date +%T)"
  python v3/scripts/gb_v2.py --weather $Y --price-year $Y --data /work/data/gb_years/$Y --stock-v3 cal --inputs sourced \
    --out /work/out/v3f_matched/$Y 2>&1 | grep -E "^done|Error|Traceback"
done
echo MATCHEDDONE
for Y in $SENS; do
  [ -f out/v3f_half/$Y/run.json ] || python v3/scripts/gb_v2.py --weather $Y $COMMON --hyb-size 0.55 --out /work/out/v3f_half/$Y 2>&1 | grep -E "^done|Error"
  [ -f out/v3f_levy/$Y/run.json ] || python v3/scripts/gb_v2.py --weather $Y $COMMON --flat 34.3:8.17,20.4:8.17,16.3:8.17,22:9.5 --out /work/out/v3f_levy/$Y 2>&1 | grep -E "^done|Error"
done
echo SENSDONE
for Y in $SENS; do
  [ -f out/v3f_pre/$Y/run.json ] && continue
  echo "== pre $Y $(date +%T)"
  python v3/scripts/gb_v2.py --weather $Y $COMMON --preheat --stock 8000 --out /work/out/v3f_pre/$Y 2>&1 | grep -E "^done|Error|Traceback"
done
echo ALLDONE
