"""Taiwan MOPS monthly revenue fetcher.

Taiwan-listed companies must report monthly revenue by the 10th of the
following month. Two free primary sources:

1. Current month (no key, UTF-8 CSV, published as government open data):
   - TWSE listed:  https://mopsfin.twse.com.tw/opendata/t187ap05_L.csv
   - TPEx (OTC):   https://mopsfin.twse.com.tw/opendata/t187ap05_O.csv
   (data.gov.tw dataset 18420, "Monthly summary of operating income")

2. Historical archive (no key, Big5 HTML tables, one page per market/month):
   https://mops.twse.com.tw/nas/t21/{sii|otc}/t21sc03_{rocYear}_{month}_{0|1}.html
   suffix 0 = domestic issuers, 1 = KY (foreign primary listings).

Both normalize to one CSV per (month, market) under
data/taiwan/monthly_revenue/YYYY-MM_{sii|otc}.csv. Revenue unit: thousand TWD.

Usage:
    python -m signals.taiwan_mops current
    python -m signals.taiwan_mops archive 2026-06
    python -m signals.taiwan_mops backfill 2024-01 2026-06
"""

from __future__ import annotations

import csv
import io
import re
import sys
import time
from pathlib import Path

from .common import (DATA_DIR, TableParser, fmt, http_get, iso_to_roc,
                     month_range, parse_number, roc_to_iso_month)

OPEN_CSV_URLS = {
    "sii": "https://mopsfin.twse.com.tw/opendata/t187ap05_L.csv",
    "otc": "https://mopsfin.twse.com.tw/opendata/t187ap05_O.csv",
}
ARCHIVE_URL = "https://mops.twse.com.tw/nas/t21/{market}/t21sc03_{roc_year}_{month}_{suffix}.html"

OUT_DIR = DATA_DIR / "taiwan" / "monthly_revenue"

HEADER = [
    "report_month", "market", "company_id", "company_name", "industry",
    "rev_month_twd_k", "rev_prev_month_twd_k", "rev_year_ago_month_twd_k",
    "mom_pct", "yoy_pct",
    "rev_cum_twd_k", "rev_cum_prev_year_twd_k", "cum_yoy_pct", "note",
]

# Open-data CSV column names -> normalized fields (matched by substring so
# minor header revisions don't break the parser).
OPEN_CSV_FIELDS = {
    "company_id": ["公司代號"],
    "company_name": ["公司名稱"],
    "industry": ["產業別"],
    "rev_month_twd_k": ["營業收入-當月營收"],
    "rev_prev_month_twd_k": ["營業收入-上月營收"],
    "rev_year_ago_month_twd_k": ["營業收入-去年當月營收"],
    "mom_pct": ["營業收入-上月比較增減"],
    "yoy_pct": ["營業收入-去年同月增減"],
    "rev_cum_twd_k": ["累計營業收入-當月累計營收"],
    "rev_cum_prev_year_twd_k": ["累計營業收入-去年累計營收"],
    "cum_yoy_pct": ["累計營業收入-前期比較增減"],
    "note": ["備註"],
    "_data_month": ["資料年月"],
}


def _match_column(fieldnames: list[str], needles: list[str]) -> str | None:
    for name in fieldnames:
        for needle in needles:
            if needle in name:
                return name
    return None


