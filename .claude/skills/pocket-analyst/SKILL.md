---
name: pocket-analyst
description: Run the full Pocket Analyst loop on one name - information layer, three blind parallel analysts (company/macro/industry), supervisor reconcile/challenge/audit, then the investment judgment memo. Use when the user asks to run the lab, the loop, or the pocket analysts on a ticker. Usage - /pocket-analyst TICKER [--masked] [--tier 1|2]
---

# Pocket Analyst — the loop

Orchestrate the full pipeline on one name. The loop is the constitution's
Tier 1-2 workhorse (§4.1): cheap enough to run often, honest enough to
produce calibration data. Tier 3 (Conviction) work still requires the full
protocol in `investment-lab-constitution.md` — this loop feeds it, it does
not replace it.

```
research corpus (SEC / earnings / transcripts / macro / news)
        │
        ▼  /pocket-brief — retrieval, filtering, ranking → packets
        │
        ▼  three pocket analysts, blind, parallel (§6)
   company · macro · industry
        │
        ▼  pocket-supervisor — reconcile / challenge / audit
        │
        ▼  judgment memo — thesis, variant view, catalyst,
           valuation, risks, confidence + logged forecasts (§14)
        │
        ▼  /pocket-feedback — human labels → labeled examples
           (the corpus for evals and, eventually, a lab-tuned model)
```

## Steps

1. **Information layer.** Invoke the `pocket-brief` skill for the ticker
   (pass `--masked` through if given). If Gate -1 fails, the loop ends here —
   report and stop.

2. **Blind parallel first pass (§6 — the load-bearing step).** Spawn all
   three analysts in ONE message so they run concurrently, each as a separate
   Agent call, each receiving ONLY its own packet path:

   - `pocket-company-analyst` ← `packets/company.md`
   - `pocket-macro-analyst` ← `packets/macro.md`
   - `pocket-industry-analyst` ← `packets/industry.md`

   The spawn prompts must contain the packet path and nothing else about the
   name — no other analyst's packet, no preliminary view of yours, no hint of
   an expected answer (§6.2). Write each submission verbatim to
   `submissions/company.yaml`, `submissions/macro.yaml`,
   `submissions/industry.yaml` in the run directory AS EACH ARRIVES, before
   reading the next — submissions are preserved before any cross-examination
   (§6.2, §6.4).

3. **Supervisor.** Only after all three submissions are written, spawn
   `pocket-supervisor` with the three submission paths and the packet paths.
   Write its memo to `supervisor.md`. If `advance_to_judgment: blocked`,
   stop: report the blocking reasons and do not write a judgment memo — a
   blocked run is a first-class outcome (§13.6 spirit), not a failure to
   route around.

4. **Investment judgment.** Write `judgment.md` from the template at
   `pocket-analyst/templates/judgment-memo.md`. This is where synthesis is
   finally allowed. Required content, no section skipped:

   - **Thesis** — the claim, the payer, the mispricing hypothesis (Tier 1
     one-pager discipline, §4.1).
   - **Variant view** — what specifically the market misunderstands and why
     it is knowable now (§10 Mispricing anchors: "market underappreciates"
     with no mechanism scores a 2).
   - **Catalyst / recognition path** — recognition-clock stage and the time
     stop on the mispricing leg (§12.2, §13.3).
   - **Valuation** — reverse-DCF verdict, base-rate gap stated in words
     (§9), probability-weighted payoff sketch.
   - **Risks** — failure-risk state: pass / cap / veto (§10.3, a gate, not a
     weight), kill lines (§13.1), the supervisor's strongest unresolved
     disagreement verbatim.
   - **Confidence & forecasts (§14)** — 2-5 explicit probability forecasts
     with resolution dates, appended to `lab/calibration-ledger.md`
     (append-only; create with a header row if absent; never edit prior
     rows).
   - **Validation status (§21)** — the standing label, verbatim:
     "Architecturally reviewed and synthetic-gate tested; not yet
     empirically validated." Plus the independence label the supervisor
     assigned.

5. **Hand off to the human.** Report the run directory, the judgment
   headline, the forecasts logged, and prompt the user to grade the run with
   `/pocket-feedback <run-dir>` when they have formed their own view —
   ideally after doing their own §17 baseline pass first, and their labels
   are the loop's training signal, so ungraded runs are wasted runs.

## Hard rules

- Never simulate the analysts inside this conversation. If the Agent tool is
  unavailable, produce nothing labeled independent — run a single-pass
  analysis and label it "single-context analysis" prominently (§6.5).
- Never let a spawn prompt leak one analyst's view to another; if it happens,
  the run is contaminated — record it and restart the first pass.
- The judgment memo advises paper decisions only. No real capital moves on a
  loop recommendation (§20 Track 3 preconditions).
