"""Independent cross-check of the warehouse against the source CSV (and the API, if it is running).

It recomputes the expected numbers with plain pandas (no pipeline code) and compares.
    python scripts/verify.py [path/to/source.csv]
Exit code 1 if anything disagrees.
"""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.config import DB_PATH  # noqa: E402

csv = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "bayut_selling_properties.csv"
API = "http://127.0.0.1:8000"
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  - {detail}" if detail else ""))


raw = pd.read_csv(csv)
valid = raw[raw["price"] > 0].drop_duplicates()          # what SHOULD be loaded
con = duckdb.connect(str(DB_PATH), read_only=True)
wh = con.execute("SELECT * FROM dw.v_listings").df()

n_raw = con.execute("SELECT count(*) FROM raw.listings_raw").fetchone()[0]
n_rej = con.execute("SELECT count(*) FROM staging.rejected").fetchone()[0]
check("raw rows in warehouse == CSV rows", n_raw == len(raw), f"{n_raw} vs {len(raw)}")
check("loaded + rejected == CSV rows", len(wh) + n_rej == len(raw), f"{len(wh)} + {n_rej} vs {len(raw)}")
check("loaded listings == valid distinct CSV rows", len(wh) == len(valid), f"{len(wh)} vs {len(valid)}")

for col_csv, col_wh, label in [("city", "city", "city"), ("type", "property_type", "property type")]:
    a = valid.groupby(col_csv).agg(n=("price", "size"), med=("price", "median"))
    b = wh.groupby(col_wh).agg(n=("price_aed", "size"), med=("price_aed", "median"))
    j = a.join(b, how="outer", lsuffix="_csv", rsuffix="_wh")
    bad = j[(j["n_csv"] != j["n_wh"]) | ((j["med_csv"] - j["med_wh"]).abs() > 0.5)]
    check(f"count + median price per {label} match", bad.empty,
          f"{len(j)} groups" if bad.empty else "\n" + bad.to_string())

b = wh[["price_aed", "bedrooms", "bathrooms", "city", "listed_date"]].copy()
b["price_aed"] = b["price_aed"].astype(float)
a = valid.assign(price=valid["price"].astype(float))[["price", "beds", "baths", "city", "post_date"]].astype(str).value_counts()
b["listed_date"] = pd.to_datetime(b["listed_date"]).dt.strftime("%Y-%m-%d")
b = b.astype(str).rename(columns={"price_aed": "price", "bedrooms": "beds", "bathrooms": "baths", "listed_date": "post_date"}).value_counts()
check("every row matches on price/beds/baths/city/date", a.equals(b.reindex(a.index).fillna(-1).astype(int)) and len(a) == len(b),
      f"{len(a)} distinct row signatures")

d = pd.to_datetime(wh["listed_date"]).dt.strftime("%Y-%m-%d")
check("date range matches", d.min() == valid["post_date"].min() and d.max() == valid["post_date"].max(),
      f"{valid['post_date'].min()} .. {valid['post_date'].max()}")

try:  # API vs pandas, only if the server is up
    q = urllib.parse.urlencode({"purpose": "Sale", "cities": "Dubai", "propertyTypes": "Apartment"})
    with urllib.request.urlopen(f"{API}/api/market/summary?{q}", timeout=5) as r:
        s = json.load(r)
    sub = valid[(valid["city"] == "Dubai") & (valid["type"] == "Apartment")]
    check("API summary (Dubai apartments) == CSV", s["listings"] == len(sub) and abs(s["medianPrice"] - sub["price"].median()) < 1,
          f"API {s['listings']} listings / median {s['medianPrice']:,.0f}; CSV {len(sub)} / {sub['price'].median():,.0f}")
except Exception as e:  # noqa: BLE001
    print(f"[SKIP] API check - server not reachable at {API} ({type(e).__name__})")

print(f"\n{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
