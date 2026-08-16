# IBKR sleeve pilot — dataset

Source: EODHD (primary source per CLAUDE.md Section 9.4), fetched 2026-08-16
via the EODHD MCP tools. Raw API output saved verbatim; no hand edits.

- `prices/<TICKER>.csv` — daily OHLCV + adjusted close, 2015-01-01 → 2026-08-15
  (EUAD.US and INDA.US: 2026-08-01 → 2026-08-15, validation-fill window only).
  `adjusted_close` is split- and dividend-adjusted (gross dividends, reinvested
  same day, local currency) — the total-return basis required by Section 5.6.
  LSE series (RR.LSE, IMB.LSE) are quoted in pence (GBX).
  `*.FOREX` files are FX rates (units of USD per 1 EUR / GBP / CAD).
- `dividends/<TICKER>.csv` — cash dividend history (documentation/validation of
  the adjusted series; not separately added on top of adjusted_close).
- `splits/<TICKER>.csv` — split history.

Calendar rule (Section 5.7): analysis uses the union of the five equity
venues' trading dates; each local price and FX rate is forward-filled across
its own venue's holidays. No inner joins; no silently dropped history.

Known caveat (open item): adjusted_close reinvests gross dividends — dividend
withholding tax (e.g., 26% Italy, 15% Canada treaty rate) is not deducted, so
USD total returns are slightly overstated for a US taxable holder. Flagged for
the contest sessions; immaterial for the drawdown-cap diagnostic.
