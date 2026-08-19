# Session 1 memo — drawdown cap, dataset, validation (rev 2)

Date: 2026-08-16, revised same day after Jim's five rulings on rev 1.
Rules: `CLAUDE.md` (repo root), Section 9 agenda items 1–4. Reproduce every
number with `python3 ibkr-sleeve/analysis/reconcile_dividends.py` then
`python3 ibkr-sleeve/analysis/session1_cap.py`.

Rev 2 scope: this pilot is an experimental departure from the constitution's
usual single-name process, per Jim — the CLAUDE.md brief governs it. Rulings
applied: (1) cash leg at the 3-month T-bill rate; (2) dividend records
reconciled against IBKR corporate-action records and company declarations;
(3) per-venue withholding applied to dividends; (4) Milan/XETRA proxy
accepted with label after a spot check; (5) the 4.0% and 50% inputs in the
cap derivation documented as to provenance, with sensitivity.

## 1. The drawdown cap X (agenda item 1)

**Result: X = 25% maximum peak-to-trough decline of the sleeve's USD
total-return value** — at today's NLV of $11,622.81 that is **$2,905.70**
peak-to-trough. ("Drawdown" = how far the portfolio falls from its highest
point before recovering.)

Labeled inputs, before any math (Section 5.8):

| Input | Value | Provenance |
|---|---|---|
| Retirement nominal target T | $1,970,000 | household (Section 2) |
| Horizon H | 14 years | household (Section 2) |
| Withdrawal rate w | 3.5% | household (Section 2) |
| Required nominal return | ~0% | household (Section 2) |
| UST par yields, 2026-08-14 | 10Y 4.68%, 20Y 5.25% | EODHD Treasury curve (market data) |
| Sustainable-withdrawal boundary w_max | 4.0% | **judgment call** — Bengen (1994)/Trinity literature anchor, NOT a household input |
| Sleeve share at full mandate scale | 50% | Section 3 guardrail **maximum** — rule-derived, but choosing the max is a judgment call |

Derivation:

1. Required return ~0% over 14 years ⇒ liquid assets today ≈ the target
   (A₀ = T/(1+0)^14 ≈ $1.97M).
2. **Solvency bound:** an unrecovered household drawdown D is tolerable while
   the return needed to still reach T stays within bond-equivalent reach —
   the 14y Treasury rate, interpolated 4.68% + (5.25−4.68)×4/10 = 4.91%:
   D ≤ 1 − 1.0491^(−14) = **48.9%**.
3. **Income bound:** an unrecovered drawdown D forces the withdrawal rate to
   w/(1−D); tolerable while that stays ≤ w_max: D ≤ 1 − 3.5/4.0 = **12.5%**.
4. Household tolerance = min = **12.5%** (income bound binds).
5. **Sleeve translation:** at the guardrail maximum the sleeve is 50% of
   household liquid assets, the rest bond-equivalent (≈ drawdown-free), so
   household drawdown = 50% × sleeve drawdown ⇒ **X = 12.5%/50% = 25%**.

### Answers to Jim's two questions (ruling #5)

**"Which household input is the 4.0%?" — None.** The household input is your
3.5% withdrawal rate. The 4.0% is the classic sustainable-withdrawal
boundary from the retirement literature (Bengen 1994; Trinity study),
imported because a chosen withdrawal rate only becomes a *risk budget*
relative to some ceiling: the gap between 3.5% and the boundary is the
income you can permanently lose without the plan failing by that standard.
It is hereby **recorded as a judgment call, not a derivation.**

**"What justifies 50% rather than 40% or 60%?"** It is the Section 3
guardrail: total active ex-US is capped at 50% of household liquid assets.
60% is not a legal state under the mandate. Using the guardrail **maximum**
(rather than expected actual deployment) is the conservative direction — it
yields the *tightest* cap the rules can ever force; if the strategy actually
runs at 40% of household assets, true tolerance is looser (X would be
31.25%), never tighter. Rule-derived ceiling, judgment call to anchor on it.

**Sensitivity (what moves X to 20% or 30%):**

| Target X | via w_max (s fixed at 50%) | via s (w_max fixed at 4.0%) |
|---|---|---|
| 20% | w_max = 3.889% | s = 62.5% — not permitted by mandate |
| 30% | w_max = 4.118% | s = 41.7% |

Gradient ≈ +4.4 points of X per +0.1pp of w_max: **w_max is the driving
assumption**. The solvency bound never binds unless w_max ≥ 6.85%
(implausible). X is insensitive to T, H, and r_req over any reasonable range
because they only enter through the (slack) solvency bound.

