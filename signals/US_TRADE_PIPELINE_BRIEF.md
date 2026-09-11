# Brief: U.S. trade leg for the optical-interconnect names

**Status (2026-09-11): built.** `signals/us_census.py`, config in
`signals/config/us_endpoints.json`, steps in `update-signals.yml`, history
backfilled 2024-01 to 2026-07 (40,489 rows), HTS descriptions snapshotted
in `data/us/hts_codes.csv`. Findings from the live payloads are at the end.

Scoped 2026-09-11 against live documentation. Companion to
`JAPAN_PIPELINE_BRIEF.md`; the build pattern is the same (config-driven
fetcher, raw payloads preserved, append-only stores, a workflow step with
`continue-on-error`, offline fixtures). This sandbox's egress proxy blocks
api.census.gov, datawebws.usitc.gov, api.bls.gov and fred.stlouisfed.org, so
the build-then-capture-in-Actions loop from the Japan leg applies again.

## Who tracks U.S. trade in these goods

| Body | Role | Public, machine-readable? | Key needed |
|---|---|---|---|
| **CBP** | Collects the entry data (ACE) | No shipment-level release. Ocean bills of lading reach the public only through resellers (Panjiva, ImportGenius, Datamyne). Publishes classification rulings (CROSS). | n/a |
| **Census Bureau** | Compiles and publishes the official monthly trade statistics from CBP entries | Yes: International Trade API, `api.census.gov/data/timeseries/intltrade/{imports,exports}/hs`, HS2/4/6/10 by country, district, value, quantity, 2013-present. USA Trade Online is the same data behind a web login. | Free API key, instant by email |
| **USITC DataWeb** | Redistributes Census data with HTS-10 descriptions, rate provisions, longer history, saved queries, monthly e-mail runs | Web queries need no account. API (`datawebws.usitc.gov/dataweb/api/v2/report2/runReport`) needs a Login.gov account and a bearer token. | Account + token for API |
| **USITC HTS** | The tariff schedule itself | `hts.usitc.gov/reststop` JSON, no auth: code lookup, descriptions, units, current and past releases. | None |
| **BLS** | Producer and import price indexes | API v2, 25 queries/day without key, 500 with a free key. Series: PCU333242333242 (semiconductor machinery PPI), PCU335921335921 (fiber-optic cable PPI), PCU33423342 (communications equipment PPI), IZ3342 (import price index, communications equipment). FRED mirrors them. | Optional |
| **BEA** | Balance-of-payments aggregates | No HS detail. Not useful here. | — |
| **ITA / TradeStats Express** | Repackages Census | Nothing firsthand beyond Census. | — |
| **USTR / FCC / Commerce BIS** | Tariff actions, the proposed FCC ban on new Chinese optical modules (Reuters, Aug 2026), export controls | Policy documents, not data. They change what the data means (origin shifts). | — |
| **SEC (via edgar-tools MCP)** | 10-K/10-Q customer concentration, facility lists | Yes. The only company-level firsthand record. | Already connected |

So: not just USITC DataWeb. **Census is the primary source; DataWeb is a
convenience layer on it.** The leg should read Census directly and use the
HTS REST API for code metadata.

## What U.S. import data can and cannot say about the names

Country of origin follows substantial transformation, and none of the
U.S.-listed names manufactures transceivers only in one country. Import
by origin is therefore a proxy for flows, not for a company.

| Name | Where the shipped product is made (10-K) | What U.S. imports by origin can show |
|---|---|---|
| Lumentum | Fabrinet (Thailand) for most modules; own fabs in US, UK, Japan, China, Slovenia; CMs in Thailand, Taiwan, Malaysia, Philippines | Thailand 8517.62 imports (shared with Coherent, Nvidia/Fabrinet, Cisco/Acacia) |
| Coherent | Datacom modules in China, Malaysia, Philippines, Vietnam; InP lasers in Sherman TX and Sweden | China/Malaysia/Philippines/Vietnam 8517.62; laser chips are domestic and invisible in imports |
| AAOI | Laser chips Sugar Land TX; transceivers Taipei; subassemblies Ningbo | Taiwan 8517.62 (shared with many); China 8517.70 parts |
| Credo | Fabless, Asian CMs | Not isolable |
| Fabrinet | Thailand (Pinehurst) | Thailand 8517.62 + 9013 is the closest public proxy; its 10-K customer table (Nvidia, Cisco, Lumentum shares) is the better firsthand read |