def parse_open_csv(text: str, market: str) -> tuple[str, list[list]]:
    """Parse a t187ap05 open-data CSV. Returns (report_month, normalized rows)."""
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    if not reader.fieldnames:
        raise ValueError("open CSV has no header row")
    colmap = {field: _match_column(reader.fieldnames, needles)
              for field, needles in OPEN_CSV_FIELDS.items()}
    missing = [f for f in ("company_id", "rev_month_twd_k", "_data_month")
               if not colmap[f]]
    if missing:
        raise ValueError(
            f"open CSV missing expected columns {missing}; got {reader.fieldnames}")

    rows: list[list] = []
    report_month = ""
    for rec in reader:
        code = (rec.get(colmap["company_id"]) or "").strip()
        if not re.fullmatch(r"\d{4,6}", code):
            continue
        if not report_month:
            report_month = roc_to_iso_month(rec[colmap["_data_month"]])
        get = lambda f: (rec.get(colmap[f]) or "").strip() if colmap[f] else ""
        rows.append([
            report_month, market, code, get("company_name"), get("industry"),
            fmt(parse_number(get("rev_month_twd_k"))),
            fmt(parse_number(get("rev_prev_month_twd_k"))),
            fmt(parse_number(get("rev_year_ago_month_twd_k"))),
            fmt(parse_number(get("mom_pct"))),
            fmt(parse_number(get("yoy_pct"))),
            fmt(parse_number(get("rev_cum_twd_k"))),
            fmt(parse_number(get("rev_cum_prev_year_twd_k"))),
            fmt(parse_number(get("cum_yoy_pct"))),
            get("note").replace("\n", " "),
        ])
    if not rows:
        raise ValueError("open CSV parsed to zero company rows")
    return report_month, rows


def parse_archive_html(html: str, market: str, report_month: str) -> list[list]:
    """Parse a nas/t21 archive page (already decoded from Big5)."""
    parser = TableParser()
    parser.feed(html)
    rows: list[list] = []
    for industry, cells in parser.rows:
        if len(cells) < 10:
            continue
        code = cells[0].strip()
        if not re.fullmatch(r"\d{4,6}", code):
            continue
        name = cells[1].strip()
        nums = [parse_number(c) for c in cells[2:10]]
        note = cells[10].strip().replace("\n", " ") if len(cells) > 10 else ""
        rows.append([
            report_month, market, code, name, industry,
            fmt(nums[0]), fmt(nums[1]), fmt(nums[2]),  # month, prev month, year-ago
            fmt(nums[3]), fmt(nums[4]),                # mom %, yoy %
            fmt(nums[5]), fmt(nums[6]), fmt(nums[7]),  # cum, cum prev year, cum yoy %
            note,
        ])
    return rows


def _write_month(report_month: str, market: str, rows: list[list]) -> Path:
    out = OUT_DIR / f"{report_month}_{market}.csv"
    from .common import write_csv
    write_csv(out, HEADER, rows)
    print(f"wrote {out.relative_to(DATA_DIR.parent)} ({len(rows)} companies)")
    return out


def fetch_current() -> list[Path]:
    """Fetch the latest month for both markets from the open-data CSVs."""
    written = []
    for market, url in OPEN_CSV_URLS.items():
        resp = http_get(url)
        resp.encoding = "utf-8-sig"
        report_month, rows = parse_open_csv(resp.text, market)
        written.append(_write_month(report_month, market, rows))
    return written


def fetch_archive(iso_month: str, markets: tuple[str, ...] = ("sii", "otc"),
                  pause: float = 3.0) -> list[Path]:
    """Fetch one historical month per market from the Big5 HTML archive.

    Merges domestic (suffix 0) and KY (suffix 1) issuers into one file.
    """
    roc_year, month = iso_to_roc(iso_month)
    written = []
    for market in markets:
        merged: list[list] = []
        for suffix in (0, 1):
            url = ARCHIVE_URL.format(market=market, roc_year=roc_year,
                                     month=month, suffix=suffix)
            try:
                resp = http_get(url)
            except RuntimeError as err:
                # KY pages don't exist for every market/month; domestic must.
                if suffix == 1:
                    print(f"  skip {url}: {err}")
                    continue
                raise
            html = resp.content.decode("big5", errors="replace")
            merged.extend(parse_archive_html(html, market, iso_month))
            time.sleep(pause)  # be polite to MOPS
        if not merged:
            raise RuntimeError(f"no rows parsed for {iso_month} {market}")
        written.append(_write_month(iso_month, market, merged))
    return written


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd = argv[0]
    if cmd == "current":
        fetch_current()
    elif cmd == "archive":
        fetch_archive(argv[1])
    elif cmd == "backfill":
        for iso_month in month_range(argv[1], argv[2]):
            out = OUT_DIR / f"{iso_month}_sii.csv"
            if out.exists():
                print(f"skip {iso_month} (exists)")
                continue
            fetch_archive(iso_month)
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
