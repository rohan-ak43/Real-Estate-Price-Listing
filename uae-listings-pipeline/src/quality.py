"""Automated data-quality checks. 'error' failures roll the warehouse load back; 'warn' only reports."""
from dataclasses import dataclass


@dataclass
class Check:
    name: str
    severity: str  # error | warn
    passed: bool
    detail: str


def run_checks(con, batch_id: int, stats: dict) -> list[Check]:
    one = lambda sql, *p: con.execute(sql, list(p)).fetchone()[0]
    out: list[Check] = []

    def add(name, severity, passed, detail):
        out.append(Check(name, severity, bool(passed), detail))

    # reconciliation: nothing silently lost between raw and staging
    accounted = stats["rows_staged"] + stats["rows_rejected"] + stats["rows_dup_removed"]
    add("row_count_reconciliation", "error", accounted == stats["rows_raw"],
        f"raw={stats['rows_raw']} staged+rejected+dups={accounted}")

    n = one("SELECT count(*) FROM dw.fact_listings WHERE price_aed IS NULL OR price_aed <= 0")
    add("no_non_positive_prices", "error", n == 0, f"{n} offending rows")

    n = one("""SELECT count(*) FROM dw.fact_listings f LEFT JOIN dw.dim_location l USING (location_key)
               WHERE l.location_key IS NULL OR trim(l.community) = ''""")
    add("no_null_locations", "error", n == 0, f"{n} offending rows")

    n = one("SELECT count(*) - count(DISTINCT listing_id) FROM dw.fact_listings")
    add("unique_listing_id", "error", n == 0, f"{n} duplicate ids")

    n = one("""SELECT count(*) FROM dw.fact_listings f
               LEFT JOIN dw.dim_property_type p USING (property_type_key)
               LEFT JOIN dw.dim_date d ON d.date_key = f.listed_date_key
               WHERE p.property_type_key IS NULL OR d.date_key IS NULL""")
    add("referential_integrity", "error", n == 0, f"{n} orphan rows")

    fact = one("SELECT count(*) FROM dw.fact_listings")
    expected = one("""SELECT count(DISTINCT listing_id) FROM staging.listings
                      WHERE _batch_id = ? OR _batch_id IN
                        (SELECT batch_id FROM ops.pipeline_runs WHERE status = 'success')""", batch_id)
    add("fact_rowcount_matches_staging", "error", fact == expected, f"fact={fact} distinct staged ids={expected}")

    bad = one("""SELECT count(*) FROM dw.fact_listings WHERE price_per_sqft IS NOT NULL AND NOT (
                   (purpose = 'Sale' AND price_per_sqft BETWEEN 300 AND 8000) OR
                   (purpose = 'Rent' AND price_per_sqft BETWEEN 15 AND 700))""")
    pct = 100 * bad / max(fact, 1)
    add("price_per_sqft_plausible", "warn", pct <= 1.0, f"{bad} rows ({pct:.2f}%) outside plausible range")

    rate = 100 * stats["rows_rejected"] / max(stats["rows_raw"], 1)
    add("reject_rate_below_10pct", "warn", rate <= 10, f"{rate:.1f}% of raw rows rejected")
    return out


def has_errors(checks: list[Check]) -> bool:
    return any(c.severity == "error" and not c.passed for c in checks)
