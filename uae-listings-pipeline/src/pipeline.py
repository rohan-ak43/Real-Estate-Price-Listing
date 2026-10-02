"""Orchestrator: ingest -> clean -> (transaction: load -> quality checks -> commit | rollback).

    python -m src.pipeline            # exit code 1 if any batch fails error-level checks
"""
import sys
from datetime import datetime
import traceback
from pathlib import Path

from . import clean, ingest, quality, warehouse
from .db import connect

COUNTS = ["rows_raw", "rows_staged", "rows_rejected", "rows_dup_removed"]


def _record(con, run_id, batch_id, started, stats, load, status, checks):
    con.execute("INSERT INTO ops.pipeline_runs VALUES (?, ?, ?, now(), ?, ?, ?, ?, ?, ?, ?)",
                [run_id, batch_id, started, *(stats.get(k) for k in COUNTS),
                 load.get("fact_inserted"), load.get("fact_updated"), status])
    for c in checks:
        con.execute("INSERT INTO ops.dq_results VALUES (?, ?, ?, ?, ?, ?, now())",
                    [run_id, batch_id, c.name, c.severity, c.passed, c.detail])


def process_batch(con, batch_id: int) -> bool:
    run_id = con.execute("SELECT coalesce(max(run_id), 0) + 1 FROM ops.pipeline_runs").fetchone()[0]
    started = datetime.now()
    stats, load, checks = {}, {}, []
    try:
        stats = clean.stage_batch(con, batch_id)
        con.begin()                                   # write-audit-publish
        load = warehouse.load_batch(con, batch_id)
        checks = quality.run_checks(con, batch_id, stats)
        if quality.has_errors(checks):
            con.rollback()
            status = "failed_dq"
        else:
            con.commit()
            status = "success"
    except Exception:
        try:
            con.rollback()
        except Exception:
            pass
        traceback.print_exc()
        status = "error"
    _record(con, run_id, batch_id, started, stats, load if status == "success" else {}, status, checks)
    for c in checks:
        print(f"[dq] {'PASS' if c.passed else 'FAIL'} ({c.severity}) {c.name}: {c.detail}")
    print(f"[run] batch {batch_id}: {status}")
    return status == "success"


def run(db_path=None, inbox: Path | None = None) -> bool:
    con = connect(db_path)
    try:
        ingest.ingest(con, inbox)
        pending = [r[0] for r in con.execute("""
            SELECT batch_id FROM raw.ingest_log
            WHERE batch_id NOT IN (SELECT batch_id FROM ops.pipeline_runs WHERE status = 'success')
            ORDER BY batch_id""").fetchall()]
        if not pending:
            print("[run] nothing to do: no new or failed batches")
        return all([process_batch(con, b) for b in pending])
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
