# Pocket Data

Local Sharadar store for the Investment Lab: one script that syncs Nasdaq
Data Link tables into a DuckDB file at `lab/data/sharadar.duckdb`, so
packets, screens, and §18 point-in-time validation query licensed data
locally instead of hammering an API mid-analysis.

## Setup (the two steps only a human can do)

1. **Subscribe** at [data.nasdaq.com](https://data.nasdaq.com) — Sharadar
   sells there as tables. Two options; check both prices before checkout:
   - **SF1 Core US Fundamentals** alone — serves the §18 PIT validation
     track (as-reported fundamentals with `datekey`).
   - **Core US Equities Bundle** — adds daily prices (SEP), the ticker
     master file, corporate actions, and insider data (SF2). The bundle's
     specific virtue: it includes **delisted companies**, making it a
     survivorship-bias-free price + fundamentals set from a single vendor.
     If backtesting is part of the intent, the bundle is the version that
     serves it.
2. **Copy your API key** from account settings. One key covers everything
   you're entitled to. Put it in the environment or a repo-root `.env`:

   ```
   NASDAQ_DATA_LINK_API_KEY=xxxx
   ```

   `.env` and `lab/data/` are gitignored — the key and the licensed data
   never enter git.

## Usage

```bash
pip install -r pocket-data/requirements.txt

python3 pocket-data/sharadar_sync.py                  # SF1 only
python3 pocket-data/sharadar_sync.py --bundle         # all five tables
python3 pocket-data/sharadar_sync.py --status         # local state, no fetch
python3 pocket-data/sharadar_sync.py --bulk SF1       # force full re-export
```

Or `/pocket-data sync` / `/pocket-data status` inside Claude Code.

**First run** per table is a bulk export — the whole table as a zipped CSV
(a few hundred MB for SF1), loaded straight into DuckDB and deleted.
**Every later run** is incremental: SF1/SEP/SF2 carry a `lastupdated`
column, so the script fetches only rows changed since the local maximum and
merges them replace-by-key inside a transaction. Small, fast, cheap. The
small tables (TICKERS, ACTIONS) are simply re-exported wholesale each sync.
A `_sync_log` table in the DB records every run.

Caveats built in: a delta that hits the API's 1M-row page ceiling refuses
to merge and tells you to `--bulk` that table; a 403 on a table means it
isn't in your subscription, and the script continues with the rest. SF2's
export arrives without a `lastupdated` column, so the script detects that
and re-exports it wholesale each sync (~11M rows) — if that's too heavy
for a routine refresh, sync it on its own cadence with `--tables SF2` and
run day-to-day refreshes as `--tables SF1,SEP,TICKERS,ACTIONS`.

## Point-in-time rules (§18)

- `datekey` = when the filing became knowable; `reportperiod` = what it
  covers. Frozen packets filter `datekey <= cutoff`, never `reportperiod`.
- As-reported dimensions (ARQ/ART/ARY) for PIT work; MR* dimensions embed
  restatements and serve current-state analysis only.
- Universe construction at a past date must include then-listed,
  since-delisted names — that is the entire point of paying for the bundle.
