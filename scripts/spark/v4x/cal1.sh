cd /work
for L in 0.7216; do for Y in 2020 2021 2022; do
  o=out/v4cal/${Y}_L$L; [ -f $o/run.json ] || python v4x/scripts/gb_v2.py --weather $Y --data /work/data/gb --stock-v3 cal --inputs sourced --exvat --iog 6.6:36.39 --stock 8000 --cop-level $L:$L --out $o 2>&1 | grep -E "^done|Error|Traceback"
done; done
python v4x/scripts/gb_spf_cal.py
