"""CLI for the Nasdaq Data Link (Sharadar) connector.

Examples:
    python -m connectors.nasdaq_data_link sync                      # SF1 only
    python -m connectors.nasdaq_data_link sync --tables fundamentals
    python -m connectors.nasdaq_data_link sync --tables bundle
    python -m connectors.nasdaq_data_link sync --tables sf1,sep --full
    python -m connectors.nasdaq_data_link status
"""

import argparse
import logging

from .config import DEFAULT_DB_PATH, PRESETS, TABLES, resolve_tables
from .connector import status, sync


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m connectors.nasdaq_data_link",
        description="Sync Sharadar tables from Nasdaq Data Link into DuckDB.",
    )
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help=f"DuckDB file (default: {DEFAULT_DB_PATH})")
    sub = parser.add_subparsers(dest="command", required=True)

    p_sync = sub.add_parser("sync", help="bulk-load or incrementally refresh tables")
    p_sync.add_argument(
        "--tables", default="sf1",
        help=f"comma-separated table names ({', '.join(TABLES)}) "
             f"or a preset ({', '.join(PRESETS)}); default: sf1",
    )
    p_sync.add_argument("--full", action="store_true", help="force a full re-export even if data exists")

    sub.add_parser("status", help="show row counts, watermarks, and last sync per table")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.command == "sync":
        try:
            specs = resolve_tables(args.tables)
        except ValueError as exc:
            parser.error(str(exc))
        results = sync(specs, db_path=args.db, full=args.full)
        failed = [n for n, (mode, _) in results.items() if mode == "error"]
        for name, (mode, rows) in results.items():
            print(f"{name:12s} {mode:12s} {rows:>12,d} rows")
        return 1 if failed else 0

    if args.command == "status":
        rows = status(db_path=args.db)
        if not rows:
            print(f"No database at {args.db} (run a sync first).")
            return 0
        header = f"{'table':12s} {'rows':>12s}  {'data watermark':19s}  {'last sync':26s} {'mode'}"
        print(header)
        print("-" * len(header))
        for r in rows:
            print(
                f"{r['table']:12s} {r['rows']:>12,d}  {str(r['watermark']):19s}  "
                f"{str(r['last_sync']):26s} {r['last_mode']}"
            )
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
