"""End-to-end: idempotency, incremental loads, price history, rollback on failed quality checks."""
import duckdb

from src import pipeline
from src.generate_sample_data import make_batch


def _fact_count(db):
    con = duckdb.connect(str(db), read_only=True)
    try:
        return con.execute("SELECT count(*) FROM dw.fact_listings").fetchone()[0]
    finally:
        con.close()


def test_incremental_pipeline(tmp_path):
    inbox, db = tmp_path / "inbox", tmp_path / "wh.duckdb"
    inbox.mkdir()
    make_batch(1).to_csv(inbox / "b1.csv", index=False)
    assert pipeline.run(db, inbox)
    n1 = _fact_count(db)
    assert n1 > 4000

    assert pipeline.run(db, inbox)                 # nothing new -> nothing changes
    assert _fact_count(db) == n1

    make_batch(2).to_csv(inbox / "b2.csv", index=False)
    assert pipeline.run(db, inbox)
    con = duckdb.connect(str(db), read_only=True)
    assert con.execute("SELECT count(*) FROM dw.fact_listings").fetchone()[0] > n1
    assert con.execute("SELECT count(*) FROM dw.fact_price_history").fetchone()[0] > 0
    assert con.execute("SELECT count(*) - count(DISTINCT listing_id) FROM dw.fact_listings").fetchone()[0] == 0
    assert con.execute("SELECT count(*) FROM ops.pipeline_runs WHERE status = 'success'").fetchone()[0] == 2
    con.close()


def test_failed_quality_check_rolls_back(tmp_path, monkeypatch):
    inbox, db = tmp_path / "inbox", tmp_path / "wh.duckdb"
    inbox.mkdir()
    make_batch(1).to_csv(inbox / "b1.csv", index=False)

    real = pipeline.warehouse.load_batch

    def corrupt(con, batch_id):                    # simulate a bug that lets a bad price through
        res = real(con, batch_id)
        con.execute("UPDATE dw.fact_listings SET price_aed = -1 WHERE listing_id = (SELECT min(listing_id) FROM dw.fact_listings)")
        return res

    monkeypatch.setattr(pipeline.warehouse, "load_batch", corrupt)
    assert pipeline.run(db, inbox) is False
    assert _fact_count(db) == 0                    # nothing was published
    con = duckdb.connect(str(db), read_only=True)
    assert con.execute("SELECT status FROM ops.pipeline_runs").fetchone()[0] == "failed_dq"
    assert con.execute("SELECT count(*) FROM ops.dq_results WHERE NOT passed AND check_name = 'no_non_positive_prices'").fetchone()[0] == 1
    con.close()
