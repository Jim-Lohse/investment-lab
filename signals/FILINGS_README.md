# Foreign company filings

Purpose: read the company's own documents for non-US names instead of a
vendor's summary of them. Every feed is free and comes from the company's
own filing or announcement channel.

| Feed | What it is | Key needed | Code |
|---|---|---|---|
| TDnet | Japan's same-day company announcements: earnings releases, guidance changes, buybacks | No | `python -m signals.filings tdnet` |
| EDINET | Japan's filing system (Japan's version of SEC EDGAR): half-year and annual reports, 5% big-holder reports, buyback status reports | Yes, free | `python -m signals.filings edinet` |
| OpenDART | Korea's filing system: every disclosure, plus structured 5% ownership reports | Yes, free | `python -m signals.filings dart` |
| RNS | UK company announcements, read from Investegate's page for each company; daily buyback notices are turned into a running tally | No | `python -m signals.filings uk` |

The watch list, the topics each company is watched for, and the dated events
are in `signals/config/filings_watchlist.json`. Add a company there and the
next run picks it up. The repository is public, so the watch list holds
companies and topics only, never position sizes or prices paid.

## Where things land

| Path | What |
|---|---|
| `data/filings/japan_tdnet.csv` | One row per TDnet announcement, with the link to the company's PDF and, for earnings releases, the XBRL data file |
| `data/filings/japan_edinet.csv` | One row per EDINET filing by or about a watched company |
| `data/filings/korea_dart.csv` | One row per OpenDART filing |
| `data/filings/korea_dart_5pct.csv` | Holders crossing or changing a 5% stake, with the stake and the change |
| `data/filings/uk_rns.csv` | One row per UK announcement |
| `data/filings/uk_buyback.csv` | Shares bought, average price, low and high, shares left in issue, per daily buyback notice |
| `data/derived/filings_whats_new.md` | The plain-English brief: what arrived this run, what needs reading, buyback pace, dated events coming up |

A row marked `needs_reading = yes` touches one of the questions that company
is watched for (for example, a Musashi earnings release, which is where a
separate line for the energy-storage unit would first appear).

## Switching on the two keyed feeds

Both keys are free. Until each is added, its step prints "skipped" and the
brief lists it under What now. Nothing else is affected.

**EDINET (Japan).**
1. Open the EDINET API page at `https://api.edinet-fsa.go.jp/` and choose
   the option to issue an API key (the page is in Japanese; the button reads
   APIキー発行).
2. The sign-up may ask for a phone number to receive a text-message code.
   If it refuses a US number, stop there and note it, as happened with
   Korea's data.go.kr portal in August. Do not keep retrying the form.
3. Copy the key it shows.

**OpenDART (Korea).**
1. Open `https://opendart.fss.or.kr/` and choose 인증키 신청 (apply for a key).
2. Fill in an email address and a short purpose, for example "personal
   research on listed companies". Confirm the email.
3. The key appears under 인증키 관리 (key management), usually the same day.

**Adding a key to the repository.**
GitHub, this repository, Settings, Secrets and variables, Actions, New
repository secret. Names must be exactly `EDINET_API_KEY` and `DART_API_KEY`.
The next scheduled run of the update-filings workflow (07:45 and 13:15 UTC, weekdays) uses them.

## Why TDnet comes through Yanoshin

TDnet's own site forbids automated reading of its listing pages in its
robots.txt. The free Yanoshin TDnet API republishes the listing with TDnet's
own document links, so the pipeline reads the listing there and links
straight to the company's PDF on TDnet. The PDFs themselves are opened by a
person, not downloaded in bulk.

## When a parser breaks

Run the update-filings workflow manually with `capture` set to any value. Raw pages
land in `data/filings/raw/`, and the parser can be repaired against them.
The offline tests (`tests/test_filings.py`) use fixtures copied from what
each source returned on 26 Sep 2026.
