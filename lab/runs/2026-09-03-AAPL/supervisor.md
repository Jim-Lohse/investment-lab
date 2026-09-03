# Reconciliation memo — run 2026-09-03-AAPL (Tier 1)

Supervisor pass over the three preserved blind submissions:
- /home/user/investment-lab/lab/runs/2026-09-03-AAPL/submissions/company.yaml
- /home/user/investment-lab/lab/runs/2026-09-03-AAPL/submissions/macro.yaml
- /home/user/investment-lab/lab/runs/2026-09-03-AAPL/submissions/industry.yaml

against packets in /home/user/investment-lab/lab/runs/2026-09-03-AAPL/packets/ and the constitution at /home/user/investment-lab/investment-lab-constitution.md.

---

## 1. Correlation ledger (§5)

```yaml
correlation_ledger:
  agreeing_analysts: 3
  # Consensus points and their genuinely independent path counts:
  #   (a) "Business/moat is real; cash translation is real" — 3 agree, ~1.5 paths:
  #       company path is primary (10-K/10-Q XBRL, accession-anchored); industry's
  #       corroboration (tracker share gains, Google's $20B willingness-to-pay) uses
  #       different evidence and method — a genuinely distinct path — but its sources
  #       are NOT in the preserved record (see Contamination sweep); macro adds no
  #       path (its subject profile is the same 10-K facts restated by the orchestrator).
  #   (b) "Price requires a top-decile reference-class outcome" — 3 agree, 3 methods,
  #       2 fully independent paths: company reverse-DCF arithmetic, macro
  #       rising-term-premium regime class, industry #1-2-market-cap-at-~40x class
  #       differ in method AND causal hypothesis (§5 satisfied), but the company and
  #       industry paths both key off the identical shared price/multiple input
  #       ($324.96 / $4.74T / 42x FY25), which is one orchestrator genealogy.
  #   (c) "Recognition is complete; return must come from earnings, not rerating" —
  #       2 agree (industry T7 call; company FY27-revisions rollover), 2 paths,
  #       but both lean on the same shared facts (-9.27% print reaction, $4.74T cap).
  independent_evidence_paths: 2   # conservative floor across the load-bearing consensus;
                                  # 3 if industry's unpreserved citations verify
  shared_assumptions:
    - "Sell-side aggregates (FY26 $477.7B / FY27 $9.53) are a fair read of market expectations"
    - "~2.4B active devices — a management figure — treated as near-fact by all three"
    - "The -9.27% reaction to the 2026-07-30 8-K indicates fully loaded expectations"
    - "FY2025 10-K XBRL is accurate as filed (all quantitative work bottoms out here)"
    - "All three analysts are the same base model; §6 call separation does not remove model-level correlated priors"
  shared_sources:   # orchestrator built all packets from overlapping raw pulls — one genealogy each
    - "EDGAR/exchange market-data pull: $324.96 close, ~$4.74T cap (company + industry packets)"
    - "FY2025 10-K XBRL (accession 0000320193-25-000079): appears in all three packets (fundamentals table, macro subject profile, industry peer row)"
    - "2026-07-30 8-K + -9.27%/-7.87% reaction measurement (company + industry packets)"
    - "Ternus Form 4 (2026-09-01) + CEO-transition media coverage — media items are one genealogy back to one announcement (company + industry packets)"
    - "WWDC26 / 'Siri AI' framing — all media derivatives collapse to Apple's own launch event and 8-K ex-99.1 (single promotional genealogy, disclosed by company analyst)"
  unresolved_disagreements:
    - "AI-layer ownership: company treats 'all-new Siri AI' as Apple's potential second act (status uncertain); industry treats the same layer as a 'strategic cession of the frontier-model layer... an option Google holds on the future agent relationship with subject's users.' Same facts, opposite sign. Not resolved; preserved."
    - "Tariff sign: company's retrieved Q3 8-K shows ~2pp GM / $0.11 EPS of ONE-TIME TARIFF REFUNDS (tariffs were a live cost, briefly reversed); macro classifies current US-China tariff/tech-policy state as thesis-critical, two-sided, and NOT retrieved. The current policy state is an open gap both point at from different directions."
    - "Consensus direction: FY26 revisions 21 up / 8 down vs FY27 revisions 8 up / 19 down with avg cut $9.71→$9.53 — near-year and out-year consensus disagree; company preserved both, no analyst reconciled them."
    - "Duration: industry blends device-ecosystem duration at anchor-8 (>5yr, no funded replication) against take-rate duration at anchor-2 (regulatory erosion enacted, EU terms in force 2026-10-01) for a blended 5; company's compounder framing implicitly treats duration as strong. The blend vs the split is unresolved."
    - "Confidence spread 0.60 (industry) to 0.80 (company) — note the confidences attach to differently scoped claims, so the spread is not directly a disagreement, but it is not corroboration either."
```

