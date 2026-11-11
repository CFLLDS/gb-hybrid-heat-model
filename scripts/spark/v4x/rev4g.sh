cd /work
S=v4x/scripts
python $S/review_spark.py --rev rev4 --data /work/data/gb --out-dir /work/out --json /work/out/review4_spark.json > /work/out/review4_spark.log 2>&1 && echo SPARK_OK
python $S/gb_div_digest.py --rev rev4 --data /work/data/gb --out-dir /work/out --json /work/out/review4_div.json > /work/out/review4_div.log 2>&1 && echo DIV_OK
python v4x/art/review_sdp.py --src /work/out/rev4_base12 --gb /work/data/gb --out /work/out/review4_sdp_base12.json > /work/out/review4_sdp_base12.log 2>&1 && echo B12_OK
python v4x/art/review_sdp.py --src /work/out/rev4_div --gb /work/data/gb --out /work/out/review4_sdp_div.json > /work/out/review4_sdp_div.log 2>&1 && echo SDPDIV_OK
echo G_POST_DONE
