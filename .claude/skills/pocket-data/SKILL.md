---
name: pocket-data
description: Local fundamentals/prices store for the Investment Lab — sync Sharadar tables (SF1 fundamentals, SEP prices, tickers, actions, insiders) from Nasdaq Data Link into DuckDB, bulk on first run and incremental thereafter. Use when the user asks to sync, refresh, load, or check the Sharadar/Nasdaq data. Usage - /pocket-data [sync|status] [--bundle|--tables LIST]
---

# Pocket Data — the local Sharadar store

Drive `pocket-data/sharadar_sync.py`, which maintains
`lab/data/sharadar.duckdb`. First load per table is a bulk export (whole
table as zipped CSV, a few hundred MB for SF1); every later run fetches only
rows whose `lastupdated` changed — small, fast, cheap.

## Steps

1. **Preflight.** Confirm deps (`pip install -r pocket-data/requirements.txt`
   if imports fail) and that an API key is present — `NASDAQ_DATA_LINK_API_KEY`
   in the environment or a `.env` line at repo root. NEVER print, echo, or
   commit the key; `.env` and `lab/data/` are gitignored and must stay so.
   If there is no key, stop and tell the user the two steps that are theirs
   alone: subscribe at data.nasdaq.com (SF1 alone serves the §18 PIT
   validation track; the Core US Equities Bundle adds SEP prices, tickers,
   actions, and insiders — and includes delisted names, which is what makes
   it survivorship-bias-free for backtesting), then copy the API key from
   account settings.

2. **Run.**
   - `status` → `python3 pocket-data/sharadar_sync.py --status` (no fetch)
   - `sync` → `python3 pocket-data/sharadar_sync.py` (SF1 only) or
     `--bundle` / `--tables SF1,SEP` per the user's entitlement.
   - A first bulk run downloads for many minutes; run it in the background
     and report when loaded rather than blocking.

3. **Verify, then report.** After a sync: row counts and max `lastupdated`
   per table (the script prints both), plus any failures. Interpret the
   common ones instead of dumping tracebacks:
   - 403/Forbidden → entitlement gap: that table isn't in the subscription.
   - Truncation warning → the delta hit the API's 1M-row page ceiling; rerun
     that table with `--bulk`.
   - Missing key → step 1.

4. **Hygiene.** SF2 arrives without a `lastupdated` column, so the script
   re-exports it wholesale on every sync that includes it — suggest (once)
   keeping routine refreshes to `--tables SF1,SEP,TICKERS,ACTIONS` with SF2
   on its own slower cadence. Note that
   `/pocket-observations` can fold a data-freshness line into its brief: a
   stale local store silently degrades every packet built from it.

## Point-in-time discipline (why this store exists)

For §18 frozen packets and any backtest:

- Query fundamentals with `datekey <= cutoff` — `datekey` is when the filing
  became knowable, `reportperiod` is what it covers. Filtering on
  `reportperiod` leaks the future.
- Use as-reported dimensions (ARQ/ART/ARY) for PIT work; MR* dimensions
  incorporate restatements and are for current-state analysis only.
- The bundle's delisted names are the survivorship-bias defense: a universe
  built from today's TICKERS listing filtered to `isdelisted='N'` at a past
  cutoff is a §18 violation (knowledge of future survivors).
