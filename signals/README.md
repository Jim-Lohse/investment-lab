# Early demand signals: Taiwan MOPS + Korea Customs

The two fastest free, legal, public reads on global tech demand:

1. **Taiwan monthly revenue (MOPS).** Every TWSE/TPEx-listed company must
   report monthly revenue by the 10th of the following month — actual sales,
   weeks ahead of any quarterly print, covering TSMC, the AI-server ODMs, the
   power/cooling chain, and the robotics motion complex.
2. **Korea Customs 10/20-day exports.** Korea publishes trade data three times
   a month (days 1–10 on the 11th, days 1–20 on the 21st, full month on the
   1st) with a semiconductor breakout — the earliest broad demand datapoint in
   each month, anywhere.

No vendor dependency: both are primary government sources (constitution §8.1
source class: *government or industry dataset* / *primary regulatory record*).
Everything lands in this repo as plain CSV via a scheduled GitHub Action.

## Layout

| Path | What |
|---|---|
| `signals/taiwan_mops.py` | Fetch current month (open-data CSV, no key) and historical archive (Big5 HTML) |
| `signals/korea_customs.py` | Fetch monthly HS-code trade + 10/20-day flash via data.go.kr APIs |
| `signals/compute_signals.py` | Aggregate YoY / median / breadth per watch group; snapshot report |
| `signals/config/watchgroups.json` | Taiwan ticker groups (AI compute, server ODM, power/cooling, robotics motion) |
| `signals/config/korea_endpoints.json` | Korea endpoint config incl. HS codes (8542 semis, 8486 semi equipment, 8479 robots) |
| `data/taiwan/monthly_revenue/` | One normalized CSV per month & market (thousand TWD) |
| `data/korea/` | Append-only long tables + verbatim raw API responses |
| `data/derived/` | Recomputed signals + `latest_report.md` (regenerated each run) |
| `tests/test_signals.py` | Offline parser/math tests (`python -m unittest discover tests`) |

## Setup

**Taiwan — works immediately, no key.**

```bash
pip install -r signals/requirements.txt
python -m signals.taiwan_mops current              # latest month, both markets
python -m signals.taiwan_mops backfill 2024-01 2026-06   # history (polite, slow)
python -m signals.compute_signals
```

**Korea — one free registration.**

1. Register at [data.go.kr](https://www.data.go.kr) (free, instant) and
   request use of the KCS trade-statistics APIs (수출입무역통계). Approval for
   these is automatic.
2. Put the **decoded** service key in the env var `DATA_GO_KR_API_KEY`
   (for Actions: repo → Settings → Secrets → `DATA_GO_KR_API_KEY`).
3. Request use of these three datasets (all auto-approved, instant):
   [15157908](https://www.data.go.kr/en/data/15157908/openapi.do) — 10-day
   provisional exports by major item;
   [15157901](https://www.data.go.kr/en/data/15157901/openapi.do) — 10-day
   provisional imports;
   [15101609](https://www.data.go.kr/en/data/15101609/openapi.do) — monthly
   trade by item/HS code.
4. Everything is pre-wired in `signals/config/korea_endpoints.json` (endpoints
   verified against the dataset pages 2026-08-14). Flash history reaches back
   to 2016-01 — after the key works, run
   `python -m signals.korea_customs flash-backfill 2016-01 <current month>`
   once (or use the workflow input) so every new print grades against a decade
   of same-window comparables. The same numbers are viewable at
   [tradedata.go.kr](https://tradedata.go.kr) for cross-checking. One caveat:
   the datasets don't document their per-record XML field names, so the flash
   parser extracts defensively and stores every record's full field set in an
   `extra_json` column — if the first live payload uses unexpected names, no
   data is lost and the parser gets a one-line update.

**Korea without any registration — tradedata.go.kr fallback.** The workflow
also scrapes the KCS statistics portal's public English dashboard
([tradedata.go.kr](https://tradedata.go.kr/cts/index_eng.do), no login) every
run via `signals/korea_tradedata.py`: total exports and imports for the latest
10/20-day or full-month window, with YoY rates as published (USD million;
`data/korea/tradedata_flash.csv`). This runs regardless of whether the API key
exists, so headline Korea flash prints flow with zero registration. Totals
only — the by-item semiconductor breakout needs either the data.go.kr API key
(preferred) or a parser extension against the portal's item page, whose raw
HTML the workflow's `capture_pages` input snapshots into
`data/korea/raw/pages/` for that purpose.

**Automation.** `.github/workflows/update-signals.yml` runs daily at 07:30 UTC
(after Taipei/Seoul publish times), fetches whatever is newly published,
recomputes `data/derived/`, and commits only when data changed. Manual runs
accept backfill ranges.

## What the signals mean (and don't)

`compute_signals.py` produces, per watch group and month: aggregate YoY
(group revenue vs the same companies' same-month-last-year revenue, from the
same report), median member YoY, and breadth (% of members growing). Korea
series get YoY once a year-ago observation exists in the store — after the
first year, every flash print grades itself against its own history.

Constitution discipline (§21 validation status): this is **Tier 1 screening
input** — mechanically aggregated primary data. It opens watch items, never
decision windows (§13.7). Group membership is a screening convenience, not a
thesis claim. On the recognition clock (§12.2) these series are useful
precisely because they sit at T0–T1: they show demand before it reaches
guidance, estimates, or sell-side notes.

Known caveats:

- Taiwan revenue is unconsolidated for some holdings and reported in thousand
  TWD; currency effects distort YoY for USD-billing exporters.
- Korea 10-day windows are working-day sensitive (Lunar New Year, Chuseok);
  compare YoY, mind the calendar, and prefer the 20-day print for signal.
- The archive backfill hits MOPS politely (3s pauses); backfill years, not
  decades, in one run.
- This environment's egress policy blocked live endpoint verification at build
  time; parsers are tested offline against the documented formats, and the
  first scheduled run is the live validation. If a source has drifted, the
  failing fetcher names the URL and the raw payload is preserved.
