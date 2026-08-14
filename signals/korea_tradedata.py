"""No-registration fallback: scrape KCS tradedata.go.kr for flash trade totals.

The Korea Customs Service statistics portal publishes the 10/20-day and
full-month provisional customs-clearance results on its public dashboard —
no login, no API key. The English dashboard's "Clearance Result" table
carries total exports and imports for the latest published window with
year-on-year rates already computed (unit: USD million).

    https://tradedata.go.kr/cts/index_eng.do

Scope and honesty: the dashboard shows TOTALS ONLY. The by-item breakout
(semiconductors etc.) lives on a JavaScript-driven page whose data loads
via background requests; the `capture` command saves that page's raw HTML
into data/korea/raw/pages/ from a CI run so the parser can be extended
against the real markup (or replaced by the data.go.kr API once a service
key exists — see korea_customs.py, which remains the preferred source).

Output (append-only, first print wins):
  data/korea/tradedata_flash.csv

Usage:
    python -m signals.korea_tradedata dashboard
    python -m signals.korea_tradedata capture
"""

from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

from .common import (DATA_DIR, TableParser, append_dedup_csv, fmt, http_get,
                     parse_number)

DASHBOARD_URL = "https://tradedata.go.kr/cts/index_eng.do"
CAPTURE_URLS = {
    "dashboard_eng": DASHBOARD_URL,
    "ten_day_stats_kr": "https://tradedata.go.kr/cts/index.do?menuId=ETS_MNU_00000134",
    "main_kr": "https://tradedata.go.kr/cts/index.do",
    # The provisional-stats (잠정통계) screen fragment behind the dashboard
    # widget; candidate source for the by-item 10-day breakout.
    "provisional_stats_kr": "https://tradedata.go.kr/cts/hmpg/openETS0100173Q.do",
    # Site JS defining the screen loaders and widget data calls.
    "js_main": "https://tradedata.go.kr/cts/js/ets/hmpg/main/main.js",
    "js_ets_common": "https://tradedata.go.kr/cts/js/ets/cmmn/ets_common.js",
    "js_index_main": "https://tradedata.go.kr/cts/js/ets/cmmn/indexMain.js",
    "js_menu": "https://tradedata.go.kr/cts/js/menu.js",
    "js_kcs4g_ajax": "https://tradedata.go.kr/cts/js/kcs4g/kcs4g_ajax.js",
}

OUT_DIR = DATA_DIR / "korea"
PAGES_DIR = OUT_DIR / "raw" / "pages"

HEADER = ["yyyymm", "period_label", "period_type", "metric",
          "value_usd_m", "yoy_pct", "retrieved_at"]

