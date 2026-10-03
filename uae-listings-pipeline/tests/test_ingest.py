from src.ingest import derive_listing_id, read_source

HEADER = "price,type,beds,baths,address,furnishing,completion_status,post_date,area_name,city,purpose\n"
ROW = 'Apartment,1,2,"The Bay, Business Bay, Dubai",Furnished,Ready,2024-04-15,Business Bay,Dubai,For Sale\n'


def _csv(tmp_path, name, *prices):
    p = tmp_path / name
    p.write_text(HEADER + "".join(f"{pr},{ROW}" for pr in prices))
    return p


def test_listing_id_is_derived_and_stable(tmp_path):
    a = read_source(_csv(tmp_path, "a.csv", 1450000, 2000000))
    b = read_source(_csv(tmp_path, "b.csv", 1450000))
    assert a["listing_id"].str.startswith("DRV-").all()
    assert a.loc[0, "listing_id"] == b.loc[0, "listing_id"]            # same row -> same id
    assert a.loc[0, "listing_id"] != a.loc[1, "listing_id"]            # same unit details, other price -> distinct row kept
    assert a.loc[0, "listed_date"] == "2024-04-15" and a.loc[0, "community"] == "Business Bay"


def test_price_can_be_excluded_from_id(tmp_path):
    a = read_source(_csv(tmp_path, "a.csv", 1450000, 2000000))
    ids = derive_listing_id(a.assign(price=a["price"]), exclude=("price",))
    assert ids.nunique() == 1