Structural caveats, all documented in the sources:
- **Air freight.** Transceivers ship by air. Census captures air in the
  value and quantity fields (`AIR_VAL_MO`), so the statistics are complete,
  but bill-of-lading resellers see ocean only and miss most of this trade.
- **Indirect routing.** Much AI-cluster optics enters the U.S. inside
  switches and servers assembled in Taiwan and Mexico, classified as
  8471/8517.62 equipment, not as modules. Direct module imports understate
  U.S. demand and overstate the hyperscaler-direct channel.
- **Tariff and policy noise.** Section 301 (7.5-25% on Chinese-origin
  8517.62) and the proposed FCC ban push assembly to Thailand, Malaysia,
  Vietnam. Origin shares will move for policy reasons, not demand.
- **Lag.** Census releases monthly data 34-36 days after month end
  (July 2026 on Sept 3; August on Oct 6), after Japan's and Korea's prints.

## Codes to track (verify each against `hts.usitc.gov/reststop` at build time)

- 8517.62.0090 optical transceivers (CBP rulings N336394, N302251;
  older filings used 8517.62.0050)
- 8517.70 / 8517.79 TOSA, ROSA, transceiver parts (ruling N041692)
- 8541.42 / 8541.49 / 8541.10 laser diodes and photodiodes; 9013.80.60
  laser-diode modules with essential optics (rulings 088628, 955114). The
  HS-2022 renumbering of 8541.40 must be confirmed from the HTS API.
- 9001.10 optical fibre and bundles; 8544.70 fibre-optic cables
- 8486 semiconductor equipment (the Japan leg's mirror image: Japan exports
  to USA vs. U.S. imports from Japan is a free consistency check)

## Proposed build (one module, `signals/us_census.py`)

1. `fetch_hs`: Census imports/hs at HS10 for the configured codes, all
   countries, `GEN_VAL_MO`, `CON_VAL_MO`, `GEN_QY1_MO`, `UNIT_QY1`,
   `AIR_VAL_MO`; YEAR/MONTH parameters (the guide says `time=` ranges time
   out on HS endpoints). One call per code per month; ~10 codes.
2. `fetch_exports`: exports/hs for 8541 and 8486 by destination, to read
   Coherent/AAOI laser-chip exports and the Japan cross-check.
3. `hts_lookup`: HTS REST API to snapshot descriptions and units for every
   configured code into `data/us/raw/`, so a renumbering is visible.
4. `prices` (optional): BLS PPI/import-price series for deflating.
5. Store: `data/us/trade_monthly_hs.csv` keyed on (yyyymm, imex, hs10,
   cty_code); raw JSON under `data/us/raw/`; `reparse` as in Japan.
6. Signals: value and unit YoY per code and per origin; origin-share
   table for 8517.62.0090 (China / Thailand / Taiwan / Malaysia / Vietnam /
   Mexico); Japan-export-to-USA vs U.S.-import-from-Japan reconciliation.
7. Setup cost for Jim: one Census API key
   (https://api.census.gov/data/key_signup.html), stored as the
   `CENSUS_API_KEY` repo secret. DataWeb account optional; not needed.

Effort estimate: comparable to the Japan leg's second half (parsers are
JSON, not XML/CSV, and documented), one capture round in Actions.

## Commercial and third-party sources (assessed 2026-09-11)

Classified per constitution §8.1. None of these is a government dataset;
they sit beside the customs legs, not inside them.

