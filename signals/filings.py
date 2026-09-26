"""Foreign company filings: read the company's own documents, not a vendor summary.

Four feeds, one module, all free:

  tdnet   Japan same-day company announcements (earnings releases, guidance
          changes, buybacks). TDnet itself forbids automated crawling in its
          robots.txt, so the listing comes through the free Yanoshin TDnet
          API, which returns TDnet's own document links. No key.
  edinet  Japan's filing system (Japan's version of SEC EDGAR): half-year
          and annual reports, big-holder (5%) reports, buyback status
          reports. Free key: EDINET_API_KEY. Skips cleanly until it is set.
  dart    Korea's filing system (OpenDART): every disclosure plus the
          structured 5% ownership reports. Free key: DART_API_KEY. Skips
          cleanly until it is set.
  uk      UK company announcements (RNS) via Investegate's per-company
          page. No key. Daily "Transaction in Own Shares" notices are also
          parsed into a buyback tally (shares bought, average price).

  brief   Write data/derived/filings_whats_new.md: what arrived this run,
          which of it needs reading, buyback pace, coming dated events.
  capture Save raw pages to data/filings/raw/ for parser repair.

Every fetcher is idempotent: rows are keyed on the source's own document id
and appended once (append-only, like the other legs). Each row carries
`first_seen_utc`, which is how the brief knows what is new.

This repository is public. Nothing here records holdings, sizes or prices
paid: the watch list is companies and topics only.

Usage:
    python -m signals.filings tdnet
    python -m signals.filings edinet [--days N]
    python -m signals.filings dart [--days N]
    python -m signals.filings uk
    python -m signals.filings brief --since 2026-09-26T07:30:00Z
    python -m signals.filings capture
"""

from __future__ import annotations

import datetime as dt
import html
import io
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from .common import CONFIG_DIR, DATA_DIR, append_dedup_csv, http_get, read_csv_dicts

CONFIG_PATH = CONFIG_DIR / "filings_watchlist.json"
FILINGS_DIR = DATA_DIR / "filings"
RAW_DIR = FILINGS_DIR / "raw"
STATE_PATH = FILINGS_DIR / "state.json"
BRIEF_PATH = DATA_DIR / "derived" / "filings_whats_new.md"
STALE_DAYS = 10  # older documents are history, not news

TDNET_CSV = FILINGS_DIR / "japan_tdnet.csv"
EDINET_CSV = FILINGS_DIR / "japan_edinet.csv"
DART_CSV = FILINGS_DIR / "korea_dart.csv"
DART_5PCT_CSV = FILINGS_DIR / "korea_dart_5pct.csv"
UK_CSV = FILINGS_DIR / "uk_rns.csv"
UK_BUYBACK_CSV = FILINGS_DIR / "uk_buyback.csv"
DART_CODES_PATH = FILINGS_DIR / "dart_corp_codes.json"
EDINET_CODES_PATH = FILINGS_DIR / "edinet_codes.json"

YANOSHIN_URL = "https://webapi.yanoshin.jp/webapi/tdnet/list/{code}.json"
EDINET_LIST_URL = "https://api.edinet-fsa.go.jp/api/v2/documents.json"
EDINET_CODELIST_URL = "https://disclosure2dl.edinet-fsa.go.jp/searchdocument/codelist/Edinetcode.zip"
EDINET_VIEW_URL = "https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?{doc_id}"
DART_LIST_URL = "https://opendart.fss.or.kr/api/list.json"
DART_5PCT_URL = "https://opendart.fss.or.kr/api/majorstock.json"
DART_CORPCODE_URL = "https://opendart.fss.or.kr/api/corpCode.xml"
DART_VIEW_URL = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
INVESTEGATE_COMPANY_URL = "https://www.investegate.co.uk/company/{tidm}"
INVESTEGATE_BASE = "https://www.investegate.co.uk"

# EDINET document types worth a row (everything else a watched company files
# is still kept, labelled with its code).
EDINET_DOC_TYPES = {
    "120": "annual securities report",
    "130": "annual report, amended",
    "140": "quarterly report",
    "160": "half-year report",
    "170": "half-year report, amended",
    "180": "extraordinary report",
    "220": "buyback status report",
    "230": "buyback status report, amended",
    "240": "tender offer",
    "350": "big-holder (5%) report",
    "360": "big-holder (5%) report, amended",
}

TDNET_FIELDS = ["tdnet_id", "code", "company", "published_jst", "title", "doc_url",
                "xbrl_url", "topics", "needs_reading", "first_seen_utc"]
EDINET_FIELDS = ["doc_id", "code", "company", "filer", "doc_type_code", "doc_type",
                 "description", "submitted_jst", "period_start", "period_end",
                 "link", "topics", "needs_reading", "first_seen_utc"]
