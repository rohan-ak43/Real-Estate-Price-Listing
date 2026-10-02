"""Generate deliberately messy UAE property-listing CSVs (SYNTHETIC data).

Batch 1 = full history. Batch N>1 = new listings + price changes on existing ones
(+ duplicates / stale versions), so you can demo incremental loads.

    python -m src.generate_sample_data --batch 1
    python -m src.generate_sample_data --batch 2
"""
import argparse
import random
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from .config import INBOX

SEED, N_BASE, N_NEW, N_CHANGED = 42, 5000, 300, 250
FIRST_AS_OF = date(2026, 9, 30)

# community, city, sale AED/sqft, weight, villa share
LOCATIONS = [
    ("Downtown Dubai", "Dubai", 2400, 8, 0.0), ("Dubai Marina", "Dubai", 1750, 11, 0.0),
    ("Palm Jumeirah", "Dubai", 2900, 6, 0.25), ("Business Bay", "Dubai", 1850, 10, 0.0),
    ("Jumeirah Village Circle", "Dubai", 1150, 13, 0.05), ("Dubai Hills Estate", "Dubai", 1950, 7, 0.35),
    ("Arabian Ranches", "Dubai", 1300, 4, 0.8), ("Jumeirah Beach Residence", "Dubai", 1850, 5, 0.0),
    ("Dubai Silicon Oasis", "Dubai", 950, 5, 0.0), ("Al Barsha South", "Dubai", 1000, 4, 0.0),
    ("Mirdif", "Dubai", 1050, 4, 0.6), ("Damac Hills", "Dubai", 1250, 5, 0.45),
    ("Yas Island", "Abu Dhabi", 1500, 4, 0.2), ("Saadiyat Island", "Abu Dhabi", 2300, 3, 0.3),
    ("Al Reem Island", "Abu Dhabi", 1350, 5, 0.0), ("Al Majaz", "Sharjah", 900, 3, 0.0),
]
ALIASES = {"Dubai Marina": "Marina", "Jumeirah Village Circle": "JVC",
           "Downtown Dubai": "Downtown", "Jumeirah Beach Residence": "JBR"}
TYPE_MULT = {"Apartment": 1.0, "Villa": 0.8, "Townhouse": 0.85, "Penthouse": 1.25}
TYPE_VARIANTS = {
    "Apartment": ["Apartment", "apartment", "Apt", "APARTMENT ", "Flat"],
    "Villa": ["Villa", "villa", "VILLA", " Villa"],
    "Townhouse": ["Townhouse", "Town House", "townhouse", "TH"],
    "Penthouse": ["Penthouse", "penthouse", "PH"],
}
PURPOSE_VARIANTS = {"Sale": ["Sale", "For Sale", "sale", "Buy"], "Rent": ["Rent", "For Rent", "rent", "Rental"]}
CITY_VARIANTS = {"Dubai": ["Dubai", "dubai", "DUBAI ", "DXB"], "Abu Dhabi": ["Abu Dhabi", "abu dhabi", "AUH"],
                 "Sharjah": ["Sharjah", "sharjah"]}


def _listing(i: int, rng: random.Random, nprng: np.random.Generator, as_of: date, listed: date | None = None) -> dict:
    comm, city, ppsf, _, villa = rng.choices(LOCATIONS, weights=[l[3] for l in LOCATIONS])[0]
    r = rng.random()
    if r < villa:
        ptype = "Villa" if rng.random() < 0.7 else "Townhouse"
    elif villa < 0.2 and r > 0.97:
        ptype = "Penthouse"
    else:
        ptype = "Apartment"
    beds = {
        "Apartment": rng.choices([0, 1, 2, 3, 4], [.12, .33, .33, .17, .05])[0],
        "Villa": rng.choices([3, 4, 5, 6], [.2, .35, .3, .15])[0],
        "Townhouse": rng.choices([2, 3, 4], [.25, .5, .25])[0],
        "Penthouse": rng.choices([3, 4, 5], [.4, .4, .2])[0],
    }[ptype]
    base_area = {"Apartment": 380 + beds * 330, "Villa": 2200 + beds * 500,
                 "Townhouse": 1500 + beds * 350, "Penthouse": 2000 + beds * 400}[ptype]
    area = round(base_area * float(nprng.lognormal(0, 0.12)))
    purpose = "Sale" if rng.random() < 0.45 else "Rent"
    noise = float(nprng.lognormal(0, 0.18))
    if purpose == "Sale":
        price = round(area * ppsf * TYPE_MULT[ptype] * noise / 5000) * 5000
    else:
        price = round(area * ppsf * TYPE_MULT[ptype] * rng.uniform(0.05, 0.08) * noise / 1000) * 1000
    listed = listed or as_of - timedelta(days=rng.randint(0, 364))
    upd = min(as_of, listed + timedelta(days=rng.randint(0, 10)))
    return dict(
        listing_id=f"LST-{i:06d}",
        title=("Studio" if beds == 0 else f"{beds}BR") + f" {ptype} in {comm}",
        price=float(max(price, 1000)), area=float(area), bedrooms=beds, bathrooms=max(1, min(beds + 1, 7)),
        property_type=ptype, purpose=purpose, community=comm, city=city, listed_date=listed,
        updated_at=datetime.combine(upd, datetime.min.time()) + timedelta(seconds=rng.randint(0, 86399)),
    )


