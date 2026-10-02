-- Layers: raw (as received) -> staging (typed, cleaned) -> dw (star schema) ; ops (audit)
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS dw;
CREATE SCHEMA IF NOT EXISTS ops;

-- ---------- RAW: everything is text, nothing is fixed ----------
CREATE TABLE IF NOT EXISTS raw.listings_raw (
    listing_id VARCHAR, title VARCHAR, price VARCHAR, area VARCHAR,
    bedrooms VARCHAR, bathrooms VARCHAR, property_type VARCHAR, purpose VARCHAR,
    community VARCHAR, city VARCHAR, listed_date VARCHAR, updated_at VARCHAR,
    _batch_id INTEGER, _source_file VARCHAR, _ingested_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS raw.ingest_log (
    batch_id INTEGER PRIMARY KEY, source_file VARCHAR, file_sha256 VARCHAR UNIQUE,
    row_count INTEGER, ingested_at TIMESTAMP
);

-- ---------- STAGING: typed + cleaned + deduplicated ----------
CREATE TABLE IF NOT EXISTS staging.listings (
    listing_id VARCHAR, title VARCHAR, price_aed DOUBLE, area_sqft DOUBLE,
    bedrooms INTEGER, bathrooms INTEGER, property_type VARCHAR, purpose VARCHAR,
    community VARCHAR, city VARCHAR, listed_date DATE, updated_at TIMESTAMP,
    record_hash VARCHAR, _batch_id INTEGER
);
CREATE TABLE IF NOT EXISTS staging.rejected (
    listing_id VARCHAR, title VARCHAR, price VARCHAR, area VARCHAR,
    bedrooms VARCHAR, bathrooms VARCHAR, property_type VARCHAR, purpose VARCHAR,
    community VARCHAR, city VARCHAR, listed_date VARCHAR, updated_at VARCHAR,
    reject_reason VARCHAR, _batch_id INTEGER
);

-- ---------- DW: star schema ----------
CREATE SEQUENCE IF NOT EXISTS dw.seq_location START 1;
CREATE SEQUENCE IF NOT EXISTS dw.seq_property_type START 1;

CREATE TABLE IF NOT EXISTS dw.dim_location (
    location_key INTEGER PRIMARY KEY DEFAULT nextval('dw.seq_location'),
    community VARCHAR NOT NULL, city VARCHAR NOT NULL,
    UNIQUE (community, city)
);
CREATE TABLE IF NOT EXISTS dw.dim_property_type (
    property_type_key INTEGER PRIMARY KEY DEFAULT nextval('dw.seq_property_type'),
    property_type VARCHAR NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS dw.dim_date (
    date_key INTEGER PRIMARY KEY, full_date DATE NOT NULL, year INTEGER, quarter INTEGER,
    month INTEGER, month_name VARCHAR, year_month VARCHAR, day_of_week INTEGER, is_weekend BOOLEAN
);
INSERT INTO dw.dim_date
SELECT CAST(strftime(d, '%Y%m%d') AS INTEGER), d, year(d), quarter(d), month(d),
       monthname(d), strftime(d, '%Y-%m'), dayofweek(d), dayofweek(d) IN (0, 6)
FROM (SELECT CAST(x AS DATE) AS d
      FROM generate_series(DATE '2020-01-01', DATE '2030-12-31', INTERVAL 1 DAY) t(x))
WHERE NOT EXISTS (SELECT 1 FROM dw.dim_date);

-- Grain: one row per listing (current state). History of price changes kept separately.
CREATE TABLE IF NOT EXISTS dw.fact_listings (
    listing_id VARCHAR PRIMARY KEY,
    location_key INTEGER NOT NULL REFERENCES dw.dim_location (location_key),
    property_type_key INTEGER NOT NULL REFERENCES dw.dim_property_type (property_type_key),
    listed_date_key INTEGER NOT NULL REFERENCES dw.dim_date (date_key),
    purpose VARCHAR NOT NULL,
    bedrooms INTEGER, bathrooms INTEGER,
    price_aed DOUBLE NOT NULL, area_sqft DOUBLE, price_per_sqft DOUBLE,
    record_hash VARCHAR NOT NULL,
    source_updated_at TIMESTAMP,
    first_loaded_at TIMESTAMP, last_loaded_at TIMESTAMP, _batch_id INTEGER
);
CREATE TABLE IF NOT EXISTS dw.fact_price_history (
    listing_id VARCHAR, price_aed DOUBLE, valid_from TIMESTAMP, valid_to TIMESTAMP, _batch_id INTEGER
);

CREATE OR REPLACE VIEW dw.v_listings AS
SELECT f.*, l.community, l.city, p.property_type, d.full_date AS listed_date, d.year_month
FROM dw.fact_listings f
JOIN dw.dim_location l ON l.location_key = f.location_key
JOIN dw.dim_property_type p ON p.property_type_key = f.property_type_key
JOIN dw.dim_date d ON d.date_key = f.listed_date_key;

-- ---------- OPS: audit ----------
CREATE TABLE IF NOT EXISTS ops.pipeline_runs (
    run_id INTEGER, batch_id INTEGER, started_at TIMESTAMP, finished_at TIMESTAMP,
    rows_raw INTEGER, rows_staged INTEGER, rows_rejected INTEGER, rows_dup_removed INTEGER,
    fact_inserted INTEGER, fact_updated INTEGER, status VARCHAR
);
CREATE TABLE IF NOT EXISTS ops.dq_results (
    run_id INTEGER, batch_id INTEGER, check_name VARCHAR, severity VARCHAR,
    passed BOOLEAN, detail VARCHAR, checked_at TIMESTAMP
);
