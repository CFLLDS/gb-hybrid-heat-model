#!/bin/bash
# Stage H (10 Nov 2026): the Electrification of Heat trial's measured behaviour inside the model, on the v4 basis,
# 8,000 homes per town, the 12 sensitivity winters. Each run is compared with rev4_fb1/<Y>/k0 (same homes, no options).
#   rev4_eoh      measured heat-pump heating habits: each model home keeps one trial home's daily on/off patterns
#                 (data/gb/eoh_schedules.npz, scripts/spark/ukds/eoh_schedules.py) with the trial's median
#                 evening-to-night setback, 1.1 K, instead of a set point held all day
#   rev4_bivm     hybrids switched as the trial's 141 metered hybrids did: controller bivm (--biv-meas), a fixed
#                 per-home changeover temperature drawn so the stock's boiler share of heat by outdoor temperature
#                 equals the measured share
#   rev4_eohbivm  both together
# Then the Freedom-style coincidence run with the measured habits (div_cf_eoh.json, against div_cf_lib.json's IDEAL
# habits and review4_coincidence.json's none), and SD-Power's delivery on the measured-habits runs (review4_sdp_eoh).
# Resumable: a run is skipped once its run.json exists. Run inside the image:
#   docker run --rm --gpus all -v ~/cfl-model:/work --entrypoint "" cfl-model:1 bash /work/v4x/rev4h.sh
cd /work
S=v3r/scripts
V4="--exvat --iog 6.6:36.39"
COMMON="--data /work/data/gb --stock-v3 cal --inputs sourced $V4 --stock 8000"
EOH="--div-lib /work/data/gb/eoh_schedules.npz --div-setback 1.1"
BIVM="--biv-meas /work/data/gb/eoh.json"
SENS="1962 2025 1941 1945 1950 1965 1974 1981 1992 1998 2004 2024"
run() { local out=$1; shift; [ -f $out/run.json ] && return; echo "== $out $(date +%T)"
        python $S/gb_v2.py "$@" --out $out 2>&1 | grep -E "^done|Error|Traceback"; }

for Y in $SENS; do
  run out/rev4_eoh/$Y --weather $Y $COMMON $EOH
  run out/rev4_bivm/$Y --weather $Y $COMMON $BIVM
  run out/rev4_eohbivm/$Y --weather $Y $COMMON $EOH $BIVM
done
echo H_RUNS_DONE
[ -f out/div_cf_eoh.json ] || python $S/gb_coincidence.py --weather 2017 --data /work/data/gb --stock-v3 cal --inputs sourced $V4 \
    --stock 4000 --towns Cardiff,Swansea --cold-days 10 --div-cont 0 $EOH --out /work/out/div_cf_eoh.json 2>&1 | grep -vE "^WARNING"
echo CF_DONE
for R in eoh eohbivm; do
  [ -f out/review4_sdp_$R.json ] || python v4x/art/review_sdp.py --src /work/out/rev4_$R --gb /work/data/gb \
      --out /work/out/review4_sdp_$R.json > /work/out/review4_sdp_$R.log 2>&1 && echo SDP_${R}_OK
done
echo H_DONE
