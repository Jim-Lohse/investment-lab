"""Sync engine: Nasdaq Data Link bulk/filtered table exports -> DuckDB.

First run per table is a bulk export (zipped CSV) loaded whole. Later runs
export only rows with ``lastupdated`` >= the newest value already stored and
upsert them, so refreshes are small and fast. Both paths use the same
``export_table`` endpoint, which has no row-count ceiling (unlike paginated
``get_table``).
"""

import logging
import os
import tempfile
import zipfile

import duckdb

from .config import DEFAULT_DB_PATH, SCHEMA, STATE_TABLE, TableSpec

log = logging.getLogger("nasdaq_data_link")


def configure_api_key() -> None:
    """Point the client at the API key from env or the standard key file."""
    import nasdaqdatalink

    key = os.environ.get("NASDAQ_DATA_LINK_API_KEY")
    if key:
        nasdaqdatalink.ApiConfig.api_key = key
        return
    try:
        nasdaqdatalink.read_key()
    except Exception:
        pass
    if not nasdaqdatalink.ApiConfig.api_key:
        raise SystemExit(
            "No API key found. Set NASDAQ_DATA_LINK_API_KEY, or store the key "
            "with: python -c \"import nasdaqdatalink; nasdaqdatalink.save_key('YOUR_KEY')\""
        )


def fetch_csvs(spec: TableSpec, workdir: str, **filters) -> list[str]:
    """Export a datatable (optionally filtered) and return extracted CSV paths.

    ``export_table`` blocks while Nasdaq generates the file, then downloads a
    zip containing one or more CSVs.
    """
    import nasdaqdatalink

    zip_path = os.path.join(workdir, f"{spec.name}.zip")
    nasdaqdatalink.export_table(spec.code, filename=zip_path, **filters)
    with zipfile.ZipFile(zip_path) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise RuntimeError(f"{spec.code}: export zip contained no CSV files")
        zf.extractall(workdir)
    return [os.path.join(workdir, n) for n in names]


def connect(db_path: str = DEFAULT_DB_PATH) -> duckdb.DuckDBPyConnection:
    dirname = os.path.dirname(db_path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    con = duckdb.connect(db_path)
    con.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')
    con.execute(
        f'CREATE TABLE IF NOT EXISTS "{SCHEMA}"."{STATE_TABLE}" ('
        "  table_name VARCHAR, synced_at TIMESTAMP DEFAULT current_timestamp,"
        "  mode VARCHAR, rows BIGINT, watermark VARCHAR)"
    )
    return con


def _qualified(spec: TableSpec) -> str:
    return f'"{SCHEMA}"."{spec.name}"'


def _table_exists(con, spec: TableSpec) -> bool:
    return bool(
        con.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = ? AND table_name = ?",
            [SCHEMA, spec.name],
        ).fetchone()
    )


def _watermark(con, spec: TableSpec) -> str | None:
    if spec.strategy != "incremental" or not _table_exists(con, spec):
        return None
    value = con.execute(
        f'SELECT max("{spec.watermark}") FROM {_qualified(spec)}'
    ).fetchone()[0]
    return None if value is None else str(value)


def _load_full(con, spec: TableSpec, csv_paths: list[str]) -> int:
    con.execute(
        f"CREATE OR REPLACE TABLE {_qualified(spec)} AS "
        "SELECT * FROM read_csv_auto(?, union_by_name=true)",
        [csv_paths],
    )
    return con.execute(f"SELECT count(*) FROM {_qualified(spec)}").fetchone()[0]


