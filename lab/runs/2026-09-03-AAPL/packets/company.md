# Evidence packet — COMPANY — Apple Inc. (AAPL)

```yaml
packet_id: 2026-09-03-AAPL/company
built: 2026-09-03
masked: false
gate_minus_1: pass  # liquidity ~$11B ADV; mandate note: mcap $4.74T sits outside the constitution's written example band ($10-80B compounder); band is per-engine and user-set (§3)
contamination_check: no analyst conclusions, scores, or rankings included
tier: 1
```

## Market data [source class: aggregator/exchange data, retrieved 2026-09-03]

- Last close (2026-09-02): $324.96; day volume 33.8M shares (~$11.0B notional)
- Market cap approx: $4,743.5B (EDGAR valuation module, prior close $325.03)
- FY-figure multiples at that price: P/E (FY2025) 42.35, P/S 11.4, P/B 64.33

## Fundamentals, FY2018-FY2025 [source class: company filings (10-K XBRL); latest FY2025 10-K filed 2025-10-31, accession 0000320193-25-000079; NOTE: latest annual data is ~10 months old — FY2026 ends this month, unreported]

| FY (ends Sept) | Revenue $B | YoY | Net income $B | Gross profit $B | Diluted EPS | OpCF $B | Capex $B | R&D $B | Diluted shares B |
|---|---|---|---|---|---|---|---|---|---|
| 2025 | 416.2 | +6.4% | 112.0 | 195.2 | 7.46 | 111.5 | 12.7 | 34.6 | 15.00 |
| 2024 | 391.0 | +2.0% | 93.7 | 180.7 | 6.08 | 118.3 | 9.4 | 31.4 | 15.41 |
| 2023 | 383.3 | -2.8% | 97.0 | 169.1 | 6.13 | 110.5 | 11.0 | 29.9 | 15.81 |
| 2022 | 394.3 | +7.8% | 99.8 | 170.8 | 6.11 | 122.2 | 10.7 | 26.3 | 16.33 |
| 2021 | 365.8 | +33.3% | 94.7 | 152.8 | 5.61 | 104.0 | 11.1 | 21.9 | 16.86 |
| 2020 | 274.5 | +5.5% | 57.4 | 105.0 | 3.28 | 80.7 | 7.3 | 18.8 | 17.53 |
| 2019 | 260.2 | -2.0% | 55.3 | 98.4 | 2.97 | 69.4 | 10.5 | 16.2 | 18.60 |
| 2018 | 265.6 | — | 59.5 | 101.8 | 2.98 | 77.4 | 13.3 | 14.2 | 20.00 |

8-year CAGRs: revenue 6.6%, net income 9.5%, EPS 14.0% (share count -4.0%/yr), R&D 13.5%.
FY2025 anomalies: net income +19.5% vs revenue +6.4%; OpCF -5.7% YoY despite NI growth; capex +34.6% YoY to $12.7B.

## Ratios, FY2025 [source class: company filing (10-K XBRL)]

- Gross margin 46.9%, operating margin 32.0%, net margin 26.9%, FCF margin 23.7%
- ROE 151.9% (equity shrunk by buybacks), ROA 31.2%
- Current ratio 0.89, quick ratio 0.86; debt/equity 3.87, net debt/EBITDA 0.38
- EDGAR analysis hint (tool-generated, treat as agent inference): "strong margins; tight liquidity; high leverage"

## Recent 8-K events [source class: primary regulatory record]

- 2026-07-30: 8-K items 2.02/9.01 — FY2026 Q3 (June qtr) earnings release. Price reaction: **-9.27% next day, -7.87% over 5 days** (EOD venue-blend measurements as of 2026-08-06). The 8-K body was not retrieved into this packet; the reaction size is the fact on record here.

## CEO transition [source class: primary regulatory record (Form 4) + media]

- Form 4 filed for John Ternus: RSU grant dated 2026-09-01, officer title listed as **CEO** (12.5% vests 2027-03-15, multi-year schedule).
- Media reports (secondary, one genealogy): Tim Cook stepped down after ~15 years; Ternus took over ~2026-09-01.

## Insider activity, last 90 days [source class: primary regulatory records (Forms 4); data as of 2026-09-01]

- 11 transactions, 3 unique insiders. Most recent open-market BUY by any insider: **2015-07-27** (none in over a decade).
- Jennifer Newstead (SVP, GC): 10b5-1 sales ~1,439 shares/week at $307-311 during August 2026 (~3.6% of position per sale); June RSU vest + tax withholding.
- Ben Borders (PAO): small June vest/withhold/sell (~$34K discretionary).
- Tool self-check caveat: summary net_value (-$6.2M) diverges from transaction-level sum (-$1.4M); treat aggregates with caution.

## Consensus estimates [source class: independent financial research (sell-side aggregate); retrieved 2026-09-03]

- FY2026 (ends 2026-09-30): EPS avg $8.81 (range 8.28-8.94, n=37); revenue avg $477.7B (+14.8% vs FY2025). Revisions last 30d: 21 up / 8 down.
- FY2027: EPS avg $9.53 (range 8.24-10.67, n=39); revenue avg $525.0B. Revisions last 30d: **8 up / 19 down**; avg fell from $9.71 (30d ago) to $9.53.
- Sept-2026 quarter: EPS avg $1.98, revenue avg $113.6B. Dec-2026 quarter: EPS avg $2.91, revenue avg $154.4B (wide range 132.9-170.4).
- Implied multiples at $324.96: ~36.9x FY2026E EPS, ~34.1x FY2027E EPS.

## Gaps

- FY2026 Q3 10-Q line items and the earnings-release body not included; retrieve from EDGAR if load-bearing (form 8-K item 2.02 dated 2026-07-30, or the Q3 10-Q).
- No segment split (iPhone/Services/etc.) in this packet; in the 10-K/10-Q if needed.
- Company overview endpoint rate-limited; dividend/beta fields absent.
