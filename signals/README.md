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
| `signals/us_census.py` | Fetch U.S. Census monthly imports/exports by HTS code and partner country (free key) plus a keyless HTS description snapshot |
| `signals/compute_signals.py` | Aggregate YoY / median / breadth per watch group; snapshot report |
| `signals/cftc_cot.py` | CFTC Commitments of Traders via the Socrata API at publicreporting.cftc.gov (keyless SODA 2.1 GET; SODA 3.0 POST when `CFTC_APP_TOKEN` is set), normalized to long/short/net per trader group |
| `signals/fx_rates.py` | Daily USD reference rates (yen, won), keyless, for the currency-adjusted series |
| `signals/intel.py` | Diff the derived tables against the previous run; flag watch items; feed the daily brief |
| `signals/config/watchgroups.json` | Taiwan ticker groups (AI compute, server ODM, power/cooling, robotics motion) |
| `signals/config/korea_endpoints.json` | Korea endpoint config incl. HS codes (8542 semis, 8486 semi equipment, 8479 robots) |
| `signals/config/japan_endpoints.json` | Japan endpoints (URL patterns, stage codes, e-Stat navigation), HS prefixes and principal-commodity codes |
| `signals/config/cftc_endpoints.json` | CFTC report dataset ids (legacy, disaggregated, TFF), both API routes, tracked contract market codes (088691 COMEX gold) |
| `signals/config/us_endpoints.json` | Census/HTS endpoints, requested variables, the HTS codes tracked (transceivers, laser diodes, fibre, wafers, equipment) |
| `data/taiwan/monthly_revenue/` | One normalized CSV per month & market (thousand TWD) |
| `data/korea/` | Append-only long tables + verbatim raw API responses |
| `data/japan/` | Append-only long tables + verbatim raw XML/CSV/HTML payloads (`raw/`) |
| `data/us/` | Append-only long table by (month, direction, code, country) + verbatim Census JSON (`raw/`) |
| `data/cftc/` | Append-only positions table + verbatim JSON payloads (`raw/`) |
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

**Currency adjustment — telling the yen from the trade.** Japan publishes in
yen, so a weaker yen inflates every headline without a single extra machine
shipping. `signals/fx_rates.py` stores a daily USD reference rate for the yen
and the won (ECB Data Portal, keyless, cross-rated through USD per EUR;
frankfurter.app as fallback) in `data/fx/rates_daily.csv`. `compute_signals`
then restates each Japan row at the rate for the window that print covers — the
first 10 days, the first 20, or the whole month — and `japan_signals.csv` gains
four columns: `jpy_per_usd`, `value_usd_k`, `yoy_pct_usd` and `fx_effect_pt`.
The last is the published yen YoY minus the USD YoY: the percentage points of
the growth that are the currency. A row with no stored rate keeps those columns
empty; no rate is ever assumed. Korea's series is already in USD and is not
adjusted, so the won rate is stored for context only.

Two rates, both carried. The market rate answers what a flow is worth in
dollars today. Japan Customs applies its own rate when it values a shipment,
and Japan's yen figures embed that one — so `jpy_per_usd_customs` and
`yoy_pct_usd_customs` restate the series at it. The customs rate is not
fetched: customs law fixes a week's rate at the average market rate of the week
two weeks earlier, so it is computed from the stored daily rates, which also
means it reaches back as far as they do. Verified against three published
weeks to within 0.2%; the residual is the fixing convention. The official
weekly PDF remains the authority — `python -m signals.fx_rates customs
<date>` prints the computed rate for that week and the URL to check it against.
In practice the two USD growth rates land within about a point of each other,
so the choice of rate rarely changes a reading; when it does, that is worth
knowing.

**What changed, every run.** After `compute_signals`, the workflow runs
`python -m signals.intel --previous <snapshot>` against the pre-run copy of
`data/derived/`. It writes `data/derived/whats_new.md` (new prints per
source and window, revised rows, and threshold flags: |YoY| >= 25% on a
headline row, a U.S. origin's share of its code moving >= 5 points month over
month), appends the same markdown to the Actions run page (job summary), and
puts a one-line subject on the data commit ("2 new print groups, 3 flags").
Flags are screening arithmetic (constitution §21, Tier 1): they open watch
items, never decision windows (§13.7).

**Daily intelligence summary.** A Claude Routine fires every weekday at 19:30
UTC, after the second scheduled run. Its prompt is a short pointer; the whole
specification lives in `signals/DAILY_SUMMARY.md` in this repository, so the
wording, shape and rules are changed with a commit rather than by editing the
Routine in a browser. The summary reads the data commits since the previous
one, judges each flag as act now, keep watching or ignore, and posts to issue
#3 with a push and email notification carrying the same text. It is one page,
plain English, in four parts: Bottom line, What, So what, What now. Days with
no new figures produce nothing.

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

**United States — one free key.** Register at
[api.census.gov/data/key_signup.html](https://api.census.gov/data/key_signup.html)
(instant, by email), store the key as the `CENSUS_API_KEY` repository secret.

```bash
CENSUS_API_KEY=... python -m signals.us_census monthly          # last four published months
CENSUS_API_KEY=... python -m signals.us_census backfill 2013-01 2026-07
python -m signals.us_census hts                                 # keyless code descriptions
python -m signals.us_census reparse                             # rebuild from data/us/raw/
```

The Census International Trade API is the official U.S. customs statistic
(CBP collects, Census compiles; USITC DataWeb redistributes the same table).
Monthly data land 34-36 days after month end. One call per code per month per
direction returns every partner country with general and consumption value,
quantity, and the air/vessel split; `data/us/trade_monthly_hs.csv` keeps one
row per country, `data/derived/us_signals.csv` adds YoY and each country's
share of the code. Codes are in `us_endpoints.json`; note that 8517.62.0090,
where CBP classifies optical transceivers, is a broad basket that also holds
switches, routers and modems, so the read is in origin mix and growth, not
in the level. Exports use HS6 only because Schedule B numbers differ from
import HTS at ten digits.

**Automation.** `.github/workflows/update-signals.yml` runs daily at 07:30 UTC
(after Taipei/Seoul/Tokyo publish times), fetches whatever is newly published,
recomputes `data/derived/`, and commits only when data changed. Manual runs
accept backfill ranges; the `japan_only` input skips the Taiwan and Korea
steps so a Japan-only dispatch does not spend tradedata.go.kr's manual-run
budget, `us_only` does the same for the Census steps, `us_backfill` walks
history one year at a time, and `japan_capture` snapshots every Japan source raw.

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
