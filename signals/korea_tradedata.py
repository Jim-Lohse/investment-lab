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
    "js_common": "https://tradedata.go.kr/cts/js/common/common.js",
    # The 10-day provisional screen's own controller: names its grid-data call.
    "js_ets173": "https://tradedata.go.kr/cts/js/ets/hmpg/trade/ETS0100173Q.js",
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
    # Single attempt, short timeout: when the site's protection is blocking
    # cloud-runner IPs, backoff-hammering only entrenches the block.
    resp = http_get(DASHBOARD_URL, retries=1, timeout=30)
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


ITEMS_HEADER = ["yyyymm", "period_label", "period_type", "imex", "item_slot",
                "item_name", "value_usd_k", "retrieved_at"]
TENTATIVE_URL = "https://tradedata.go.kr/cts/hmpg/retrieveTentativeValues.do"


def _session():
    import requests

    from .common import USER_AGENT
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    session.get("https://tradedata.go.kr/cts/index.do", timeout=30)
    session.headers.update({
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://tradedata.go.kr/cts/index.do",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        # The portal's kcs4g AJAX wrapper marks every call with this custom
        # header; requests without it can be rejected server-side.
        "isAjax": "true",
    })
    return session


def _hangul_strings(node, out):
    if isinstance(node, str):
        if any("가" <= ch <= "힣" for ch in node):
            out.append(node.strip())
    elif isinstance(node, list):
        for child in node:
            _hangul_strings(child, out)
    elif isinstance(node, dict):
        for child in node.values():
            _hangul_strings(child, out)


def parse_tentative_json(payload, retrieved_at: str, imex: str) -> list[dict]:
    """Normalize the 10-day by-item grid response.

    Rows carry priodDt/priodMon plus pivoted itemUsdAmt<NN> columns. Item
    names for the slots are resolved from Korean strings in the same row
    when present, else the row order of a header-ish record; failing both,
    slots keep generic labels (raw JSON is preserved regardless).
    """
    from .korea_customs import classify_period

    # Collect every dict that looks like a grid row.
    rows_in: list[dict] = []

    def walk(node):
        if isinstance(node, dict):
            if any(k.startswith("itemUsdAmt") for k in node):
                rows_in.append(node)
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(payload)

    out: list[dict] = []
    for row in rows_in:
        period_label = str(row.get("priodDt") or "").strip()
        month_raw = str(row.get("priodMon") or "").replace(".", "")
        yyyymm = (f"{month_raw[:4]}-{month_raw[4:6]}"
                  if len(month_raw) >= 6 else "")
        curtitle = str(row.get("curTitle") or "").strip()
        ptype = classify_period(period_label) or classify_period(curtitle)
        slots = sorted(k for k in row if k.startswith("itemUsdAmt"))
        for slot in slots:
            value = str(row.get(slot) or "").replace(",", "").strip()
            if not value:
                continue
            # A header-style record carries names instead of numbers: use it
            # to label subsequent numeric rows via the shared slot key.
            try:
                float(value)
            except ValueError:
                _SLOT_NAMES[(imex, slot)] = value
                continue
            out.append({
                "yyyymm": yyyymm,
                "period_label": period_label or curtitle,
                "period_type": ptype,
                "imex": imex,
                "item_slot": slot.replace("itemUsdAmt", ""),
                "item_name": _SLOT_NAMES.get((imex, slot), ""),
                "value_usd_k": value,
                "retrieved_at": retrieved_at,
            })
    return out


_SLOT_NAMES: dict = {}


