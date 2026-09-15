# Data store

Filled by the scheduled `update-signals` workflow (see `signals/README.md`).

- `taiwan/monthly_revenue/YYYY-MM_{sii,otc}.csv` — normalized MOPS monthly
  revenue, one file per month and market. Unit: thousand TWD. Rewritten on
  re-fetch (source revisions are rare and legitimate).
- `korea/trade_monthly.csv`, `korea/exports_flash.csv` — append-only long
  tables keyed on period+item; first write wins, so history is never silently
  restated. `korea/raw/` keeps verbatim API payloads.
- `japan/press_release.csv` (million yen), `japan/time_series.csv` (thousand
  yen), `japan/trade_monthly_hs.csv` (thousand yen) — append-only long tables,
  first write wins. `japan/raw/` keeps every verbatim payload (press-release
  XML, MOF time-series CSVs, e-Stat CSVs) and `japan/raw/pages/` the index and
  listing pages the fetchers navigate; `python -m signals.japan_customs
  reparse` rebuilds the three tables from `raw/` after a parser fix.
- `us/trade_monthly_hs.csv` (U.S. dollars) — append-only rows per (month,
  direction, HTS code, partner country), first write wins; `us/raw/` keeps
  every Census JSON response and the HTS snapshots; `python -m
  signals.us_census reparse` rebuilds the table from `raw/`.
- `fx/rates_daily.csv` — daily USD reference rates (yen, won) from the ECB
  Data Portal, keyless, cross-rated through USD per EUR; append-only, first
  write wins, with the source named per row. `fx/raw/` keeps the payloads and
  `python -m signals.fx_rates reparse` rebuilds the table from them. Used to
  restate the yen series in USD so a currency move can be told from a real one.
  Market reference rates, not customs valuation rates.
- `derived/` — recomputed outputs (`taiwan_signals.csv`, `korea_signals.csv`,
  `japan_signals.csv`, `us_signals.csv`, `whats_new.md`, `latest_report.md`).
  Derived, disposable, regenerated every run.
