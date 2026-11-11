cd /work
D="2022-12-09,2022-12-11,2022-12-13,2022-12-15,2022-12-17,2023-01-17,2023-01-19,2023-01-21,2023-03-08"
C="--weather 2022 --data /work/data/gb --stock-v3 cal --inputs sourced --exvat --iog 6.6:36.39 --stock 4000 --towns Newcastle,Edinburgh,Maidstone --dates $D"
python v3r/scripts/gb_coincidence.py $C --out /work/out/val_cf_base.json 2>&1 | grep -v WARNING
python v3r/scripts/gb_coincidence.py $C --div-cont 0 --div-lib /work/data/gb/eoh_schedules.npz --div-setback 1.1 --out /work/out/val_cf_eoh.json 2>&1 | grep -v WARNING
echo VAL_DONE
