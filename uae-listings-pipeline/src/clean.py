"""STAGING layer: parse, standardise, reject bad rows (with a reason), deduplicate."""
import hashlib
import re
from datetime import datetime

import pandas as pd

SQFT_PER_SQM = 10.7639
NULLS = {"", "null", "none", "nan", "n/a", "na", "-", "ask for price"}
HASH_COLS = ["price_aed", "area_sqft", "bedrooms", "bathrooms", "property_type",
             "purpose", "community", "city", "listed_date"]


def nullify(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    s = str(x).strip()
    return None if s.lower() in NULLS else s


def parse_price(x):
    """'AED 1,250,000' | '1,250,000 AED' | '1.25M' | '850k' | '1250000' -> float AED."""
    s = nullify(x)
    if s is None:
        return None
    s = re.sub(r"(?i)\b(aed|dhs?)\b|د\.إ", "", s.replace(",", "")).strip()
    s = re.sub(r"(?i)^aed", "", s).strip()
    s = re.sub(r"(?i)aed$", "", s).strip()
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*([kKmM])?", s)
    if not m:
        return None
    return float(m.group(1)) * {"k": 1e3, "m": 1e6}.get((m.group(2) or "").lower(), 1)


def parse_area(x):
    """'1,200 sqft' | '1200 sq ft' | '111.5 sqm' | '111.5 m²' | '1200' -> float sqft."""
    s = nullify(x)
    if s is None:
        return None
    t = s.lower().replace(",", "")
    m = re.search(r"-?\d+(?:\.\d+)?", t)
    if not m:
        return None
    val = float(m.group(0))
    if re.search(r"sq\.?\s*m|m2|m²|meter|metre", t):
        val *= SQFT_PER_SQM
    return round(val, 2)


def parse_int(x):
    s = nullify(x)
    if s is None:
        return None
    if s.lower() == "studio":
        return 0
    m = re.search(r"\d+", s)
    return int(m.group(0)) if m else None


TYPE_MAP = {"apartment": "Apartment", "apt": "Apartment", "flat": "Apartment", "villa": "Villa",
            "townhouse": "Townhouse", "town house": "Townhouse", "th": "Townhouse",
            "penthouse": "Penthouse", "ph": "Penthouse"}
PURPOSE_MAP = {"sale": "Sale", "for sale": "Sale", "buy": "Sale",
               "rent": "Rent", "for rent": "Rent", "rental": "Rent"}
CITY_MAP = {"dubai": "Dubai", "dxb": "Dubai", "abu dhabi": "Abu Dhabi", "auh": "Abu Dhabi", "sharjah": "Sharjah"}
COMMUNITY_ALIASES = {"marina": "Dubai Marina", "jvc": "Jumeirah Village Circle",
                     "downtown": "Downtown Dubai", "jbr": "Jumeirah Beach Residence"}


def norm_type(x):
    s = nullify(x)
    return "Other" if s is None else TYPE_MAP.get(re.sub(r"\s+", " ", s.lower()), s.title())


def norm_purpose(x):
    s = nullify(x)
    return None if s is None else PURPOSE_MAP.get(s.lower())


def norm_city(x):
    s = nullify(x)
    return "Unknown" if s is None else CITY_MAP.get(s.lower(), s.title())


def norm_community(x):
    s = nullify(x)
    if s is None:
        return None
    s = re.sub(r"\s+", " ", s).strip()
    return COMMUNITY_ALIASES.get(s.lower(), s.title())


DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%b %d, %Y", "%d-%m-%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]


def parse_dt(x):
    s = nullify(x)
    if s is None:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _hash(row) -> str:
    return hashlib.md5("|".join(str(row[c]) for c in HASH_COLS).encode()).hexdigest()


def clean_batch(raw: pd.DataFrame):
    """raw (text) -> (clean, rejected, stats). Pure function: easy to unit-test."""
    df = raw.copy().reset_index(drop=True)
    df["_row"] = df.index
    out = pd.DataFrame({
        "listing_id": df["listing_id"].map(nullify),
        "title": df["title"].map(nullify),
        "price_aed": df["price"].map(parse_price),
        "area_sqft": df["area"].map(parse_area),
        "bedrooms": df["bedrooms"].map(parse_int),
        "bathrooms": df["bathrooms"].map(parse_int),
        "property_type": df["property_type"].map(norm_type),
        "purpose": df["purpose"].map(norm_purpose),
        "community": df["community"].map(norm_community),
        "city": df["city"].map(norm_city),
    })
    listed = [parse_dt(v) for v in df["listed_date"]]
    updated = [parse_dt(v) for v in df["updated_at"]]
    out["listed_date"] = pd.Series([d.date() if d else None for d in listed], dtype=object)
    out["updated_at"] = pd.Series([u or l for u, l in zip(updated, listed)], dtype=object)
    out.loc[out["area_sqft"].notna() & (out["area_sqft"] <= 0), "area_sqft"] = None
    out["_row"] = df["_row"]

    def reason(r):
        if pd.isna(r["listing_id"]): return "missing_listing_id"
        if pd.isna(r["community"]): return "missing_location"
        if pd.isna(r["price_aed"]) or r["price_aed"] <= 0: return "invalid_price"
        if pd.isna(r["listed_date"]): return "invalid_date"
        if pd.isna(r["purpose"]): return "invalid_purpose"
        return None

    out["reject_reason"] = out.apply(reason, axis=1)
    bad = out["reject_reason"].notna()
    rejected = raw.loc[bad.values].copy()
    rejected["reject_reason"] = out.loc[bad, "reject_reason"].values

    good = out.loc[~bad].sort_values(["updated_at", "_row"], ascending=False)
    deduped = good.drop_duplicates("listing_id", keep="first").drop(columns=["_row", "reject_reason"])
    deduped = deduped.reset_index(drop=True)
    deduped["record_hash"] = deduped.apply(_hash, axis=1) if len(deduped) else pd.Series(dtype=str)
    stats = {"rows_raw": len(raw), "rows_staged": len(deduped), "rows_rejected": int(bad.sum()),
             "rows_dup_removed": len(good) - len(deduped)}
    return deduped, rejected, stats


def stage_batch(con, batch_id: int) -> dict:
    """Read one raw batch, clean it, (re)write its staging rows. Idempotent per batch."""
    cols = ["listing_id", "title", "price", "area", "bedrooms", "bathrooms", "property_type",
            "purpose", "community", "city", "listed_date", "updated_at"]
    raw = con.execute(f"SELECT {', '.join(cols)} FROM raw.listings_raw WHERE _batch_id = ?", [batch_id]).df()
    clean, rejected, stats = clean_batch(raw)
    con.begin()
    try:
        con.execute("DELETE FROM staging.listings WHERE _batch_id = ?", [batch_id])
        con.execute("DELETE FROM staging.rejected WHERE _batch_id = ?", [batch_id])
        con.register("clean_df", clean)
        con.register("rej_df", rejected)
        con.execute("""
            INSERT INTO staging.listings
            SELECT listing_id, title, CAST(price_aed AS DOUBLE), CAST(area_sqft AS DOUBLE),
                   CAST(bedrooms AS INTEGER), CAST(bathrooms AS INTEGER), property_type, purpose,
                   community, city, CAST(listed_date AS DATE), CAST(updated_at AS TIMESTAMP),
                   record_hash, ? FROM clean_df""", [batch_id])
        con.execute(f"INSERT INTO staging.rejected SELECT {', '.join(cols)}, reject_reason, ? FROM rej_df", [batch_id])
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.unregister("clean_df")
        con.unregister("rej_df")
    print(f"[clean] batch {batch_id}: {stats}")
    return stats
