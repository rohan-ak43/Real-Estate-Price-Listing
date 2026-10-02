"""Central configuration. Paths can be overridden with environment variables."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("PIPELINE_DB", ROOT / "data" / "warehouse.duckdb"))
INBOX = Path(os.getenv("PIPELINE_INBOX", ROOT / "data" / "inbox"))
SQL_DIR = ROOT / "sql"

# Canonical raw columns. Every source file is mapped onto these (values untouched).
RAW_COLUMNS = [
    "listing_id", "title", "price", "area", "bedrooms", "bathrooms",
    "property_type", "purpose", "community", "city", "listed_date", "updated_at",
]

# Source header (lower-case) -> canonical column. EDIT THIS when you plug in a real
# dataset (e.g. a Kaggle Dubai listings CSV): map its headers to the names on the right.
COLUMN_MAP = {
    "id": "listing_id", "property_id": "listing_id", "ad_id": "listing_id",
    "name": "title",
    "price_aed": "price",
    "size": "area", "size_sqft": "area", "area_sqft": "area",
    "beds": "bedrooms", "no_of_bedrooms": "bedrooms",
    "baths": "bathrooms", "no_of_bathrooms": "bathrooms",
    "type": "property_type", "category": "property_type",
    "neighborhood": "community", "neighbourhood": "community", "location": "community",
    "date": "listed_date", "posted_date": "listed_date", "added_on": "listed_date",
    "last_updated": "updated_at",
}
