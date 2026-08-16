# Session 1 memo — drawdown cap, dataset, validation

Date: 2026-08-16. Rules: `CLAUDE.md` (repo root), Section 9 agenda items 1–4.
Reproduce every number here with `python3 ibkr-sleeve/analysis/session1_cap.py`.

## 1. The drawdown cap X (agenda item 1)

**Result: X = 25% maximum peak-to-trough decline of the sleeve's USD
total-return value.** ("Drawdown" = how far the portfolio falls from its
highest point before recovering; "peak-to-trough" = measured from that high
to the low.)

Labeled inputs, before any math (Section 5.8):

| Input | Value | Source |
|---|---|---|
| Retirement nominal target T | $1,970,000 | household (Section 2) |
| Horizon H | 14 years | household (Section 2) |
| Withdrawal rate w | 3.5% | household (Section 2) |
| Required nominal return | ~0% | household (Section 2) |
| UST par yields, 2026-08-14 | 10Y 4.68%, 20Y 5.25% | EODHD Treasury curve |
| Sustainable-withdrawal boundary w_max | 4.0% | Bengen (1994) / Trinity study — the one imported constant |
| Sleeve share at full mandate scale | 50% | Section 3 guardrail |

The derivation, step by step:

1. **Required return ~0% over 14 years means liquid assets today already
   roughly equal the target** (A₀ = T/(1+0)^14 ≈ $1.97M). The plan is on
   track without needing any market return.
2. **Solvency bound.** If assets fell by D and never recovered, the return
   needed to still reach T in 14 years is (1−D)^(−1/14) − 1. That stays
   within reach of bond-equivalents (no equity risk) as long as it is below
   the 14-year Treasury rate — interpolated between 10Y and 20Y:
   4.68% + (5.25%−4.68%)×4/10 = **4.91%**. Solving: D ≤ 1 − 1.0491^(−14)
   = **48.9%**.
3. **Income bound.** An unrecovered drawdown D forces the withdrawal rate up
   from 3.5% to 3.5%/(1−D) for the same dollar income. The household's own
   choice of 3.5% sits below the standard 4.0% sustainable boundary; that
   margin is the risk budget: D ≤ 1 − 3.5/4.0 = **12.5%**.
4. **Household tolerance = the tighter bound = 12.5%.**
5. **Sleeve translation.** At full mandate scale the active ex-US sleeve is
   capped at 50% of household liquid assets, the rest bond-equivalent
   (roughly drawdown-free). Household drawdown = 50% × sleeve drawdown, so
   the sleeve may fall **X = 12.5% / 50% = 25%** before the household
   tolerance is touched.

Honesty notes: (a) today's sleeve is ~0.6% of household assets, so no
sleeve-level cap is required by household arithmetic *today* — X = 25% is the
discipline for the strategy at the scale the mandate permits, applied to the
pilot now so the contest optimizes under the constraint that will bind at
scale. (b) The only number not taken from the household inputs, the mandate,
or live market data is the 4.0% sustainable-withdrawal anchor.

**Verdict: ACTION — Jim confirms X = 25% (specifically the 4.0% anchor and
the 50%-scale translation). REOPEN IF either is changed; the derivation
recomputes mechanically.**

## 2. Cap firing frequency (agenda item 2)

Sleeve history = the five current names at current weights (ISP 37.6%, RR
16.2%, IMB 15.8%, FFH 14.1%, SCCO 9.9%, cash 6.4% at 0%), bought and held
from each window's start, USD total return (dividends reinvested,
split-adjusted), union calendar across the four venues with stated
forward-fill (Section 5.7). "Fired" = the sleeve's value closed at or below
25% under its running peak.

| Window (labeled per Section 7.3) | Max drawdown | Days below −25% | Share of days |
|---|---|---|---|
| 2015-01-02 → 2026-08-14 (11.6y) | −50.6% | 393 | 13.1% |
| 2021-08-16 → 2026-08-14 (5y) | −35.3% | 94 | 7.3% |
| 2024-08-14 → 2026-08-14 (2y) | −15.1% | 0 | 0% |

Reading: over the last two years the cap never fires (max drawdown −15.1%) —
seatbelt behavior. The full-window breaches are concentrated in 2020–2022
(COVID crash: Rolls-Royce lost most of its value before its rescue rights
issue). A 25% cap would have de-risked the sleeve through that period —
which is exactly the seatbelt engaging, not whipsaw. Whipsaw only appears at
much tighter caps (at 12.5% the sleeve is in breach 41% of all days over
11.6y — a household-level 12.5% applied directly to the sleeve would be a
whipsaw machine, which is why the 50%-scale translation matters).

