#!/bin/bash
# Sensitivity runs (Craig 7 Nov), after pass 2 finishes: 12 years spanning winter severity (docs/article/results/
# sens_years.json + 1962 + 2025). (a) hybrid heat pump sized to the MCS 55% minimum; (b) levy-rebalancing sweep on
# flat tariffs, elec:gas p/kWh -- ratio 4.2 (34.3:8.17), 2.5 (20.4:8.17), 2.0 (16.3:8.17), levies moved onto gas (22:9.5).
# Code: v21s/scripts (identical to v21 except the --hyb-size option, which is inert at its default).
cd /work
until grep -q ALLDONE out/v21_pass2.log; do sleep 60; done
for Y in 1962 2025 1941 1945 1950 1965 1974 1981 1992 1998 2004 2024; do
  [ -f out/sens_half/$Y/run.json ] || { echo "== half $Y $(date +%T)"; python v21s/scripts/gb_v2.py --weather $Y --data /work/data/gb \
      --hyb-size 0.55 --out /work/out/sens_half/$Y 2>&1 | grep -E "^done|Error|Traceback"; }
  [ -f out/sens_levy/$Y/run.json ] || { echo "== levy $Y $(date +%T)"; python v21s/scripts/gb_v2.py --weather $Y --data /work/data/gb \
      --flat 34.3:8.17,20.4:8.17,16.3:8.17,22:9.5 --out /work/out/sens_levy/$Y 2>&1 | grep -E "^done|Error|Traceback"; }
done
echo ALLDONE
