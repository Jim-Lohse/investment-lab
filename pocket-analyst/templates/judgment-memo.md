# Judgment Memo — <ticker or mask> — <date>

```yaml
run: <lab/runs/... directory>
tier: 1 | 2
masked_first_pass: true | false
independence_label: architecturally-independent | single-context-analysis
```

## Thesis

<The claim, the payer, the mispricing hypothesis. One page maximum — §4.1.>

## Variant view

<What specifically the market misunderstands, why it is knowable now, and
why the market is wrong (structural seller, coverage gap, complexity). No
mechanism = no variant view — §10 Mispricing anchors.>

## Catalyst and recognition path

- Recognition-clock stage (§12.2): T_
- Time stop on the mispricing leg (§13.3): <date by which T3+ should have begun>
- Expected recognition mechanism: <what makes the market notice>

## Valuation

- Reverse-DCF verdict: <what the price already pays for>
- Base-rate gap (§9): <inside view vs reference class, stated in words —
  "requires a top-decile outcome" if it does>
- Probability-weighted payoff sketch: <bear / base / bull with weights>

## Risks

- Failure-risk state (§10.3): pass | cap | veto — <reasoning>
- Kill lines (§13.1): <specific observable conditions>
- Strongest unresolved disagreement (from supervisor, verbatim): <...>
- What this memo is most likely to be wrong about: <...>

## Confidence and forecasts (§14)

Overall confidence in thesis: <0.0-1.0>

| # | Forecast | P | Resolves |
|---|----------|---|----------|
| 1 | <observable event> | 0.__ | <date/event> |
| 2 | <observable event> | 0.__ | <date/event> |

<2-5 forecasts; each also appended to lab/calibration-ledger.md.>

## Validation status (§21)

Architecturally reviewed and synthetic-gate tested; not yet empirically
validated. Paper-only: no real capital moves on this memo (§20 Track 3).
