#!/bin/bash
# Model v2.1 pass 2: wait for pass 1 (out/v2, gb_v2_history.sh) to finish, then for every year compute the SD-Power
# shed shares from pass 1 (gb_sdp_phi.py) and rerun with them into out/v21/<Y>. ccop etc. reproduce pass 1 exactly.
cd /work
until grep -q ALLDONE out/v2_history.log; do sleep 60; done
for Y in 2025 2010 1962 1946 1981 2009 1978 1985 1986 1990 $(seq 1940 2024); do
  [ -f out/v21/$Y/run.json ] && continue
  [ -f out/v2/$Y/flex_region.npz ] || { echo "no pass 1 for $Y"; continue; }
  echo "== $Y $(date +%T)"
  python v21/scripts/gb_sdp_phi.py --flex out/v2/$Y/flex_region.npz --data data/gb --out out/v2/$Y/sdp_phi.npz
  GIT_COMMIT=$GIT_COMMIT python v21/scripts/gb_v2.py --weather $Y --data /work/data/gb --sdp-phi /work/out/v2/$Y/sdp_phi.npz \
    --out /work/out/v21/$Y 2>&1 | grep -E "^done|Error|Traceback|assert"
done
echo ALLDONE
