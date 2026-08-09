---
name: pocket-portfolio
description: Portfolio analytics layer of the Investment Lab — ingest holdings (IBKR or CSV), decompose into economic drivers, factors, and growth/inflation quadrants with ETF look-through, run the scenario grid, and enforce §15.2 exposure control. Descriptive, not predictive. Use when the user asks to analyze, decompose, stress, or audit the portfolio. Usage - /pocket-portfolio [--source ibkr|csv] [--stress] [--audit]
---

# Pocket Portfolio — exposure decomposition and control

Answer one question honestly: **what do you actually own?** Not ticker by
ticker — driver by driver. Several individually attractive names on one
economic driver are one position for risk purposes and are sized as such
(constitution §15.2). This skill produces no buy/sell signals and no return
forecasts; it decomposes, stresses, and polices. The alpha question stays
with the human and with Pocket Analyst's paper judgments.

## Steps

1. **Ingest holdings.**
   - `--source ibkr` (default if the IBKR MCP tools are available): pull
     positions, account allocation, and balances via
     `get_account_positions` / `get_pa_allocation`. Record which account
     holds each position — the account-placement rule (§3 custody fit) is
     checked later.
   - `--source csv` (fallback, and the fully open path): read
     `lab/portfolio/holdings.csv` with columns
     `account,ticker,description,quantity,cost_basis,currency`. If the file
     is missing, write a commented example and stop with instructions.
   - Fetch current prices via the market-data MCP servers to compute weights.
     Never estimate a price from memory.

2. **Load or seed the driver map.** `lab/portfolio/driver-map.yaml` (template
   at `pocket-portfolio/templates/driver-map.yaml`) is the maintained,
   human-confirmed mapping of each holding to drivers, factor tilts, and
   quadrant sensitivities. For any holding missing from the map, PROPOSE an
   entry (from fundamentals, sector, and filings evidence) marked
   `confirmed: false`, and tell the user to review it. Unconfirmed mappings
   are flagged in every report — a driver decomposition built on unreviewed
   guesses is labeled as such, not passed off as measurement.

3. **Look through the wrappers (§15.2 explicitly requires this).** For every
   ETF or fund holding, pull constituents (ETF profile endpoints on the
   market-data servers) and allocate its weight to drivers via its top
   holdings and sector mix. An ETF is not a driver; it is a bag of them.
   Record overlap between ETF constituents and directly-held names — the
   classic hidden doubling.

4. **Decompose.** Produce three tables, weights summing to 100% each:
   - **Economic drivers:** growth, inflation, real rates, credit spreads,
     USD, energy/commodities, liquidity-and-vol regime, idiosyncratic.
     A holding may split across drivers; the map records the split.
   - **Factor tilts:** value, quality, momentum, size, low-vol, plus any
     named factor from the map's `named_caps` section (the "tobacco factor
     cap" pattern, §15.2).
   - **Quadrant balance:** portfolio weight by sensitivity to the four
     growth/inflation environments (G↑I↑, G↑I↓, G↓I↑, G↓I↓). This is a
     public-domain balance diagnostic, presented descriptively — it shows
     where the portfolio is lopsided, it does not claim the lopsidedness is
     wrong or predict which environment arrives.

5. **Check the caps.** Compare every driver, factor, and named-cap exposure
   against the limits declared in `driver-map.yaml`. A breach is reported as
   a §15.2 finding with the overweight names listed; consolidation ("pick
   the best single expression") is offered as the constitutional remedy, not
   auto-executed.

6. **Scenario grid (`--stress`).** Walk the portfolio through the standard
   grid: recession, inflation shock, rates +200bp, rates −200bp, credit
   crunch, commodity spike, USD ±10%. For each: arithmetic from the STATED
   sensitivities in the driver map, reported as a direction and a coarse
   range, never a precise number. Label every cell an estimate. Distinguish
   drawdown from impairment (§10.3) — flag any scenario where a position's
   loss looks permanent, not cyclical.

7. **Adversarial audit (`--audit`, or automatically when any cap is within
   20% of its limit).** Spawn `pocket-exposure-auditor` as a separate agent
   call with the holdings table, the decomposition, and the driver map — and
   NOT your narrative about why the portfolio is fine. Its job is refutation.
   Append its findings verbatim to the report.

8. **Write the report** from `pocket-portfolio/templates/portfolio-report.md`
   to `lab/portfolio/reports/<YYYY-MM-DD>.md`. Reports are append-only
   snapshots — never edit a prior report; the time series of reports IS the
   exposure history.

## Hard rules

- No expected returns, price targets, or trade recommendations anywhere in
  the output. Consolidation suggestions cite §15.2 and name the duplicated
  driver; they do not say which name to keep.
- Every number is either fetched (with tool provenance) or arithmetic on
  fetched numbers and stated sensitivities. Nothing from memory.
- Positions found in accounts that violate the standing account-placement
  rule are reported as Gate -1 custody findings, not silently accepted.
- The report carries the §21 validation label and the sentence:
  "Descriptive decomposition and stress arithmetic; not predictive; not
  investment advice."
