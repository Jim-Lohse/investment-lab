#!/usr/bin/env python3
"""Sharadar -> DuckDB sync via Nasdaq Data Link.

First run per table is a bulk export (zipped CSV of the whole table, loaded
straight into DuckDB). Later runs are incremental: fetch only rows whose
`lastupdated` is at or after the local maximum, then replace-by-key.

Usage:
  python pocket-data/sharadar_sync.py                       # sync SF1 only
  python pocket-data/sharadar_sync.py --bundle              # all five tables
  python pocket-data/sharadar_sync.py --tables SF1,SEP      # explicit set
  python pocket-data/sharadar_sync.py --bulk SF1            # force re-export
  python pocket-data/sharadar_sync.py --status              # counts, no fetch

API key: NASDAQ_DATA_LINK_API_KEY in the environment, or a `.env` line.
The key is never printed. The database (default lab/data/sharadar.duckdb)
and downloads are gitignored — data stays local, per vendor terms.
"""

import argparse
import os
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = REPO_ROOT / "lab" / "data" / "sharadar.duckdb"
DOWNLOAD_DIR = REPO_ROOT / "lab" / "data" / "downloads"
PAGINATE_CAP = 1_000_000  # nasdaq-data-link get_table row ceiling per call

# mode "incremental": bulk on first load, lastupdated-delta + replace-by-key after.
# mode "full": small tables, re-exported wholesale every sync (no key games).
TABLES = {
    "SF1": {
        "code": "SHARADAR/SF1",
        "mode": "incremental",
        "key": ["ticker", "dimension", "datekey", "reportperiod"],
    },
    "SEP": {
        "code": "SHARADAR/SEP",
        "mode": "incremental",
        "key": ["ticker", "date"],
    },
    "SF2": {
        # SF2 has no clean natural key; this composite catches nearly all
        # rows. A periodic --bulk SF2 trues up any residue (see README).
        "code": "SHARADAR/SF2",
        "mode": "incremental",
        "key": ["ticker", "filingdate", "ownername", "transactiondate",
                "securityadcode", "transactioncode"],
    },
    "TICKERS": {"code": "SHARADAR/TICKERS", "mode": "full", "key": None},
    "ACTIONS": {"code": "SHARADAR/ACTIONS", "mode": "full", "key": None},
}
BUNDLE = ["SF1", "SEP", "TICKERS", "ACTIONS", "SF2"]


def load_api_key():
    key = os.environ.get("NASDAQ_DATA_LINK_API_KEY")
    if not key:
        env_file = REPO_ROOT / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line.startswith("NASDAQ_DATA_LINK_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip("'\"")
                    break
    if not key:
        sys.exit(
            "No API key. Set NASDAQ_DATA_LINK_API_KEY in the environment or "
            "in a .env line at the repo root (the .env file is gitignored)."
        )
    import nasdaqdatalink

    nasdaqdatalink.ApiConfig.api_key = key
    return nasdaqdatalink


def table_exists(con, name):
    return bool(
        con.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = ? AND table_schema = 'main'",
            [name],
        ).fetchone()
    )


def log_sync(con, name, action, rows):
    con.execute(
        "CREATE TABLE IF NOT EXISTS _sync_log ("
        "table_name VARCHAR, action VARCHAR, rows BIGINT, finished_at TIMESTAMP)"
    )
    con.execute(
        "INSERT INTO _sync_log VALUES (?, ?, ?, current_timestamp)",
        [name, action, rows],
    )


def bulk_load(ndl, con, name, spec):
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    zpath = DOWNLOAD_DIR / f"{name}.zip"
    print(f"  {name}: bulk export (whole table — the big first-run download)...")
    ndl.export_table(spec["code"], filename=str(zpath))
    with zipfile.ZipFile(zpath) as z:
        member = z.namelist()[0]
        z.extract(member, DOWNLOAD_DIR)
    csv_path = DOWNLOAD_DIR / member
    con.execute(
        f"CREATE OR REPLACE TABLE {name} AS "
        "SELECT * FROM read_csv_auto(?, sample_size=-1)",
        [str(csv_path)],
    )
    rows = con.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
    csv_path.unlink(missing_ok=True)
    zpath.unlink(missing_ok=True)
    log_sync(con, name, "bulk", rows)
    print(f"  {name}: loaded {rows:,} rows (bulk)")


