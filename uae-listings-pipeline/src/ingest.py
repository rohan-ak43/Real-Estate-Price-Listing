"""RAW layer: land source CSVs exactly as received (all text) + log them for idempotency."""
import hashlib
from pathlib import Path

import pandas as pd

from .config import COLUMN_MAP, INBOX, RAW_COLUMNS


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_source(path: Path) -> pd.DataFrame:
    """Read a CSV as text and map headers onto canonical raw columns. Values are NOT altered."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df.columns = [COLUMN_MAP.get(c.strip().lower(), c.strip().lower()) for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    for col in RAW_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[RAW_COLUMNS]


def ingest(con, inbox: Path | None = None) -> list[int]:
    """Load every not-yet-seen CSV in the inbox. Returns the new batch ids."""
    inbox = Path(inbox or INBOX)
    new_batches = []
    for f in sorted(inbox.glob("*.csv")):
        sha = _sha256(f)
        if con.execute("SELECT 1 FROM raw.ingest_log WHERE file_sha256 = ?", [sha]).fetchone():
            continue  # already loaded -> idempotent
        df = read_source(f)
        batch_id = con.execute("SELECT coalesce(max(batch_id), 0) + 1 FROM raw.ingest_log").fetchone()[0]
        con.register("df_in", df)
        con.begin()
        try:
            cols = ", ".join(RAW_COLUMNS)
            con.execute(f"INSERT INTO raw.listings_raw SELECT {cols}, ?, ?, now() FROM df_in", [batch_id, f.name])
            con.execute("INSERT INTO raw.ingest_log VALUES (?, ?, ?, ?, now())", [batch_id, f.name, sha, len(df)])
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.unregister("df_in")
        print(f"[ingest] {f.name}: {len(df)} rows -> batch {batch_id}")
        new_batches.append(batch_id)
    return new_batches
