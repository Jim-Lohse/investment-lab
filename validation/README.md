# PIT evidence packets

Tooling for the constitution's Section 18 point-in-time validation: build a
frozen, evidence-only packet from the local Sharadar DuckDB, hand it to a
fresh chat that has never seen this repository, and score the verdict back
here.

## The three-step workflow

1. **Build the packet** (on the machine holding `data/sharadar.duckdb`):

   ```bash
   python -m validation.pit_packet AAPL --cutoff 2025-11-01
   ```

   This writes two files:
   - `packets/packet_<cutoff>_<label>.md` — the evidence packet. This is the
     only thing the rerun context may ever see.
   - `packets/keys/key_<cutoff>_<label>.md` — the label→ticker mapping and
     build notes, for scoring. **Never attach the key to a rerun chat.**

2. **Run the blind rerun**: open a brand-new, empty chat (claude.ai or a
   fresh session with no project context), attach the packet file, and let
   it produce the decision and probability forecasts the packet's TASK
   section asks for. One case per chat; a context that has read this repo —
   whose Appendix A states the correct answers — is contaminated and may
   never serve as a rerun context.

3. **Score it here**: bring the verdict back to a working session, compare
   against the case's pre-defined correct decision, log both (append-only),
   and record which contexts saw what.

## What the builder enforces

- **Point-in-time**: fundamentals are as-reported rows (SF1, default ARQ)
  with `datekey <= cutoff` — each row was public by its filing date, and
  restatements arrive as new rows so the cutoff view is preserved.
  Valuation (DAILY) and insider filings (SF2, by `filingdate`) are cut the
  same way.
- **Masking (Section 7)**: by default the packet withholds name, ticker,
  exchange, industry, geography, and price history; coarsens monetary
  values to two significant figures; omits share counts; and labels
  companies "Company A/B/…". `--unmasked` turns all of that off (for the
  post-reveal rescore).
- **No forward information**: nothing dated after the cutoff is queried.
  One caveat, recorded in every key file: the local mirror holds the
  vendor's latest view, so in-place error corrections made since the cutoff
  are not excluded (as-reported restatements are).

Multiple tickers build one packet with per-company sections
(`python -m validation.pit_packet AJINY IBDNF --cutoff 2025-11-01`);
`--labels` overrides the default mask names. Packets and keys stay local —
`packets/` is gitignored because it contains licensed vendor data and,
in the keys, case identities.

## Chronological reveal

For the protocol's incremental-reveal step, build additional packets at
later cutoffs (`--cutoff 2026-02-01`, …) and feed them to the rerun chat
one at a time, in order, without commentary.
