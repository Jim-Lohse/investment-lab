"""Korea Customs Service (KCS) export statistics fetcher.

Korea publishes trade data three times a month — days 1-10 on the 11th,
days 1-20 on the 21st, and the full month on the 1st of the next month —
with a semiconductor breakout. This is the fastest broad public read on
global tech demand.

Sources (all free; data.go.kr requires a no-cost registered service key):
  - Monthly item-level trade by HS code (stable, documented):
      https://apis.data.go.kr/1220000/Itemtrade/getItemtradeList
  - 10/20-day provisional statistics by major item: data.go.kr KCS datasets
    (endpoint paths configured in config/korea_endpoints.json; the numbers
    are also on https://tradedata.go.kr and in KCS press releases at
    https://www.customs.go.kr — the press release is the primary record).

Normalized output (append-only, deduplicated):
  data/korea/trade_monthly.csv   — monthly HS-code series (USD)
  data/korea/exports_flash.csv   — 10/20-day provisional series (USD k)
Raw API responses are kept verbatim under data/korea/raw/ so a field-name
revision never loses data.

Usage:
    DATA_GO_KR_API_KEY=... python -m signals.korea_customs monthly 2024-01 2026-07
    DATA_GO_KR_API_KEY=... python -m signals.korea_customs monthly-latest
    DATA_GO_KR_API_KEY=... python -m signals.korea_customs flash
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from .common import CONFIG_DIR, DATA_DIR, append_dedup_csv, http_get

OUT_DIR = DATA_DIR / "korea"
RAW_DIR = OUT_DIR / "raw"

MONTHLY_HEADER = ["year_month", "hs_code", "item_name",
                  "export_usd", "import_usd", "balance_usd", "retrieved_at"]
FLASH_HEADER = ["period_start", "period_end", "period_type", "item_code",
                "item_name", "export_usd_k", "import_usd_k", "retrieved_at"]

# Candidate tag names seen across KCS API generations; parsed defensively.
TAGS_YEAR = ("year", "priodTitle", "aggrgtDt", "prdDe")
TAGS_HS = ("hsCd", "statCd", "hsSgn", "itemCd")
TAGS_NAME = ("statKor", "statCdCntnKor1", "itemNm", "korePrlstNm")
TAGS_EXP = ("expDlr", "expUsdAmt", "expAmt")
TAGS_IMP = ("impDlr", "impUsdAmt", "impAmt")
TAGS_BAL = ("balPayments", "balAmt")


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


def _current_flash_period(today: dt.date) -> tuple[dt.date, dt.date, str] | None:
    """Which flash window is freshly published today? (11th->D10, 21st->D20,
    1st-3rd -> previous FULL month). Returns None outside publish windows."""
    if 11 <= today.day <= 13:
        start = today.replace(day=1)
        return start, start.replace(day=10), "D10"
    if 21 <= today.day <= 23:
        start = today.replace(day=1)
        return start, start.replace(day=20), "D20"
    if today.day <= 3:
        last_of_prev = today.replace(day=1) - dt.timedelta(days=1)
        return last_of_prev.replace(day=1), last_of_prev, "FULL"
    return None


def parse_flash_xml(content: bytes, period_start: str, period_end: str,
                    period_type: str, retrieved_at: str) -> list[dict]:
    root = ET.fromstring(content)
    _check_api_error(root, "flash 10-day stats")
    rows = []
    for item in root.iter("item"):
        name = _first_text(item, TAGS_NAME)
        exp = _num(_first_text(item, TAGS_EXP))
        imp = _num(_first_text(item, TAGS_IMP))
        if not (name or exp or imp):
            continue
        rows.append({
            "period_start": period_start,
            "period_end": period_end,
            "period_type": period_type,
            "item_code": _first_text(item, TAGS_HS),
            "item_name": name,
            "export_usd_k": exp,
            "import_usd_k": imp,
            "retrieved_at": retrieved_at,
        })
    return rows


def fetch_flash(force_period: tuple[str, str, str] | None = None) -> int:
    cfg = _load_config()
    period = force_period or _current_flash_period(dt.date.today())
    if period is None:
        print("No flash window publishing today (runs matter on the 1st-3rd, "
              "11th-13th, 21st-23rd); nothing to do.")
        return 0
    if force_period:
        start_s, end_s, ptype = force_period
    else:
        start_d, end_d, ptype = period  # type: ignore[misc]
        start_s, end_s = start_d.isoformat(), end_d.isoformat()

    key = _service_key()
    retrieved_at = dt.date.today().isoformat()
    added_total = 0
    for feed in ("flash_exports_10day", "flash_imports_10day"):
        feed_cfg = cfg[feed]
        if not feed_cfg.get("url"):
            print(f"NOTICE: {feed} endpoint not configured yet "
                  f"(see signals/config/korea_endpoints.json '_setup'); skipping.")
            continue
        params = {name: template.format(
                      service_key=key,
                      period_start_yyyymmdd=start_s.replace("-", ""),
                      period_end_yyyymmdd=end_s.replace("-", ""))
                  for name, template in feed_cfg["params"].items()}
        resp = http_get(feed_cfg["url"], params=params)
        _save_raw(f"{feed}_{end_s}.xml", resp.content)
        rows = parse_flash_xml(resp.content, start_s, end_s, ptype, retrieved_at)
        added = append_dedup_csv(OUT_DIR / "exports_flash.csv", FLASH_HEADER, rows,
                                 ["period_start", "period_end", "item_code", "item_name"])
        print(f"{feed} {start_s}..{end_s}: {len(rows)} rows fetched, {added} new")
        added_total += added
    return added_total


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
        if len(argv) == 4:  # explicit: start end D10|D20|FULL
            fetch_flash((argv[1], argv[2], argv[3]))
        else:
            fetch_flash()
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