DART_FIELDS = ["rcept_no", "stock_code", "company", "report", "filer", "received",
               "remark", "link", "topics", "needs_reading", "first_seen_utc"]
DART_5PCT_FIELDS = ["rcept_no", "stock_code", "company", "received", "holder",
                    "report_type", "shares", "shares_change", "stake_pct",
                    "stake_change_pct", "reason", "first_seen_utc"]
UK_FIELDS = ["ann_id", "tidm", "company", "published", "source", "headline", "link",
             "topics", "needs_reading", "routine", "first_seen_utc"]
UK_BUYBACK_FIELDS = ["ann_id", "tidm", "trade_date", "shares", "avg_price_gbp_pence",
                     "low_pence", "high_pence", "shares_in_issue", "programme",
                     "first_seen_utc"]


# --- shared helpers ---------------------------------------------------------

def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_config(path: Path = CONFIG_PATH) -> dict:
    return json.loads(path.read_text("utf-8"))


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text("utf-8"))
    return {}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", "utf-8")


def tag_topics(text: str, topics: dict) -> list[str]:
    """Topic keys whose patterns appear in the title (case-sensitive for CJK,
    case-insensitive for Latin text)."""
    found = []
    low = text.lower()
    for key, spec in topics.items():
        for pat in spec["patterns"]:
            if pat in text or (pat.isascii() and pat.lower() in low):
                found.append(key)
                break
    return found


def needs_reading(found: list[str], priority: list[str]) -> str:
    return "yes" if any(t in priority for t in found) else ""


def record_status(feed: str, status: str) -> None:
    state = load_state()
    state.setdefault("status", {})[feed] = {"status": status, "at": now_utc()}
    save_state(state)


# --- Japan: TDnet via Yanoshin ---------------------------------------------

def parse_yanoshin(payload: dict, code: str, company: str, topics: dict,
                   priority: list[str], seen_at: str) -> list[dict]:
    rows = []
    for item in payload.get("items", []):
        t = item.get("Tdnet", item)
        title = (t.get("title") or "").strip()
        found = tag_topics(title, topics)
        rows.append({
            "tdnet_id": t.get("id", ""),
            "code": code,
            "company": company,
            "published_jst": t.get("pubdate", ""),
            "title": title,
            "doc_url": _unwrap_yanoshin(t.get("document_url") or ""),
            "xbrl_url": _unwrap_yanoshin(t.get("url_xbrl") or ""),
            "topics": ";".join(found),
            "needs_reading": needs_reading(found, priority),
            "first_seen_utc": seen_at,
        })
    return rows


def _unwrap_yanoshin(url: str) -> str:
    """Yanoshin wraps TDnet links in a redirect (rd.php?<real url>); keep the real one."""
    marker = "rd.php?"
    return url.split(marker, 1)[1] if marker in url else url


def fetch_tdnet(cfg: dict, limit: int = 30) -> int:
    seen_at = now_utc()
    added = 0
    for co in cfg["japan"]:
        resp = http_get(YANOSHIN_URL.format(code=co["code"]), params={"limit": limit})
        rows = parse_yanoshin(resp.json(), co["code"], co["name"], cfg["topics"],
                              co.get("priority", []), seen_at)
        n = append_dedup_csv(TDNET_CSV, TDNET_FIELDS, rows, ["tdnet_id"])
        print(f"tdnet {co['code']} {co['name']}: {len(rows)} listed, {n} new")
        added += n
        time.sleep(1.0)
    record_status("tdnet", "ok")
    return added


# --- Japan: EDINET ----------------------------------------------------------

def parse_edinet_list(payload: dict, watch: dict[str, dict], topics: dict,
                      seen_at: str) -> list[dict]:
    """Keep documents where a watched company is the filer OR the subject
    (a big-holder report filed by someone else about a watched company)."""
    rows = []
    for doc in payload.get("results", []) or []:
        sec = (doc.get("secCode") or "")[:4]
        edinet_ids = {doc.get("edinetCode"), doc.get("issuerEdinetCode"),
                      doc.get("subjectEdinetCode")}
        co = watch.get(sec)
        if co is None:
            co = next((c for c in watch.values() if c.get("edinet_code") in edinet_ids
                       and c.get("edinet_code")), None)
        if co is None:
            continue
        code = doc.get("docTypeCode") or ""
        desc = (doc.get("docDescription") or "").strip()
        found = tag_topics(desc, topics)
        if code in ("350", "360") and "ownership" not in found:
            found.append("ownership")
        if code in ("220", "230") and "buyback" not in found:
            found.append("buyback")
        if code in ("120", "140", "160") and "results" not in found:
            found.append("results")
        rows.append({
            "doc_id": doc.get("docID", ""),
            "code": co["code"],
            "company": co["name"],
            "filer": doc.get("filerName", ""),
            "doc_type_code": code,
            "doc_type": EDINET_DOC_TYPES.get(code, f"document type {code}"),
            "description": desc,
            "submitted_jst": doc.get("submitDateTime", ""),
            "period_start": doc.get("periodStart") or "",
            "period_end": doc.get("periodEnd") or "",
            "link": EDINET_VIEW_URL.format(doc_id=doc.get("docID", "")),
            "topics": ";".join(found),
            "needs_reading": needs_reading(found, co.get("priority", [])),
            "first_seen_utc": seen_at,
        })
    return rows


