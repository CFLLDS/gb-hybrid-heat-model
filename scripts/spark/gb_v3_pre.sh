#!/bin/bash
# Re-run of the v3 pre-heating phase after the power-limit fix in gbmodel/thermal.py (8 Nov 2026): stored heat only
# from the heat pump within capacity, plus a 'full output' charge action. The faulty first run is kept in
# out/v3f_pre_unbounded for the record.
cd /work
COMMON="--data /work/data/gb --stock-v3 cal --inputs sourced"
SENS="1962 2025 1941 1945 1950 1965 1974 1981 1992 1998 2004 2024"
for Y in $SENS; do
  [ -f out/v3f_pre/$Y/run.json ] && continue
  echo "== pre $Y $(date +%T)"
  python v3/scripts/gb_v2.py --weather $Y $COMMON --preheat --stock 8000 --out /work/out/v3f_pre/$Y 2>&1 | grep -E "^done|Error|Traceback"
done
echo PREDONE