def _upsert(con, spec: TableSpec, csv_paths: list[str]) -> int:
    """Delete stored rows matching incoming key tuples, then insert the batch."""
    con.execute(
        "CREATE OR REPLACE TEMP TABLE incoming AS "
        "SELECT * FROM read_csv_auto(?, union_by_name=true)",
        [csv_paths],
    )
    n = con.execute("SELECT count(*) FROM incoming").fetchone()[0]
    if n == 0:
        return 0

    target_cols = dict(
        con.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = ? AND table_name = ? ORDER BY ordinal_position",
            [SCHEMA, spec.name],
        ).fetchall()
    )
    incoming_cols = {
        row[0]: row[1] for row in con.execute("DESCRIBE incoming").fetchall()
    }
    # Vendor added a column since the bulk load: extend the target table.
    for col, dtype in incoming_cols.items():
        if col not in target_cols:
            log.info("%s: new column %s (%s)", spec.name, col, dtype)
            con.execute(f'ALTER TABLE {_qualified(spec)} ADD COLUMN "{col}" {dtype}')
            target_cols[col] = dtype

    missing_keys = [k for k in spec.key if k not in incoming_cols]
    if missing_keys:
        raise RuntimeError(
            f"{spec.name}: key column(s) {missing_keys} absent from incoming batch"
        )

    match = " AND ".join(
        f't."{k}" IS NOT DISTINCT FROM i."{k}"' for k in spec.key
    )
    con.execute(
        f"DELETE FROM {_qualified(spec)} t "
        f"WHERE EXISTS (SELECT 1 FROM incoming i WHERE {match})"
    )
    # Cast explicitly to the target's types: a small incremental batch can
    # make read_csv_auto infer narrower/looser types than the bulk load did.
    select = ", ".join(
        f'CAST(i."{col}" AS {dtype}) AS "{col}"' if col in incoming_cols else f'NULL AS "{col}"'
        for col, dtype in target_cols.items()
    )
    cols = ", ".join(f'"{c}"' for c in target_cols)
    con.execute(f"INSERT INTO {_qualified(spec)} ({cols}) SELECT {select} FROM incoming i")
    con.execute("DROP TABLE incoming")
    return n


def _record(con, spec: TableSpec, mode: str, rows: int) -> None:
    con.execute(
        f'INSERT INTO "{SCHEMA}"."{STATE_TABLE}" (table_name, mode, rows, watermark) '
        "VALUES (?, ?, ?, ?)",
        [spec.name, mode, rows, _watermark(con, spec)],
    )


def sync_table(con, spec: TableSpec, full: bool = False) -> tuple[str, int]:
    """Sync one table; returns (mode, row count touched)."""
    watermark = None if full else _watermark(con, spec)
    incremental = spec.strategy == "incremental" and watermark is not None

    with tempfile.TemporaryDirectory(prefix=f"ndl_{spec.name}_") as workdir:
        if incremental:
            log.info("%s: incremental export, %s >= %s", spec.name, spec.watermark, watermark)
            csvs = fetch_csvs(spec, workdir, **{spec.watermark: {"gte": watermark}})
            rows = _upsert(con, spec, csvs)
            mode = "incremental"
        else:
            log.info("%s: full export of %s", spec.name, spec.code)
            csvs = fetch_csvs(spec, workdir)
            rows = _load_full(con, spec, csvs)
            mode = "full"

    _record(con, spec, mode, rows)
    log.info("%s: %s sync complete, %d rows", spec.name, mode, rows)
    return mode, rows


def sync(specs: list[TableSpec], db_path: str = DEFAULT_DB_PATH, full: bool = False) -> dict:
    """Sync several tables, isolating entitlement/API failures per table."""
    from nasdaqdatalink import AuthenticationError, ForbiddenError

    configure_api_key()
    con = connect(db_path)
    results = {}
    try:
        for spec in specs:
            try:
                results[spec.name] = sync_table(con, spec, full=full)
            except AuthenticationError:
                raise SystemExit("API key rejected by Nasdaq Data Link (authentication error).")
            except ForbiddenError:
                log.warning(
                    "%s: subscription does not cover %s — skipped. "
                    "(SF1-only covers the 'fundamentals' preset; SEP/SF2 need the bundle.)",
                    spec.name, spec.code,
                )
                results[spec.name] = ("forbidden", 0)
            except Exception as exc:  # keep one bad table from killing the run
                log.error("%s: sync failed: %s", spec.name, exc)
                results[spec.name] = ("error", 0)
    finally:
        con.close()
    return results


def status(db_path: str = DEFAULT_DB_PATH) -> list[dict]:
    """Per-table row counts, data watermarks, and last sync info."""
    if not os.path.exists(db_path):
        return []
    con = duckdb.connect(db_path, read_only=True)
    try:
        from .config import TABLES

        out = []
        for spec in TABLES.values():
            if not _table_exists(con, spec):
                continue
            rows = con.execute(f"SELECT count(*) FROM {_qualified(spec)}").fetchone()[0]
            last = con.execute(
                f'SELECT synced_at, mode, rows FROM "{SCHEMA}"."{STATE_TABLE}" '
                "WHERE table_name = ? ORDER BY synced_at DESC LIMIT 1",
                [spec.name],
            ).fetchone()
            out.append({
                "table": spec.name,
                "rows": rows,
                "watermark": _watermark(con, spec),
                "last_sync": str(last[0]) if last else None,
                "last_mode": last[1] if last else None,
                "last_rows": last[2] if last else None,
            })
        return out
    finally:
        con.close()
