"""U.S. Census Bureau international-trade fetcher (free API key).

The U.S. side of the optical-interconnect and semiconductor-equipment chain:
monthly imports and exports at 6- or 10-digit HTS by partner country, from
the Census International Trade API (CBP collects the entries, Census
compiles them; USITC DataWeb only redistributes the same table).

Sources (documented; the sandbox cannot reach either host, so the first
GitHub Actions run captures the payloads under data/us/raw/):
  imports: https://api.census.gov/data/timeseries/intltrade/imports/hs
  exports: https://api.census.gov/data/timeseries/intltrade/exports/hs
    - get=<variables>&I_COMMODITY=<code>&COMM_LVL=HS10&YEAR=2026&MONTH=07&key=...
    - JSON: a list of rows, first row = column names; CTY_CODE "-" is the
      all-countries total; SUMMARY_LVL separates countries from groupings.
    - HTTP 204 = no rows (unpublished month or no trade); HTTP 400 = a bad
      variable, named in the body.
  HTS descriptions: https://hts.usitc.gov/reststop/searchByNumber?query=...
    (keyless JSON, snapshotted so a renumbering is visible in the repo).

Release lag is 34-36 days: July data on Sept 3, August on Oct 6. History
from 2013-01. Values are U.S. dollars; imports carry both general value
(GEN_VAL_MO, all arrivals) and consumption value (CON_VAL_MO).

Output (append-only, first print wins):
  data/us/trade_monthly_hs.csv — one row per (month, direction, code, country)
  data/us/hts_codes.csv        — HTS descriptions and units per configured code

Usage:
    CENSUS_API_KEY=... python -m signals.us_census monthly           # last 4 published months
    CENSUS_API_KEY=... python -m signals.us_census monthly 2024-01 2026-07
    CENSUS_API_KEY=... python -m signals.us_census backfill 2013-01 2026-07
    python -m signals.us_census hts                                  # keyless snapshot
    python -m signals.us_census reparse                              # rebuild from raw
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

from .common import (CONFIG_DIR, DATA_DIR, USER_AGENT, append_dedup_csv, fmt,
                     month_range, parse_number, write_csv)

OUT_DIR = DATA_DIR / "us"
RAW_DIR = OUT_DIR / "raw"

TRADE_HEADER = ["yyyymm", "imex", "code", "comm_lvl", "cty_code", "cty_name",
                "summary_lvl", "value_usd", "value_cons_usd", "qty1", "unit1",
                "air_value_usd", "vessel_value_usd", "description", "extra_json",
                "retrieved_at"]
TRADE_KEY = ["yyyymm", "imex", "code", "cty_code"]
HTS_HEADER = ["code", "htsno", "description", "unit1", "unit2", "general", "retrieved_at"]

VALUE_FIELDS = ("GEN_VAL_MO", "ALL_VAL_MO")
CONS_FIELDS = ("CON_VAL_MO",)
QTY_FIELDS = ("GEN_QY1_MO", "QTY_1_MO", "CON_QY1_MO")
DESC_FIELDS = ("I_COMMODITY_SDESC", "E_COMMODITY_SDESC", "I_COMMODITY_LDESC",
               "E_COMMODITY_LDESC")


def _load_config() -> dict:
    return json.loads((CONFIG_DIR / "us_endpoints.json").read_text("utf-8"))


def _api_key() -> str:
    key = os.environ.get("CENSUS_API_KEY", "").strip()
    if not key:
        print("NOTICE: CENSUS_API_KEY not set — skipping U.S. Census fetch. "
              "Register free at https://api.census.gov/data/key_signup.html.")
        raise SystemExit(0)
    return key


def _save_raw(name: str, content: bytes) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / name).write_bytes(content)


def _redact(text: str, key: str) -> str:
    return text.replace(key, "<key>") if key else text


# --- Parsing ------------------------------------------------------------------

def parse_census_rows(payload, imex: str, code: str, comm_lvl: str, yyyymm: str,
                      retrieved_at: str) -> list[dict]:
    """Normalise the Census list-of-lists JSON into long rows.

    Column names come from the first row, so variable renames or reorderings
    only change which fields land in extra_json, never the row keys.
    """
    if not isinstance(payload, list) or len(payload) < 2:
        return []
    header = [str(h) for h in payload[0]]
    rows: list[dict] = []
    for rec in payload[1:]:
        fields = {header[i]: ("" if v is None else str(v)) for i, v in enumerate(rec)
                  if i < len(header)}
        cty_code = fields.get("CTY_CODE", "").strip()
        if not cty_code:
            continue

        def first(names: tuple[str, ...]) -> str:
            for name in names:
                if fields.get(name, "") not in ("", None):
                    return fields[name]
            return ""

        value = parse_number(first(VALUE_FIELDS))
        if value is None:
            continue
        qty = parse_number(first(QTY_FIELDS))
        if value == 0 and not qty:
            continue  # Census lists every partner; zero-trade rows carry nothing
        rows.append({
            "yyyymm": yyyymm, "imex": imex, "code": code, "comm_lvl": comm_lvl,
            "cty_code": cty_code, "cty_name": fields.get("CTY_NAME", "").strip(),
            "summary_lvl": fields.get("SUMMARY_LVL", "").strip(),
            "value_usd": fmt(value),
            "value_cons_usd": fmt(parse_number(first(CONS_FIELDS))),
            "qty1": fmt(qty),
            "unit1": fields.get("UNIT_QY1", "").strip(),
            "air_value_usd": fmt(parse_number(fields.get("AIR_VAL_MO"))),
            "vessel_value_usd": fmt(parse_number(fields.get("VES_VAL_MO"))),
            "description": first(DESC_FIELDS).strip(),
            "extra_json": json.dumps(fields, ensure_ascii=False, sort_keys=True),
            "retrieved_at": retrieved_at,
        })
    return rows


BAD_VAR_RE = re.compile(r"(?:unknown|invalid|not (?:a )?valid)[^A-Za-z0-9_]*(?:variable|predicate)?[^A-Za-z0-9_]*'?([A-Z][A-Z0-9_]{2,})", re.IGNORECASE)


def bad_variable(error_text: str, requested: list[str]) -> str:
    """Name of the requested variable a Census 400 body complains about."""
    for name in requested:
        if re.search(rf"\b{re.escape(name)}\b", error_text):
            return name
    match = BAD_VAR_RE.search(error_text)
    return match.group(1) if match and match.group(1) in requested else ""


def parse_hts_payload(payload, code: str, retrieved_at: str) -> list[dict]:
    items = payload.get("HTSDataSet") if isinstance(payload, dict) else payload
    rows: list[dict] = []
    for item in items or []:
        if not isinstance(item, dict) or not item.get("htsno"):
            continue
        # The live exportList payload carries units as a list ("units": ["No."]);
        # older docs show unit1/unit2 scalars, kept as a fallback.
        units = item.get("units")
        if not isinstance(units, list):
            units = [item.get("unit1"), item.get("unit2")]
        units = [str(u or "").strip() for u in units] + ["", ""]
        rows.append({
            "code": code, "htsno": str(item.get("htsno", "")).strip(),
            "description": re.sub(r"\s+", " ", str(item.get("description", ""))).strip(),
            "unit1": units[0],
            "unit2": units[1],
            "general": str(item.get("general", "") or "").strip(),
            "retrieved_at": retrieved_at,
        })
    return rows


# --- Fetching -------------------------------------------------------------------

def _get(url: str, params: dict, key: str, timeout: float = 90.0) -> requests.Response:
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, timeout=timeout,
                                headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        except (requests.ConnectionError, requests.Timeout) as err:
            if attempt == 2:
                raise RuntimeError(f"GET {url} failed: {err}") from err
            time.sleep(2.0 * (2 ** attempt))
            continue
        if resp.status_code in (429, 500, 502, 503, 504) and attempt < 2:
            time.sleep(2.0 * (2 ** attempt))
            continue
        return resp
    raise RuntimeError(f"GET {url}: exhausted retries")


def _dotted(code: str) -> str:
    digits = code.replace(".", "")
    parts = [digits[:4], digits[4:6], digits[6:8], digits[8:10]]
    return ".".join(p for p in parts if p)


def fetch_hts_codes() -> int:
    """Keyless snapshot of HTS descriptions for every configured code.

    Tries each configured endpoint template in order (the export-by-range
    endpoint is the documented one; keyword search is the fallback) and
    keeps the first that returns JSON rows for the code."""
    cfg = _load_config()
    retrieved_at = dt.date.today().isoformat()
    codes = sorted({c for section in ("imports", "exports")
                    for c in cfg["codes"][section] if not c.startswith("_")})
    rows: list[dict] = []
    problems: list[str] = []
    for code in codes:
        got: list[dict] = []
        last = ""
        for template in cfg["hts_api"]["url_templates"]:
            url = template.format(code=_dotted(code), code6=_dotted(code[:6]))
            resp = _get(url, {}, "")
            _save_raw(f"hts_{code}.json", resp.content)
            last = f"HTTP {resp.status_code}"
            if resp.status_code != 200:
                continue
            try:
                got = parse_hts_payload(resp.json(), code, retrieved_at)
            except ValueError:
                last = "not JSON"
                continue
            if got:
                break
        if got:
            rows += got
        else:
            problems.append(f"{code}: {last}")
        time.sleep(0.5)
    if rows:
        write_csv(OUT_DIR / "hts_codes.csv", HTS_HEADER,
                  [[r[c] for c in HTS_HEADER] for r in rows])
        print(f"hts_codes.csv: {len(rows)} rows for {len(codes)} codes")
    if problems:
        raise RuntimeError("HTS API: " + "; ".join(problems))
    return len(rows)


def _default_range(today: dt.date, months: int = 4) -> tuple[str, str]:
    """Latest month likely published (two months back) and `months` before it."""
    end = (today.replace(day=1) - dt.timedelta(days=1)).replace(day=1)
    end = (end - dt.timedelta(days=1)).replace(day=1)
    start = end
    for _ in range(months - 1):
        start = (start - dt.timedelta(days=1)).replace(day=1)
    return start.strftime("%Y-%m"), end.strftime("%Y-%m")


def fetch_month(imex: str, code: str, month: str, key: str, cfg: dict,
                retrieved_at: str) -> list[dict]:
    """One Census call: one code, one month, every country. Drops a variable
    the API rejects and retries once; 204 means no rows."""
    census = cfg["census"]
    url = census["imports_url"] if imex == "I" else census["exports_url"]
    get_vars = list(census["imports_get"] if imex == "I" else census["exports_get"])
    comm_lvl = census["comm_lvl_by_length"].get(str(len(code)), "HS10")
    comm_param = "I_COMMODITY" if imex == "I" else "E_COMMODITY"
    year, mon = month.split("-")
    for attempt in range(2):
        params = {"get": ",".join(get_vars), comm_param: code, "COMM_LVL": comm_lvl,
                  "YEAR": year, "MONTH": mon, "key": key}
        resp = _get(url, params, key)
        raw_name = f"census_{imex}_{code}_{month}.json"
        if resp.status_code == 204 or not resp.content.strip():
            _save_raw(raw_name, b"[]")
            return []
        if resp.status_code == 400:
            text = _redact(resp.text, key)
            _save_raw(raw_name.replace(".json", ".error.txt"), text.encode())
            bad = bad_variable(text, get_vars)
            if bad and attempt == 0:
                print(f"  {imex} {code} {month}: API rejected {bad}; retrying without it")
                get_vars.remove(bad)
                continue
            raise RuntimeError(f"census {imex} {code} {month}: HTTP 400: {text[:300]}")
        if resp.status_code != 200:
            raise RuntimeError(f"census {imex} {code} {month}: HTTP {resp.status_code}")
        _save_raw(raw_name, resp.content)
        try:
            payload = resp.json()
        except ValueError as err:
            raise RuntimeError(f"census {imex} {code} {month}: not JSON "
                               f"(saved data/us/raw/{raw_name})") from err
        rows = parse_census_rows(payload, imex, code, comm_lvl, month, retrieved_at)
        if not rows:
            raise RuntimeError(f"census {imex} {code} {month}: 0 rows parsed from a 200 "
                               f"(saved data/us/raw/{raw_name})")
        return rows
    return []


def fetch_monthly(start_iso: str | None = None, end_iso: str | None = None) -> int:
    cfg = _load_config()
    key = _api_key()
    today = dt.date.today()
    default_start, default_end = _default_range(today)
    start_iso, end_iso = start_iso or default_start, end_iso or default_end
    retrieved_at = today.isoformat()
    added_total = 0
    problems: list[str] = []
    for month in month_range(start_iso, end_iso):
        month_rows: list[dict] = []
        for imex, section in (("I", "imports"), ("E", "exports")):
            for code in cfg["codes"][section]:
                if code.startswith("_"):
                    continue
                try:
                    rows = fetch_month(imex, code, month, key, cfg, retrieved_at)
                except RuntimeError as err:
                    problems.append(str(err))
                    continue
                if not rows:
                    print(f"  {imex} {code} {month}: no rows (not published or no trade)")
                    continue
                print(f"  {imex} {code} {month}: {len(rows)} rows")
                month_rows += rows
                time.sleep(0.5)
        # One store rewrite per month, not per (code, month): the store is
        # tens of thousands of rows and append_dedup_csv rewrites it whole.
        if month_rows:
            added = append_dedup_csv(OUT_DIR / "trade_monthly_hs.csv", TRADE_HEADER,
                                     month_rows, TRADE_KEY)
            print(f"  {month}: {len(month_rows)} rows fetched, {added} new")
            added_total += added
    if problems:
        raise RuntimeError("census: " + "; ".join(problems[:10])
                           + (f"; +{len(problems) - 10} more" if len(problems) > 10 else ""))
    return added_total


def reparse_hts() -> None:
    """Rebuild data/us/hts_codes.csv from the raw hts_*.json on disk."""
    retrieved_at = dt.date.today().isoformat()
    rows: list[dict] = []
    for path in sorted(RAW_DIR.glob("hts_*.json")):
        match = re.fullmatch(r"hts_(\d+)\.json", path.name)
        if not match:
            continue
        try:
            payload = json.loads(path.read_bytes() or b"[]")
        except ValueError:
            continue
        rows += parse_hts_payload(payload, match.group(1), retrieved_at)
    if rows:
        write_csv(OUT_DIR / "hts_codes.csv", HTS_HEADER,
                  [[r[c] for c in HTS_HEADER] for r in rows])
        print(f"hts_codes.csv: rebuilt with {len(rows)} rows")


def reparse() -> None:
    """Rebuild data/us/trade_monthly_hs.csv (and hts_codes.csv) from the raw
    JSON on disk. Row order follows the raw file names, so a reparse after a
    fetch reorders the store without changing its content."""
    reparse_hts()
    retrieved_at = dt.date.today().isoformat()
    cfg = _load_config()
    rows: list[dict] = []
    for path in sorted(RAW_DIR.glob("census_*.json")):
        match = re.fullmatch(r"census_([EI])_(\w+)_(\d{4}-\d{2})\.json", path.name)
        if not match:
            continue
        imex, code, month = match.groups()
        comm_lvl = cfg["census"]["comm_lvl_by_length"].get(str(len(code)), "HS10")
        try:
            payload = json.loads(path.read_bytes() or b"[]")
        except ValueError:
            continue
        rows += parse_census_rows(payload, imex, code, comm_lvl, month, retrieved_at)
    path = OUT_DIR / "trade_monthly_hs.csv"
    if rows:
        write_csv(path, TRADE_HEADER, [])
        added = append_dedup_csv(path, TRADE_HEADER, rows, TRADE_KEY)
        print(f"trade_monthly_hs.csv: rebuilt with {added} rows")
    elif path.exists():
        path.unlink()
        print("trade_monthly_hs.csv: removed (no raw payloads)")


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd = argv[0]
    if cmd == "monthly":
        if len(argv) >= 3:
            fetch_monthly(argv[1], argv[2])
        else:
            fetch_monthly()
    elif cmd == "backfill":
        start, end = argv[1], argv[2]
        year = int(start[:4])
        while year <= int(end[:4]):
            chunk_start = start if year == int(start[:4]) else f"{year}-01"
            chunk_end = end if year == int(end[:4]) else f"{year}-12"
            print(f"--- chunk {chunk_start}..{chunk_end}")
            try:
                fetch_monthly(chunk_start, chunk_end)
            except Exception as err:  # noqa: BLE001 - one chunk must not abort the walk
                print(f"    chunk failed ({type(err).__name__}: {err}); continuing")
            year += 1
            time.sleep(5.0)
    elif cmd == "hts":
        fetch_hts_codes()
    elif cmd == "reparse":
        reparse()
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
