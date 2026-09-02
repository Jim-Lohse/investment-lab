# Early demand signals: Taiwan MOPS + Korea Customs + Japan MOF

The fastest free, legal, public reads on global tech demand — and, with
Japan, on the supply response:

1. **Taiwan monthly revenue (MOPS).** Every TWSE/TPEx-listed company must
   report monthly revenue by the 10th of the following month — actual sales,
   weeks ahead of any quarterly print, covering TSMC, the AI-server ODMs, the
   power/cooling chain, and the robotics motion complex.
2. **Korea Customs 10/20-day exports.** Korea publishes trade data three times
   a month (days 1–10 on the 11th, days 1–20 on the 21st, full month on the
   1st) with a semiconductor breakout — the earliest broad demand datapoint in
   each month, anywhere.
3. **Japan MOF/Customs trade statistics.** The same three-revision cadence
   (first 10 days, first 20 days, monthly), but read from the *supply* side:
   semiconductor-equipment and materials exports (Tokyo Electron, Screen,
   Shin-Etsu, SUMCO) and optical components (Sumitomo Electric, Fujikura,
   Furukawa). This is the capacity-response signal constitution §9 warns
   about, observed at the supplier's dock rather than the buyer's.

No vendor dependency: all three are primary government sources (constitution
§8.1 source class: *government or industry dataset* / *primary regulatory
record*). Everything lands in this repo as plain CSV via a scheduled GitHub
Action.

## Layout

| Path | What |
|---|---|
| `signals/taiwan_mops.py` | Fetch current month (open-data CSV, no key) and historical archive (Big5 HTML) |
| `signals/korea_customs.py` | Fetch monthly HS-code trade + 10/20-day flash via data.go.kr APIs |
| `signals/japan_customs.py` | Fetch MOF press-release XML (10/20-day totals, monthly commodity breakdown), keyless time-series CSVs and e-Stat 9-digit commodity CSVs |
| `signals/compute_signals.py` | Aggregate YoY / median / breadth per watch group; snapshot report |
| `signals/config/watchgroups.json` | Taiwan ticker groups (AI compute, server ODM, power/cooling, robotics motion) |
| `signals/config/korea_endpoints.json` | Korea endpoint config incl. HS codes (8542 semis, 8486 semi equipment, 8479 robots) |
| `signals/config/japan_endpoints.json` | Japan endpoints (URL patterns, stage codes, e-Stat navigation), HS prefixes and principal-commodity codes |
| `data/taiwan/monthly_revenue/` | One normalized CSV per month & market (thousand TWD) |
| `data/korea/` | Append-only long tables + verbatim raw API responses |
| `data/japan/` | Append-only long tables + verbatim raw XML/CSV/HTML payloads (`raw/`) |
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

**Japan — works immediately, no key.** Three keyless sources, each its own
workflow step so one drifting schema is one red step:

```bash
python -m signals.japan_customs flash          # 10/20-day + monthly press-release XML, last 3 months
python -m signals.japan_customs timeseries     # monthly series by principal commodity since 1988
python -m signals.japan_customs estat          # newest 9-digit-code monthly CSV (HS 8486, 8541, 8517, 9001, ...)
python -m signals.japan_customs flash-backfill 2021-01 2026-08   # one-time history
python -m signals.japan_customs reparse        # rebuild the CSV stores from data/japan/raw/
```

1. *Press releases* (`data/japan/press_release.csv`, million yen). File names
   are deterministic: `trade-st_e/<YYYY>/<YYYYMM><stage>e.xml` with stage 1 =
   first 10 days, 2 = first 20 days, 4 = monthly provisional, 5 = exports
   detailed / imports 9-digit provisional. **The 10- and 20-day files carry
   totals only** (exports, imports, balance, each with the year-ago value and
   MOF's own YoY) — unlike Korea there is no early commodity breakout. The
   monthly file carries every principal commodity (value, quantity, YoY, share,
   contribution) for the world and for USA / EU / Asia / China / Korea / ASEAN
   / Middle East / Russia, so `SEMICON MACHINERY ETC` by destination is
   available on the ~20th of the following month.
2. *Time series* (`data/japan/time_series.csv`, thousand yen): MOF's own
   monthly CSVs by press-release commodity (概況品 codes: 70131 semiconductor
   equipment, 70323 semiconductors, 81101 scientific/optical) from 1988 —
   a decade-plus of same-month comparables on day one, no backfill needed.
3. *e-Stat 9-digit tables* (`data/japan/trade_monthly_hs.csv`, thousand yen):
   the monthly "Values by Commodity" CSV filtered to the HS prefixes in
   `japan_endpoints.json` (8486 equipment, 3818 wafers, 2804.61 polysilicon,
   8541 laser diodes / photodiodes, 8517 transceivers, 9001 fibre, 9013
   optics). Reached by scraping e-Stat's listing page → month page → file id;
   every hop is saved under `data/japan/raw/pages/` so a layout change is
   diagnosable from the repo.

Publication calendar (JST): first 10 days ~28th of the same month (08:50),
first 20 days ~7th of the next month, monthly provisional ~20th of the next
month, detailed ~end of the next month (09:30). See
[calend_e.htm](https://www.customs.go.jp/toukei/calendar/calend_e.htm).

**Automation.** `.github/workflows/update-signals.yml` runs daily at 07:30 UTC
(after Taipei/Seoul/Tokyo publish times), fetches whatever is newly published,
recomputes `data/derived/`, and commits only when data changed. Manual runs
accept backfill ranges; the `japan_only` input skips the Taiwan and Korea
steps so a Japan-only dispatch does not spend tradedata.go.kr's manual-run
budget, and `japan_capture` snapshots every Japan source raw.

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
- Japan's 10/20-day prints are totals only; the commodity read arrives with
  the monthly provisional (~20th of the following month). Values are yen, so
  YoY carries the currency move; MOF publishes the average customs rate in
  the monthly summary if a USD view is needed. Japan's trade data reads
  geographies, not companies: it isolates no US-listed optical name
  (Lumentum, Coherent, Credo, AAOI have distributed manufacturing). Fabrinet
  is the one exception (Thailand), which is a separate, unverified source.
- The archive backfill hits MOPS politely (3s pauses); backfill years, not
  decades, in one run.
- This environment's egress policy blocked live endpoint verification at build
  time; parsers are tested offline against the documented formats, and the
  first scheduled run is the live validation. If a source has drifted, the
  failing fetcher names the URL and the raw payload is preserved.