def parse_edinet_codelist(csv_bytes: bytes, wanted: set[str]) -> dict[str, str]:
    """EDINET's keyless code list (CSV, cp932, one title line then a header)
    -> {4-digit stock code: EDINET code}. Needed to catch big-holder reports
    that someone else files about a watched company."""
    import csv as _csv
    text = csv_bytes.decode("cp932", errors="replace")
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if "ＥＤＩＮＥＴコード" in l or "EDINETコード" in l), 0)
    out = {}
    for rec in _csv.DictReader(lines[start:]):
        code = (rec.get("ＥＤＩＮＥＴコード") or rec.get("EDINETコード") or "").strip()
        sec = (rec.get("証券コード") or "").strip()[:4]
        if sec in wanted and code:
            out[sec] = code
    return out


def edinet_codes(cfg: dict) -> dict[str, str]:
    wanted = {c["code"] for c in cfg["japan"]}
    cached = {}
    if EDINET_CODES_PATH.exists():
        cached = json.loads(EDINET_CODES_PATH.read_text("utf-8"))
    if wanted <= set(cached):
        return cached
    try:
        resp = http_get(EDINET_CODELIST_URL)
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
            cached.update(parse_edinet_codelist(zf.read(name), wanted))
    except Exception as err:  # the list is a convenience; own filings still match
        print(f"edinet: code list unavailable ({err}); big-holder reports filed by "
              "others will be missed until it loads")
        return cached
    EDINET_CODES_PATH.parent.mkdir(parents=True, exist_ok=True)
    EDINET_CODES_PATH.write_text(json.dumps(cached, indent=2, sort_keys=True) + "\n", "utf-8")
    return cached


def fetch_edinet(cfg: dict, days: int = 7) -> int:
    key = os.environ.get("EDINET_API_KEY", "").strip()
    if not key:
        print("edinet: no EDINET_API_KEY yet; skipped (add the key as a repository secret)")
        record_status("edinet", "waiting for key")
        return 0
    codes = edinet_codes(cfg)
    watch = {c["code"]: {**c, "edinet_code": codes.get(c["code"], "")} for c in cfg["japan"]}
    seen_at = now_utc()
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
    state = load_state()
    last = state.get("edinet_last_date")
    start = today - dt.timedelta(days=days - 1)
    if last:
        # Re-read the last finished day too: late-evening filings land after
        # an early run, and dedup makes the overlap free.
        start = max(start, dt.date.fromisoformat(last))
    added = 0
    day = start
    while day <= today:
        resp = http_get(EDINET_LIST_URL, params={
            "date": day.isoformat(), "type": 2, "Subscription-Key": key})
        payload = resp.json()
        status = str(payload.get("metadata", {}).get("status", "200"))
        if status != "200":
            raise RuntimeError(f"EDINET {day}: status {status} "
                               f"{payload.get('metadata', {}).get('message', '')}")
        rows = parse_edinet_list(payload, watch, cfg["topics"], seen_at)
        n = append_dedup_csv(EDINET_CSV, EDINET_FIELDS, rows, ["doc_id"])
        print(f"edinet {day}: {len(payload.get('results') or [])} filed market-wide, "
              f"{len(rows)} watched, {n} new")
        added += n
        day += dt.timedelta(days=1)
        time.sleep(1.0)
    state = load_state()
    state["edinet_last_date"] = (today - dt.timedelta(days=1)).isoformat()
    save_state(state)
    record_status("edinet", "ok")
    return added


# --- Korea: OpenDART --------------------------------------------------------

def parse_dart_corp_codes(xml_bytes: bytes, wanted: set[str]) -> dict[str, str]:
    """CORPCODE.xml -> {stock_code: corp_code} for the wanted stock codes."""
    out = {}
    root = ET.fromstring(xml_bytes)
    for item in root.iter("list"):
        stock = (item.findtext("stock_code") or "").strip()
        if stock in wanted:
            out[stock] = (item.findtext("corp_code") or "").strip()
    return out