Caveats, stated plainly: this is a *hindsight portfolio* — today's weights on
names that survived to today (Section 7.5 survivorship caveat; RR nearly
didn't). It answers "how often would this cap level have engaged on these
names," not "how good is this portfolio." Episode counts oscillate around
the threshold, so days-in-breach is the honest frequency measure. Actual
overlapping data coverage is 11.6 years — longer than the "roughly two
years" the brief assumed; all windows above are labeled.

**Verdict: DONE — at X = 25% the cap is a seatbelt on recent history and
engaged only in the 2020-class crash on the full window. REOPEN IF the
candidate universe changes the sleeve's character materially.**

## 3. CLAUDE.md committed (agenda item 3)

**DONE** — commit `9307ba4` at repo root of branch
`claude/commit-claude-md-8zauau`, so every session and subagent inherits it.

## 4. Dataset and validation (agenda item 4)

EODHD (primary source) daily OHLCV + adjusted close 2015-01-02 → 2026-08-14
(~2,915–3,001 rows/series), dividends and splits, saved verbatim under
`ibkr-sleeve/data/` (see its README for the calendar and units rules).

**Venue substitution, flagged:** this EODHD plan has no Borsa Italiana data
(ISP.MI → 404; no Milan exchange on the plan's list). The dataset uses
Intesa Sanpaolo's XETRA line **IES.XETRA — same ISIN IT0000072618, EUR** — as
a proxy for the Milan line. Cross-listed arbitrage keeps the two within
basis points, and the Milan fill below lands inside the XETRA day range, but
this is a proxy, not Milan data.

Validation against known fills (Section 5.9) — raw values first, all PASS:

| Fill (IBKR record) | Dataset day range (raw O/H/L/C) | Result |
|---|---|---|
| 2026-08-06 BUY 545 ISP @ €6.843 | IES.XETRA 6.818 / 6.857 / 6.792 / 6.792 | PASS (inside range) |
| 2026-08-14 BUY 26 IMB @ 2629p | IMB.LSE 2637 / 2652 / 2597 / 2609 | PASS |
| 2026-08-14 SELL 25.5427 EUAD @ $47.86 | EUAD.US 47.86 / 48.15 / 47.61 / 47.89 | PASS (= open) |
| 2026-08-14 SELL 21 INDA @ $49.775 | INDA.US 49.88 / 49.92 / 49.735 / 49.78 | PASS |

FX on fill dates (raw closes): EURUSD 1.1525 (08-06), 1.1570 (08-14);
GBPUSD 1.3470 (08-06), 1.3491 (08-14). LSE units confirmed pence (RR close
1541, IMB 2609 on 08-14) — but EODHD *dividend* rows for LSE names are in
pounds (RR 0.06, IMB 0.419); do not mix units.

**Verdict: DONE — dataset reproduces all four fills; contest may proceed on
it once open items are accepted.**

## 5. Open items (nothing estimated around — Section 10)

1. **Milan venue proxy** (above). REOPEN IF Milan-native data becomes
   available; Italian FTT frictions still apply per rules regardless.
2. **IMB dividend near-duplicate in EODHD:** rows 2026-05-21 (0.4168) and
   2026-05-28 (0.419) share payment date 2026-06-30 — possibly one real
   event returned twice, which would slightly overstate IMB's adjusted
   total return. Returned exactly so by the API; not independently verified.
3. **SCCO possible missing dividend:** no EODHD row between 2024-02-12 and
   2024-08-09 (a quarterly payer). Unverified; would slightly *understate*
   SCCO total return.
4. **Withholding tax:** adjusted series reinvests gross dividends (26%
   Italy, 15% Canada treaty not deducted) — USD total returns slightly
   overstated for a US taxable holder. Must be handled in contest frictions.
5. **Cash modeled at 0%** in the diagnostic; contest backtests must use the
   T-bill series instead (de-risk asset per Section 3).
6. **RR dividend gap 2019-10 → 2025-04** matches the real suspension —
   consistency check passed, noted for the record.

## 6. STOP (agenda item 5)

Items 1–4 pass. Per Section 9.5, no hypothesis agent runs until the
candidate universe (incumbents + challengers) is written and committed —
that file does not exist yet and is the next session's first deliverable.

**Session verdict: ACTION — Jim to confirm X = 25% and accept/dispute open
items 1–4; then commit the candidate list to unlock the contest.**
