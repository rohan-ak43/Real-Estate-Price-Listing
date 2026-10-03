"""FastAPI backend for the UAE Property Listings dashboard.

Serves the warehouse to the React frontend via read-only REST endpoints.
"""

import hashlib
import sys
import time
from pathlib import Path
from typing import Any

import duckdb
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add project root to path so we can import src.config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import DB_PATH  # noqa: E402

app = FastAPI(title="UAE Property Listings API")

# Allow the React dev server to make requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Simple in-memory cache (TTL = 60 s), keeps repeated dashboard requests cheap
# ---------------------------------------------------------------------------
_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL = 60


def _cache_key(sql: str, params: tuple) -> str:
    raw = f"{sql}|{params}"
    return hashlib.md5(raw.encode()).hexdigest()


def _query(sql: str, params: tuple = ()) -> list[dict]:
    """Execute a read-only DuckDB query with caching.  Returns list of dicts."""
    key = _cache_key(sql, params)
    now = time.time()
    if key in _cache and (now - _cache[key][0]) < CACHE_TTL:
        return _cache[key][1]

    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        result = con.execute(sql, list(params)).fetchdf()
        rows = result.to_dict(orient="records")
        _cache[key] = (now, rows)
        return rows
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Health-check & warehouse status
# ---------------------------------------------------------------------------
@app.get("/api/status")
def status():
    if not DB_PATH.exists():
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": "Warehouse not found. Run `make demo` first."},
        )
    return {"ok": True}


# ---------------------------------------------------------------------------
# Market endpoints
# ---------------------------------------------------------------------------
@app.get("/api/market/options")
def market_options():
    """Distinct filter values — mirrors: SELECT DISTINCT city, property_type, purpose FROM dw.v_listings"""
    if not DB_PATH.exists():
        return JSONResponse(status_code=503, content={"error": "Warehouse not found."})
    rows = _query("SELECT DISTINCT city, property_type, purpose FROM dw.v_listings")
    if not rows:
        return {"empty": True, "cities": [], "propertyTypes": [], "purposes": []}
    cities = sorted({r["city"] for r in rows})
    property_types = sorted({r["property_type"] for r in rows})
    purposes = sorted({r["purpose"] for r in rows}, reverse=True)  # Sale first
    return {"empty": False, "cities": cities, "propertyTypes": property_types, "purposes": purposes}


@app.get("/api/market/summary")
def market_summary(
    purpose: str = Query(...),
    cities: list[str] = Query(...),
    propertyTypes: list[str] = Query(..., alias="propertyTypes"),
):
    """KPI cards."""
    if not DB_PATH.exists():
        return JSONResponse(status_code=503, content={"error": "Warehouse not found."})
    where = "purpose = ? AND list_contains(?, city) AND list_contains(?, property_type)"
    sql = f"""
        SELECT count(*) AS n,
               median(price_aed) AS med_price,
               avg(price_aed) AS avg_price,
               count(DISTINCT community) AS areas
        FROM dw.v_listings
        WHERE {where}
    """
    rows = _query(sql, (purpose, cities, propertyTypes))
    r = rows[0] if rows else {"n": 0, "med_price": None, "avg_price": None, "areas": 0}
    return {
        "listings": int(r["n"]),
        "medianPrice": r["med_price"],
        "averagePrice": r["avg_price"],
        "communities": int(r["areas"]),
    }


@app.get("/api/market/community-prices")
def community_prices(
    purpose: str = Query(...),
    cities: list[str] = Query(...),
    propertyTypes: list[str] = Query(..., alias="propertyTypes"),
):
    """Median price by community — horizontal bar chart data."""
    if not DB_PATH.exists():
        return JSONResponse(status_code=503, content={"error": "Warehouse not found."})
    where = "purpose = ? AND list_contains(?, city) AND list_contains(?, property_type)"
    sql = f"""
        SELECT community,
               round(median(price_aed)) AS median_price
        FROM dw.v_listings
        WHERE {where}
        GROUP BY 1
        HAVING count(*) >= 20
        ORDER BY 2 DESC
    """
    return _query(sql, (purpose, cities, propertyTypes))


@app.get("/api/market/property-types")
def property_types_chart(
    purpose: str = Query(...),
    cities: list[str] = Query(...),
    propertyTypes: list[str] = Query(..., alias="propertyTypes"),
):
    """Listings count by property type — vertical bar chart data."""
    if not DB_PATH.exists():
        return JSONResponse(status_code=503, content={"error": "Warehouse not found."})
    where = "purpose = ? AND list_contains(?, city) AND list_contains(?, property_type)"
    sql = f"""
        SELECT property_type,
               count(*) AS listings
        FROM dw.v_listings
        WHERE {where}
        GROUP BY 1
        ORDER BY 2 DESC
    """
    return _query(sql, (purpose, cities, propertyTypes))


@app.get("/api/market/price-trend")
def price_trend(
    purpose: str = Query(...),
    cities: list[str] = Query(...),
    propertyTypes: list[str] = Query(..., alias="propertyTypes"),
):
    """Median price trend by month listed — line chart data."""
    if not DB_PATH.exists():
        return JSONResponse(status_code=503, content={"error": "Warehouse not found."})
    where = "purpose = ? AND list_contains(?, city) AND list_contains(?, property_type)"
    sql = f"""
        SELECT year_month,
               round(median(price_aed)) AS median_price
        FROM dw.v_listings
        WHERE {where}
        GROUP BY 1
        HAVING count(*) >= 20
        ORDER BY 1
    """
    return _query(sql, (purpose, cities, propertyTypes))


@app.get("/api/market/price-changes")
def price_changes():
    """Biggest recent price changes — table data.  Not filtered."""
    if not DB_PATH.exists():
        return JSONResponse(status_code=503, content={"error": "Warehouse not found."})
    sql = """
        SELECT h.listing_id,
               l.community,
               l.property_type,
               h.price_aed  AS old_price,
               f.price_aed  AS new_price,
               round(100 * (f.price_aed - h.price_aed) / h.price_aed, 1) AS change_pct,
               h.valid_to   AS changed_at
        FROM dw.fact_price_history h
        JOIN dw.fact_listings f USING (listing_id)
        JOIN dw.v_listings l   USING (listing_id)
        ORDER BY abs(change_pct) DESC
        LIMIT 15
    """
    return _query(sql)


# ---------------------------------------------------------------------------
# Pipeline-health endpoints
# ---------------------------------------------------------------------------
@app.get("/api/health/pipeline-runs")
def pipeline_runs():
    """All pipeline runs, most recent first."""
    if not DB_PATH.exists():
        return JSONResponse(status_code=503, content={"error": "Warehouse not found."})
    return _query("SELECT * FROM ops.pipeline_runs ORDER BY run_id DESC")


@app.get("/api/health/data-quality")
def data_quality():
    """Latest data-quality results (for the most recent run_id)."""
    if not DB_PATH.exists():
        return JSONResponse(status_code=503, content={"error": "Warehouse not found."})
    sql = """
        SELECT check_name, severity, passed, detail, run_id
        FROM ops.dq_results
        WHERE run_id = (SELECT max(run_id) FROM ops.dq_results)
        ORDER BY severity, check_name
    """
    return _query(sql)


@app.get("/api/health/rejected-rows")
def rejected_rows():
    """Rejected rows grouped by reason."""
    if not DB_PATH.exists():
        return JSONResponse(status_code=503, content={"error": "Warehouse not found."})
    return _query(
        "SELECT reject_reason, count(*) AS rows FROM staging.rejected GROUP BY 1 ORDER BY 2 DESC"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