MONTHS = {name: i + 1 for i, name in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"])}


def parse_window(label: str, retrieved: dt.date) -> tuple[str, str]:
    """'Aug.1~Aug.10' -> ('2026-08', 'D10'); 'Jun.1~Jun.30' -> (..., 'FULL').

    The label carries no year: use the retrieval date's year, rolling back one
    year when the label's month is ahead of the retrieval month (a December
    window read in January).
    """
    match = re.search(
        r"([A-Za-z]{3,9})\.?\s*\d{1,2}\s*[~∼–-]\s*(?:([A-Za-z]{3,9})\.?\s*)?(\d{1,2})",
        label)
    if not match:
        return "", ""
    month_name = (match.group(2) or match.group(1))[:3].lower()
    month = MONTHS.get(month_name)
    if not month:
        return "", ""
    end_day = int(match.group(3))
    year = retrieved.year - (1 if month > retrieved.month else 0)
    if end_day == 10:
        ptype = "D10"
    elif end_day == 20:
        ptype = "D20"
    elif end_day >= 28:
        ptype = "FULL"
    else:
        ptype = ""
    return f"{year:04d}-{month:02d}", ptype


def parse_dashboard(html: str, retrieved: dt.date) -> list[dict]:
    """Extract the current-window Export/Import rows from the Clearance
    Result table (7-cell layout: metric, prev-cum pair, current pair,
    annual-cum pair)."""
    parser = TableParser()
    parser.feed(html)

    label = ""
    for _, cells in parser.rows:
        for cell in cells:
            match = re.search(r"Current month\s*\(([^)]+)\)", cell)
            if match:
                label = match.group(1).strip()
                break
        if label:
            break
    yyyymm, ptype = parse_window(label, retrieved)

    rows: list[dict] = []
    for _, cells in parser.rows:
        if len(cells) < 7 or cells[0].strip() not in ("Export", "Import"):
            continue
        value = parse_number(cells[3])
        yoy = parse_number(cells[4])
        if value is None:
            continue
        rows.append({
            "yyyymm": yyyymm,
            "period_label": label,
            "period_type": ptype,
            "metric": cells[0].strip(),
            "value_usd_m": fmt(value),
            "yoy_pct": fmt(yoy),
            "retrieved_at": retrieved.isoformat(),
        })
    return rows


def fetch_dashboard() -> int:
    retrieved = dt.date.today()
    resp = http_get(DASHBOARD_URL)
    resp.encoding = resp.encoding or "utf-8"
    rows = parse_dashboard(resp.text, retrieved)
    if not rows:
        # Keep the evidence when parsing fails so the parser can be fixed
        # against the actual payload.
        PAGES_DIR.mkdir(parents=True, exist_ok=True)
        (PAGES_DIR / "dashboard_eng_unparsed.html").write_text(resp.text, "utf-8")
        raise RuntimeError(
            "tradedata dashboard: 0 rows parsed; raw page saved to "
            "data/korea/raw/pages/dashboard_eng_unparsed.html")
    added = append_dedup_csv(OUT_DIR / "tradedata_flash.csv", HEADER, rows,
                             ["yyyymm", "period_label", "metric"])
    for row in rows:
        print(f"  {row['metric']:<6} {row['period_label']:<16} "
              f"{row['value_usd_m']} USD m ({row['yoy_pct']}% YoY)")
    print(f"tradedata dashboard: {len(rows)} rows parsed, {added} new")
    return added


def capture() -> None:
    """Save raw page HTML for parser development (run from CI where the
    site is reachable; pages land in the repo via the data commit)."""
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in CAPTURE_URLS.items():
        try:
            resp = http_get(url)
            resp.encoding = resp.encoding or "utf-8"
            (PAGES_DIR / f"{name}.html").write_text(resp.text, "utf-8")
            print(f"captured {name}: {len(resp.text)} chars")
        except RuntimeError as err:
            print(f"capture {name} failed: {err}")


def probe() -> None:
    """Exercise candidate data endpoints from CI and save every response.

    Read-only requests against the portal's own widget endpoints; results
    land in data/korea/raw/pages/ for parser development.
    """
    import requests

    from .common import USER_AGENT

    base = "https://tradedata.go.kr"
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    session.get(f"{base}/cts/index.do", timeout=60)  # establish session cookie
    xhr = {"X-Requested-With": "XMLHttpRequest",
           "Referer": f"{base}/cts/index.do",
           "Accept": "application/json, text/javascript, */*; q=0.01"}

    attempts = [
        ("probe_pprc_get", "GET", f"{base}/cts/hmpg/retrieveTradePprc.do", None),
        ("probe_pprc_post", "POST", f"{base}/cts/hmpg/retrieveTradePprc.do", {}),
        ("probe_173_post", "POST", f"{base}/cts/hmpg/openETS0100173Q.do",
         {"menuId": "ETS_MNU_00000134"}),
        ("probe_173_get_menu", "GET",
         f"{base}/cts/hmpg/openETS0100173Q.do?menuId=ETS_MNU_00000134", None),
    ]
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    for name, method, url, data in attempts:
        try:
            resp = session.request(method, url, data=data, headers=xhr, timeout=60)
            body = resp.content[:400_000]
            (PAGES_DIR / f"{name}.txt").write_bytes(
                f"HTTP {resp.status_code} {resp.headers.get('Content-Type','')}\n"
                .encode() + body)
            print(f"{name}: HTTP {resp.status_code}, {len(resp.content)} bytes, "
                  f"{resp.headers.get('Content-Type','')}")
        except requests.RequestException as err:
            (PAGES_DIR / f"{name}.txt").write_text(f"ERROR {err}", "utf-8")
            print(f"{name}: {err}")


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    if argv[0] == "dashboard":
        fetch_dashboard()
    elif argv[0] == "capture":
        capture()
    elif argv[0] == "probe":
        probe()
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
