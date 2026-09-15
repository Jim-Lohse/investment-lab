# Daily summary: instructions for the scheduled Routine

This file is the whole specification for the daily intelligence summary. The
Routine that runs it holds only a short pointer to this file, so the wording,
the shape and the rules can be changed here with a commit, and never by
editing the Routine in the browser. Anything here overrides habit.

## Who you are writing for

Jim is building his economics vocabulary. He has asked, in his words, to
finish the summary with zero questions about what the data means. A summary
that is technically correct but needs a glossary has failed. Write so a smart
reader with no economics training understands every line.

## Standing rules

Do not recommend trades. Zero fabrication: a figure you cannot find is written
as "not reported", never estimated. Never modify the repository, never push,
never open a pull request. Never create, change or delete a scheduled task or
Routine.

## Step 0. Get access to the repository, then find the baseline

Try a local checkout first:

```
cd /home/user/investment-lab && git fetch origin main && git checkout -q --detach origin/main
```

If that works, the git commands below work as written. If there is no such
directory, or git is unavailable, read the repository through the GitHub tools
instead: `list_commits` and `get_file_contents` against owner `Jim-Lohse`, repo
`investment-lab`. `git log` becomes `list_commits` on branch main; `git show
<sha>:<path>` becomes `get_file_contents` with that path and ref `<sha>`. Do
not stop because git is missing.

Then find the baseline. Read the newest comment on issue #3, "Trade-signal
intelligence log" (owner `Jim-Lohse`, repo `investment-lab`, issue 3). Its
first line reads `Summary through commit <sha> — <date>`; that sha is the
baseline. If no summary comment exists yet, the baseline is the newest commit
on main older than 24 hours.

## Step 1. Find what landed

List the commits on main after the baseline whose subject starts with
`signals: data update`:

```
git log --format='%H %s' <baseline>..origin/main -- data/
```

If there are none, or every one ends in `no new prints`, stop. Post nothing,
and end with the single line: `No new figures since the last summary; nothing
posted.`

Otherwise read, in this order:

- `data/derived/whats_new.md` at **each** of those commits, so a figure that
  landed in the morning run is not missed by the afternoon one.
- `data/derived/latest_report.md` at the newest commit.
- The rows you need from `data/derived/taiwan_signals.csv`,
  `korea_signals.csv`, `japan_signals.csv` and `us_signals.csv`. Pull at least
  a year of history for anything flagged, so you can tell a lasting trend from
  a one-month jump. These files are large; reading through GitHub tools, fetch
  only what a flag actually needs.

### Columns worth knowing

In `japan_signals.csv`, `yoy_pct` is growth measured in yen, `yoy_pct_usd` is
the same growth measured in dollars, and `fx_effect_pt` is the difference —
the share of the growth that is only the weaker yen. Always report the dollar
figure alongside the yen one. The yen figure alone overstates what really
happened. Korea and United States figures are already in dollars and need no
such adjustment.

## Step 2. Judge every flag

Each flag in `whats_new.md` gets exactly one verdict:

- **ACT NOW** — Jim should do something today. For example: two countries'
  figures independently point the same way on something he is watching; a
  named country's share of what the United States buys shifts sharply; or a
  revision reverses an earlier reading.
- **KEEP WATCHING** — real, but nothing to do yet.
- **IGNORE** — say plainly why. Common reasons: it is mostly the weaker yen;
  last year's figure was unusually low so the growth looks bigger than it is;
  the figure covers only ten days; the amount is too small to matter.

Check whether a second country's figures agree, and name both countries when
they do:

- Japan's exports of chip-making equipment against Korea's imports of the same.
- United States purchases of network gear from Thailand and Vietnam against
  Taiwanese manufacturers' monthly sales.
- Japan's shipments of chip materials against United States purchases of the
  same.

## Step 3. Write it

Plain English. Short sentences. No italics. **One page maximum**, about 500
words or 60 lines. If it does not fit, drop findings rather than dropping the
explanations of the ones you keep.

```
Summary through commit <newest data-commit sha, full 40 characters> — <today YYYY-MM-DD>
```

**## Bottom line** — Two or three sentences. What someone who reads nothing
else should know. If anything needs acting on, name it here, first, starting
with `Act now:`.

**## What** — A short table of the figures that arrived: what it is, the
amount, how it compares with the same month a year ago, and what stretch of
time it covers. Plain column headings, no abbreviations. For Japanese figures
add a column showing the growth measured in dollars. Say what is new since the
last summary.

**## So what** — What it means, in ordinary words. Which of the things being
watched it bears on. Whether a second country's figures agree or disagree,
naming both. What would make the reading wrong. End this section with exactly
this sentence: `This is early evidence that puts things on the watch list; on
its own it is not grounds for a decision.`

**## What now** — A table with these columns: Who (Claude or Jim) | What to
do, in plain words | What would close it | Status (open, done, or blocked and
why). Carry forward every open item from the previous summary with its status
updated, then add new ones. Label anything optional as optional. If there is
nothing, write `Nothing open.`

End with a blank line, a line containing only `---`, then the line
`_Generated by [Claude Code](https://claude.ai/code)_`

## Words to avoid

Never write the left column. Use the right.

| Do not write | Write instead |
|---|---|
| YoY, year-on-year | compared with the same month last year |
| a bare customs code such as HS 8517.62.0090 | the customs code covering network gear, which includes optical transceivers |
| provisional, preliminary | a first estimate, which may be revised |
| flash, 10-day window | the first ten days of the month |
| origin share | share of what the United States bought |
| base effect | last year's figure was unusually low, which flatters this year's growth |
| aggregate, breadth | the combined total; how many companies grew |
| corroborates | a second country's figures point the same way |
| FX effect, currency-adjusted | how much of the growth is only the weaker yen |
| Tier 1 screening input | early evidence, not a reason to act |

No section symbols, no rule numbers, no unexplained abbreviations. Spell out
any unavoidable term in the sentence where it first appears.

## Step 4. Post it

Post the summary as a new comment on issue #3 using the GitHub
`add_issue_comment` tool (owner `Jim-Lohse`, repo `investment-lab`,
`issue_number` 3). Then return the same summary as your final message, so the
notification carries it. If the GitHub tools are unavailable, say so in one
line and still return the summary as your final message.
