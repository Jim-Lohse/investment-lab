# IBKR sleeve pilot — dataset

Source: EODHD (primary source per CLAUDE.md Section 9.4), fetched 2026-08-16
via the EODHD MCP tools; plus the IBKR API for Intesa Sanpaolo's Borsa
Italiana line, which the EODHD plan does not carry (per Jim, 2026-08-16).
Raw API output saved verbatim; no hand edits.

- `prices/ISP.BVME.ibkr.csv` — ISP on Borsa Italiana via IBKR (contract
  29816328, EUR, SMART-routed bars), daily OHLCV 2021-08-16 → 2026-08-14
  (IBKR's 5-year maximum). Raw trade prices, NOT dividend-adjusted; the
  analysis reinvests EUR dividends on ex-dates to build total return.
  For pre-2021 ISP history the XETRA line below is the labeled proxy.
- `corp_actions/ISP.BVME.ibkr.csv` — IBKR's dividend records for that
  contract, extracted verbatim (dates are YYYYMMDD); matches the EODHD
  dividend table on every date and amount.

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

## Rev 2 additions (Jim's rulings, 2026-08-16)

- `rates/UST_BILL_3M.csv` — EODHD 13-week T-bill rates 2015-01-02 →
  2026-08-14 (2,906 rows; `discount` = bank-discount basis, `coupon` =
  coupon-equivalent/bond-equivalent yield, plus API average variants;
  percent units). Cash leg accrues at `coupon` (ruling #1).
- `corp_actions/{IMB.LSE,RR.LSE,SCCO.NYSE,FFH.TSE}.ibkr.csv` — IBKR
  corporate-action records (5y window), saved verbatim; SCCO's include ten
  StockDividends events 2024-05-07 → 2026-08-11. FFH values are the USD
  declarations (EODHD carries CAD conversions).
- `prices/ISP.BVME.monthly.ibkr.csv` — IBKR monthly bars for the BVME
  contract back to 2014-07 (raw EUR), used for the pre-2021 Milan-vs-XETRA
  proxy spot check.
- `dividends_reconciled/<KEY>.csv` — the contest-grade dividend tables built
  by `analysis/reconcile_dividends.py`: EODHD ∪ IBKR ∪ company declarations,
  with per-row `sources`/`note`. IMB's spurious 2026-05-28 row is dropped
  (RNS + IBKR evidence); SCCO rows are as-declared amounts (IBKR where
  covered, EODHD × K_eodhd=1.08085 inversion earlier, verified to 0.00% on
  all 19 overlap rows). `stock_events.csv` holds share-adjustment factors
  (SCCO only). Total-return construction: raw closes + these tables, net of
  withholding (IT 26%, CA 15%, UK 0%, US 0%) — EODHD `adjusted_close` is no
  longer the total-return basis.
- `prices/ISP.MI.upload.csv` — Milan-native ISP daily file supplied by Jim
  (2026-08-19; Yahoo-Finance-style columns, EUR, 2025-08-19 → 2026-08-19,
  two null rows). Verification source only — cross-checked against the IBKR
  Milan bars (mean abs close diff 0.167%) by `analysis/check_isp_upload.py`;
  the IBKR daily series remains primary.
