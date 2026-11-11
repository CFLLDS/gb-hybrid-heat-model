#!/usr/bin/env python3
"""National peaks with measured heating habits (out/rev_div/<Y>, gb_div.sh) against the same winters without them
(out/rev_fb1/<Y>/k0: 8,000 homes per town, no feedback), using review_spark.py's peak and national-mean code.

Herd = Agile C-COP peak above SD-Power's cap, where the cap is the flat-tariff (SVR) C-COP peak of the same run, as in
the paper; also against the cap without habits. Peak removed = (all-HP peak - C-COP peak) / (all-HP peak - baseline).
    python gb_div_digest.py --data /work/data/gb --out-dir /work/out --json /work/out/review_div.json
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import review_spark as RS  # noqa: E402

O = RS.O
TAR = RS.TAR


def main():
    R, N = {"by_year": {}}, {}
    for y in RS.SENS:
        a, b = O / f"{RS.REV}_fb1" / str(y) / "k0", O / f"{RS.REV}_div" / str(y)
        if not ((a / "run.json").exists() and (b / "run.json").exists()):
            continue
        R["by_year"][y] = {"base": {"peaks": RS.peaks(a), "nat": RS.nat(a)}, "div": {"peaks": RS.peaks(b), "nat": RS.nat(b)}}
        print(y, {k: round(R["by_year"][y][k]["peaks"]["ccop_agile"], 1) for k in ("base", "div")}, flush=True)
    by = R["by_year"]
    if not by:
        raise SystemExit("no finished winters")
    S = json.load(open(f"{RS.D}/base_demand.json"))["series"]
    base_max = max(S.values()) / 1000.0
    for v, V in (("base", "BASE"), ("div", "DIV")):
        cap = max(by[y][v]["peaks"]["ccop_svr"] for y in by)
        for t in TAR:
            N[f"REV_DIV_{V}_PEAK_CCOP_{t.upper()}_MAX"] = f"{max(by[y][v]['peaks'][f'ccop_{t}'] for y in by):.0f}"
            N[f"REV_DIV_{V}_PEAK_HP_{t.upper()}_MAX"] = f"{max(by[y][v]['peaks'][f'hp_{t}'] for y in by):.0f}"
            N[f"REV_DIV_{V}_HERD_{t.upper()}_GW"] = f"{max(max(by[y][v]['peaks'][f'ccop_{t}'] for y in by) - cap, 0):.0f}"
            rem = [100 * (by[y][v]['peaks'][f'hp_{t}'] - by[y][v]['peaks'][f'ccop_{t}']) /
                   (by[y][v]['peaks'][f'hp_{t}'] - base_max) for y in by]
            N[f"REV_DIV_{V}_REMOVED_{t.upper()}"] = f"{np.mean(rem):.0f}"
            N[f"REV_DIV_{V}_HYB_{t.upper()}"] = f"{np.median([by[y][v]['nat'][t]['hyb_wins'] for y in by]):.0f}"
            N[f"REV_DIV_{V}_HPGBP_{t.upper()}"] = f"{np.median([by[y][v]['nat'][t]['hp_gbp'] for y in by]):,.0f}"
        N[f"REV_DIV_{V}_CAP_GW"] = f"{cap:.0f}"
    cap0 = max(by[y]["base"]["peaks"]["ccop_svr"] for y in by)
    N["REV_DIV_HERD_AGILE_VS_BASECAP_GW"] = f"{max(max(by[y]['div']['peaks']['ccop_agile'] for y in by) - cap0, 0):.0f}"
    N["REV_DIV_YEARS"] = str(len(by))
    R["numbers"] = N
    json.dump(R, open(RS.ARG("--json", "/work/out/review_div.json"), "w"), indent=1)
    print(json.dumps(N, indent=1))


if __name__ == "__main__":
    main()
