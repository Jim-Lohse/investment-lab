# Data store

Filled by the scheduled `update-signals` workflow (see `signals/README.md`).

- `taiwan/monthly_revenue/YYYY-MM_{sii,otc}.csv` — normalized MOPS monthly
  revenue, one file per month and market. Unit: thousand TWD. Rewritten on
  re-fetch (source revisions are rare and legitimate).
- `korea/trade_monthly.csv`, `korea/exports_flash.csv` — append-only long
  tables keyed on period+item; first write wins, so history is never silently
  restated. `korea/raw/` keeps verbatim API payloads.
- `derived/` — recomputed outputs (`taiwan_signals.csv`, `korea_signals.csv`,
  `latest_report.md`). Derived, disposable, regenerated every run.
