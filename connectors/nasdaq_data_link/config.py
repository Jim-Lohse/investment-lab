"""Table registry and configuration for the Nasdaq Data Link (Sharadar) connector.

Which tables actually sync depends on the Nasdaq Data Link subscription:

- "Core US Fundamentals" (SF1) entitles the ``fundamentals`` preset.
- "Core US Equities Bundle" adds daily prices (SEP) and insider filings (SF2),
  i.e. the ``bundle`` preset. The bundle includes delisted companies, which is
  what makes it survivorship-bias-free for backtesting.

A table the account is not entitled to fails with a clear message and the
sync moves on to the next table.
"""

from dataclasses import dataclass

DEFAULT_DB_PATH = "data/sharadar.duckdb"
STATE_TABLE = "_sync_state"


@dataclass(frozen=True)
class TableSpec:
    """One Sharadar datatable and how it lands in DuckDB.

    strategy:
        "incremental" — bulk export on first run, then filtered exports on
        ``watermark`` >= the max value already stored; changed rows are
        upserted by deleting every stored row whose ``key`` columns match an
        incoming row, then inserting the batch.
        "replace" — small tables, fully re-downloaded and replaced each run.

    key: the deletion scope for incremental upserts. Incoming batches must
    contain every current row for a given key tuple (true for these tables:
    Sharadar re-stamps ``lastupdated`` on all rows of a revised record).
    """

    name: str
    code: str
    strategy: str
    key: tuple = ()
    watermark: str = "lastupdated"


TABLES = {
    spec.name: spec
    for spec in [
        # --- Core US Fundamentals (SF1 product) ---
        TableSpec("sf1", "SHARADAR/SF1", "incremental",
                  key=("ticker", "dimension", "datekey", "reportperiod")),
        TableSpec("daily", "SHARADAR/DAILY", "incremental",
                  key=("ticker", "date")),
        TableSpec("tickers", "SHARADAR/TICKERS", "replace"),
        TableSpec("indicators", "SHARADAR/INDICATORS", "replace"),
        TableSpec("actions", "SHARADAR/ACTIONS", "replace"),
        TableSpec("events", "SHARADAR/EVENTS", "replace"),
        TableSpec("sp500", "SHARADAR/SP500", "replace"),
        # --- added by the Core US Equities Bundle ---
        TableSpec("sep", "SHARADAR/SEP", "incremental",
                  key=("ticker", "date")),
        # A refiled Form 4 re-stamps every row of the filing, so the filing
        # (ticker, filingdate, ownername) is the safe deletion scope.
        TableSpec("sf2", "SHARADAR/SF2", "incremental",
                  key=("ticker", "filingdate", "ownername")),
    ]
}

PRESETS = {
    "fundamentals": ["sf1", "daily", "tickers", "indicators", "actions", "events", "sp500"],
    "bundle": ["sf1", "daily", "tickers", "indicators", "actions", "events", "sp500", "sep", "sf2"],
}


def resolve_tables(arg: str) -> list[TableSpec]:
    """Expand a preset name or comma-separated table list into TableSpecs."""
    names = PRESETS.get(arg, [t.strip().lower() for t in arg.split(",") if t.strip()])
    unknown = [n for n in names if n not in TABLES]
    if unknown:
        raise ValueError(
            f"Unknown table(s): {', '.join(unknown)}. "
            f"Known tables: {', '.join(TABLES)}. Presets: {', '.join(PRESETS)}."
        )
    return [TABLES[n] for n in names]
