import duckdb
from pathlib import Path
from .config import DB_PATH, SQL_DIR


def connect(db_path: Path | str | None = None) -> duckdb.DuckDBPyConnection:
    path = Path(db_path or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    init_schema(con)
    return con


def init_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Idempotent: creates schemas/tables/views if missing and seeds dim_date once."""
    con.execute((SQL_DIR / "schema.sql").read_text())
