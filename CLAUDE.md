# IBKR Sleeve Optimization Pilot — Project Brief and Rules

Save this file as `CLAUDE.md` in the project directory (branch or subdirectory of the
`investment-lab` repo) so every Claude Code session and every subagent inherits it.
The Investment Lab constitution (v2.2.1, repo root) governs this project. Where this
brief and the constitution conflict, the constitution wins.

---

## 1. Project definition

- **Goal:** find the optimal version of the IBKR sleeve using a multi-agent process:
  hypothesis agents propose portfolios, adversarial agents attack them, research agents
  supply evidence, and a synthesis pass produces a verdict.
- **Scope:** IBKR sleeve only. A separate future project will handle an unconstrained
  (no geographic bounds) portfolio. Do not expand scope into that project.
- **Outcome space:** keep, replace, or scrap any or all of the current names. Scrapping
  the names is allowed. Scrapping the mandate is not (see Section 3).

## 2. Objective function (decided — do not reopen)

- **Primary objective:** maximize return SUBJECT TO a maximum drawdown cap.
  Drawdown = worst peak-to-trough decline in portfolio value.
- **The cap X is not yet set.** It must be DERIVED in Session 1 from the household
  inputs below — never assumed, never a round number picked for convenience:
  - Retirement nominal target: ~$1.97M
  - Horizon: 14 years
  - Withdrawal rate assumption: 3.5%
  - Required nominal return on liquid accounts: approximately zero (pension +
    Social Security act as bond-equivalents)
- **Cap check:** after deriving X, backtest how often the cap would have fired on
  sleeve history. A cap that fires rarely is a seatbelt; one that fires constantly is
  a whipsaw machine. Report firing frequency alongside the level.
- **Sharpe and Calmar are tiebreakers and diagnostics only.** They are never the
  objective. If two portfolios have similar capped returns, prefer the better Sharpe.

## 3. Universe rules

- **Mandate (hard constraint for the verdict):** international macro-conviction,
  ex-US. Existing guardrails apply: 50% cap total active ex-US at the household level,
  12% Japan, 8% Korea-memory, 6% any other single country.
- **Instrument-agnostic:** any wrapper is eligible — foreign ordinary shares, ADRs,
  ETFs, cash, and T-bills. The agents pick the EXPOSURE; the wrapper is then chosen
  on after-cost returns. Cash/T-bills must be in the toolkit (the drawdown cap
  requires a de-risk asset by construction).
- **Challengers come from a written finite list.** Before any contest runs, the
  candidate universe (incumbents + challengers) must exist as a committed file.
  No agent may add a name mid-contest.
- **Incumbent positions (verified via IBKR API, 2026-08-14):**
  | Name | Venue | Shares | Weight (of NLV) |
  |---|---|---|---|
  | ISP (Intesa Sanpaolo) | Borsa Italiana | 545 | 37.6% |
  | RR (Rolls-Royce) | LSE | 90 | 16.2% |
  | IMB (Imperial Brands) | LSE | 52 | 15.8% |
  | FFH (Fairfax Financial) | TSX | 1 | 14.1% |
  | SCCO (Southern Copper) | NYSE | 6.1649 | 9.9% |
  | Cash | — | — | 6.4% |
  - NLV: $11,622.81. Total cash in USD terms: $741.32 (includes €29.27 leftover).

## 4. Shadow-price diagnostic (decided — run exactly once)

- Run the primary contest INSIDE the mandate. Then run ONE labeled diagnostic
  contest with the geography constraint OFF — same objective, same frictions,
  same data, same candidate-list discipline.
- Report the gap between the two winning portfolios in return and drawdown terms.
  That gap is the measured cost of the ex-US mandate ("shadow price" = the price
  of a rule, measured by comparing results with the rule on vs off).
- The verdict memo stays inside the mandate regardless of the gap. A large gap is
  recorded as the opening finding for the future unconstrained project — it does
  not change this pilot's verdict.

## 5. Hard data rules (apply to every agent, every session)

1. **Zero fabrication.** Never guess, interpolate, or invent a missing data point.
   If data is missing, halt and list exactly what is missing.
2. **Point-in-time data only.** Use prices, dividends, and corporate actions as they
   were knowable on the date in question.
3. **Signal lag.** Signals are generated on prior-period data only. Yesterday's close
   may decide today's trade. Same-day close may never decide same-day execution.
