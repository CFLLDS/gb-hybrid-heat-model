#!/bin/bash
# Model v4 runs (review 4, "draft 3 teardown", 9 Nov 2026). Same model as v3-final + the review options; changes:
#   one fiscal basis   --exvat (2025-26 Agile and Cosy before 1 Oct 2026 / 1.05) and --iog 6.6:36.39 (Southern IOG
#                      from 16 Oct 2026, VAT-free), so every tariff is today's, without VAT, as the Oct-Dec 2026 cap
#   heated homes       data/gb/region_weights.json "homes" = gas meters x 0.86 (gb_national_scale.py); only the
#                      post-processing and SD-Power's phi read it
#   SD-Power           pass 2 for the 12 sensitivity winters only, on the gross cap as before (v4p2) and on a cap on
#                      demand net of transmission wind (v4p2r, gb_sdp_phi.py --basis residual)
#   weather-matched    the 12 sensitivity winters priced on the nearest-temperature 2016-26 day (gb_wmatch.py)
#   efficiency level   low end recalibrated 0.72 -> 0.816 (physics.STOCK_LEVEL) so the stock realises the trial's 2.78;
#                      outputs from the 0.72 range were moved to out/v4a* (9 Nov 2026, 20:55 UTC)
# Ordered so the 12 sensitivity winters finish first. Resumable: a run is skipped once its run.json exists.
cd /work
S=v3r/scripts
V4="--exvat --iog 6.6:36.39"
COMMON="--data /work/data/gb --stock-v3 cal --inputs sourced $V4"
SENS="1962 2025 1941 1945 1950 1965 1974 1981 1992 1998 2004 2024"
YEARS="2025 2010 1962 1946 1981 2009 1978 1985 1986 1990 $(seq 1940 2024)"
hist() { python -c "import json,sys;y=json.load(open('/work/data/gb/hist_prices.json'))['years'].get('$1');print(f\"--hist-price {y['elec_unit_p']}:{y['gas_unit_p']}:{y['gas_sc_p_day']}\" if y else '')"; }
run() { local out=$1; shift; [ -f $out/run.json ] && return; echo "== $out $(date +%T)"
        python $S/gb_v2.py "$@" --out $out 2>&1 | grep -E "^done|Error|Traceback"; }

# 0. the recalibrated low level (0.816) over the trial winters, to confirm it realises 2.78 (gb_spf_cal.py)
for Y in 2020 2021 2022; do run out/v4cal/${Y}_L0.816 --weather $Y $COMMON --stock 8000 --cop-level 0.816:0.816; done
python $S/gb_spf_cal.py --json /work/out/v4cal/spf_cal.json
# A. pass 1, the 12 sensitivity winters
for Y in $SENS; do run out/v4/$Y --weather $Y $COMMON $(hist $Y); done
echo A_DONE
# B. weather-matched market, same winters, same homes
for Y in $SENS; do
  run out/v4wm/$Y --weather $Y --data /work/data/gb_wm/$Y --stock-v3 cal --inputs sourced $V4
  for B in gross residual; do
    [ -f out/v4wm/$Y/sdp_phi_$B.npz ] || python $S/gb_sdp_phi.py --flex out/v4wm/$Y/flex_region.npz \
        --data /work/data/gb_wm/$Y --basis $B --out out/v4wm/$Y/sdp_phi_$B.npz
  done
done
echo B_DONE
# C. pre-heating, 8,000 homes (as v3)
for Y in $SENS; do run out/v4pre/$Y --weather $Y $COMMON --preheat --stock 8000; done
echo C_DONE
# D. SD-Power pass 2 for the 12 winters, gross and residual caps
for Y in $SENS; do
  for B in gross residual; do
    [ -f out/v4/$Y/sdp_phi_$B.npz ] || python $S/gb_sdp_phi.py --flex out/v4/$Y/flex_region.npz --data /work/data/gb \
        --basis $B --out out/v4/$Y/sdp_phi_$B.npz
  done
  run out/v4p2/$Y --weather $Y $COMMON $(hist $Y) --sdp-phi /work/out/v4/$Y/sdp_phi_gross.npz
  run out/v4p2r/$Y --weather $Y $COMMON $(hist $Y) --sdp-phi /work/out/v4/$Y/sdp_phi_residual.npz
done
echo D_DONE
# E. every other winter: pass 1 only (SD-Power's pass 2 and its cost come from the 12 winters in D; ~7 min a run)
for Y in $YEARS; do run out/v4/$Y --weather $Y $COMMON $(hist $Y); done
echo E_DONE
# F. hybrid heat pump at the MCS minimum, and the levy-rebalancing sweep
for Y in $SENS; do
  run out/v4_half/$Y --weather $Y $COMMON --hyb-size 0.55
  run out/v4_levy/$Y --weather $Y $COMMON --flat 34.3:8.17,20.4:8.17,16.3:8.17,22:9.5
done
echo F_DONE
# G. the review sensitivities again on the v4 basis, 8,000 homes (gb_review.sh, gb_div.sh); feedback without VAT
for SC in 1 2; do
  YS=$SENS; [ $SC = 2 ] && YS="1962 2025 1981 2004"
  for Y in $YS; do
    B=/work/out/rev4_fb$SC/$Y
    run $B/k0 --weather $Y $COMMON --stock 8000
    for K in 1 2 3 4 5 6; do
      P=$((K - 1))
      [ -f $B/add$K.npz ] || python $S/gb_feedback.py --flex $B/k$P/flex_region.npz --data /work/data/gb --scale $SC \
          --vat 1.0 $([ $P -gt 0 ] && echo "--prev $B/add$P.npz") --out $B/add$K.npz
      run $B/k$K --weather $Y $COMMON --stock 8000 --agile-add $B/add$K.npz
    done
  done
done
for Y in $SENS; do
  run out/rev4_coplo/$Y --weather $Y $COMMON --stock 8000 --cop-level 0.816:0.816
  run out/rev4_cophi/$Y --weather $Y $COMMON --stock 8000 --cop-level 1.0:1.0
  run out/rev4_copcorr/$Y --weather $Y $COMMON --stock 8000 --cop-corr 0.5
  run out/rev4_wday/$Y --weather $Y $COMMON --stock 8000 --weekday-align
  run out/rev4_div/$Y --weather $Y $COMMON --stock 8000 --div-lib /work/data/gb/ideal_schedules.npz
done
echo ALLDONE
