# Working conventions for this repository

## Reporting after pipeline or workflow work

When a task produces data — a fetcher run, a workflow dispatch, a backfill,
a recomputed `data/derived/` — the closing message ends with three sections,
after the engineering recap:

1. **What.** The headline prints the output actually contains: values, YoY,
   window, and what is new versus the prior window. Numbers in short tables.
2. **So what.** The read in the constitution's language: which thesis or
   watch item it bears on, cross-source corroboration or conflict (Taiwan /
   Korea / Japan), and the caveats that bound it (currency, calendar,
   provisional vs revised). Classify per §21: Tier 1 screening input; it opens
   watch items, never decision windows (§13.7).
3. **What now (due outs).** Every open item, each tagged `Claude` or `Jim`,
   with what would close it. Say explicitly when the list is empty. Optional
   follow-ups are listed as optional, not implied.

Engineering caveats (sandbox limits, how something was verified) belong in
the recap or the docs, not in due outs, unless they leave work undone.
