import pandas as pd

from src.ingest import read_source

HEADER = "price,type,beds,baths,address,furnishing,completion_status,post_date,area_name,city,purpose\n"


def test_listing_id_is_derived_stable_and_price_independent(tmp_path):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    a.write_text(HEADER + "1450000,Apartment,1,2,\"The Bay, Business Bay, Dubai\",Furnished,Ready,2024-04-15,Business Bay,Dubai,For Sale\n"
                          "2000000,Villa,4,5,\"X, Arabian Ranches, Dubai\",Unfurnished,Ready,2024-04-16,Arabian Ranches,Dubai,For Sale\n")
    b.write_text(HEADER + "1500000,Apartment,1,2,\"The Bay, Business Bay, Dubai\",Furnished,Ready,2024-04-15,Business Bay,Dubai,For Sale\n")
    da, db_ = read_source(a), read_source(b)
    assert da["listing_id"].str.startswith("DRV-").all() and da["listing_id"].nunique() == 2
    assert da.loc[0, "listing_id"] == db_.loc[0, "listing_id"]          # price changed, same listing
    assert da.loc[0, "listed_date"] == "2024-04-15" and da.loc[0, "community"] == "Business Bay"
