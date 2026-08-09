# Pocket Portfolio

The Investment Lab's portfolio analytics layer: a prosumer, fully
open-source toolchain that answers "what do I actually own, driver by
driver?" and walks the monitoring calendar so nothing lapses silently. It
implements constitution §15.2 (Portfolio-Level Exposure Control) and §13
(Exit and Review Discipline) as runnable Claude Code skills over data a
serious individual actually has: a brokerage account, cheap market-data
APIs, and a git repository.

```
        holdings (IBKR account, or plain CSV)
                        │
                        ▼
              DRIVER MAP (maintained data)          lab/portfolio/driver-map.yaml
        human-confirmed holding → driver /          proposed by the tool,
        factor / quadrant mappings + named caps     confirmed by the human
                        │
                        ▼
                 DECOMPOSITION                      /pocket-portfolio
        drivers · factors · quadrant balance        ETF look-through (§15.2),
        cap checks · scenario grid                  drawdown vs impairment (§10.3)
                        │
                        ▼
              ADVERSARIAL AUDIT                     pocket-exposure-auditor
        false diversification · wrapper             separate context — the
        doubling · silent factor bets               owner's story stays out
                        │
                        ▼
              MONITORING LOOP                       /pocket-observations
        calendar gates · staleness rule ·           §13.2/.5/.6, §14
        review cadence · kill-line watch ·          resolutions due
        forecast resolutions
                        │
                        ▼
        append-only reports and briefs              lab/portfolio/
```

## What this is

- **Exposure decomposition with look-through.** Every ETF is opened up;
  every holding maps to economic drivers (growth, inflation, real rates,
  credit, USD, commodities, liquidity/vol, idiosyncratic), factor tilts,
  and growth/inflation quadrant sensitivities. The mappings live in a
  version-controlled YAML file that the human owns — the tool proposes,
  the human confirms, and every report discloses how much of the
  decomposition is still unconfirmed.
- **Concentration control.** Named caps on shared drivers, checked every
  run, with drift trajectory. Several attractive names on one driver are
  one position and are reported as such (§15.2).
- **Stress arithmetic.** A standard scenario grid computed from the stated
  sensitivities — directions and coarse ranges, every cell labeled an
  estimate, impairment distinguished from drawdown (§10.3).
- **An adversary.** The exposure auditor runs in a separate agent context,
  without the owner's rationalizations in its input, and tries to refute
  the diversification story. The same architectural-independence principle
  the research loop uses (§6), applied to risk.
- **A calendar with teeth.** The observations brief enforces the review
  cadence, the two-quarter staleness rule, and the calendar gate — dated
  obligations surface until a recorded decision closes them (§13).

## What this is not

Deliberately and permanently:

- **Not an alpha engine.** Nothing here generates trade signals, expected
  returns, price targets, or timing. Institutional systems of this genre
  pair analytics with proprietary return forecasts; this project does not
  have return forecasts, does not claim to, and is honest that the hard
  part lives elsewhere. The only forward-looking numbers in the lab are
  the §14 probability forecasts attached to paper judgments — and those
  exist to be Brier-scored, not traded.
- **Not predictive.** The quadrant table shows balance, not which
  environment arrives. The scenario grid shows arithmetic, not
  probabilities.
- **Not advice.** Paper discipline throughout; the §20 Track 3
  preconditions govern any real-capital relevance, and the standing §21
  label applies to every report.

## Components

| Piece | Implementation |
|---|---|
| Decomposition + stress | `.claude/skills/pocket-portfolio/` |
| Adversarial auditor | `.claude/agents/pocket-exposure-auditor.md` |
| Monitoring brief | `.claude/skills/pocket-observations/` |
| Driver map template | `pocket-portfolio/templates/driver-map.yaml` |
| Report template | `pocket-portfolio/templates/portfolio-report.md` |

Artifacts land in `lab/portfolio/` (reports, observations, the driver
map). Reports and briefs are append-only snapshots; their time series is
the exposure history, which is the §19 spirit applied to risk: the process
record is the near-term product.

## Usage

```
/pocket-portfolio --source csv --stress --audit   # full pass from a CSV
/pocket-portfolio                                  # IBKR pull, decompose, caps
/pocket-observations                               # what needs attention today
```

Pairs with the research loop: Pocket Analyst decides what deserves paper
conviction; Pocket Portfolio decides whether the sum of those decisions is
still one portfolio or three bets wearing twelve tickers.
