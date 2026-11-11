"""EoH cleansed half-hourly CSV (2.47 GB) -> one parquet, plus a per-property index with first/last timestamp, rows,
and how many rows carry a boiler reading (hybrid), a heat-pump output reading and a whole-system reading."""
import json
import time

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

SRC = "/w/x/UKDA-9209-csv/csv/eoh_cleaned_half_hourly.csv"
OUT = "/w/work/eoh_hh.parquet"
t0 = time.time()
w = None
idx = {}
for ch in pd.read_csv(SRC, chunksize=2_000_000, dtype={"Property_ID": "string"}, parse_dates=["Timestamp"]):
    ch = ch.drop(columns=["half-hour"])
    for c in ch.columns:
        if c not in ("Property_ID", "Timestamp"):
            ch[c] = ch[c].astype("float32")
    tb = pa.Table.from_pandas(ch, preserve_index=False)
    if w is None:
        w = pq.ParquetWriter(OUT, tb.schema, compression="zstd")
    w.write_table(tb)
    for pid, g in ch.groupby("Property_ID"):
        d = idx.setdefault(pid, {"rows": 0, "t0": str(g.Timestamp.min()), "t1": None, "boiler": 0, "hp_out": 0, "sys": 0})
        d["rows"] += len(g)
        d["t1"] = str(g.Timestamp.max())
        d["boiler"] += int(g.Boiler_Energy_Output.notna().sum())
        d["hp_out"] += int(g.Heat_Pump_Energy_Output.notna().sum())
        d["sys"] += int(g.Whole_System_Energy_Consumed.notna().sum())
    print(f"{sum(v['rows'] for v in idx.values()) / 1e6:.1f}M rows {time.time() - t0:.0f}s", flush=True)
w.close()
json.dump(idx, open("/w/work/eoh_index.json", "w"), indent=0)
print("properties", len(idx), "with boiler readings", sum(1 for v in idx.values() if v["boiler"] > 1000))
