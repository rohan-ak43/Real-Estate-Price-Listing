import pandas as pd
import pytest

from src.clean import clean_batch, norm_city, norm_community, norm_type, parse_area, parse_dt, parse_int, parse_price


@pytest.mark.parametrize("raw,expected", [
    ("AED 1,250,000", 1_250_000), ("1,250,000 AED", 1_250_000), ("AED1250000", 1_250_000),
    ("1.25M", 1_250_000), ("850k", 850_000), ("1250000", 1_250_000), ("-5", -5),
    ("", None), ("Ask for price", None), ("abc", None), (None, None),
])
def test_parse_price(raw, expected):
    assert parse_price(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("1,200 sqft", 1200), ("1200 sq ft", 1200), ("1200", 1200),
    ("100 sqm", 1076.39), ("100 m²", 1076.39), ("", None),
])
def test_parse_area(raw, expected):
    assert parse_area(raw) == expected


def test_parse_int_and_normalisers():
    assert parse_int("Studio") == 0 and parse_int("3 BR") == 3 and parse_int("") is None
    assert norm_type(" APT ") == "Apartment" and norm_type("Town House") == "Townhouse"
    assert norm_city("DXB") == "Dubai" and norm_city("") == "Unknown"
    assert norm_community("  dubai   marina ") == "Dubai Marina" and norm_community("JVC") == "Jumeirah Village Circle"
    assert norm_community("N/A") is None


def test_parse_dt_formats():
    assert parse_dt("14/03/2026").date().isoformat() == "2026-03-14"
    assert parse_dt("Mar 14, 2026").date().isoformat() == "2026-03-14"
    assert parse_dt("2026-03-14T10:00:00").hour == 10 and parse_dt("garbage") is None


def _raw(**kw):
    base = dict(listing_id="A1", title="t", price="AED 1,000,000", area="1000 sqft", bedrooms="2",
                bathrooms="2", property_type="apartment", purpose="For Sale", community="Dubai Marina",
                city="dubai", listed_date="2026-01-01", updated_at="2026-01-02 10:00:00")
    base.update(kw)
    return base


def test_clean_batch_rejects_dedupes_and_keeps_latest():
    raw = pd.DataFrame([
        _raw(),                                                       # older version of A1
        _raw(price="1.1M", updated_at="2026-02-01 10:00:00"),         # latest A1 -> kept
        _raw(listing_id="B1", community=""),                          # missing location
        _raw(listing_id="C1", price="-100"),                          # invalid price
        _raw(listing_id="D1", price="Ask for price"),                 # invalid price
        _raw(listing_id="E1", purpose="???"),                         # invalid purpose
    ])
    clean, rejected, stats = clean_batch(raw)
    assert stats == {"rows_raw": 6, "rows_staged": 1, "rows_rejected": 4, "rows_dup_removed": 1}
    assert clean.loc[0, "price_aed"] == 1_100_000 and clean.loc[0, "purpose"] == "Sale"
    assert set(rejected["reject_reason"]) == {"missing_location", "invalid_price", "invalid_purpose"}
    assert stats["rows_staged"] + stats["rows_rejected"] + stats["rows_dup_removed"] == stats["rows_raw"]


def test_community_casing_is_preserved_when_mixed():
    assert norm_community("Jumeirah Village Circle (JVC)") == "Jumeirah Village Circle (JVC)"
    assert norm_community("DAMAC Hills") == "DAMAC Hills"
    assert norm_community("DUBAI MARINA") == "Dubai Marina" and norm_community("business bay") == "Business Bay"
