# The Investment Lab

A research-governance constitution for single-name equity research. Version 2.2.1.

## What this is

This document defines the rules under which an independent research process operates: how ideas enter and move through tiers of rigor, how evidence requirements scale with capital at risk, how agent independence and identity masking are enforced, how probability forecasts are logged and Brier-scored, how exits and reviews are pre-registered, and how the process validates itself against its own preserved historical decisions before it is allowed to claim anything.

It is a governance layer, not a stock-picking method. The stock-picking machinery it governs (idea pipeline, return engines, screening) is a separate system; this document is what keeps that system honest.

Two design commitments distinguish it:

1. Process metrics before returns. Section 19 (the Process-Metrics Principle) explicitly forbids grading the lab on paper P&L in its first year, in either direction. At realistic idea flow, near-term returns are statistically indistinguishable from luck. The near-term validation currency is calibration curves, thesis-accuracy rates, and gate behavior. Returns are the long-term currency.

2. Amendment from case law. The constitution changes only when its own operation produces a documented failure or near-failure. Every amendment in the changelog cites the specific case that produced it. Version 2.2.1's three amendments (a masking principle, a calendar gate against silently lapsing decision windows, and an evidence floor for opening dated windows) each trace to a named precedent from the lab's own records.

## What this is not

- Not investment advice. Nothing here is a recommendation to buy or sell anything.
- Not a track record. No performance is claimed, and by the document's own Section 19, none may be claimed yet.
- Not a backtest. The validation protocol (Section 18) uses point-in-time frozen evidence packets from the lab's own preserved research records, scored on decision quality and calibration rather than outcomes.

## Status

Version 2.2.1, applied 2026-07-30. Under open validation: the point-in-time case roster (Appendix A) is being executed, and the live calibration ledger is accumulating its first scored forecasts. Two Appendix A cases reference live positions and are de-identified until those positions close; the de-identification is itself an application of the document's disclosure discipline.

Worked case files will be added to this repository as their redaction passes complete, beginning with a closed case that resolved as an explicit pass — published precisely because a documented "no" is a stronger demonstration of process than a documented win.

## Structure

- `investment-lab-constitution.md` — the full constitution: purpose and authority, tiered rigor, research controls (independence, masking, evidence genealogy, base rates), scorecard and value-capture waterfall, decision and risk discipline (exit rules, calibration, committee), and the validation program (synthetic gates, baselines, point-in-time and forward tracks), with the seeded case roster as Appendix A.
- `pocket-analyst/` — the Pocket Analyst loop: a runnable Claude Code implementation of the lab's Tier 1-2 research pipeline (information layer → blind parallel analysts → supervisor → judgment memo → human-graded labeled examples). Agents and skills live under `.claude/`; see `pocket-analyst/README.md`.
- `pocket-data/` — local data store: syncs Sharadar tables (SF1 fundamentals, and optionally the Core US Equities Bundle) from Nasdaq Data Link into DuckDB — bulk export on first run, `lastupdated`-incremental after — with point-in-time query rules for the §18 validation track. See `pocket-data/README.md`.
- `pocket-portfolio/` — the Pocket Portfolio layer: prosumer portfolio analytics implementing §15.2 exposure control and §13 monitoring discipline (driver decomposition with ETF look-through, named caps, scenario arithmetic, an adversarial exposure auditor, and a recurring observations brief). Descriptive, not predictive — no signals, no return forecasts; see `pocket-portfolio/README.md`.

## License

Creative Commons Attribution 4.0 International (CC BY 4.0). See `LICENSE`.

## Disclaimer

This material is provided for informational and educational purposes only. It does not constitute investment advice, an offer, or a solicitation. The author holds or may hold positions in securities referenced in case materials. Do your own research; better yet, build your own governance for it.
