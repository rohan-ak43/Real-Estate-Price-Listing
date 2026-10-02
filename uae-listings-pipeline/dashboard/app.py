"""Streamlit dashboard over the star schema.  Run: make dashboard"""
import sys
from pathlib import Path

import duckdb
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import DB_PATH  # noqa: E402

st.set_page_config(page_title="UAE Property Listings", layout="wide")


@st.cache_data(ttl=60)
def q(sql: str, params: tuple = ()):
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        return con.execute(sql, list(params)).df()
    finally:
        con.close()


if not DB_PATH.exists():
    st.error("No warehouse found. Run `make demo` first.")
    st.stop()

st.title("UAE Property Listings")
market, health = st.tabs(["Market", "Pipeline health"])

with market:
    opts = q("SELECT DISTINCT city, property_type, purpose FROM dw.v_listings")
    if opts.empty:
        st.warning("Warehouse is empty. Run the pipeline.")
        st.stop()
    purposes = sorted(opts["purpose"].unique(), reverse=True)  # Sale first
    purpose = st.sidebar.radio("Purpose", purposes)
    cities = st.sidebar.multiselect("City", sorted(opts["city"].unique()), default=sorted(opts["city"].unique()))
    types = st.sidebar.multiselect("Property type", sorted(opts["property_type"].unique()),
                                   default=sorted(opts["property_type"].unique()))
    st.sidebar.caption("Price per sqft is AED per sqft (annual rent for Rent).")
    where = "purpose = ? AND list_contains(?, city) AND list_contains(?, property_type)"
    p = (purpose, cities, types)

    k = q(f"""SELECT count(*) AS n, median(price_aed) AS med_price, avg(price_per_sqft) AS ppsf,
                     count(DISTINCT community) AS areas FROM dw.v_listings WHERE {where}""", p).iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Listings", f"{int(k['n']):,}")
    c2.metric("Median price (AED)", f"{k['med_price']:,.0f}" if k["n"] else "-")
    c3.metric("Avg AED / sqft", f"{k['ppsf']:,.0f}" if k["n"] else "-")
    c4.metric("Communities", int(k["areas"]))

    left, right = st.columns(2)
    with left:
        st.subheader("Average price per sqft by community")
        d = q(f"""SELECT community, round(avg(price_per_sqft)) AS avg_price_per_sqft
                  FROM dw.v_listings WHERE {where} GROUP BY 1 ORDER BY 2 DESC""", p)
        st.bar_chart(d, x="community", y="avg_price_per_sqft", horizontal=True)
    with right:
        st.subheader("Listings by property type")
        d = q(f"SELECT property_type, count(*) AS listings FROM dw.v_listings WHERE {where} GROUP BY 1 ORDER BY 2 DESC", p)
        st.bar_chart(d, x="property_type", y="listings")

    st.subheader("Price per sqft trend (by month listed)")
    d = q(f"""SELECT year_month, round(avg(price_per_sqft)) AS avg_price_per_sqft
              FROM dw.v_listings WHERE {where} GROUP BY 1 ORDER BY 1""", p)
    st.line_chart(d, x="year_month", y="avg_price_per_sqft")

    st.subheader("Biggest recent price changes")
    st.dataframe(q("""
        SELECT h.listing_id, l.community, l.property_type, h.price_aed AS old_price,
               f.price_aed AS new_price, round(100 * (f.price_aed - h.price_aed) / h.price_aed, 1) AS change_pct,
               h.valid_to AS changed_at
        FROM dw.fact_price_history h JOIN dw.fact_listings f USING (listing_id)
        JOIN dw.v_listings l USING (listing_id)
        ORDER BY abs(change_pct) DESC LIMIT 15"""), width="stretch", hide_index=True)

with health:
    st.subheader("Pipeline runs")
    st.dataframe(q("SELECT * FROM ops.pipeline_runs ORDER BY run_id DESC"), width="stretch", hide_index=True)
    st.subheader("Latest data-quality results")
    st.dataframe(q("""SELECT check_name, severity, passed, detail, run_id FROM ops.dq_results
                      WHERE run_id = (SELECT max(run_id) FROM ops.dq_results) ORDER BY severity, check_name"""),
                 width="stretch", hide_index=True)
    st.subheader("Rejected rows by reason")
    st.dataframe(q("SELECT reject_reason, count(*) AS rows FROM staging.rejected GROUP BY 1 ORDER BY 2 DESC"),
                 width="stretch", hide_index=True)
