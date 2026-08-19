# Candidate universe — DRAFT v0.1 for Jim's approve / edit / cut

Status: **DRAFT — not yet the committed contest list.** Per CLAUDE.md
Section 3, no contest runs until this file is finalized and committed, and
no agent may add a name mid-contest. Jim approves, edits, or cuts; the
approved version becomes v1.0.

## How the names were generated (the context Jim asked for)

Four explicit channels, each name tagged below with its channel. Method
honesty: names came from model-knowledge peer mapping and the household's
own infrastructure, filtered by the mandate (ex-US macro-conviction), the
country guardrails, and a practical wrapper/data constraint learned in
Session 1 (Milan-only listings are hard on our data plan; LSE, XETRA, TSX,
US ADR/ETF paths are proven). **Being listed is not endorsement — the
contest exists to kill names.** Every thesis line below is a hypothesis to
be evidenced or refuted in the contest, not a data claim.

- **Channel A — incumbent peer mapping.** For each current holding's macro
  thesis, the closest liquid ex-US competitors. Rationale: if an incumbent
  deserves its slot, it should beat its own nearest peers after costs;
  if a peer beats it, that is a REPLACE candidate by construction.
- **Channel B — household signal infrastructure.** This repo already runs
  Taiwan MOPS monthly-revenue and Korea customs semiconductor-export
  pipelines as Tier-1 screening inputs, and the household guardrails
  (12% Japan, 8% Korea-memory) imply standing theses there. Candidates the
  existing signals can actually monitor.
- **Channel C — sold-position rematch.** Positions the household exited on
  2026-08-14. Adversarial discipline: the contest re-tests the exits with
  the same rules as everything else.
- **Channel D — cheap-beta null hypotheses.** Broad wrappers the
  stock-picks must beat after costs to justify existing (the constitution's
  simplicity-auditor instinct, applied to this sleeve).

## Derived constraints the contest must respect (mechanical, from the rules)

- Drawdown cap X = 25% on sleeve USD net-total-return NAV (confirmed
  2026-08-19).
- Country caps are household-level; at the guardrail-max deployment (sleeve
  = 50% of household) they translate to sleeve-level caps of:
  **Japan ≤ 24%, Korea-memory ≤ 16%, any other single country ≤ 12%** of
  sleeve NAV. Note: the current sleeve violates this at full scale (ISP =
  37.6% ⇒ Italy 18.8% of household vs 6% cap) — pilot-size artifact,
  recorded; contest portfolios must be legal at scale.
- Frictions per Section 5.5 (venue commissions, 0.5% UK stamp duty, 0.1%
  Italian FTT, FX spreads, ETF expense ratios); dividends net of
  withholding (IT 26%, CA 15%, UK 0%, US 0%); wrapper chosen per exposure
  on after-cost returns.
- Cash / 3-month T-bills are in the toolkit as the de-risk asset (required).

## Incumbents (automatically in; KEEP/REPLACE/SCRAP verdicts due per Section 8)

| # | Name | Exposure | Note |
|---|---|---|---|
| I1 | Intesa Sanpaolo (ISP) | Italian bank | data: IBKR Milan + XETRA proxy |
| I2 | Rolls-Royce (RR) | UK aero engines/defense | LSE |
| I3 | Imperial Brands (IMB) | UK tobacco value/income | LSE |
| I4 | Fairfax Financial (FFH) | Canadian insurance compounder | TSX |
| I5 | Southern Copper (SCCO) | copper (Peru/Mexico assets, NYSE wrapper) | NYSE |
| I6 | Cash / 3M T-bills | de-risk asset | required by construction |

## Challengers — DRAFT (channel-tagged; wrapper options in parentheses)

**Channel A — peers of ISP (European bank normalization thesis):**

| # | Name | Thesis to test | Wrapper/data path |
|---|---|---|---|
| C1 | UniCredit | Same Italian-bank thesis, historically more aggressive capital return; the direct "did we buy the right Italian bank" test | XETRA line or US OTC ADR (Milan-only path is a data problem — availability check required) |
| C2 | Banco Santander | Eurozone bank thesis without single-country overlap with ISP (Spain bucket) | NYSE ADR SAN or Madrid |
| C3 | BNP Paribas | Core-Europe universal bank; tests whether Italy-specific risk is being paid for | Paris / US OTC ADR |

**Channel A — peers of RR (European aerospace/defense cycle):**

