"""DW layer: incremental load of the star schema from one staging batch.

Incremental rule: a listing is inserted if new, updated only if its content hash differs AND the
incoming record is not older than what the warehouse already holds (handles out-of-order files).
Runs inside the caller's transaction so it can be rolled back if data-quality checks fail.
"""


def load_batch(con, batch_id: int) -> dict:
    b = int(batch_id)

    # 1. dimensions: add only members we have not seen
    con.execute(f"""
        INSERT INTO dw.dim_location (community, city)
        SELECT DISTINCT s.community, s.city FROM staging.listings s
        WHERE s._batch_id = {b} AND NOT EXISTS (
            SELECT 1 FROM dw.dim_location l WHERE l.community = s.community AND l.city = s.city)""")
    con.execute(f"""
        INSERT INTO dw.dim_property_type (property_type)
        SELECT DISTINCT s.property_type FROM staging.listings s
        WHERE s._batch_id = {b} AND NOT EXISTS (
            SELECT 1 FROM dw.dim_property_type p WHERE p.property_type = s.property_type)""")

    # 2. resolve surrogate keys for this batch
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE incoming AS
        SELECT s.listing_id, l.location_key, p.property_type_key,
               CAST(strftime(s.listed_date, '%Y%m%d') AS INTEGER) AS listed_date_key,
               s.purpose, s.bedrooms, s.bathrooms, s.price_aed, s.area_sqft,
               CASE WHEN s.area_sqft > 0 THEN round(s.price_aed / s.area_sqft, 2) END AS price_per_sqft,
               s.record_hash, s.updated_at AS source_updated_at
        FROM staging.listings s
        JOIN dw.dim_location l ON l.community = s.community AND l.city = s.city
        JOIN dw.dim_property_type p ON p.property_type = s.property_type
        WHERE s._batch_id = {b}""")

    changed = """FROM incoming i JOIN dw.fact_listings f USING (listing_id)
                 WHERE f.record_hash <> i.record_hash AND i.source_updated_at >= f.source_updated_at"""
    n_updated = con.execute(f"SELECT count(*) {changed}").fetchone()[0]
    n_new = con.execute("""SELECT count(*) FROM incoming i
                           WHERE NOT EXISTS (SELECT 1 FROM dw.fact_listings f WHERE f.listing_id = i.listing_id)""").fetchone()[0]

    # 3. keep price history for listings whose price moved
    con.execute(f"""
        INSERT INTO dw.fact_price_history
        SELECT f.listing_id, f.price_aed, f.source_updated_at, i.source_updated_at, {b}
        {changed} AND f.price_aed <> i.price_aed""")

    # 4. update changed rows, insert new ones
    con.execute(f"""
        UPDATE dw.fact_listings AS f SET
            location_key = i.location_key, property_type_key = i.property_type_key,
            listed_date_key = i.listed_date_key, purpose = i.purpose, bedrooms = i.bedrooms,
            bathrooms = i.bathrooms, price_aed = i.price_aed, area_sqft = i.area_sqft,
            price_per_sqft = i.price_per_sqft, record_hash = i.record_hash,
            source_updated_at = i.source_updated_at, last_loaded_at = now(), _batch_id = {b}
        FROM incoming i
        WHERE f.listing_id = i.listing_id AND f.record_hash <> i.record_hash
          AND i.source_updated_at >= f.source_updated_at""")
    con.execute(f"""
        INSERT INTO dw.fact_listings
        SELECT i.listing_id, i.location_key, i.property_type_key, i.listed_date_key, i.purpose,
               i.bedrooms, i.bathrooms, i.price_aed, i.area_sqft, i.price_per_sqft, i.record_hash,
               i.source_updated_at, now(), now(), {b}
        FROM incoming i
        WHERE NOT EXISTS (SELECT 1 FROM dw.fact_listings f WHERE f.listing_id = i.listing_id)""")
    print(f"[load] batch {b}: inserted={n_new} updated={n_updated}")
    return {"fact_inserted": n_new, "fact_updated": n_updated}
