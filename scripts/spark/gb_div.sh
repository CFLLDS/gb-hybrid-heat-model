#!/bin/bash
# National herd with measured heating habits (review, 9 Nov 2026, P0): 12 sensitivity winters, 8,000 homes per town,
# each home keeping one IDEAL home's habits (gbmodel/diversity.py, data/gb/ideal_schedules.npz from ideal_gas.py).
# First proves the option inert: 1962 without it must reproduce rev_fb1/1962/k0 byte for byte.
cd /work
S=v3r/scripts
COMMON="--data /work/data/gb --stock-v3 cal --inputs sourced --stock 8000"
SENS="1962 2025 1941 1945 1950 1965 1974 1981 1992 1998 2004 2024"
python $S/gb_v2.py --weather 1962 $COMMON --out /work/out/rev_divcheck 2>&1 | grep -E "^done|Error|Traceback"
cmp /work/out/rev_divcheck/stock_summary.csv /work/out/rev_fb1/1962/k0/stock_summary.csv && echo INERT_OK || echo INERT_FAIL
for Y in $SENS; do
  [ -f /work/out/rev_div/$Y/run.json ] && continue
  echo "== $Y $(date +%T)"
  python $S/gb_v2.py --weather $Y $COMMON --div-lib /work/data/gb/ideal_schedules.npz --out /work/out/rev_div/$Y 2>&1 | grep -E "^done|Error|Traceback"
done
echo DIVDONE