def make_base() -> pd.DataFrame:
    rng, nprng = random.Random(SEED), np.random.default_rng(SEED)
    return pd.DataFrame([_listing(i, rng, nprng, FIRST_AS_OF) for i in range(1, N_BASE + 1)])


def _dirty_row(r: dict, rng: random.Random) -> dict:
    """Turn a clean listing into a messy string-only row."""
    p = r["price"]
    price = rng.choice([
        lambda: f"{p:.0f}", lambda: f"AED {p:,.0f}", lambda: f"{p:,.0f} AED", lambda: f"AED{p:.0f}",
        (lambda: f"{p / 1e6:g}M") if p % 10000 == 0 else (lambda: f"{p:.0f}"),
    ])()
    a = r["area"]
    area = rng.choice([
        lambda: f"{a:.0f}", lambda: f"{a:,.0f} sqft", lambda: f"{a:.0f} sq ft",
        lambda: f"{a / 10.7639:.1f} sqm", lambda: f"{a / 10.7639:.1f} m²",
    ])()
    b = r["bedrooms"]
    beds = rng.choice(["Studio", "studio", "0"]) if b == 0 else rng.choice([str(b), f"{b} BR", f"{b} Beds"])
    comm = r["community"]
    cv = rng.random()
    comm = (ALIASES.get(comm, comm) if cv < 0.08 else comm.lower() if cv < 0.16
            else comm.upper() if cv < 0.22 else comm + "  " if cv < 0.26 else comm)
    ld, ua = r["listed_date"], r["updated_at"]
    ld_s = rng.choice([ld.strftime("%Y-%m-%d"), ld.strftime("%d/%m/%Y"), ld.strftime("%b %d, %Y")])
    ua_s = rng.choice([ua.strftime("%Y-%m-%d %H:%M:%S"), ua.strftime("%Y-%m-%dT%H:%M:%S")])
    row = dict(
        listing_id=r["listing_id"], title=r["title"], price=price, area=area, bedrooms=beds,
        bathrooms=str(r["bathrooms"]), property_type=rng.choice(TYPE_VARIANTS[r["property_type"]]),
        purpose=rng.choice(PURPOSE_VARIANTS[r["purpose"]]), community=comm,
        city=rng.choice(CITY_VARIANTS[r["city"]]), listed_date=ld_s, updated_at=ua_s,
    )
    # injected defects
    if rng.random() < 0.03:
        row["community"] = rng.choice(["", "N/A", "null"])
    x = rng.random()
    if x < 0.012:
        row["price"] = rng.choice(["-1", "0", "-250000"])
    elif x < 0.022:
        row["price"] = rng.choice(["", "Ask for price"])
    if rng.random() < 0.02:
        row["area"] = ""
    return row


def dirtify(df: pd.DataFrame, seed: int) -> pd.DataFrame:
    rng = random.Random(seed)
    rows = [_dirty_row(r, rng) for r in df.to_dict("records")]
    extra = []
    for r in rng.sample(rows, int(len(rows) * 0.05)):          # exact duplicates
        extra.append(dict(r))
    for src in rng.sample(df.to_dict("records"), int(len(df) * 0.02)):  # stale older versions
        old = dict(src, price=round(src["price"] * 1.05 / 1000) * 1000,
                   updated_at=src["updated_at"] - timedelta(days=3))
        extra.append(_dirty_row(old, rng))
    out = pd.DataFrame(rows + extra)
    return out.sample(frac=1, random_state=seed).reset_index(drop=True)


def make_batch(batch: int) -> pd.DataFrame:
    base = make_base()
    if batch == 1:
        return dirtify(base, SEED)
    as_of = FIRST_AS_OF + timedelta(days=batch - 1)
    rng, nprng = random.Random(SEED + batch), np.random.default_rng(SEED + batch)
    start = N_BASE + 1 + (batch - 2) * N_NEW
    new = pd.DataFrame([_listing(start + k, rng, nprng, as_of, listed=as_of) for k in range(N_NEW)])
    changed = base.sample(N_CHANGED, random_state=SEED + batch).copy()
    changed["price"] = [round(p * rng.uniform(0.9, 1.1) / 1000) * 1000 or 1000 for p in changed["price"]]
    changed["updated_at"] = [datetime.combine(as_of, datetime.min.time()) + timedelta(seconds=rng.randint(0, 86399))
                             for _ in range(len(changed))]
    return dirtify(pd.concat([new, changed], ignore_index=True), SEED + batch)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--out", default=str(INBOX))
    args = ap.parse_args()
    from pathlib import Path
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    df = make_batch(args.batch)
    path = out / f"listings_batch_{args.batch:03d}.csv"
    df.to_csv(path, index=False)
    print(f"wrote {path} ({len(df)} rows)")


if __name__ == "__main__":
    main()
