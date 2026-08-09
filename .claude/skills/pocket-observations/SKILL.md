---
name: pocket-observations
description: Recurring monitoring brief for the Investment Lab — enforce the review cadence, staleness rule, and calendar gates across the portfolio and open research; surface forecast resolutions due and material changes since the last brief. Use when the user asks for observations, a check-in, a morning/weekly lab brief, or what needs attention. Usage - /pocket-observations
---

# Pocket Observations — the monitoring loop

The constitution's monitoring rules (§13) only work if something actually
walks the calendar. This skill is that walk. It produces a short brief of
what CHANGED and what the process REQUIRES — not market commentary, not
predictions, no "our view on stocks." If nothing needs attention, the
correct brief is short and says so.

## Steps

1. **Establish the delta window.** Find the most recent brief in
   `lab/portfolio/observations/`; everything since its date is in scope. If
   none exists, this is the founding brief — say so and baseline everything.

2. **Process obligations first (these outrank everything, §2):**
   - **Calendar gates (§13.6).** Scan `lab/` (runs, judgment memos,
     observations) for dated decision windows. Any window expiring within 7
     days: flag loudly. Any window found already lapsed WITHOUT a recorded
     act/pass/extend decision: report as a process violation of the same
     severity as entry without an exit plan — top of the brief.
   - **Staleness rule (§13.5).** Any alert, trigger level, or watchlist
     entry older than two quarters without reconfirmation: mark STALE,
     state that it may not be acted on until re-underwritten.
   - **Review cadence (§13.2).** Any position unreviewed for more than one
     quarter: list with its last-review date. Check the upcoming-earnings
     endpoints for holdings reporting in the next two weeks — each print is
     a scheduled review trigger.
   - **Forecast resolutions (§14).** Scan `lab/calibration-ledger.md` for
     forecasts whose resolution date has passed or falls within 7 days.
     Due-or-past ones are listed with the instruction to run
     `/pocket-feedback` — an unresolved expired forecast is a silently
     lapsing window by another name.

3. **Kill-line watch (§13.1).** For every kill line recorded in judgment
   memos and the driver map, check the observable it names (dividend
   actions, leverage, price levels, announced capacity) against fresh data.
   A fired kill line is reported in one sentence, first line of the brief,
   before anything else: kill lines are executed, not renegotiated.

4. **Material deltas since last brief.** Only then, the news:
   - Holdings with price moves beyond the threshold in `driver-map.yaml`
     (default ±8% since last brief), with one line of cause from primary
     sources — filings and company releases outrank aggregator headlines
     (§8.1).
   - Macro prints in the window that touch mapped drivers (rates decisions,
     CPI, treasury-yield shifts >25bp), stated as facts with dates.
   - New filings for holdings (8-Ks, insider clusters via edgar-tools).
   - Cap trajectory: any §15.2 exposure that moved meaningfully toward or
     past its cap due to price drift alone — drift rebalances the portfolio
     whether you notice or not.

5. **Write the brief** to `lab/portfolio/observations/<YYYY-MM-DD>.md`:
   fired kill lines and violations first, then obligations due, then
   deltas, then a `nothing else requires attention` line if true.
   Append-only, like everything else in `lab/`.

6. **Offer the schedule once.** If the user hasn't scheduled this and the
   session environment supports recurring triggers, mention (once, not
   every run) that the skill can run on a weekday cadence; a stale
   monitoring loop is itself a §13.5 violation — the monitor must not need
   monitoring.

## Hard rules

- No predictions, no positioning suggestions, no "we expect." Facts, dates,
  obligations, and rule citations only.
- Never mark an obligation done because it was mentioned in a brief.
  Briefs surface obligations; humans discharge them; only a recorded
  decision (act/pass/extend, review note, resolution row) closes one.
- If two consecutive briefs list the same lapsed obligation, escalate the
  language: repetition without action is how windows lapse silently.
