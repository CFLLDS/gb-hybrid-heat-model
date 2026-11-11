cd /work
for L in 0.80 0.82 0.84; do for Y in 2020 2021 2022; do
  o=out/v4cal/${Y}_L$L; [ -f $o/run.json ] || python v4x/scripts/gb_v2.py --weather $Y --data /work/data/gb --stock-v3 cal --inputs sourced --exvat --iog 6.6:36.39 --stock 8000 --cop-level $L:$L --out $o 2>&1 | grep -E "Error|Traceback"
done; done
o=out/v4cal/2025_L1.0; [ -f $o/run.json ] || python v4x/scripts/gb_v2.py --weather 2025 --data /work/data/gb --stock-v3 cal --inputs sourced --exvat --iog 6.6:36.39 --stock 8000 --cop-level 1.0:1.0 --out $o 2>&1 | grep -E "Error|Traceback"
python v4x/scripts/gb_spf_cal.py --json /work/out/v4cal/spf_cal.json
