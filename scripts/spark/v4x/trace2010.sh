cd /work
S=v3r/scripts; hist() { python -c "import json,sys;y=json.load(open('/work/data/gb/hist_prices.json'))['years'].get('$1');print(f\"--hist-price {y['elec_unit_p']}:{y['gas_unit_p']}:{y['gas_sc_p_day']}\" if y else '')"; }; V4="--exvat --iog 6.6:36.39"; COMMON="--data /work/data/gb --stock-v3 cal --inputs sourced $V4"
[ -f out/v4/2010/sdp_phi_gross.npz ] || python $S/gb_sdp_phi.py --flex out/v4/2010/flex_region.npz --data /work/data/gb --basis gross --out out/v4/2010/sdp_phi_gross.npz
[ -f out/v4p2/2010/run.json ] || python $S/gb_v2.py --weather 2010 $COMMON $(hist 2010) --sdp-phi /work/out/v4/2010/sdp_phi_gross.npz --out out/v4p2/2010 2>&1 | grep -E "^done|Error|Traceback"
python v4x/scripts/gb_trace.py --weather 2010 --data /work/data/gb $V4 --run /work/out/v4p2/2010 --phi /work/out/v4/2010/sdp_phi_gross.npz --out /work/out/v4p2/trace_2010.json 2>&1 | grep -vE "^WARNING|^I0000" | tail -3
ln -sfn ../v4p2/2010 out/v4p2c/2010
python v4x/art/review_sdp.py --src /work/out/v4p2c --gb /work/data/gb --out /work/out/review4_sdp.json 2>&1 | grep -A3 "\"check\""
echo TRACE_DONE