Three-analysts-one-press-release check: the AI-cycle claim is exactly this pattern — 8-K framing, WWDC26 keynote, and all media coverage are one Apple-controlled genealogy. One evidentiary pathway, and it is promotional. The company analyst collapsed it correctly; recorded here so the judgment layer cannot count it twice.

## 2. Merged claim map (best status across analysts)

| # | Load-bearing claim | Best status | Basis / notes |
|---|---|---|---|
| 1 | Compounding engine real; cash translation real (46.9% GM, 23.7% FCF margin, -4%/yr shares) | **supported** | Primary (10-K/10-Q XBRL, accessions cited). Industry's independent willingness-to-pay corroboration is real method-diversity but unverified provenance |
| 2 | AI drives a durable multi-year upgrade cycle | **uncertain — single promotional genealogy** | One quarter of filed results (+16%) is partial confirmation; the durability framing is management's own. Contested in sign by industry (Gemini-inside-Siri) |
| 3 | FY26 revenue ~$477.7B (+14.8%) | **supported** | Q1-Q3 filed; only Sept quarter is estimate |
| 4 | Gross margin structurally ~48-50% | **supported at ~48%, not 50.1% headline** | 8-K itself discloses ~2pp one-time tariff-refund benefit |
| 5 | FY27 growth ~+10% (EPS $9.53) | **uncertain** | Sell-side only; revision momentum negative (8 up / 19 down) |
| 6 | CEO transition seamless; strategy and capital-return continue | **management-assertion-only** | Form 4 proves the fact; continuity has no source. Company analyst flags edgar-tools 8-K feed 35 days stale — a 5.02 transition 8-K may exist unretrieved |
| 7 | Capital-return engine persists (~4%/yr shrink) | **supported historically, challenged forward** | 8 years of filings; forward-challenged by macro (buyback rate-sensitivity vs 4.68% 10y) and company (capex +35%, intangibles $11.1B→$20.3B) |
| 8 | Take-rate erosion enacted (EU 30%→26% + tiers, Oct-1; Brazil/Japan stores) | **uncertain pending verification** | Cited to primary-class sources (Apple newsroom 2026-08-18, EU legal record) that are not in the packet or preserved record — see audit |
| 9 | Customers fail to leave (share +3.9pp during -7.4% industry contraction) | **uncertain pending verification** | Same provenance problem (IDC/Counterpoint/Omdia not retrieved into any preserved artifact) |
| 10 | Price requires top-decile reference-class outcome | **supported** | Three convergent methods, two fully independent paths; the strongest-corroborated forward-looking claim in the run |
| 11 | Recognition at T7; rerating ~100%+ realized | **supported** (facts) + inference | $303 raised target below $324.96 market; no T0-T3 milestone claimable |
| 12 | Current US-China tariff/policy state | **GAP — thesis-critical, unretrieved by anyone** | Flagged by macro as thesis-critical and by both macro and industry packets as not retrieved; company's tariff-refund find proves the exposure is live, not what it currently is |

## 3. Challenge findings

**3.1 Uncertain-claim survival test (§8.3).** Claims 2, 5, and 6 are the ones the marginal dollar of the $4.74T price rests on, per the company submission's own reverse-DCF: branch (a) needs 7-9% FCF growth AND a held 28-30x multiple AND the continuing 4%/yr shrink; branch (b) is never-achieved. If claim 2 is false (one-year pull-forward), FY26's +16% is the top, FY27 consensus keeps falling, and a 37x entry has no return path — the thesis does not survive. If claim 6 is false (allocation regime reset — and the intangibles/capex ramp is circumstantial evidence a reset is underway), branch (a)'s shrink leg fails independently. These are not weaknesses to note; under §8.3 an affirmative long thesis is **blocked** while these claims carry a decisive share of expected return on management assertion and one quarter of data. The mature-compounder version of the claim (claims 1, 3, 4, 7-historical) is well supported — but that version does not support the price.

**3.2 Steelman counter to the strongest submission** (company.yaml is the strongest: accession-anchored, self-caveated, honest one-off decomposition). Its implicit verdict is "the price pays for a story the filed record doesn't support." Best counter, from Concentrated Quality (§15.1, discipline 4):