def incremental_load(ndl, con, name, spec):
    has_lastupdated = con.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = ? AND column_name = 'lastupdated'",
        [name],
    ).fetchone()
    if not has_lastupdated:
        print(f"  {name}: local table has no lastupdated column — "
              "re-exporting wholesale instead of incrementally")
        return bulk_load(ndl, con, name, spec)
    cutoff = con.execute(f"SELECT max(lastupdated) FROM {name}").fetchone()[0]
    if cutoff is None:
        return bulk_load(ndl, con, name, spec)
    print(f"  {name}: incremental since {cutoff}...")
    df = ndl.get_table(
        spec["code"], lastupdated={"gte": str(cutoff)}, paginate=True
    )
    if df is None or len(df) == 0:
        log_sync(con, name, "incremental", 0)
        print(f"  {name}: no changes")
        return
    if len(df) >= PAGINATE_CAP:
        print(
            f"  {name}: WARNING — delta hit the {PAGINATE_CAP:,}-row API "
            f"ceiling and is likely truncated. Run --bulk {name} instead."
        )
        log_sync(con, name, "incremental-truncated", 0)
        return
    df = df.reset_index(drop=True)
    con.register("incoming", df)
    # Null-safe replace-by-key: drop local rows the delta supersedes, insert.
    cond = " AND ".join(
        f"{name}.{k} IS NOT DISTINCT FROM i.{k}" for k in spec["key"]
    )
    con.execute("BEGIN")
    con.execute(f"DELETE FROM {name} USING incoming i WHERE {cond}")
    con.execute(f"INSERT INTO {name} BY NAME SELECT * FROM incoming")
    con.execute("COMMIT")
    con.unregister("incoming")
    log_sync(con, name, "incremental", len(df))
    print(f"  {name}: merged {len(df):,} changed rows")


def status(con):
    print(f"{'table':<10}{'rows':>14}  {'max lastupdated':<18}")
    for name in TABLES:
        if not table_exists(con, name):
            print(f"{name:<10}{'—':>14}  not loaded")
            continue
        rows = con.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
        cols = {
            r[0]
            for r in con.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = ?",
                [name],
            ).fetchall()
        }
        lu = (
            con.execute(f"SELECT max(lastupdated) FROM {name}").fetchone()[0]
            if "lastupdated" in cols
            else "n/a"
        )
        print(f"{name:<10}{rows:>14,}  {lu}")
    if table_exists(con, "_sync_log"):
        print("\nlast five syncs:")
        for r in con.execute(
            "SELECT table_name, action, rows, finished_at FROM _sync_log "
            "ORDER BY finished_at DESC LIMIT 5"
        ).fetchall():
            print(f"  {r[3]}  {r[0]:<8} {r[1]:<22} {r[2]:>10,} rows")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tables", default="SF1",
                    help="comma-separated table names (default: SF1)")
    ap.add_argument("--bundle", action="store_true",
                    help=f"sync the Core US Equities Bundle: {','.join(BUNDLE)}")
    ap.add_argument("--bulk", default="",
                    help="comma-separated tables to force full re-export")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--status", action="store_true",
                    help="report local state, fetch nothing")
    args = ap.parse_args()

    try:
        import duckdb
    except ImportError:
        sys.exit("Missing deps: pip install -r pocket-data/requirements.txt")

    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(args.db)

    if args.status:
        status(con)
        return

    ndl = load_api_key()
    names = BUNDLE if args.bundle else [
        t.strip().upper() for t in args.tables.split(",") if t.strip()
    ]
    force_bulk = {t.strip().upper() for t in args.bulk.split(",") if t.strip()}
    unknown = [n for n in list(names) + sorted(force_bulk) if n not in TABLES]
    if unknown:
        sys.exit(f"Unknown table(s): {', '.join(unknown)}. "
                 f"Known: {', '.join(TABLES)}")

    failures = []
    for name in dict.fromkeys(list(names) + list(force_bulk)):
        spec = TABLES[name]
        try:
            if name in force_bulk or spec["mode"] == "full" \
                    or not table_exists(con, name):
                bulk_load(ndl, con, name, spec)
            else:
                incremental_load(ndl, con, name, spec)
        except Exception as e:  # entitlement, network, schema drift
            msg = str(e)
            hint = ""
            if "403" in msg or "Forbidden" in msg or "not authorized" in msg.lower():
                hint = " (looks like an entitlement gap — is this table in your subscription?)"
            failures.append(name)
            print(f"  {name}: FAILED — {msg}{hint}")

    print()
    status(con)
    if failures:
        sys.exit(f"\nSync incomplete; failed: {', '.join(failures)}")


if __name__ == "__main__":
    main()
