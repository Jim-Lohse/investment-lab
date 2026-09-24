# CFTC weekly summary: specification

What the weekly CFTC Commitments of Traders summary contains, when it is sent,
and how it decides between a research action and situational awareness. Two
Claude Routines follow this file; their prompts only name the private parts
(the Notion database and the email address), so the rules change with a commit
here rather than by editing a Routine. The general writing rules in `CLAUDE.md`
apply on top of this file.

## Schedule

| Step | UTC | US Eastern (daylight / standard time) |
|---|---|---|
| CFTC publishes positions as of Tuesday | Fri 19:30 / 20:30 | Fri 3:30 pm |
| `update-signals.yml` fetches CFTC only | Fri 21:30 | Fri 5:30 pm / 4:30 pm |
| Routine "CFTC weekly intelligence": main run | Fri 22:30 | Fri 6:30 pm / 5:30 pm |
| Routine "CFTC weekly intelligence backup" | Sat and Tue 12:00 | 8:00 am / 7:00 am |

Holiday weeks slip the release to Monday, which the daily 07:30 UTC fetch
picks up and the Tuesday backup delivers. A government shutdown stops
publication; the backups send one short "report delayed" note per missing week.
Only one summary is sent per week: the Notion database is the record of what
was sent, and every run checks it first.

The runs cannot reach publicreporting.cftc.gov from Claude's sandbox; they
read only what the workflow committed.

## Run steps

1. Check out `origin/main` and `pip install -r signals/requirements.txt`. If
   that fails or `data/derived/cftc_flows.csv` is missing, email a two-sentence
   failure notice (subject "CFTC weekly intelligence: run failed") and stop.

2. Facts for today. Run `python -m signals.cftc_cot brief`. It prints and
   writes `data/derived/cftc_brief.md`: D (the latest week in the data), the
   week that should be published by today, Status (current or STALE), and one
   row per headline series with net, change from last week, move rank, net
   rank, net a year earlier, and flags. Use these numbers exactly. Never
   estimate or fill a missing number.

3. What has already been sent. Look in the Notion database for pages whose
   Week equals D and whose Verdict is not "Report delayed" (query the data
   source; if querying is unavailable, search it for the title "Week of D").
   Also read the most recent earlier page's What-now items.

4. Decide.
   - A page for week D (not "Report delayed") exists: reply "Week D already
     delivered." and stop. Send nothing.
   - Status current and no page for D: write the summary and deliver it
     (next two sections).
   - Status STALE on the Friday run: stop quietly; the fetch may be late and
     Saturday's run retries.
   - Status STALE on the Saturday or Tuesday run: if a "Report delayed" page
     already exists for the expected week, stop quietly. Otherwise create one
     (Name "Week of <expected week>: report delayed", Week = expected week,
     Verdict "Report delayed") holding two plain sentences, which week's
     report is late and when the next check runs, email the same two
     sentences with subject "CFTC weekly intelligence: week of <expected
     week> report delayed", and stop.

## The summary

Follow `CLAUDE.md` (four sections Bottom line, What, So what, What now; plain words; numbers in tables; about one page; its exact closing sentence). No italics anywhere. Words: say "institutions (pension funds, mutual funds, insurers)" for asset managers and "hedge funds" for leveraged money and managed money. Explain "net" once: contracts betting on a rise minus contracts betting on a fall.

Every row in the What table gets an Action column, and every item is one of exactly two labels:

- "Research action". Use it for: a series flagged "unusual move" or "extreme net"; a series flagged in the previous week's page that moved the same way again (say "second week running" and put it on the watch list); a previous page's What-now item that this week's data resolves (say whether it was confirmed or turned out to be noise). A research action is only ever one of: re-check next week, add to or remove from the watch list, list which of Jim's holdings are exposed, or compare with another signal in the repo. Never suggest buying, selling, sizing or timing a position.
- "Situational awareness only": everything else.

The Bottom line names every research action first. If there are none, it says plainly that this week is for situational awareness only.

In So what, cover the relevant caveats in plain words:

- Quarterly expiry. Stock-index futures (S&P 500, Nasdaq-100) expire on the third Friday of March, June, September and December, and positions roll to the next contract in the week before. Dollar-index futures expire two business days before the third Wednesday of those months. If the week ending D contains or is just before one of these dates, or open_interest in cftc_flows.csv fell more than 15% from the week before, say that expiring positions can inflate the move and that next week's report confirms it or not.
- A hedge fund's bet against stock-index futures is often the other side of owning the stocks, not a bet that stocks fall.
- These are contract counts, not dollars and not fund flows. They stand in for SPY, QQQ, UUP, GLD and USO; they do not measure money going into them.
- The dollar-index market is small (give its open_interest), so a few traders can move it.
- Positions are as of Tuesday and published Friday.

What now: a table (Owner Claude or Jim, what, what would close it). Claude owns re-checks; anything for Jim is labelled optional unless it is needed.

## Delivery

1. Create the Notion page in the data source: Name "Week of D: <short headline>", Week = D, Verdict = "Research action" if any row has one, otherwise "Situational awareness only", Flags = the markets with a research action, Emailed unchecked. Use Notion-flavored markdown: an orange callout for the Bottom line (gray if situational awareness only), `<table header-row="true">` tables, research-action rows with `color="orange_bg"`. End with a source line naming `data/derived/cftc_flows.csv`.
2. Send the email with the Gmail send tool to the address in the Routine prompt. Subject: "CFTC weekly intelligence, week of D: research action (<markets>)", or "CFTC weekly intelligence, week of D: situational awareness only". Use htmlBody with the same four sections, inline-styled tables, research-action rows shaded #fff4e5, and a link to the Notion page. Also include a plain-text body.
3. Set Emailed on the Notion page to checked.

If the email fails, leave Emailed unchecked and say so in your closing message. If Notion fails, still send the email and say the page could not be saved.

The run ends with three lines: what was sent (or why nothing was), the Notion
page link, and any failure.

## Why the numbers are computed in code

`python -m signals.cftc_cot brief` computes every figure the summary quotes,
so the written summary never recomputes or estimates one. The flags in
`cftc_flows.csv`: `unusual_move` when a weekly change is bigger (either
direction) than 90% of that series' earlier weekly changes; `extreme_net` when
the net sits above 95% or below 5% of its earlier weeks. Ranks use only weeks
before the one ranked and need a year of history, so a flag never uses
information that was not available that week. Since 2006 about 10% of weeks
carry an `unusual_move` flag per series, which is what the threshold implies.
