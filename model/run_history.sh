#!/bin/bash
# Model v2: every heating year through gb_v2.py (2025-26 first, then the hard ones, then the rest). Skips finished years.
cd /work
for Y in 2025 2010 1962 1946 1981 2009 1978 1985 1986 1990 $(seq 1940 2024); do
  [ -f out/v2/$Y/run.json ] && continue
  echo "== $Y $(date +%T)"
  GIT_COMMIT=$GIT_COMMIT python scripts/gb_v2.py --weather $Y --out /work/out/v2/$Y 2>&1 | grep -E "^done|Error|Traceback|assert"
done
echo ALLDONE