| # | Name | Thesis to test | Wrapper/data path |
|---|---|---|---|
| C4 | BAE Systems | Defense budgets thesis with less single-product risk than RR | LSE (proven path) |
| C5 | Safran | The other big engine maker; RR's closest aftermarket-economics peer | Paris / US OTC ADR |
| C6 | MTU Aero Engines | Engine aftermarket pure-play | XETRA (proven path) |

**Channel A — peers of IMB (tobacco value/income):**

| # | Name | Thesis to test | Wrapper/data path |
|---|---|---|---|
| C7 | British American Tobacco | Same thesis, bigger next-gen portfolio; the direct IMB rematch | LSE, or NYSE ADR BTI |
| C8 | Japan Tobacco | Tobacco value + fills the Japan bucket the guardrails reserve | Tokyo / US OTC ADR |

**Channel A — peers of FFH (insurance compounder / hard market):**

| # | Name | Thesis to test | Wrapper/data path |
|---|---|---|---|
| C9 | Munich Re | Reinsurance pricing cycle, dividend-heavy alternative to FFH's equity-book style | XETRA |
| C10 | Zurich Insurance | Boring-compounder null vs FFH's hedge-fund-in-an-insurer model | Swiss / US OTC ADR (CH withholding 35%/15% treaty — cost check) |
| C11 | Fairfax India | Same manager, concentrated India macro; overlaps Channel C's INDA test | TSX FIH.U (USD) |

**Channel A — peers of SCCO (copper/electrification):**

| # | Name | Thesis to test | Wrapper/data path |
|---|---|---|---|
| C12 | Antofagasta | Pure-play copper, Chilean assets, LSE wrapper (vs SCCO's NYSE wrapper + Peru/Mexico) | LSE |
| C13 | Glencore | Copper plus trading arm; different way to own the same macro | LSE |
| C14 | Ivanhoe Mines | Higher-beta copper growth (DRC) — tests whether the cap tolerates more octane | TSX |

**Channel B — household signal infrastructure (Asia tech/macro):**

| # | Name | Thesis to test | Wrapper/data path |
|---|---|---|---|
| C15 | TSMC | The Taiwan MOPS revenue pipeline in this repo exists to watch exactly this; AI-capex chokepoint | NYSE ADR TSM (Taiwan 12%-scaled country cap... 6% household ⇒ 12% sleeve) |
| C16 | SK Hynix | Korea customs semi-export signal + the "Korea-memory" guardrail implies this standing thesis; HBM cycle | Seoul only — ADR illiquid; wrapper/data check REQUIRED before finalization |
| C17 | Samsung Electronics | Same Korea-memory thesis, cheaper multiple, weaker HBM position — the intra-Korea rematch | Seoul / LSE GDR; same data check required |
| C18 | Mitsubishi Corp | Japan bucket: trading-house cash machines, shareholder-return regime change | Tokyo / US OTC ADR |

**Channel C — sold-position rematch:**

| # | Name | Thesis to test | Wrapper/data path |
|---|---|---|---|
| C19 | EUAD (European defense ETF) | Sold 2026-08-14 — was exiting the defense theme (vs RR single-name) right? | US ETF (proven data) |
| C20 | INDA (India ETF) | Sold 2026-08-14 — re-tests India beta vs the new sleeve | US ETF (proven data) |

**Channel D — cheap-beta null hypotheses:**

| # | Name | Thesis to test | Wrapper/data path |
|---|---|---|---|
| C21 | VXUS (total ex-US index) | The null: does ANY picked portfolio beat just indexing ex-US after costs, under the cap? | US ETF |
| C22 | IEFA or VEA (developed ex-US) | Developed-only variant of the null | US ETF |

## Notes and open flags for finalization

1. **Survivorship caveat (Section 7.5):** every challenger exists today;
   the 2015-era loser set is invisible. Stated here, restated in verdicts.
2. **Data availability gate:** before v1.0, every surviving name gets an
   EODHD/IBKR coverage check (venue, history depth, dividends) — the ISP
   lesson. Names failing it get a wrapper substitution or are cut.
3. **Korea names (C16/C17)** are the most likely data casualties; if Seoul
   lines aren't reachable, options are the LSE GDR (Samsung), or honest
   exclusion with a note that the Korea-memory thesis stays household-level.
4. **Withholding differs by candidate country** (CH 35%/15%, DE 26.375%/15%,
   FR 25%/15%, JP 15.315%, TW 21%, KR 22%) — the contest's net-dividend
   table extends to whichever names survive Jim's cut.
5. List size: 22 challengers is deliberately over-inclusive for a first
   cut. More names + ~11y history = more lucky noise (Section 7.4), so
   pruning here is a feature, not a courtesy.