**Verdict: DONE — X = 25% CONFIRMED by Jim, 2026-08-19:** he would hold
through a $2,905.70 peak-to-trough decline; his stated response to a cap
breach is a research review ("determine if the story changed or if it was
ordinary market selloff action and not indicative of the given company's
fundamentals"), not reflexive liquidation. Recorded implication for the
contest: X is the *constraint* candidate portfolios must satisfy in
backtest/Monte Carlo (drawdown ≤ 25%); in live operation a breach triggers
the story-vs-selloff review that feeds the existing sell-rule framework
(Section 8.1), with cash/T-bills as the de-risk asset if the review says
de-risk. REOPEN IF w_max ≠ 4.0% or the guardrail-max anchoring is revised.

## 2. Cap firing frequency (agenda item 2) — rev 2 numbers

Sleeve history = five current names at current weights (ISP 37.6%, RR 16.2%,
IMB 15.8%, FFH 14.1%, SCCO 9.9%, cash 6.4%), bought and held from each
window start, USD **net** total return: raw venue closes, reconciled
dividends net of withholding reinvested on ex-dates, SCCO's ten stock
dividends applied as share adjustments, RR's 2020 rights-issue factor
applied, **cash accruing at the 3M T-bill coupon-equivalent rate**
(×1.2734 cumulative over the full window — ruling #1). Union calendar,
stated forward-fill (Section 5.7).

| Window | Max drawdown | Days below −25% | Share of days |
|---|---|---|---|
| 2015-01-02 → 2026-08-14 (11.6y; ISP pre-2021 = XETRA proxy) | −51.4% | 440 | 14.7% |
| 2021-08-16 → 2026-08-14 (5y; ISP = Milan/IBKR) | −34.1% | 88 | 6.8% |
| 2024-08-14 → 2026-08-14 (2y; ISP = Milan/IBKR) | −15.4% | 0 | 0% |

Reading unchanged in kind from rev 1, slightly worse in degree (net
dividends reinvest less): the cap never fires in the trailing 2y (max
−15.4%) — seatbelt; full-window breaches concentrate in the 2020–2022
COVID/RR-crisis era. Tighter caps whipsaw (12.5% directly on the sleeve =
in breach 42% of all days over 11.6y). Same caveats as rev 1: hindsight
portfolio of survivors (Section 7.5); days-in-breach is the honest
frequency measure; windows labeled per Section 7.3.

**Verdict: DONE (numbers final pending only Jim's X confirmation).**

## 3. CLAUDE.md committed (agenda item 3)

**DONE** — commit `9307ba4`, repo root of `claude/commit-claude-md-8zauau`.

## 4. Dataset, reconciliation, and validation (agenda item 4)

Sources: EODHD (prices 2015→2026-08-14, FX, dividends, splits, 3M T-bill
rates, Treasury curve); IBKR (ISP Borsa Italiana daily bars 2021-08→ and
monthly bars 2014-07→, corporate-action records for all five names).
Everything saved verbatim under `ibkr-sleeve/data/` (see its README).

**Dividend reconciliation (ruling #2) — both disputes resolved with
primary-source evidence:**

- **IMB duplicate — confirmed spurious and dropped.** Imperial Brands' RNS
  of 2026-05-12 (via Investegate) declares ONE first interim instalment of
  41.68p, record 2026-05-22, payment 2026-06-30; IBKR's records carry
  exactly one matching row (ex 2026-05-21, 0.4168 GBP). EODHD's second row
  (ex 2026-05-28, 0.419, same payment date) matches no declared event —
  dropped from the reconciled table. The 2026-08-20 second instalment is
  corrected to the declared 41.68p (EODHD had 0.419); it is beyond the
  price window and does not enter the backtest.
- **SCCO "missing 2024 dividend" — it was a STOCK dividend, and they're
  recurring.** Company PR 2024-04-19 and Form 8-K: quarterly stock dividend
  of 0.0104 shares/share, ex 2024-05-07 — no cash. IBKR's records show TEN
  stock-dividend events 2024-05-07 → 2026-08-11 (factors 1.0056–1.012),
  nine paired with cash. All ten now enter the total-return construction as
  share adjustments (ignoring them understates SCCO by ~9% cumulative since
  2024). Additionally, EODHD's SCCO dividend values turned out to be
  restated per-current-share, not as-declared; the reconciled table uses
  IBKR's declared amounts where covered (2021-11→) and inverts EODHD's own
  restatement chain for earlier rows — verified to **0.00% worst deviation**
  on all 19 overlapping records (the inversion also independently confirmed
  EODHD's chain omits the standalone 2024-05-07 event — the original gap).
  Restated 2015 rows land on clean declared amounts (e.g. $0.10).

**Withholding (ruling #3) — quantified, then applied.** Net-of-withholding
dividend rates per venue: Italy 26% (IBKR default absent filed treaty
relief), Canada 15% treaty, UK 0%, US-listed SCCO 0% at source. Annualized
total-return drag, full series: **ISP −2.33pp/y** (larger than the 1–1.5pp
estimate — ISP's recent payout is big), **FFH −0.32pp/y**, RR/IMB/SCCO 0.
The asymmetric thumb on the scale is removed: all backtests now run net.

**Milan/XETRA proxy (ruling #4) — spot check done, item closed with
label.** IBKR *monthly* bars for the BVME contract reach back to 2014-07,
past the 5y daily-bar cap. Comparing 79 month-end Milan closes vs the XETRA
proxy over the proxy window (2015-01 → 2021-07): mean difference **0.00%**,
mean absolute **0.64%**, worst **3.63%** (2018-10), 13/79 months over 1%.
That is normal thin-line noise around an unbiased center: the proxy is fit
for the pre-2021 segment of the long window, with the standing label that
its *daily* readings carry staleness noise. Milan-native daily data remains
preferable if the EODHD plan ever adds Borsa Italiana.

**Fill validation (Section 5.9) — all PASS, ISP now against Milan/IBKR:**

| Fill (IBKR record) | Dataset day range (O/H/L/C) | Result |
|---|---|---|
| 2026-08-06 BUY 545 ISP @ €6.843 | Milan/IBKR 6.637 / 6.864 / 6.637 / 6.807 | PASS |
| 2026-08-14 BUY 26 IMB @ 2629p | IMB.LSE 2637 / 2652 / 2597 / 2609 | PASS |
| 2026-08-14 SELL 25.5427 EUAD @ $47.86 | EUAD.US 47.86 / 48.15 / 47.61 / 47.89 | PASS |
| 2026-08-14 SELL 21 INDA @ $49.775 | INDA.US 49.88 / 49.92 / 49.735 / 49.78 | PASS |

Cash leg (ruling #1): EODHD 13-week T-bill series, 2015-01-02 → 2026-08-14,
2,906 rows, no gaps; coupon-equivalent yield column used; accrual applied
with the prior day's rate (no look-ahead).

**Verdict: DONE — disputes #1–#3 fixed, #4 closed with label.**

## 5. Remaining open items

1. ~~IBKR account-statement cross-check of received dividends~~ —
   **CLOSED 2026-08-19: Jim accepted the IMB dividend reconciliation** on
   the two-source evidence tier (IBKR corporate-action records + company
   RNS; the MCP toolset exposes trades/positions but not statement history,
   so the optional third layer — the 2026-06-30 credit of 26 × 41.68p —
   remains available to him in Account Management but is not required).
2. **FFH dividend currency**: IBKR records the USD declaration, EODHD the
   CAD-converted amounts; the reconciled table keeps EODHD's CAD values
   (matched to IBKR by date only). A conversion-rate audit of those 12
   annual rows is pending — impact bounded by FX noise on a ~1.4% yield.
3. **SCCO pre-2021 declared amounts** rest on inverting EODHD's restatement
   chain (verified exactly on all 19 overlap rows, 2021-11→2026-08); no
   second source covers 2015–2021 declared values on this plan.
4. **ISP treaty relief**: 26% Italian withholding is the IBKR default; if
   relief to the 15% treaty rate is ever filed, ISP's net drag shrinks by
   ~0.9pp/y — flag for the contest's ISP verdict.
5. **ISP pre-2021 daily series is the XETRA proxy** (accepted with label,
   spot-checked monthly; daily staleness noise remains).
6. Contest backtests must model **cash-in-lieu on SCCO fractional stock
   dividends** only if position sizes make fractions material (at 6.16
   shares they are; noted for the contest engine).

## 6. STOP (agenda item 5)

Items 1–4 of the agenda pass under rev 2. X = 25% is confirmed (2026-08-19,
see §1). Per Section 9.5 no hypothesis agent runs until the candidate
universe file is written and committed.

**Session verdict: ACTION — X confirmed and the IMB dividend evidence
accepted (both 2026-08-19). The single remaining gate is the candidate
list: drafted, approved by Jim, and committed. Then the contest can run.**

## 7. Addendum 2026-08-19 — Milan-native upload cross-check

Jim supplied a Milan-native ISP.MI daily file (Yahoo-Finance-style columns,
EUR, 2025-08-19 → 2026-08-19), saved verbatim as
`data/prices/ISP.MI.upload.csv` and checked by
`analysis/check_isp_upload.py`:

- **vs the IBKR Milan bars** (249 overlapping days): close differences mean
  +0.006% (unbiased), mean absolute 0.167%, worst 0.616% (2026-02-10, 6.048
  vs 6.011), 6 days over 0.5% — normal print/venue noise. This is a third
  independent source confirming the SMART-routed IBKR series; the residual
  routing concern from §4 is closed.
- **Fill check**: 2026-08-06 BUY @ €6.843 sits inside the upload's Milan day
  range (6.786–6.864) — PASS from a second Milan source.
- **Dividend ex-dates**: the upload's Adj Close ratio implies exactly two
  events in its window, 2025-11-24 and 2026-05-18 — matching the reconciled
  table's dates precisely (implied amounts 0.192/0.197 vs actual
  0.186/0.190 are within the file's 6-decimal rounding noise).
- **Quality notes**: the upload has null rows on 2026-07-20 and 2026-07-31
  where IBKR has real bars (6.33, 6.5625), and only ~1 year of depth, so the
  IBKR daily series **remains primary**; the upload is retained as
  verification evidence. Its extra days (2026-08-17→19) extend past the
  dataset's common end (2026-08-14) and will fold in at the next full
  refresh rather than extending one name piecemeal.

**Verdict: DONE — third source agrees; no pipeline change needed.**
