#!/bin/bash
# Hostile-review sensitivity runs (9 Nov 2026), queued for the cheap window (run_queue.sh); resumable, each run skipped
# once its run.json exists. Code: v3r/scripts = v3-final + inert-by-default options (--cop-level, --cop-corr,
# --weekday-align, --agile-add) and gb_feedback.py. Proved inert first: v3r reproduces out/v3f/1962 byte for byte.
#   P0-3 price feedback   Agile adder from the stock's own C-COP demand, damped fixed point, beta x1 and x2, 8,000 homes
#   P0-4 efficiency level fixed at the field-trial median (0.72), fixed at the tuned fleet (1.0), and the v3 range with
#        leakier homes given poorer installations (copula r = 0.5)
#   P1-6 calendar         each weather day priced on the same weekday of 2025-26
cd /work
S=v3r/scripts
COMMON="--data /work/data/gb --stock-v3 cal --inputs sourced"
SENS="1962 2025 1941 1945 1950 1965 1974 1981 1992 1998 2004 2024"
run() { local out=$1; shift; [ -f $out/run.json ] && return; echo "== $out $(date +%T)"
        python $S/gb_v2.py "$@" --out $out 2>&1 | grep -E "^done|Error|Traceback"; }

# All review runs use 8,000 homes per town (as the pre-heating run); rev_fb1/<Y>/k0 is their central case.
# P0-3: price feedback. k = 0 is the price-taker run; k = 1..6 add the damped adder from run k-1 (x2 slope: 4 years).
for SC in 1 2; do
  YS=$SENS; [ $SC = 2 ] && YS="1962 2025 1981 2004"
  for Y in $YS; do
    B=/work/out/rev_fb$SC/$Y
    run $B/k0 --weather $Y $COMMON --stock 8000
    for K in 1 2 3 4 5 6; do
      P=$((K - 1))
      [ -f $B/add$K.npz ] || python $S/gb_feedback.py --flex $B/k$P/flex_region.npz --data /work/data/gb --scale $SC \
          $([ $P -gt 0 ] && echo "--prev $B/add$P.npz") --out $B/add$K.npz
      run $B/k$K --weather $Y $COMMON --stock 8000 --agile-add $B/add$K.npz
    done
  done
done
echo FBDONE

# P0-4: heat-pump efficiency level
for Y in $SENS; do
  run /work/out/rev_coplo/$Y --weather $Y $COMMON --stock 8000 --cop-level 0.7216:0.7216
  run /work/out/rev_cophi/$Y --weather $Y $COMMON --stock 8000 --cop-level 1.0:1.0
  run /work/out/rev_copcorr/$Y --weather $Y $COMMON --stock 8000 --cop-corr 0.5
done
echo COPDONE

# P1-6: weekday-aligned price days
for Y in $SENS; do run /work/out/rev_wday/$Y --weather $Y $COMMON --stock 8000 --weekday-align; done
echo ALLDONE