4. **Currency.** Convert all returns to USD before any comparison or aggregation.
   Handle FX explicitly — never compare a GBP return to a USD return raw.
5. **Frictions are mandatory in every backtest.** No frictionless results, ever:
   - Venue commissions (IBKR tiered/fixed per venue)
   - UK stamp duty: 0.5% on every UK purchase (LSE names)
   - Italian financial transaction tax: 0.1% on Borsa Italiana purchases
   - FX conversion spread on every currency conversion
   - ETF expense ratios where applicable
6. **Dividends and corporate actions included.** Total-return series, split-adjusted.
7. **Data alignment.** These names trade on four venues with different holidays.
   Align calendars explicitly (align/reindex/forward-fill with a stated rule) before
   any math. Never let a silent inner join drop history.
8. **Label inputs.** Any multi-period calculation prints the raw values and dates
   used BEFORE showing the computed output.
9. **Validation against known fills.** The dataset must reproduce these before any
   contest runs (from IBKR records):
   - 2026-08-06: BUY 545 ISP @ €6.843, Borsa Italiana (+~0.1% FTT)
   - 2026-08-14: BUY 26 IMB @ 2629p, LSE (+0.5% stamp duty + commission)
   - 2026-08-14: SELL 25.5427 EUAD @ $47.86
   - 2026-08-14: SELL 21 INDA @ $49.775
   If the pipeline's prices for those dates disagree materially with these fills,
   stop and reconcile before proceeding.

## 6. Agent architecture rules

1. **Separate contexts, always.** Each agent runs as its own subagent with its own
   context window. Never simulate multiple agents inside one conversation.
2. **File-based communication.** Agents write memos to a `/memos` directory. The
   adversarial agent reads the hypothesis memo COLD — it never sees the hypothesis
   agent's reasoning process, only the written memo.
3. **The adversarial brief includes attacking the metric itself.** Every objective
   has a blind spot; the adversarial agent must state what the chosen metric cannot
   see and how the hypothesis might be exploiting it.
4. **Consensus is written, not assumed.** The synthesis pass cites which objections
   were resolved, which were accepted as open risks, and which killed a hypothesis.

## 7. Backtest and simulation rules

1. **In-sample / out-of-sample split** (e.g., 70/30) on every strategy test.
2. **Monte Carlo on resampled returns**, not just the single historical path.
   State the number of paths and the resampling method.
3. **Honest history claim.** Overlapping history for the incumbents is roughly two
   years. Any result must be labeled with its actual sample window. The honest claim
   is "best over [window]," never "best."
4. **Overfitting audit.** More candidates + short history = more lucky noise. The
   adversarial agent checks whether a winning portfolio's edge survives the
   out-of-sample window and the Monte Carlo distribution, not just the full-sample fit.
5. **Report survivorship caveats.** The candidate list contains only names that
   exist today; state this limitation in the verdict memo.

## 8. Deliverables

1. **Verdict memo — one per incumbent name:** KEEP / REPLACE / SCRAP, with proposed
   weight, the evidence tier, and the specific test results that drove the call.
   Feeds the existing sell-rule and tier framework; does not replace it.
2. **Proposed portfolio(s)** with weights, expected capped-return profile, and the
   cap-firing frequency.
3. **Shadow-price report** (Section 4) — one page, the gap in numbers.
4. **Open-items list** — anything unverified is flagged, never estimated.

## 9. Session 1 agenda (run in this order)

1. Derive the drawdown cap X from the Section 2 household inputs. Show the math.
2. Check X's firing frequency against sleeve history.
3. Confirm this file is committed as `CLAUDE.md` in the project directory.
4. Build the price/dividend dataset (EODHD primary source) for the five incumbents.
   Run the Section 5.9 validation against known fills. Print raw values and dates.
5. STOP. Do not run any hypothesis agent until items 1–4 pass and the candidate
   list (Section 3) is written and committed.

## 10. Communication rules for outputs to Jim

- Plain language. Define any technical term at first use, in one sentence, with what
  it means for the decision.
- Every research thread ends with a verdict line: DONE / ACTION / BLOCKED / REOPEN IF.
- Label all inputs (raw values + dates) before showing calculated outputs.
- Never quote a balance or position figure from an earlier snapshot after a
  transaction — re-pull.
- Flag missing data explicitly; never estimate around it silently.
