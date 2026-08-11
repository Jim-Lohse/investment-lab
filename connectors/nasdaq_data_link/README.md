# Nasdaq Data Link (Sharadar) connector

Pulls Sharadar tables from Nasdaq Data Link into a local DuckDB file
(`data/sharadar.duckdb`; tables live at the top level: `sf1`, `sep`, …).
First run per table is a bulk
export — the whole table as a zipped CSV, a few hundred MB for SF1. Every run
after that is incremental: Sharadar stamps each row with `lastupdated`, so the
connector exports only rows at or past the newest stamp already stored and
upserts them. Small, fast, cheap.

## Subscription

Subscribe at [data.nasdaq.com](https://data.nasdaq.com). Two options:

- **SF1 Core US Fundamentals** — fundamentals plus its companion tables
  (daily metrics, ticker master file, corporate actions, events, S&P 500
  constituents). Serves the point-in-time validation track.
- **Core US Equities Bundle** — adds daily prices (SEP) and insider filings
  (SF2). The bundle includes delisted companies, making it a
  survivorship-bias-free price + fundamentals set from a single vendor. If
  backtesting is part of the intent, this is the version that serves it.

Check both prices on the site before deciding. One API key (account settings)
covers everything the account is entitled to. A table outside the
subscription is skipped with a warning; the rest of the sync proceeds.

## Setup

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
export NASDAQ_DATA_LINK_API_KEY=your_key_here
```

(Or store it once with `nasdaqdatalink.save_key("your_key")`, which writes the
standard `~/.nasdaq/data_link_apikey` file.)

## Usage

```bash
# first pull + later refreshes — same command, it figures out which is needed
python -m connectors.nasdaq_data_link sync --tables fundamentals   # SF1 subscription
python -m connectors.nasdaq_data_link sync --tables bundle         # full bundle

# specific tables, forced full re-export, alternate db file
python -m connectors.nasdaq_data_link sync --tables sf1,sep --full
python -m connectors.nasdaq_data_link --db /path/to/other.duckdb sync

# what's loaded, how fresh, last sync per table
python -m connectors.nasdaq_data_link status
```

Querying:

```python
import duckdb
con = duckdb.connect("data/sharadar.duckdb", read_only=True)
con.sql("SELECT ticker, datekey, revenue FROM sf1 WHERE ticker = 'AAPL' AND dimension = 'ARQ'")
```

## Tables

| name | datatable | strategy | upsert key |
| --- | --- | --- | --- |
| `sf1` | SHARADAR/SF1 | incremental | ticker, dimension, datekey, reportperiod |
| `sep` | SHARADAR/SEP | incremental | ticker, date |
| `daily` | SHARADAR/DAILY | incremental | ticker, date |
| `sf2` | SHARADAR/SF2 | incremental | ticker, filingdate, ownername |
| `sf3` | SHARADAR/SF3 | replace | — |
| `sf3a` | SHARADAR/SF3A | replace | — |
| `sf3b` | SHARADAR/SF3B | replace | — |
| `tickers` | SHARADAR/TICKERS | replace | — |
| `indicators` | SHARADAR/INDICATORS | replace | — |
| `actions` | SHARADAR/ACTIONS | replace | — |
| `events` | SHARADAR/EVENTS | replace | — |
| `sp500` | SHARADAR/SP500 | replace | — |

Presets: `fundamentals` (the SF1 product's tables), `bundle` (adds SEP
prices and SF2 insiders), `institutional` (the SF3 13F holdings tables,
also included in the bundle subscription). The institutional tables are
quarterly data whose past quarters get amended, so they always fully
refresh — sync them occasionally (after each 13F filing season), not on
the daily cadence.

## Mechanics worth knowing

- Both bulk and incremental paths use the export endpoint
  (`export_table`), which has no row ceiling — the paginated `get_table`
  API caps out at 1M rows, which SF1 exceeds.
- The incremental filter is `lastupdated >= max(stored)`, deliberately
  overlapping the boundary value; the upsert (delete-matching-keys, then
  insert) makes the overlap harmless and the sync idempotent.
- Restatements arrive as re-stamped rows and simply overwrite in place. If a
  point-in-time packet (constitution §18) needs as-first-reported values,
  that requires Sharadar's dimension conventions (ARQ vs ART etc.) or a
  separate snapshot discipline — `lastupdated` upserts keep only the latest
  vendor view.
- New vendor columns are added to the local table automatically; existing
  rows hold NULL for them until re-stamped.
- Sync history lands in `_sync_state` (append-only), current
  freshness in `status`.

## Documentation

- [Data Access Tools](https://data.nasdaq.com/accesstools) — Nasdaq Data
  Link's current docs hub (the old docs.data.nasdaq.com site is being retired)
- [data-link-python](https://github.com/Nasdaq/data-link-python) — the
  official Python client used here; its README covers API-key configuration
  (env var, `~/.nasdaq/data_link_apikey`) and retry options