| Source | §8.1 class | Access | Adds | Bounds |
|---|---|---|---|---|
| Panjiva (S&P), ImportGenius, Descartes Datamyne | aggregator of CBP ocean manifests | Paid; free pages show counts and a sample record | Shipper→consignee pairs (e.g. Fabrinet→JDSU history, WIN Semi→Lumentum) | **Ocean only.** InP substrates, laser chips and transceivers move by air, so these platforms miss most of the flow that matters. Not "every container" |
| LightCounting | independent financial/technical research | Paid reports; free press releases | Transceiver unit and $ forecasts, lasers per module | Estimates, not records; T3-T4 on the recognition clock |
| Cignal AI | independent technical research | Paid; free blog with policy and capacity analysis | Component and transport tracking, FCC-ban analysis | Same |
| Yole Group | independent technical research | Paid; free press releases | InP/GaAs wafer market shares, 2/3/6-inch line output | Same; annual cadence |
| TrendForce | independent research | Paid; frequent free press releases | Bottleneck and export-control commentary | Same; press releases are usable as dated quotes |
| SemiAnalysis | independent research | Paid newsletter | Hyperscaler procurement, fab allocation | Same |
| Rosenblatt, Morgan Stanley "capacity trackers" | sell-side | Broker accounts only | Laser-revenue capacity math | Consensus reference (T3), not evidence |
| Veeco order backlog | company filing | Free via SEC (edgar-tools) | Leading read on InP laser capacity adds (MOCVD, ion-beam tools) | Veeco sells into many end markets; backlog is not all InP |
| AXT (AXTI) InP substrate revenue | company filing | Free via SEC | Merchant InP substrate volume; China export-permit delays disclosed in filings | Substrates made in China; permit regime dominates 2025-26 prints |
| JX Advanced Metals, Sumitomo Electric | company filing (TSE) | Free, Japanese disclosures | InP substrate capacity plans | No SEC record; no quarterly substrate line |
| Commerce BIS | primary regulatory record | Rules and entity list only | Export-control scope on equipment to China | Publishes no shipment data; the public view of licensed exports is Census export statistics |
| China MOFCOM InP export permits (Feb 2025 controls) | primary regulatory record | Announcements only | Explains AXT and Coherent supply commentary | No data feed |

What of this can be pipelined for free, in order of value:
1. **SEC XBRL via edgar-tools**: Veeco backlog and MOCVD commentary, AXT
   substrate revenue and permit status, Fabrinet customer concentration,
   Coherent/Lumentum segment revenue. Quarterly, firsthand, already
   connected. Fits the constitution's "company filing" class.
2. **Japan e-Stat 品別国別表** (commodity by country) for HS 3818 and 8541
   exports to the USA: the customs record of JX/Sumitomo substrate flows to
   Coherent's and Lumentum's U.S. fabs. Same e-Stat navigation as the
   built 統計品別表 path, different tclass1. Not yet built.
3. **Press-release scrapes** of Cignal AI, TrendForce, Yole, LightCounting
   as dated, attributed quotes in a `data/research_notes/` log, never as
   numbers in the derived tables.
4. Bills of lading only if a paid subscription exists, and only for ocean
   equipment shipments (MOCVD tools, chambers), not for optics.

## Built (2026-09-11)

- Census API accepted every requested variable on the first call; 204 marks
  unpublished months; zero-trade partner rows are dropped at parse time.
- Exports use HS6 only: the 10-digit import suffix 8517.62.0090 has no
  Schedule B twin and returns nothing on the export endpoint.
- HTS REST API: the documented `reststop/exportList?from=&to=&format=JSON`
  endpoint works; `searchByNumber` (seen in third-party posts) is a 404.
- 3818.00.00 carries a U.S. statistical suffix for GaAs wafers
  (3818.00.00.10); InP wafers sit in the "Other" suffixes. Worth adding the
  10-digit import codes if GaAs versus InP flow matters.
- 8517.62.0090 is a basket (switches, routers, modems, transceivers):
  $7.1bn of July 2026 imports. Read the origin mix and growth, not the level.
- Runtime: ~20 seconds per month of 21 codes; the 27-month backfill took
  18 minutes and ~570 calls without throttling.
