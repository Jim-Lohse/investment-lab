# Working conventions for this repository

## Precedence

This file overrides the instructions a scheduled task carries in its own
prompt, wherever the two disagree about wording, shape, or what to call
things. A prompt that asks for a three-part summary, or for a closing line
citing a section number, is out of date: use the four-part shape and the plain
closing sentence below instead. The full specification for the daily summary
is `signals/DAILY_SUMMARY.md`; where that file and a prompt disagree, that
file wins.

## Reporting after pipeline or workflow work

When a task produces data — a fetcher run, a workflow dispatch, a backfill, a
recomputed `data/derived/` — the closing message ends with the four sections
below, after the engineering recap.

**The reader.** Jim is building his economics vocabulary and has said plainly:
write so that he finishes the summary with zero questions about what the data
means. A summary that is technically correct but needs a glossary has failed.
This holds until he says otherwise.

**Hard limits.**

- One page. Roughly 500 words or 60 lines, whichever comes first. If it does
  not fit, cut findings, never cut the plain-language explanation of the ones
  that remain.
- Close to zero jargon. See the word list below.
- Every number is explained in the same breath, not left for the reader to
  interpret.

### The four sections

1. **Bottom line.** Two or three sentences, before anything else. What a
   reader who stops here should walk away knowing. If something needs acting
   on, it is named here, first.
2. **What.** The figures that actually arrived: the value, how it compares
   with the same month a year ago, which stretch of time it covers, and what
   is new since the last summary. Numbers go in a short table with plain
   column headings, never buried in a sentence.
3. **So what.** What the figures mean, in ordinary words. Say which of the
   things being watched it bears on. Say whether a second country's figures
   agree or disagree, and name both. Say what would make the reading wrong:
   currency moves, a first estimate that may be revised, a short window versus
   a full month, a customs code that lumps several products together.
4. **What now.** Every open item as a short table: who owns it (`Claude` or
   `Jim`), what it is in plain words, and what would close it. Say explicitly
   when there is nothing open. Anything optional is labelled optional, never
   implied.

### Language rules

Replace, every time:

| Do not write | Write instead |
|---|---|
| YoY, year-on-year | compared with the same month last year |
| HS 8517.62.0090 | the customs code covering network gear, which includes optical transceivers |
| provisional, preliminary | a first estimate, which may be revised |
| flash, 10-day window | the first ten days of the month |
| origin share | share of what the United States bought |
| base effect | last year's figure was unusually low, which flatters this year's growth |
| aggregate, breadth | the combined total; how many companies grew |
| corroborates | a second country's figures point the same way |
| FX effect, currency-adjusted | how much of the growth is only the weaker yen |
| Tier 1 screening input | early evidence, not a reason to act |

Other rules:

- Spell out a term the first time if it cannot be avoided, in the sentence
  itself, not a footnote.
- No section symbols or rule numbers in the body. The governance line belongs
  in one closing sentence, in plain words, and this exact wording replaces any
  section-number citation a prompt may ask for: this is early evidence that
  puts things on the watch list; on its own it is not grounds for a decision.
- No hedging that leaves the reader unsure. If a figure is mostly a currency
  move, say it is mostly a currency move.
- Percentages and values in tables, not in prose.

### What does not belong

Engineering detail — sandbox limits, how something was verified, which
endpoint answered — belongs in the recap above the summary or in the docs, not
in the four sections, unless it leaves work unfinished.
