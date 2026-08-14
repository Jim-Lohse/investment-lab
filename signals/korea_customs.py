"""Korea Customs Service (KCS) export statistics fetcher.

Korea publishes trade data three times a month — days 1-10 on the 11th,
days 1-20 on the 21st, and the full month on the 1st of the next month —
with a semiconductor breakout. This is the fastest broad public read on
global tech demand.

Sources (all free; data.go.kr requires a no-cost registered service key,
auto-approved for these datasets):
  - 10-day provisional statistics by major item (XML, thousand USD,
    history from 2016-01; verified from the dataset pages 2026-08-14):
      exports: apis.data.go.kr/1220000/prlstMmUtPrviExpAcrs/getPrlstMmUtPrviExpAcrs
               (data.go.kr dataset 15157908)
      imports: apis.data.go.kr/1220000/prlstMmUtPrviImpAcrs/getPrlstMmUtPrviImpAcrs
               (data.go.kr dataset 15157901)
    Both take serviceKey + strtYymm/endYymm (year-month range).
  - Monthly item-level trade by HS code:
      apis.data.go.kr/1220000/Itemtrade/getItemtradeList
  - Human-readable cross-check: https://tradedata.go.kr

The flash APIs' per-item field names are not published in the dataset docs,
so the flash parser is schema-tolerant: it extracts period / item / value
from candidate tag names and stores every field of each record verbatim in
an extra_json column. Raw payloads are also kept under data/korea/raw/.

Normalized output (append-only, deduplicated, first write wins):
  data/korea/trade_monthly.csv   — monthly HS-code series (USD)
  data/korea/exports_flash.csv   — 10/20-day + full-month provisional series
                                   (thousand USD; exports and imports feeds)

Usage:
    DATA_GO_KR_API_KEY=... python -m signals.korea_customs flash
    DATA_GO_KR_API_KEY=... python -m signals.korea_customs flash 2026-01 2026-08
    DATA_GO_KR_API_KEY=... python -m signals.korea_customs flash-backfill 2016-01 2026-08
    DATA_GO_KR_API_KEY=... python -m signals.korea_customs monthly 2024-01 2026-07
    DATA_GO_KR_API_KEY=... python -m signals.korea_customs monthly-latest
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from .common import CONFIG_DIR, DATA_DIR, append_dedup_csv, http_get

OUT_DIR = DATA_DIR / "korea"
RAW_DIR = OUT_DIR / "raw"

MONTHLY_HEADER = ["year_month", "hs_code", "item_name",
                  "export_usd", "import_usd", "balance_usd", "retrieved_at"]
FLASH_HEADER = ["yyyymm", "period_label", "period_type", "feed", "item_name",
                "value_usd_k", "extra_json", "retrieved_at"]

# Candidate tag names across KCS API generations; parsed defensively.
TAGS_YEAR = ("year", "priodTitle", "aggrgtDt", "prdDe")
TAGS_HS = ("hsCd", "statCd", "hsSgn", "itemCd")
TAGS_NAME = ("statKor", "statCdCntnKor1", "itemNm", "korePrlstNm", "prlstNm")
TAGS_EXP = ("expDlr", "expUsdAmt", "expAmt")
TAGS_IMP = ("impDlr", "impUsdAmt", "impAmt")
TAGS_BAL = ("balPayments", "balAmt")
TAGS_PERIOD = ("priodTitle", "prlstDt", "aggrgtDt", "baseDt", "statDt",
               "year", "yyyymm", "prdDe", "stdDt", "dt")
TAGS_VALUE = ("expDlr", "impDlr", "expUsdAmt", "impUsdAmt", "expAmt",
              "impAmt", "usdAmt", "dlr", "amt")


def _load_config() -> dict:
    return json.loads((CONFIG_DIR / "korea_endpoints.json").read_text("utf-8"))


def _service_key() -> str:
    key = os.environ.get("DATA_GO_KR_API_KEY", "").strip()
    if not key:
        print("NOTICE: DATA_GO_KR_API_KEY not set — skipping Korea fetch. "
              "Register free at https://www.data.go.kr and export the decoded key.")
        raise SystemExit(0)
    return key


def _first_text(item: ET.Element, candidates: tuple[str, ...]) -> str:
    for tag in candidates:
        node = item.find(tag)
        if node is not None and node.text:
            return node.text.strip()
    return ""


def _num(text: str) -> str:
    cleaned = text.replace(",", "").strip()
    if not cleaned:
        return ""
    try:
        return str(int(float(cleaned)))
    except ValueError:
        return ""


def _save_raw(name: str, content: bytes) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / name).write_bytes(content)


def _check_api_error(root: ET.Element, context: str) -> None:
    """data.go.kr returns HTTP 200 with an error envelope on auth failures."""
    code = root.findtext(".//resultCode") or root.findtext(".//returnReasonCode")
    msg = root.findtext(".//resultMsg") or root.findtext(".//returnAuthMsg")
    if code and code not in ("00", "0000", "INFO-0", "NORMAL SERVICE."):
        raise RuntimeError(f"{context}: API error {code}: {msg}")


# --- Monthly item trade -----------------------------------------------------

def parse_monthly_xml(content: bytes, retrieved_at: str) -> list[dict]:
    root = ET.fromstring(content)
    _check_api_error(root, "monthly item trade")
    rows = []
    for item in root.iter("item"):
        year_month = _first_text(item, TAGS_YEAR).replace(".", "-")
        hs_code = _first_text(item, TAGS_HS)
        if not year_month or year_month.startswith("총"):  # totals row: "총계"
            continue
        rows.append({
            "year_month": year_month,
            "hs_code": hs_code,
            "item_name": _first_text(item, TAGS_NAME),
            "export_usd": _num(_first_text(item, TAGS_EXP)),
            "import_usd": _num(_first_text(item, TAGS_IMP)),
            "balance_usd": _num(_first_text(item, TAGS_BAL)),
            "retrieved_at": retrieved_at,
        })
    return rows


def fetch_monthly(start_iso: str, end_iso: str, hs_codes: list[str] | None = None) -> int:
    cfg = _load_config()["monthly_item_trade"]
    key = _service_key()
    hs_codes = hs_codes or ["85", "8542", "8486", "8479"]
    retrieved_at = dt.date.today().isoformat()
    added_total = 0
    for hs_code in hs_codes:
        params = {name: template.format(
                      service_key=key,
                      start_yyyymm=start_iso.replace("-", ""),
                      end_yyyymm=end_iso.replace("-", ""),
                      hs_code=hs_code)
                  for name, template in cfg["params"].items()}
        resp = http_get(cfg["url"], params=params)
        _save_raw(f"monthly_{hs_code}_{start_iso}_{end_iso}.xml", resp.content)
        rows = parse_monthly_xml(resp.content, retrieved_at)
        added = append_dedup_csv(OUT_DIR / "trade_monthly.csv", MONTHLY_HEADER,
                                 rows, ["year_month", "hs_code"])
        print(f"HS {hs_code}: {len(rows)} rows fetched, {added} new")
        added_total += added
        time.sleep(1.0)
    return added_total


# --- 10/20-day flash --------------------------------------------------------

def classify_period(label: str) -> str:
    """Infer the window from a period label's trailing day number.

    '2026.08.01 ~ 2026.08.10' -> D10; '1일~20일' -> D20; ...31 -> FULL.
    Unknown shapes return '' (the label itself still identifies the row).
    """
    match = re.search(r"[~∼–-]\s*(?:\d{4}[./-])?(?:\d{1,2}[./-])?(\d{1,2})\s*일?\s*$",
                      label.strip())
    if not match:
        return ""
    day = int(match.group(1))
    if day == 10:
        return "D10"
    if day == 20:
        return "D20"
    if day >= 28:
        return "FULL"
    return ""


def _extract_yyyymm(item_fields: dict, period_label: str) -> str:
    for text in [period_label] + list(item_fields.values()):
        match = re.search(r"(20\d{2})[./-]?(0[1-9]|1[0-2])", text)
        if match:
            return f"{match.group(1)}-{match.group(2)}"
    return ""


def parse_flash_xml(content: bytes, feed: str, retrieved_at: str) -> list[dict]:
    """Schema-tolerant parse: known fields extracted, everything kept in extra_json."""
    root = ET.fromstring(content)
    _check_api_error(root, feed)
    rows = []
    for item in root.iter("item"):
        fields = {child.tag: (child.text or "").strip() for child in item}
        if not any(fields.values()):
            continue
        period_label = _first_text(item, TAGS_PERIOD)
        value = ""
        for tag in TAGS_VALUE:
            if fields.get(tag):
                value = _num(fields[tag])
                if value:
                    break
        rows.append({
            "yyyymm": _extract_yyyymm(fields, period_label),
            "period_label": period_label,
            "period_type": classify_period(period_label),
            "feed": feed,
            "item_name": _first_text(item, TAGS_NAME),
            "value_usd_k": value,
            "extra_json": json.dumps(fields, ensure_ascii=False, sort_keys=True),
            "retrieved_at": retrieved_at,
        })
    return rows


def fetch_flash(start_iso: str | None = None, end_iso: str | None = None) -> int:
    """Fetch flash windows for a month range (default: previous + current month).

    The APIs return every published window in the range; dedup keeps re-runs
    cheap and first-print figures immutable.
    """
    cfg = _load_config()
    key = _service_key()
    today = dt.date.today()
    if end_iso is None:
        end_iso = today.strftime("%Y-%m")
    if start_iso is None:
        start_iso = (today.replace(day=1) - dt.timedelta(days=1)).strftime("%Y-%m")

    retrieved_at = today.isoformat()
    added_total = 0
    for feed in ("flash_exports_10day", "flash_imports_10day"):
        feed_cfg = cfg[feed]
        params = {name: template.format(
                      service_key=key,
                      start_yyyymm=start_iso.replace("-", ""),
                      end_yyyymm=end_iso.replace("-", ""))
                  for name, template in feed_cfg["params"].items()}
        resp = http_get(feed_cfg["url"], params=params)
        _save_raw(f"{feed}_{start_iso}_{end_iso}.xml", resp.content)
        rows = parse_flash_xml(resp.content, feed, retrieved_at)
        added = append_dedup_csv(
            OUT_DIR / "exports_flash.csv", FLASH_HEADER, rows,
            ["feed", "yyyymm", "period_label", "item_name"])
        print(f"{feed} {start_iso}..{end_iso}: {len(rows)} rows fetched, {added} new")
        added_total += added
        time.sleep(1.0)
    return added_total


def flash_backfill(start_iso: str, end_iso: str) -> None:
    """Backfill history in one-year chunks (API range limits unknown; safe)."""
    year = int(start_iso[:4])
    while year <= int(end_iso[:4]):
        chunk_start = start_iso if year == int(start_iso[:4]) else f"{year}-01"
        chunk_end = end_iso if year == int(end_iso[:4]) else f"{year}-12"
        fetch_flash(chunk_start, chunk_end)
        year += 1
        time.sleep(2.0)


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd = argv[0]
    if cmd == "monthly":
        fetch_monthly(argv[1], argv[2])
    elif cmd == "monthly-latest":
        today = dt.date.today()
        start = (today.replace(day=1) - dt.timedelta(days=95)).replace(day=1)
        fetch_monthly(start.strftime("%Y-%m"), today.strftime("%Y-%m"))
    elif cmd == "flash":
        if len(argv) >= 3:
            fetch_flash(argv[1], argv[2])
        else:
            fetch_flash()
    elif cmd == "flash-backfill":
        flash_backfill(argv[1], argv[2])
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
