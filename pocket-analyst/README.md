# Pocket Analyst

The Investment Lab's runnable research loop: a small stack of Claude Code
agents and skills that turns the raw research corpus into an
adversarially-tested judgment memo, and turns human grades on those memos
into the labeled corpus the lab will eventually learn from. It is the Tier
1-2 workhorse under `investment-lab-constitution.md` — every layer below
maps to a constitutional control, and the constitution always wins (§2).

```
                 YOUR RESEARCH CORPUS
     SEC / earnings / transcripts / macro / news
                        │
                        ▼
               INFORMATION LAYER                    /pocket-brief
        retrieval + filtering + ranking             Gate -1 (§3), genealogy
        → per-analyst evidence packets              tagging (§8), masking (§7)
                        │
                        ▼
              POCKET ANALYST AGENTS                 blind, parallel,
       ┌────────────────┼────────────────┐          separate contexts (§6)
       ▼                ▼                ▼
  company analyst   macro analyst   industry analyst
  claims, unit      exposures,      structure, waterfall,
  economics, §8     regime stress   duration, clock
       │                │                │
       └────────────────┼────────────────┘
                        ▼
                SUPERVISOR AGENT                    pocket-supervisor
            reconcile / challenge / audit           correlation ledger (§5),
                        │                           adversarial pass (§15),
                        ▼                           process audit (§17)
              INVESTMENT JUDGMENT                   templates/judgment-memo.md
        thesis / variant view / catalyst            forecasts logged to the
        valuation / risks / confidence              calibration ledger (§14)
                        │
                        ▼
                 HUMAN FEEDBACK                     /pocket-feedback
                        │                           grades + Brier scoring,
                        ▼                           append-only (§14.2)
         labeled examples / evaluations             lab/feedback/*.yaml
                        │
                        ▼
        DOMAIN-SPECIFIC MODEL / AGENTS              future: persona iteration
                                                    and fine-tuning from the
                                                    accumulated labels (§19)
```

## Components

| Layer | Implementation |
|---|---|
| Information layer | `.claude/skills/pocket-brief/` |
| Pocket analysts | `.claude/agents/pocket-{company,macro,industry}-analyst.md` |
| Supervisor | `.claude/agents/pocket-supervisor.md` |
| Loop + judgment | `.claude/skills/pocket-analyst/` |
| Human feedback | `.claude/skills/pocket-feedback/` |
| Templates | `pocket-analyst/templates/` |

Run artifacts land in `lab/runs/<date>-<name>/` (packets, verbatim
submissions, supervisor memo, judgment memo); grades in `lab/feedback/`;
probability forecasts in `lab/calibration-ledger.md`. All three are
append-only — they are the audit trail (§20).

## Design commitments (inherited, not optional)

1. **Independence is architecture, not instruction (§6).** The three
   analysts run as separate agent calls on partitioned packets. If they
   can't be run that way, the output is labeled "single-context analysis" —
   never "independent."
2. **Evidence in, verdicts out (§18).** Packets carry no conclusions;
   contexts that have seen a verdict are recorded as contaminated for blind
   reruns.
3. **The supervisor challenges before it endorses.** Consensus is audited
   through the correlation ledger; three analysts citing one press release
   are one source (§5, §8.2).
4. **Every judgment bets something checkable (§14).** 2-5 probability
   forecasts with resolution dates, Brier-scored as they resolve. The
   calibration curve, not paper P&L, is the near-term report card (§19).
5. **The loop must earn its complexity (§17).** Every graded run records
   whether the machinery beat a competent single pass. "It added nothing"
   is a first-class label and, repeated, a mandate to simplify.

## The bottom of the stack

The last layer is deliberately empty for now. Labeled examples accumulate in
`lab/feedback/` under a stable schema; once there are enough of them, they
become (a) the regression suite any persona edit must pass, and (b) the
selection corpus for a domain-tuned analyst model. Until then, the loop's
output states its standing validation label (§21): *architecturally reviewed
and synthetic-gate tested; not yet empirically validated.*

## Usage

```
/pocket-brief NVDA --masked      # build packets only
/pocket-analyst NVDA --tier 2    # run the full loop
/pocket-feedback lab/runs/2026-08-09-NVDA   # grade it, resolve forecasts
```

Paper-only: no real capital moves on a loop recommendation until the §20
Track 3 preconditions are met.