def dart_corp_codes(cfg: dict, key: str) -> dict[str, str]:
    wanted = {c["stock_code"] for c in cfg["korea"]}
    cached = {}
    if DART_CODES_PATH.exists():
        cached = json.loads(DART_CODES_PATH.read_text("utf-8"))
    if wanted <= set(cached):
        return cached
    resp = http_get(DART_CORPCODE_URL, params={"crtfc_key": key})
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        name = next(n for n in zf.namelist() if n.lower().endswith(".xml"))
        codes = parse_dart_corp_codes(zf.read(name), wanted)
    cached.update(codes)
    DART_CODES_PATH.parent.mkdir(parents=True, exist_ok=True)
    DART_CODES_PATH.write_text(json.dumps(cached, indent=2, sort_keys=True) + "\n", "utf-8")
    return cached


def parse_dart_list(payload: dict, co: dict, topics: dict, seen_at: str) -> list[dict]:
    status = str(payload.get("status", ""))
    if status == "013":  # no data in the window
        return []
    if status != "000":
        raise RuntimeError(f"OpenDART list: status {status} {payload.get('message', '')}")
    rows = []
    for item in payload.get("list", []):
        report = re.sub(r"\s+", " ", item.get("report_nm", "")).strip()
        found = tag_topics(report, topics)
        rows.append({
            "rcept_no": item.get("rcept_no", ""),
            "stock_code": co["stock_code"],
            "company": co["name"],
            "report": report,
            "filer": item.get("flr_nm", ""),
            "received": item.get("rcept_dt", ""),
            "remark": item.get("rm", ""),
            "link": DART_VIEW_URL.format(rcept_no=item.get("rcept_no", "")),
            "topics": ";".join(found),
            "needs_reading": needs_reading(found, co.get("priority", [])),
            "first_seen_utc": seen_at,
        })
    return rows


def parse_dart_5pct(payload: dict, co: dict, seen_at: str) -> list[dict]:
    status = str(payload.get("status", ""))
    if status == "013":
        return []
    if status != "000":
        raise RuntimeError(f"OpenDART 5% reports: status {status} {payload.get('message', '')}")
    rows = []
    for item in payload.get("list", []):
        rows.append({
            "rcept_no": item.get("rcept_no", ""),
            "stock_code": co["stock_code"],
            "company": co["name"],
            "received": item.get("rcept_dt", ""),
            "holder": item.get("repror", ""),
            "report_type": item.get("report_tp", ""),
            "shares": item.get("stkqy", ""),
            "shares_change": item.get("stkqy_irds", ""),
            "stake_pct": item.get("stkrt", ""),
            "stake_change_pct": item.get("stkrt_irds", ""),
            "reason": item.get("report_resn", ""),
            "first_seen_utc": seen_at,
        })
    return rows


def fetch_dart(cfg: dict, days: int = 14) -> int:
    key = os.environ.get("DART_API_KEY", "").strip()
    if not key:
        print("dart: no DART_API_KEY yet; skipped (add the key as a repository secret)")
        record_status("dart", "waiting for key")
        return 0
    codes = dart_corp_codes(cfg, key)
    seen_at = now_utc()
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
    bgn = (today - dt.timedelta(days=days)).strftime("%Y%m%d")
    added = 0
    for co in cfg["korea"]:
        corp = codes.get(co["stock_code"])
        if not corp:
            print(f"dart {co['name']}: no corp code found for {co['stock_code']}")
            continue
        resp = http_get(DART_LIST_URL, params={
            "crtfc_key": key, "corp_code": corp, "bgn_de": bgn,
            "end_de": today.strftime("%Y%m%d"), "page_count": 100})
        rows = parse_dart_list(resp.json(), co, cfg["topics"], seen_at)
        n = append_dedup_csv(DART_CSV, DART_FIELDS, rows, ["rcept_no"])
        time.sleep(0.5)
        resp = http_get(DART_5PCT_URL, params={"crtfc_key": key, "corp_code": corp})
        big = [r for r in parse_dart_5pct(resp.json(), co, seen_at)
               if r["received"].replace("-", "") >= bgn]
        m = append_dedup_csv(DART_5PCT_CSV, DART_5PCT_FIELDS, big, ["rcept_no"])
        print(f"dart {co['name']}: {len(rows)} filings, {n} new; {len(big)} 5% reports, {m} new")
        added += n + m
        time.sleep(0.5)
    record_status("dart", "ok")
    return added


# --- UK: RNS via Investegate ------------------------------------------------

