# Portfolio Report — <date>

```yaml
source: ibkr | csv
holdings_count: <n>
lookthrough: <n ETFs decomposed | none held>
soft_decomposition_pct: <x% of weights on unconfirmed driver-map entries>
audit_run: yes | no
```

Descriptive decomposition and stress arithmetic; not predictive; not
investment advice. Architecturally reviewed and synthetic-gate tested; not
yet empirically validated (§21).

## Holdings

| Account | Name | Weight | Direct/Look-through | Map confirmed |
|---|---|---|---|---|

## Driver decomposition (§15.2)

| Driver | Weight | Largest contributors | vs cap |
|---|---|---|---|

## Factor tilts

| Factor | Net tilt | Note |
|---|---|---|

## Quadrant balance

| Environment | Helped | Hurt | Net weight exposed |
|---|---|---|---|
| Growth ↑ Inflation ↑ | | | |
| Growth ↑ Inflation ↓ | | | |
| Growth ↓ Inflation ↑ | | | |
| Growth ↓ Inflation ↓ | | | |

<One paragraph: where the portfolio is lopsided, stated descriptively.>

## Cap findings

<Every named cap: limit, current, trend since last report. Breaches cite
§15.2 and list the overweight names; the remedy decision is the human's.>

## Scenario grid (if --stress)

| Scenario | Direction | Coarse range | Impairment risk? |
|---|---|---|---|

<All cells are arithmetic on stated sensitivities. Estimates, not forecasts.
Impairment column applies §10.3: drawdown vs permanent loss.>

## Auditor findings (if run — verbatim, unedited)

<pocket-exposure-auditor YAML block>

## Changes since last report

<New positions, exits, drift-driven weight changes, cap trajectory.>
