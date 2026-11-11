cd /work
for Y in 2016 2017 2018 2019 2020 2021 2022 2023 2024; do
  [ -f out/v4_matched/$Y/run.json ] && continue
  echo "== matched $Y $(date +%T)"
  python v3r/scripts/gb_v2.py --weather $Y --price-year $Y --data /work/data/gb_years/$Y --stock-v3 cal --inputs sourced \
    --out /work/out/v4_matched/$Y 2>&1 | grep -E "^done|Error|Traceback"
done
echo MATCHEDDONE