# /announcement/<source>/<company-slug>/<headline-slug>/<id>
_ANN_LINK = re.compile(
    r'<a[^>]+href="(?P<href>(?:https?://www\.investegate\.co\.uk)?/announcement/'
    r'(?P<source>[a-z0-9-]+)/(?P<slug>[a-z0-9-]+)/[^"/]+/(?P<id>\d+))"[^>]*>(?P<text>.*?)</a>',
    re.S | re.I)
_DATE = re.compile(r"(\d{1,2} [A-Z][a-z]{2} \d{4}(?:,?\s+\d{1,2}:\d{2}(?:\s*[AP]M)?)?)")


def _clean(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def parse_investegate_company(page: str, co: dict, topics: dict, seen_at: str) -> list[dict]:
    """Announcement links on the company page. The date is taken from the
    nearest date text before the link (the listing is a table of date,
    source, headline); the numeric id is the durable key either way."""
    rows, seen = [], set()
    for m in _ANN_LINK.finditer(page):
        if m.group("slug") != co["investegate_slug"]:
            continue
        ann_id = m.group("id")
        headline = _clean(m.group("text"))
        if not headline or ann_id in seen:
            continue
        seen.add(ann_id)
        before = page[max(0, m.start() - 1500):m.start()]
        dates = _DATE.findall(_clean(before))
        found = tag_topics(headline, topics)
        routine = any(r.lower() in headline.lower() for r in co.get("routine_headlines", []))
        href = m.group("href")
        rows.append({
            "ann_id": ann_id,
            "tidm": co["tidm"],
            "company": co["name"],
            "published": dates[-1] if dates else "",
            "source": m.group("source").upper(),
            "headline": headline,
            "link": href if href.startswith("http") else INVESTEGATE_BASE + href,
            "topics": ";".join(found),
            "needs_reading": "" if routine else needs_reading(found, co.get("priority", [])),
            "routine": "yes" if routine else "",
            "first_seen_utc": seen_at,
        })
    return rows


def _num(text: str | None) -> str:
    if not text:
        return ""
    return text.replace(",", "").strip()


def parse_own_shares(text: str) -> dict:
    """Pull the numbers out of a 'Transaction in Own Shares' notice.
    Tolerant of the usual wording variants; missing fields stay blank."""
    t = _clean(text)
    def grab(pattern: str) -> str:
        m = re.search(pattern, t, re.I)
        return _num(m.group(1)) if m else ""
    return {
        "trade_date": grab(r"Date of (?:transaction|purchase)\s*:?\s*(\d{1,2} \w+ \d{4})")
                      or grab(r"on (\d{1,2} \w+ \d{4}) it purchased"),
        "shares": grab(r"Number of (?:ordinary )?shares (?:re)?purchased\s*:?\s*([\d,]+)")
                  or grab(r"Aggregate number of [^:]*?shares[^:]*?:\s*([\d,]+)"),
        "avg_price_gbp_pence": grab(r"(?:Volume weighted )?average price paid per share\s*:?\s*"
                                    r"(?:GBp|GBX|pence)?\s*([\d,]+(?:\.\d+)?)"),
        "low_pence": grab(r"Lowest price paid per share\s*:?\s*(?:GBp|GBX|pence)?\s*([\d,]+(?:\.\d+)?)"),
        "high_pence": grab(r"Highest price paid per share\s*:?\s*(?:GBp|GBX|pence)?\s*([\d,]+(?:\.\d+)?)"),
        "shares_in_issue": grab(r"ordinary shares in issue will be\s*([\d,]+)")
                           or grab(r"shares in issue[^\d]{0,40}([\d,]{7,})"),
        "programme": grab(r"pursuant to (?:its|the) (.{0,80}?programme)"),
    }


def fetch_uk(cfg: dict, max_detail: int = 15) -> int:
    seen_at = now_utc()
    added = 0
    for co in cfg["uk"]:
        page = http_get(INVESTEGATE_COMPANY_URL.format(tidm=co["tidm"])).text
        rows = parse_investegate_company(page, co, cfg["topics"], seen_at)
        if not rows:
            raise RuntimeError(f"uk {co['tidm']}: no announcements parsed; run `capture` "
                               "and repair the parser")
        n = append_dedup_csv(UK_CSV, UK_FIELDS, rows, ["ann_id"])
        print(f"uk {co['tidm']}: {len(rows)} listed, {n} new")
        added += n
        # Buyback tally: read the numbers from own-share notices not yet parsed.
        done = set()
        if UK_BUYBACK_CSV.exists():
            done = {r["ann_id"] for r in read_csv_dicts(UK_BUYBACK_CSV)}
        todo = [r for r in rows if "own shares" in r["headline"].lower()
                and r["ann_id"] not in done][:max_detail]
        tally = []
        for r in todo:
            time.sleep(1.5)
            detail = parse_own_shares(http_get(r["link"]).text)
            if not detail["shares"]:
                print(f"uk {co['tidm']}: could not read numbers from {r['link']}")
                continue
            tally.append({"ann_id": r["ann_id"], "tidm": co["tidm"],
                          "first_seen_utc": seen_at, **detail})
        m = append_dedup_csv(UK_BUYBACK_CSV, UK_BUYBACK_FIELDS, tally, ["ann_id"])
        print(f"uk {co['tidm']}: {m} buyback notices parsed")
    record_status("uk", "ok")
    return added


# --- capture (parser repair) ------------------------------------------------

def capture(cfg: dict) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.date.today().isoformat()
    for co in cfg["uk"]:
        page = http_get(INVESTEGATE_COMPANY_URL.format(tidm=co["tidm"])).text
        (RAW_DIR / f"investegate_{co['tidm']}_{stamp}.html").write_text(page, "utf-8")
        link = next((m.group("href") for m in _ANN_LINK.finditer(page)
                     if "own-shares" in m.group("href")), None)
        if link:
            url = link if link.startswith("http") else INVESTEGATE_BASE + link
            (RAW_DIR / f"investegate_{co['tidm']}_own_shares_{stamp}.html").write_text(
                http_get(url).text, "utf-8")
    co = cfg["japan"][0]
    resp = http_get(YANOSHIN_URL.format(code=co["code"]), params={"limit": 5})
    (RAW_DIR / f"yanoshin_{co['code']}_{stamp}.json").write_text(resp.text, "utf-8")
    print(f"captured raw pages into {RAW_DIR}")


# --- brief ------------------------------------------------------------------

def _rows_since(path: Path, since: str) -> list[dict]:
    if not path.exists():
        return []
    return [r for r in read_csv_dicts(path) if r.get("first_seen_utc", "") >= since]


def _doc_date(text: str) -> dt.date | None:
    """Best-effort date of a document from the formats the four sources use."""
    text = (text or "").strip()
    for fmt_, n in (("%Y-%m-%d", 10), ("%Y%m%d", 8)):
        try:
            return dt.datetime.strptime(text[:n], fmt_).date()
        except ValueError:
            pass
    m = re.match(r"(\d{1,2} [A-Z][a-z]{2} \d{4})", text)
    if m:
        try:
            return dt.datetime.strptime(m.group(1), "%d %b %Y").date()
        except ValueError:
            return None
    return None


# Plain-English names for the report titles that recur, most specific first.
# Titles with no match are shown as filed; the "About" column still says
# what they concern.
TITLE_GLOSSES = [
    ("四半期決算短信", "quarterly earnings release"),
    ("決算短信", "earnings release"),
    ("決算説明", "results presentation"),
    ("配当予想の修正", "dividend forecast changed"),
    ("業績予想の修正", "profit guidance changed"),
    ("予想値と実績値", "results versus guidance gap"),
    ("自己株式の消却", "share cancellation"),
    ("自己株式の取得", "share buyback"),
    ("自己株券買付状況", "buyback progress report"),
    ("大量保有報告書", "5% big-holder report"),
    ("変更報告書", "big-holder stake change report"),
    ("中期経営計画", "medium-term business plan"),
    ("譲渡制限付株式報酬", "restricted stock pay for staff (routine)"),
    ("半期報告書", "half-year report"),
    ("有価証券報告書", "annual report"),
    ("臨時報告書", "extraordinary report"),
    ("영업(잠정)실적", "early, unaudited operating results"),
    ("잠정실적", "early, unaudited results"),
    ("현금ㆍ현물배당결정", "dividend declared"),
    ("배당", "dividend"),
    ("주식소각결정", "share cancellation decided"),
    ("자기주식취득결정", "share buyback decided"),
    ("자기주식처분결정", "treasury shares to be sold or used"),
    ("기업가치제고계획", "corporate value-up plan (shareholder-return plan)"),
    ("기업가치 제고", "corporate value-up plan (shareholder-return plan)"),
    ("임원ㆍ주요주주특정증권등소유상황보고서", "director or major-holder share dealing"),
    ("최대주주등소유주식변동신고서", "largest shareholder group's holdings changed"),
    ("조회공시요구(풍문또는보도)에대한답변(미확정)",
     "reply to the exchange's question about a rumor or press report: not yet decided"),
    ("조회공시요구(풍문또는보도)에대한답변", "reply to the exchange's question about a rumor or press report"),
    ("조회공시요구", "reply to the exchange's question"),
    ("소송등의판결ㆍ결정", "court ruling in a lawsuit"),
    ("소송등의제기", "lawsuit filed"),
    ("주식등의대량보유상황보고서", "5% big-holder report"),
    ("신규시설투자", "new capacity investment"),
    ("기업설명회", "investor presentation scheduled"),
    ("분기보고서", "quarterly report"),
    ("반기보고서", "half-year report"),
    ("사업보고서", "annual report"),
]


def english_title(title: str) -> str:
    """'English name (original)' for recurring CJK titles; Latin titles as is."""
    if title.isascii():
        return title
    for pat, gloss in TITLE_GLOSSES:
        if pat in title:
            return f"{gloss} ({title})"
    return title


def _topic_words(keys: str, topics: dict) -> str:
    return ", ".join(topics[k]["label"] for k in keys.split(";") if k in topics) or "other"


def buyback_pace(rows: list[dict], last_n: int = 5) -> dict | None:
    """Recent pace of the UK buyback from parsed own-share notices."""
    parsed = []
    for r in rows:
        try:
            d = dt.datetime.strptime(r["trade_date"], "%d %B %Y").date()
            parsed.append((d, float(r["shares"]), float(r["avg_price_gbp_pence"] or 0)))
        except (ValueError, KeyError):
            continue
    if not parsed:
        return None
    parsed.sort()
    recent = parsed[-last_n:]
    shares = sum(s for _, s, _ in recent)
    spend = sum(s * p for _, s, p in recent) / 100.0  # pence -> pounds
    return {"last_trade": parsed[-1][0], "days": len(recent), "shares": shares,
            "spend_gbp": spend, "avg_pence": (spend * 100.0 / shares) if shares else 0.0}


def uk_business_days_between(a: dt.date, b: dt.date) -> int:
    """Weekdays strictly after a, up to and including b (bank holidays ignored)."""
    n, d = 0, a
    while d < b:
        d += dt.timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def write_brief(cfg: dict, since: str, today: dt.date | None = None) -> str:
    today = today or dt.datetime.now(dt.timezone.utc).date()
    topics = cfg["topics"]
    state = load_state().get("status", {})
    new = []
    for r in _rows_since(TDNET_CSV, since):
        new.append((r["company"], "Japan same-day announcement", r["title"],
                    r["published_jst"][:10], r["topics"], r["needs_reading"], r["doc_url"]))
    for r in _rows_since(EDINET_CSV, since):
        new.append((r["company"], f"Japan filing: {r['doc_type']}", r["description"],
                    r["submitted_jst"][:10], r["topics"], r["needs_reading"], r["link"]))
    for r in _rows_since(DART_CSV, since):
        new.append((r["company"], "Korea filing", r["report"], r["received"],
                    r["topics"], r["needs_reading"], r["link"]))
    uk_new = _rows_since(UK_CSV, since)
    routine_uk = [r for r in uk_new if r["routine"]]
    for r in uk_new:
        if not r["routine"]:
            new.append((r["company"], "UK announcement", r["headline"], r["published"],
                        r["topics"], r["needs_reading"], r["link"]))
    big_holders = _rows_since(DART_5PCT_CSV, since)
    # A feed's first run loads its recent history; documents older than
    # STALE_DAYS are kept in the CSVs but not presented as news.
    cutoff = today - dt.timedelta(days=STALE_DAYS)
    fresh = [n for n in new if (_doc_date(n[3]) or today) >= cutoff]
    history = len(new) - len(fresh)
    new = fresh
    routine_uk = [r for r in routine_uk if (_doc_date(r["published"]) or today) >= cutoff]
    big_holders = [r for r in big_holders if (_doc_date(r["received"]) or today) >= cutoff]
    must_read = [n for n in new if n[5] == "yes"]

    out = ["# Foreign company filings: what's new", "",
           f"Run date {today.isoformat()}. New means first seen since {since}.", ""]

    # 1. Bottom line
    out.append("## Bottom line")
    out.append("")
    if must_read:
        names = sorted({n[0] for n in must_read})
        out.append(f"{len(must_read)} new document(s) touch a question you are watching, "
                   f"from {', '.join(names)}. Read them first; links are in the table below.")
    elif new or routine_uk:
        out.append("New documents arrived, but none touches a question you are watching.")
    else:
        out.append("Nothing new from the watched companies since the last run.")
    if history:
        out.append(f"{history} older document(s) were loaded as history and are not listed.")
    waiting = [f for f, s in state.items() if s.get("status") == "waiting for key"]
    if waiting:
        plain = {"edinet": "Japan's filing system (EDINET)", "dart": "Korea's filing system (OpenDART)"}
        out.append("Not yet switched on, waiting for a free access key: "
                   + "; ".join(plain.get(w, w) for w in waiting) + ".")
    out.append("")

    # 2. What
    out.append("## What")
    out.append("")
    if new:
        out.append("| Company | Where | Title | Dated | About | Read now? |")
        out.append("|---|---|---|---|---|---|")
        for co, where, title, date, keys, must, link in sorted(new, key=lambda x: (x[5] != "yes", x[0])):
            t = english_title(title).replace("|", "/")
            d = _doc_date(date)
            out.append(f"| {co} | {where} | [{t}]({link}) | {d.isoformat() if d else date} | "
                       f"{_topic_words(keys, topics)} | {'yes' if must else 'no'} |")
    else:
        out.append("No new company documents.")
    out.append("")
    if big_holders:
        out.append("Big holders crossing or changing a 5% stake in Korea:")
        out.append("")
        out.append("| Company | Holder | Stake now | Change in stake | Reason given |")
        out.append("|---|---|---|---|---|")
        for r in big_holders:
            out.append(f"| {r['company']} | {r['holder']} | {r['stake_pct']}% | "
                       f"{r['stake_change_pct']} points | {r['reason']} |")
        out.append("")

    # 3. So what: buyback pace (the kill check needs to know it is still running)
    out.append("## So what")
    out.append("")
    if UK_BUYBACK_CSV.exists():
        for co in cfg["uk"]:
            rows = [r for r in read_csv_dicts(UK_BUYBACK_CSV) if r["tidm"] == co["tidm"]]
            pace = buyback_pace(rows)
            if not pace:
                continue
            gap = uk_business_days_between(pace["last_trade"], today)
            out.append(f"{co['name']} buying back its own shares. Its last {pace['days']} "
                       f"daily report(s) of purchases add up to:")
            out.append("")
            out.append("| Shares bought | Money spent | Average price paid | Most recent purchase |")
            out.append("|---|---|---|---|")
            out.append(f"| {pace['shares']:,.0f} | £{pace['spend_gbp']:,.0f} | "
                       f"{pace['avg_pence']:,.1f} pence a share | {pace['last_trade']:%d %b %Y} |")
            out.append("")
            out.append("A buyback that keeps running on schedule is the company doing what it "
                       "promised with its cash.")
            if gap >= 3:
                out.append(f"Watch: no purchase reported for {gap} working days. Either the "
                           "programme has finished or the company has paused it; the next "
                           "announcement should say which.")
            out.append("")
    if routine_uk:
        out.append(f"{len(routine_uk)} routine UK notice(s) (daily buyback reports, share-count "
                   "updates) are counted above rather than listed.")
        out.append("")
    if not new and not routine_uk:
        out.append("Nothing to interpret this run.")
        out.append("")

    # 4. What now
    out.append("## What now")
    out.append("")
    out.append("| Owner | What | What closes it |")
    out.append("|---|---|---|")
    items = 0
    for co, where, title, date, keys, must, link in must_read:
        out.append(f"| Jim or Claude | Read {co}: {english_title(title).replace('|', '/')} | "
                   f"Answer recorded on the company's research page |")
        items += 1
    for w in waiting:
        plain = {"edinet": "Register for a free EDINET key and add it as the EDINET_API_KEY secret",
                 "dart": "Register for a free OpenDART key and add it as the DART_API_KEY secret"}
        out.append(f"| Jim | {plain.get(w, w)} | Next run shows that feed as working |")
        items += 1
    if not items:
        out.append("| none | Nothing open | |")
    out.append("")
    upcoming = sorted((e for e in cfg.get("calendar", []) if e["sort_by"] >= today.isoformat()),
                      key=lambda e: e["sort_by"])[:4]
    if upcoming:
        out.append("Coming up: " + "; ".join(f"{e['company']} {e['event']}, {e['window']}"
                                             for e in upcoming) + ".")
        out.append("")
    out.append("This is early evidence that puts things on the watch list; on its own it "
               "is not grounds for a decision.")
    text = "\n".join(out) + "\n"
    BRIEF_PATH.parent.mkdir(parents=True, exist_ok=True)
    BRIEF_PATH.write_text(text, "utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(text)
    subject = (f"filings: {len(new)} new, {len(must_read)} to read" if new
               else "filings: nothing new")
    print(subject)
    return text


# --- CLI --------------------------------------------------------------------

def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    cfg = load_config()
    days = None
    if "--days" in rest:
        days = int(rest[rest.index("--days") + 1])
    if cmd == "tdnet":
        fetch_tdnet(cfg)
    elif cmd == "edinet":
        fetch_edinet(cfg, days or 7)
    elif cmd == "dart":
        fetch_dart(cfg, days or 14)
    elif cmd == "uk":
        fetch_uk(cfg)
    elif cmd == "capture":
        capture(cfg)
    elif cmd == "brief":
        since = rest[rest.index("--since") + 1] if "--since" in rest else \
            (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
        write_brief(cfg, since)
    else:
        print(f"unknown command {cmd!r}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
