cd /work/out
mkdir -p v4p2c review4_sdp_seeds
for d in v4/*/; do y=$(basename $d); [ -e v4p2c/$y ] || { if [ -f v4p2/$y/run.json ]; then ln -s ../v4p2/$y v4p2c/$y; else ln -s ../v4/$y v4p2c/$y; fi; }; done
ls v4p2c | wc -l
cd /work
python v4x/art/review_sdp.py --src /work/out/v4p2c --gb /work/data/gb --out /work/out/review4_sdp.json > /work/out/review4_sdp.log 2>&1 && echo SDP_OK
python v4x/art/review_baseline.py --src /work/out/v4p2c --gb /work/data/gb --out /work/out/review4_baseline.json > /work/out/review4_baseline.log 2>&1 && echo BASE_OK
python v4x/scripts/gb_stagger.py --data /work/data/gb --src /work/out/v4 --out /work/out/review4_stagger.json > /work/out/review4_stagger.log 2>&1 && echo STAG_OK
for s in $(seq 1 20); do python v4x/art/review_sdp.py --src /work/out/v4p2c --gb /work/data/gb --seed $s --out /work/out/review4_sdp_seeds/s$s.json > /dev/null 2>&1 || echo SEEDFAIL $s; done
echo POST_DONE