The record the skeptic cites is also the record of the single most reliable cash franchise ever filed: an installed base at an all-time high, a quarter with records in iPhone, Mac, and Services, and underlying gross margin of ~48% — up a point from FY25 even after stripping the tariff one-off the skeptic strips. The reinvestment inflection the submission treats as a red flag (R&D +32%, capex +35%, intangibles nearly doubling) is precisely what a Concentrated Quality discipline asks a franchise to do when a new attach layer appears; penalizing Apple for finally spending on AI after years of being penalized for not spending is heads-I-win skepticism. The absence of insider buying is uninformative at mega-cap scale (no open-market buy since 2015 spans the best decade in the stock's history), and the CEO succession is the most rehearsed in corporate America — an operations-bred insider elevated with a multi-year vest, not an outsider break.

Nor does the valuation math require heroics under quality-discipline assumptions. At ~2.1% trailing FCF yield with a ~3% total shareholder yield and demonstrated pricing power, high-single-digit FCF growth — below what Q3 just printed — earns a high-single-digit return if the multiple merely drifts to the low-30s rather than holding 37x; the never-achieved branch (b) is a strawman built by assuming the harshest mean-reversion and demanding the return all come from fundamentals. The 1972/2000 analogies both involved starting multiples far more extreme relative to growth (Microsoft entered 2000 near 60x on decelerating growth; Apple sits at 34x FY27E on just-reaccelerated growth). And the falsifiers the submission itself pre-registered resolve within two quarters — meaning the durability question is cheaply watchable, which for a quality franchise argues for watch-with-triggers, not for treating the uncertainty as terminal. — *The counter is recorded, not endorsed; it does not cure the §8.3 status of claims 2/5/6, because it argues from the same single-genealogy AI narrative.*

**3.3 Reverse-DCF vs base rates (§9).** The verdict is unambiguous and triply converged: **the current price requires a top-decile reference-class outcome** — top-decile of premium-multiple mega-caps on the multiple-retention branch, and a never-achieved outcome on the fundamentals-only branch ($99B→~$390B FCF from a $400B revenue base). Macro adds the regime aggravator: almost no member of the class delivered through a sustained 100bp+ long-yield rise, and the 10y is at 4.68% rising with policy flat — the specific regime in which this class historically fails. Stated in those words, per §9.

**3.4 Contamination sweep (Gate D).**
- **Cross-analyst contamination: none detected.** No submission references another's output, scores, or framing; genuine disagreements survived intact (the AI-sign disagreement is the strongest evidence the passes were blind — contaminated analysts converge).
- **Single-promotional-source collapse: present and correctly handled.** The AI-cycle genealogy collapses to Apple's own 8-K/WWDC26 channel (Gate D(ii) pattern); the company analyst collapsed it and statused the claim `uncertain` rather than counting media echo as corroboration. No violation.
- **Violation to report (not repaired): unpreserved evidence provenance in industry.yaml.** The industry packet's own gaps section says no market-share data, no supply data, and regulatory case status NOT retrieved — yet the submission's scores rest on IDC/Counterpoint/Omdia Q2-2026 share data, the EU unified terms of 2026-08-18, the EUR 500M DMA fine, the Jan-2026 Gemini deal, the ~$20B search payment, and ~300% memory inflation. These are post-training-cutoff events, so they cannot be parametric memory presented as sourced knowledge in the usual sense — the analyst evidently retrieved live in-lane (permitted), but **no retrieval artifact exists anywhere in the run directory** (verified: the run contains only packets/ and submissions/). The citations are named-and-dated but unverifiable from the preserved record. Same pattern, lesser severity, in macro.yaml (EUR/USD 1.16, USD/CNY 7.20→6.72 marked "retrieved" against a packet that says FX not retrieved). Company.yaml is the contrast case: its extra-packet retrieval is accession-anchored (0000320193-26-000020) and self-caveated. I have not repaired or re-verified these claims; claims 8 and 9 carry `uncertain pending verification` status until the sources are pulled into the record.

## 4. Audit findings

**Genealogy audit (§8).** Company: pass — every load-bearing claim traced, source-classed, honestly statused, with accessions; exemplary handling of the one-off decomposition and of its own tool-staleness caveat (a post-2026-07-30 8-K, e.g. the CEO 5.02, may be missing from the record). Macro: adequate for its lane; base-rate note rests on historical episodes (agent inference / independent-research class — acceptable, correctly not dressed up as primary). Industry: traced-in-form but **unverifiable-in-record** (finding 3.4); its two pillar scores inherit that status.

**Anchor audit (§10.2).** Genuinely pinned, not vibes: industry's Control and Capture 7 is explicitly argued against the anchor-8 wording ("retained economics" fails on administrative re-pricing → cap at 7), and Duration 5 is a disclosed blend of an anchor-2 leg (erosion announced-and-funded: EU terms enacted) and an anchor-8 leg (no funded ecosystem replication) — the blend is a defensible convention but the split should be preserved for the judgment layer, since the two legs have different investment consequences. Company's Financial Translation 8 states why it is not 9-10 (OpCF/NI divergence, cash-tax timing, unproven incremental ROIC on the AI ramp). Macro assigned no pillar scores (correct for its lane). Pass.

**Independence audit (§6).** The run qualifies as **architecturally independent**: separate parallel inference calls, each receiving only its own packet path; no spawn prompt contained another analyst's output, orchestrator views, or an expected answer; submissions preserved verbatim pre-cross-examination. Two recorded limits on what that label buys: (i) the shared orchestrator built all packets from overlapping raw pulls, so agreement on the shared facts (price, FY25 10-K, 8-K reaction, Form 4) is single-genealogy however many analysts restate it — the ledger above nets this out; (ii) all three calls run the same base model, a correlation architecture does not remove. Not masked (packets marked `masked: false`), so no §7 pre/post-reveal delta exists for this run.

**Simplicity note (§17).** Mostly honest "no" on the destination, "yes" on the furniture. A competent three-hour single pass on AAPL at 42x trailing would have reached the same terminal conclusion this run reaches — outstanding business, fully recognized, price demands an outcome the reference class almost never delivers, pass-or-watch. What the multi-analyst pass genuinely added that a single pass would likely have missed: the ~2pp tariff-refund decomposition of the Q3 gross-margin headline (changes the "structural 50%" claim to "structural 48%"); the rate-sensitivity-of-the-buyback framing (the flywheel's largest buyer competes with a 4.68% risk-free rate — a non-obvious erosion channel); and the Gemini-inside-Siri sign inversion on the AI narrative. None of these changed the decision; all three sharpen the falsifiers and kill lines a watch item would carry. The blind structure also demonstrably produced a real disagreement (AI-layer sign) that a single context would have smoothed into one view. Verdict: the process earned its cost on falsifier quality, not on the conclusion.

## 5. Supervisor verdict

```yaml
supervisor_verdict:
  advance_to_judgment: blocked
  # Scope of the block: an AFFIRMATIVE long judgment may not be produced from this
  # evidence base (§8.3 — claims 2, 5, 6 carry the decisive share of expected return
  # at $324.96 and are uncertain/management-assertion-only). A negative judgment —
  # pass, or a watch item with the merged falsifiers as reconfirmation triggers — is
  # available and is all a Tier 1 run may produce anyway: per §13.7 this scan may
  # open watch items only, never a dated decision window.
  blocking_reasons:
    - "unsupported load-bearing claim (§8.3 / §10.4): AI-cycle durability rests on a single promotional genealogy plus one filed quarter, yet carries the decisive share of expected return at the current price"
    - "unsupported load-bearing claim (§10.4): CEO-transition continuity is management-assertion-only, with a possibly-unretrieved 5.02 8-K flagged in the record"
    - "implausible valuation assumptions (§10.4): both reverse-DCF branches require a top-decile (a) or never-achieved (b) reference-class outcome, triply converged across analysts"
    - "unverified thesis-critical input: current US-China tariff/policy state retrieved by no analyst despite being flagged thesis-critical (macro) and live (company's tariff-refund find); must be in the record before any tier advancement"
  independence_label: architecturally-independent
  # with recorded caveats: shared orchestrator packet genealogy on core facts; shared
  # base model; unmasked run (no §7 delta measurable)
  strongest_unresolved_disagreement: >
    Whether Apple's AI layer is its own durable second act (company: uncertain upside)
    or an outsourced layer that hands Google an option on the agent relationship with
    Apple's users (industry: strategic cession) — the same facts read with opposite sign,
    and the falsifiers for both readings resolve within roughly two quarters.
```

Handoff note to the judgment layer: the clean, corroborated core is claims 1, 3, 4, 7-historical, 10, 11 — a real compounder, fully recognized, at a price only the unproven claims can justify. Before any Tier 2 work: pull the industry submission's cited primary sources (EU terms, tracker data, Gemini deal) and the current tariff state into the preserved record, and check EDGAR for a post-2026-07-30 8-K (item 5.02).
