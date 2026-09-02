# Working conventions for this repository

## Reporting after pipeline or workflow work

When a task produces data — a fetcher run, a workflow dispatch, a backfill,
a recomputed `data/derived/` — the closing message must contain, after the
engineering recap:

1. **Intelligence summary.** What the output actually says, in the language
   of the constitution: the headline prints with YoY, what is new versus the
   prior window, cross-source corroboration or conflict (Taiwan / Korea /
   Japan), and the caveats that bound the read (currency, calendar, provisional
   vs revised). Numbers go in short tables. Classify the read per §21 (Tier 1
   screening input; opens watch items, never decision windows, §13.7).
2. **Due outs.** A closing section listing every open item, each tagged
   `Claude` or `Jim`, with what would close it. Say explicitly when the list
   is empty. Optional follow-ups are listed as optional, not implied.

Engineering caveats (sandbox limits, how something was verified) belong in
the recap or the docs, not in due outs, unless they leave work undone.
