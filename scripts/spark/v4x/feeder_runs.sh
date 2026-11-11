cd /work
C="--data /work/data/gb --stock-v3 cal --inputs sourced --exvat --iog 6.6:36.39 --stock 4000 --towns Birmingham --cold-days 12"
hist() { python -c "import json;y=json.load(open('/work/data/gb/hist_prices.json'))['years'].get('$1');print(f\"--hist-price {y['elec_unit_p']}:{y['gas_unit_p']}:{y['gas_sc_p_day']}\" if y else '')"; }
for Y in 1962 2024; do
  [ -f out/feeder_e_${Y}_Birmingham.npz ] || python v3r/scripts/gb_coincidence.py --weather $Y $C $(hist $Y) --sdp-phi /work/out/v4/$Y/sdp_phi_gross.npz --save-e /work/out/feeder_e_$Y.npz --out /work/out/feeder_cf_$Y.json 2>&1 | grep -v WARNING
done
echo FEEDER_E_DONE
