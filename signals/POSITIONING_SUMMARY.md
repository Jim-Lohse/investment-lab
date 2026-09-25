# Positioning intelligence: specification

What the positioning layer collects, when, where it is delivered, and which
items are allowed to interrupt Jim before the weekly digest. Routines follow
this file; their prompts name only the private parts (Notion database, email
address, dashboard URL, the holdings page), so the rules change with a commit
here. The writing rules in `CLAUDE.md` apply on top of this file.

Purpose: situational awareness. Prime-brokerage notes (Goldman, Morgan
Stanley, JPMorgan) go to the banks' clients first and reach Reuters, the FT,
Bloomberg, Barron's and others days later, quoted with fixed phrases. The
searches catch those pickups. Everything here is early evidence that puts
things on the watch list; on its own it is not grounds for a decision.

## Privacy rule

The repository is public. Holdings, position sizes and account names never go
into a committed file, a commit message, a workflow log, an issue or a pull
request. Holdings live in a private Notion page named in the alert Routine's
prompt. At run time the Routine may copy them into
`signals/config/holdings.local.json` (git-ignored) to run
`python -m signals.positioning match`; it never commits that file.

## Schedule (U.S. Eastern)

| Step | When | What |
|---|---|---|
| Collect market-wide stories | Weekdays, 8:30 am (7:30 am in winter), on the existing 12:30 UTC workflow run | `python -m signals.positioning news`: the searches in `signals/config/positioning.json`, last 3 days, new stories appended to `data/positioning/headlines.csv`; weekly counts, calendar and `data/derived/positioning_brief.md` rebuilt |
| Same-day position alert | Weekdays, 9:30 am | Routine "Positioning same-day alert" (below). Silent unless a trigger fires |
| Weekly digest | Friday, 6:30 pm | A "Positioning" section inside the CFTC weekly summary (`signals/CFTC_WEEKLY_SUMMARY.md`), same email, same Notion page, and the macro dashboard's Positioning strip |

Once a day is deliberate. The feeds keep several days of stories, so one run
misses nothing, and a story known at 11 am instead of 8:30 am changes nothing
for awareness.

## Where each source belongs

| Source | Goes stale in | Delivery | Status |
|---|---|---|---|
| Prime-brokerage notes quoted in the press (the six searches) | About a week | Weekly digest; same-day only if it names a holding | Built |
| Any positioning story naming a holding (press, Bigdata.com, Alpha Vantage news) | Days | Same-day email | Routine to be created after merge |
| Calendar: month-end and quarter-end rebalancing, quarterly expiry, 13F deadline, Goldman Trend Monitor window, FINRA short-interest dates | n/a | Dashboard strip and digest | Built (Fed dates to load) |
| FINRA short interest, U.S.-listed holdings | About two weeks | Weekly digest when it shows a trend | Next phase |
| Schedule 13D on a holding | Days | Same-day email | Next phase, SEC filings page |
| Form 144 on a holding, above USD 5 million or 1% of shares outstanding | Days | Same-day email | Next phase |
| Schedule 13G, Form D, 13F, N-PORT on holdings | Weeks to a quarter | Weekly digest, SEC filings page | Next phase |
| Form ADV, N-CEN | A year | Not collected: too slow for positioning | Decided |

## The same-day alert (Routine "Positioning same-day alert")

Runs weekdays 9:30 am Eastern. Steps:

1. Read the holdings from the private Notion page named in the prompt. If it
   is empty, stop silently.
2. Check out `origin/main`. Write the holdings to
   `signals/config/holdings.local.json` and run
   `python -m signals.positioning match 1` (stories first seen today or
   yesterday that name a holding).
3. For each holding, search the last 24 hours with Bigdata.com (and Alpha
   Vantage news for U.S.-listed lines) for positioning stories only: hedge
   funds, short sellers or short interest, prime brokerage data, 13F or
   ownership filings, activist stakes, foreign investors net buying or
   selling, block trades. Ordinary company news (earnings, products) is not
   a positioning story and does not trigger an email.
4. Drop anything already recorded in the Notion database (same link, or same
   headline and holding).
5. If nothing is left, stop silently. Otherwise send one email for the run,
   subject "Positioning alert: <holding names>", with one entry per story:
   the headline as a link, the outlet and date, and two or three plain
   sentences on why it should not wait for Friday (what the story says the
   funds did, and which of Jim's holdings it touches). No trade
   recommendations. Record each story in Notion (Verdict "Same-day alert").

## The weekly Positioning section (inside the Friday CFTC summary)

Numbers come from `data/derived/positioning_brief.md`, used exactly:

- Loudness: distinct stories this week against the usual week (median of up
  to 12 earlier weeks). "Quieter than usual" below half, "about normal" up to
  1.5 times, "busier than usual" up to 2.5 times, "much busier than usual"
  above that. Before 4 weeks of history it says a baseline is being built.
- Up to five stories, record-type wording and bank-attributed first. For
  each, one plain sentence: who did what, according to which bank's data.
- The dated events in the next 21 days, marking estimates as estimates.
- Every item is situational awareness only. Busy weeks cluster around
  month-ends, quarterly expiries and Fed meetings; say so when that is why.

In So what, name the limits: these are press reports of bank data, not the
data; the press writes them when positioning moves are newsworthy, so quiet
weeks are under-reported; a count measures attention, not positions.

## Settings Jim can change (all in `signals/config/positioning.json`)

| Setting | Now | What it does |
|---|---|---|
| `queries` | Jim's six proven searches, verbatim | What is collected. Add searches below them |
| `tags` | Banks, buying or selling words, topics, record-type words | How stories are labelled and ranked |
| `loudness` | 12-week baseline, 4 weeks minimum, bands at 0.5, 1.5, 2.5 | The busy-or-quiet reading |
| `calendar.month_end_trading_days` | 5 | Width of the rebalancing window |
| `calendar.trend_monitor_after_deadline_days` | 3 to 10 | Estimated Trend Monitor window after the 13F deadline |
| `calendar.fomc_decision_dates` | empty | Fed decision days, copied from the Fed's calendar |
| `calendar.finra_short_interest_publication_dates` | empty (rule-based estimates shown) | FINRA's official dates override the estimates |
| `form144_alert` | USD 5 million or 1% of shares | Same-day Form 144 threshold |

The backfill (`positioning_backfill` input on the workflow, number of weeks)
builds the baseline at once and shows which searches actually return stories;
a search that returns nothing for 13 weeks is a candidate to reword.
