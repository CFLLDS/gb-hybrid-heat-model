#!/bin/bash
# Every heating year 1940-41 .. 2024-25 through the GB map model (gb_map.py --year --weather Y). Skips finished years.
cd /work
for Y in 1962 $(seq 1940 2024); do
  [ -f out/gb_hist/$Y/stock_summary.csv ] && continue
  echo "== $Y $(date +%T)"
  python scripts/gb_map.py --year --weather $Y --all-days --stock 32000 --out /work/out/gb_hist/$Y 2>&1 | grep -E "^done|Error|Traceback|assert" 
done
echo ALLDONE
