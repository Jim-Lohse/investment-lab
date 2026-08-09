---
name: pocket-feedback
description: Human-feedback layer of the Pocket Analyst loop — capture the user's grades on a judgment memo as an append-only labeled example, and resolve prior probability forecasts with Brier scores. Use when the user wants to grade, label, or score a run, or to resolve a forecast. Usage - /pocket-feedback RUN_DIR
---

# Pocket Feedback — human labels → labeled examples

Close the loop. Every graded run becomes a labeled example in
`lab/feedback/`; the accumulated set is the lab's evaluation corpus and,
once large enough, the training corpus for a domain-tuned analyst model.
Decision quality is scored on process and calibration, independent of
outcome (§14.5) — do not let a stock's move color a process grade.

## Steps

1. **Load the run.** Read `judgment.md` and `supervisor.md` from the given
   run directory. If the run was blocked (no judgment memo), the labeled
   example grades the blocking decision instead — a documented "no" is a
   first-class example (README: it is a stronger demonstration of process
   than a documented win).

2. **Elicit grades.** Ask the user (AskUserQuestion where interactive, plain
   prompts otherwise) for:

   - Verdict on each of: thesis, variant view, catalyst, valuation, risks —
     `agree | partial | disagree`, with a one-line reason for anything
     non-agree.
   - Which single claim in the memo they most doubt (the next falsification
     target).
   - Baseline comparison (§17): did the loop change anything versus their
     own competent pass — rejected a false positive, found a hidden
     beneficiary, caught a risk, improved calibration — or did complexity
     add nothing? "Added nothing" feeds the Simplicity Auditor and is a
     valuable label, not a failure.
   - Severity of any process violations they spotted.

3. **Write the labeled example** from
   `pocket-analyst/templates/labeled-example.yaml` to
   `lab/feedback/<run-dir-name>.yaml`. Append-only: never edit an existing
   example; corrections are new examples referencing the old id.

4. **Resolve forecasts.** Check `lab/calibration-ledger.md` for any forecast
   whose resolution date has passed. For each, ask the user (or verify from
   primary sources) whether the event occurred, compute the Brier score
   ((forecast − outcome)²), and append a resolution row — never editing the
   original entry (§14.2). If any probability band shows systematic
   overconfidence across ≥10 resolutions, say so: §14.4 requires a written
   adjustment.

5. **Report** the example path, running totals (examples by verdict,
   resolved forecasts, current mean Brier score), and — every 10th example —
   a one-paragraph drift note: what the labels say the loop systematically
   gets wrong. That note is the specification for the next iteration of the
   analyst personas, and eventually for fine-tuning data selection.

## Hard rules

- Never grade a run yourself and record it as human feedback. Empty labels
  are better than synthetic ones — a model trained on its own opinions of
  itself learns nothing (§18: contamination is a property of the context).
- Never revise a forecast, score, or example after the fact (§14.2). The
  ledger and feedback directory are append-only.
- Paper P&L is not a grade in year one, in either direction (§19).