def fetch_items(start_yyyymm: str | None = None, end_yyyymm: str | None = None) -> int:
    """Fetch the by-item 10-day grid (both exports and imports)."""
    import json as _json

    today = dt.date.today()
    if end_yyyymm is None:
        end_yyyymm = today.strftime("%Y%m")
    if start_yyyymm is None:
        prev = (today.replace(day=1) - dt.timedelta(days=1))
        start_yyyymm = prev.strftime("%Y%m")

    session = _session()
    # Load the screen once: mirrors the browser flow and establishes any
    # server-side screen state before the grid query.
    session.get("https://tradedata.go.kr/cts/hmpg/openETS0100173Q.do",
                params={"menuId": "ETS_MNU_00000134"}, timeout=30)
    retrieved_at = today.isoformat()
    added_total = 0
    for imex in ("E", "I"):
        data = {
            "menuId": "ETS_MNU_00000134",
            "statsKind": "P", "imexTpcd": imex, "priodKind": "MON",
            "priodFr": start_yyyymm, "priodTo": end_yyyymm, "priodDate": "",
            # 100 is the largest page size the screen's own select offers;
            # larger values are rejected server-side (KcsRuntimeException).
            "selectPaging": "1", "showPagingLine": "100",
            "sortColumn": "", "sortOrder": "",
        }
        resp = session.post(TENTATIVE_URL, data=data, timeout=60)
        resp.raise_for_status()
        PAGES_DIR.parent.mkdir(parents=True, exist_ok=True)
        raw_name = f"tentative_{imex}_{start_yyyymm}_{end_yyyymm}.json"
        (PAGES_DIR.parent / raw_name).write_bytes(resp.content)
        payload = _json.loads(resp.content)
        if isinstance(payload, dict) and payload.get("error") == "true":
            raise RuntimeError(
                f"tentative items imex={imex}: server error "
                f"{payload.get('errortype')}: {payload.get('message')}")
        rows = parse_tentative_json(payload, retrieved_at, imex)
        added = append_dedup_csv(
            OUT_DIR / "tradedata_items.csv", ITEMS_HEADER, rows,
            ["yyyymm", "period_label", "imex", "item_slot"])
        print(f"tentative items imex={imex} {start_yyyymm}..{end_yyyymm}: "
              f"{len(rows)} values parsed, {added} new")
        added_total += added
    return added_total


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
           "Accept": "application/json, text/javascript, */*; q=0.01",
           "isAjax": "true"}

    session.get(f"{base}/cts/hmpg/openETS0100173Q.do",
                params={"menuId": "ETS_MNU_00000134"}, timeout=30,
                headers={"isAjax": "true"})
    tent = {
        "menuId": "ETS_MNU_00000134", "statsKind": "P", "imexTpcd": "E",
        "priodKind": "MON", "priodFr": "202607", "priodTo": "202608",
        "priodDate": "", "selectPaging": "1", "showPagingLine": "100",
        "sortColumn": "", "sortOrder": "",
    }
    tent_url = f"{base}/cts/hmpg/retrieveTentativeValues.do"
    attempts = [
        # Variants for the by-item grid; kcs4g's isAjax header rides on all.
        ("probe_tent_base", "POST", tent_url, dict(tent)),
        ("probe_tent_space", "POST", tent_url,
         {**tent, "priodFr": "202607 ", "priodTo": "202608 "}),
        ("probe_tent_paging15", "POST", tent_url,
         {**tent, "showPagingLine": "15"}),
        ("probe_tent_nomenu", "POST", tent_url,
         {k: v for k, v in tent.items() if k != "menuId"}),
        ("probe_tent_d10", "POST", tent_url, {**tent, "priodDate": "1"}),
        ("probe_tent_chart", "POST",
         f"{base}/cts/hmpg/retrieveChartTentativeValues.do", dict(tent)),
        ("probe_tent_chart_N", "POST",
         f"{base}/cts/hmpg/retrieveChartTentativeValues.do",
         {**tent, "statsKind": "N"}),
        ("probe_tent_chart_N_imp", "POST",
         f"{base}/cts/hmpg/retrieveChartTentativeValues.do",
         {**tent, "statsKind": "N", "imexTpcd": "I"}),
        ("probe_tent_grid_N", "POST", tent_url, {**tent, "statsKind": "N"}),
        ("probe_tent_dljson", "POST",
         f"{base}/cts/hmpg/downloadTentativeValuesJson.do", dict(tent)),
        # The 통계항목 option list — should carry the real statsKind codes.
        ("probe_tent_selectbox", "POST",
         f"{base}/cts/hmpg/retrieveSetSelectBoxTentative.do",
         {"menuId": "ETS_MNU_00000134"}),
        ("probe_tent_selectbox_get", "GET",
         f"{base}/cts/hmpg/retrieveSetSelectBoxTentative.do?menuId=ETS_MNU_00000134",
         None),
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
    elif argv[0] == "items":
        if len(argv) >= 3:
            fetch_items(argv[1], argv[2])
        else:
            fetch_items()
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
