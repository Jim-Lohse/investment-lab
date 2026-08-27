---
name: pocket-brief
description: Information layer of the Pocket Analyst loop — retrieval, filtering, and ranking of the research corpus (SEC filings, earnings, transcripts, macro series, news) into per-analyst evidence packets. Use when the user asks to build packets, gather evidence, or prep a name for the pocket analysts. Usage - /pocket-brief TICKER [--masked]
---

# Pocket Brief — the information layer

Build the evidence packets that feed the pocket analysts. This skill does
retrieval + filtering + ranking ONLY. No conclusions, no scores, no thesis
language — packets are evidence-in, verdicts-out (constitution §18 masking
principle). A packet that editorializes contaminates every analyst downstream.

## Steps

1. **Gate -1 first (constitution §3).** Before any retrieval, check the
   universe filter: ADV-based position capacity, market-cap band, accounting
   jurisdiction, custody fit, sanctions. Use the market-data MCP servers for
   quote/ADV and the sanctions endpoints where available. If Gate -1 fails,
   STOP and report the failure — a name that fails Gate -1 is not researched,
   no exceptions by enthusiasm.

2. **Create the run directory:** `lab/runs/<YYYY-MM-DD>-<ticker-or-mask>/`
   with subdirectory `packets/`.

3. **Retrieve and rank into three packets.** If the local Sharadar store
   exists (`lab/data/sharadar.duckdb`, see `/pocket-data`), prefer it for
   fundamentals and price history — and for any packet with a historical
   cutoff (§18), query it with `datekey <= cutoff` so the packet is
   point-in-time by construction. Rank within each packet by
   source class (§8.1) — primary regulatory records and filings first,
   management statements clearly labeled as such, aggregators last. Every
   item carries: source class, date, retrieval provenance (which tool/URL),
   and a one-line genealogy note where a chain is visible.

   - `packets/company.md` — latest 10-K/10-Q sections that matter (business,
     MD&A, risk factors via edgar-tools `filing_section`), financial
     statements and trends, earnings history and estimates, insider activity,
     latest transcript excerpts. Facts and figures only.
   - `packets/macro.md` — the macro series plausibly relevant to this name's
     exposures: policy rates, treasury yields, CPI/GDP prints, relevant FX
     pairs and commodities, credit conditions. Include 1-3y of history per
     series, not just the latest print.
   - `packets/industry.md` — competitor list with basic financial comparisons
     (edgar-tools `compare_companies`), announced capacity/expansion news,
     customer and supplier signals, news search results with genealogy notes
     (collapse ten articles citing one press release into one entry, §8.2),
     institutional-ownership and sentiment context.

4. **Masking (`--masked`, constitution §7).** Replace company name, ticker,
   industry label, geography, and famous-executive names with neutral
   identifiers ("Company Q", "End Market B", "Region 2"); coarsen distinctive
   figures into bands where analytical content survives. Write the
   mask-mapping to `packets/mask-key.md` and record that masking is friction,
   not blindness. The unmasked/masked state MUST be noted in each packet
   header so the pre/post-reveal delta can be run later (§7.2).

5. **Packet header (all packets):**

   ```yaml
   packet_id: <run-dir name>/<packet name>
   built: <date>
   masked: true | false
   gate_minus_1: pass  # packets only exist if it passed
   contamination_check: no analyst conclusions, scores, or rankings included
   ```

6. **Report** the run directory path and a one-line inventory of each packet.
   Do not summarize the evidence itself in chat beyond the inventory — the
   analysts must meet the packets cold.

## Hard rules

- Never include any prior verdict, score, price target, thesis, or prior
  run's conclusions in a packet (§18: evidence in, verdicts out).
- Never fabricate data a tool did not return; a gap is recorded as a gap.
- Preserve exact figures in unmasked packets; note the retrieval date on
  everything (point-in-time discipline, §18).
