# Brief: Japan trade-statistics pipeline (not yet built)

Handoff note for a fresh session. The Taiwan + Korea pipeline in this
directory is the working template; Japan is a near-copy of the Korea leg.

## Why Japan

The existing pipeline reads *demand* (Taiwan revenue, Korea exports). Japan
adds the *supply* side: semiconductor equipment and materials exports, plus
optical components from Sumitomo Electric, Furukawa, Fujikura, Shin-Etsu.
Japan's July 2026 semiconductor-equipment export value was reported up 49.1%
YoY — that is the capacity-response signal §9 of the constitution warns
about, observed from the supplier side rather than Korea's import side.

## Verified facts (checked 2026-09-02, re-verify before building)

- MOF/Customs publishes **"Trade Statistics of Japan (First 10 and 20 days
  Provisional)"** — the same three-revision cadence as Korea (10-day
  provisional -> 20-day provisional -> detailed/fixed).
  https://www.customs.go.jp/toukei/shinbun/kako/happyou_e3.htm
- Release calendar: https://www.customs.go.jp/toukei/calendar/calend_e.htm
- Bulk downloads: https://www.customs.go.jp/toukei/info/tsdl_e.htm
- e-Stat API (free appId, HS-code level, monthly):
  https://www.e-stat.go.jp/en/stat-search/database?tstat=000001013141&toukei=00350300
- NOTE: this sandbox's egress proxy blocks customs.go.jp. Exa's fetcher
  reaches it, and GitHub Actions runners reach it — same pattern used to
  build the Korea leg.

## Open questions to resolve first

1. Does the 10/20-day provisional carry a commodity breakdown, or totals
   only? (Korea's carries 10 categories. Japan's monthly release definitely
   has commodity detail; the 10-day one is unconfirmed.)
2. e-Stat API vs. plain CSV download — prefer whichever needs no key. The
   CSV path at tsdl_e.htm appears keyless.
3. Which HS codes matter: 8486 (semi equipment), 8541 (laser/photodiodes),
   8517 (transmission apparatus incl. transceivers), 9001 (optical fibre),
   3818 (doped wafers), 2804.61 (polysilicon).

## Patterns to copy from the Korea leg

- `signals/korea_tradedata.py` — fetcher shape, session handling, raw-payload
  preservation, schema-tolerant parsing (extract names from the payload
  rather than assuming column order).
- `signals/common.py` — `http_get` with backoff, `append_dedup_csv`
  (append-only, first write wins), `TableParser`.
- `signals/config/korea_endpoints.json` — endpoints and codes in config, not
  code, so a URL change is a config edit.
- `.github/workflows/update-signals.yml` — add a step; keep
  `continue-on-error: true` so one source can't block the others.
- `tests/test_signals.py` — offline fixtures per parser; CI runs them before
  every fetch.

## Hard-won gotchas (do not relearn these)

- **Rate limiting is real and punishing.** tradedata.go.kr blocked GitHub
  runner IPs for ~5 days after ~6 manual dispatches in 15 minutes. Build,
  then let the scheduled cron validate. One manual run per day, maximum.
- **Never let a fetcher write an empty file silently.** An early version
  wrote a header-only CSV for days because the server returned an error
  envelope with HTTP 200. Always check for the error shape and raise.
- **Preserve raw payloads** under `data/<country>/raw/`. Every parser fix in
  this project came from reading a stored response.
- **A failed chunk must not abort a backfill** — catch per chunk, continue.
- Government portals cap ranges silently (KCS returns a rolling 12 months
  regardless of the range asked for). Verify coverage after a backfill
  rather than trusting the request.

## What Japan will NOT give you

Trade data reads geographies, not companies. Lumentum, Coherent, Credo and
AAOI are US-listed with distributed manufacturing; no single country's
customs file isolates them. The one real exception is **Fabrinet**, whose
manufacturing is overwhelmingly Thailand-based — Thai optical-component
exports (HS 8517.62 / 9013) are a legitimate, imperfect throughput proxy.
Thailand's Ministry of Commerce cadence is unverified; check before
promising it.
