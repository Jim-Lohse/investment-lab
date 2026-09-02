"""Japan Ministry of Finance / Customs trade-statistics fetcher (no key needed).

Japan is the supply side of the AI build-out: semiconductor-equipment and
materials exports (HS 8486, 3818, 2804.61) plus optical components (8541,
8517, 9001, 9013). MOF publishes on the same three-revision cadence as
Korea — first 10 days, first 20 days, monthly provisional, then detailed —
so the by-window YoY logic from the Korea leg carries over unchanged.

Sources (all free, no registration; verified 2026-09-02):
  1. Press-release XML on customs.go.jp:
       https://www.customs.go.jp/toukei/shinbun/trade-st_e/<YYYY>/<YYYYMM><stage>e.xml
     stage 1 = first 10 days, 2 = first 20 days, 4 = monthly provisional,
     5 = exports detailed / imports 9-digit provisional. Index:
       https://www.customs.go.jp/toukei/shinbun/happyou_e.htm
  2. Time-series CSVs (thousand yen, monthly from 1979/1988):
       https://www.customs.go.jp/toukei/suii/html/data/d41ma.csv (world total)
  3. e-Stat monthly "Values by Commodity" CSV (9-digit statistical code,
     thousand yen), linked from the listing page and downloaded as
       https://www.e-stat.go.jp/stat-search/file-download?statInfId=...&fileKind=1

The XML schema of the press release is not documented and this module was
built where customs.go.jp is unreachable, so the XML parser is deliberately
schema-tolerant: every record's fields are kept verbatim in an extra_json
column, the raw payload is saved under data/japan/raw/, and zero parsed rows
is an error rather than an empty file. A `capture` command snapshots every
source for parser development, exactly as the Korea leg did.

Output (append-only, first print wins):
  data/japan/press_release.csv   — 10/20-day and monthly press-release rows
  data/japan/time_series.csv     — long-format monthly series from the CSVs
  data/japan/trade_monthly_hs.csv — monthly value/quantity per 9-digit code
                                    for the configured HS prefixes

Usage:
    python -m signals.japan_customs flash            # prev + current month, all stages
    python -m signals.japan_customs flash 2026-06 2026-08
    python -m signals.japan_customs flash-backfill 2021-01 2026-08
    python -m signals.japan_customs timeseries
    python -m signals.japan_customs estat            # latest monthly HS-level CSVs
    python -m signals.japan_customs capture          # snapshot everything raw
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

from .common import (CONFIG_DIR, DATA_DIR, USER_AGENT, append_dedup_csv, fmt,
                     http_get, month_range, parse_number)

OUT_DIR = DATA_DIR / "japan"
RAW_DIR = OUT_DIR / "raw"
PAGES_DIR = RAW_DIR / "pages"

PRESS_HEADER = ["yyyymm", "period_type", "stage", "lang", "section", "imex",
                "name", "value", "yoy_pct", "extra_json", "retrieved_at"]
TS_HEADER = ["series", "imex", "area", "code", "name", "yyyymm", "value_jpy_k",
             "quantity", "retrieved_at"]
HS_HEADER = ["yyyymm", "imex", "hs_code", "stage", "value_jpy_k", "quantity1",
             "unit1", "quantity2", "unit2", "source_file", "retrieved_at"]

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _load_config() -> dict:
    return json.loads((CONFIG_DIR / "japan_endpoints.json").read_text("utf-8"))


def _save_raw(name: str, content: bytes, subdir: Path = RAW_DIR) -> None:
    subdir.mkdir(parents=True, exist_ok=True)
    (subdir / name).write_bytes(content)


def _get_optional(url: str, timeout: float = 60.0) -> requests.Response | None:
    """GET that returns None on 404 (an unpublished window is normal, not an
    error) and falls back to the shared backoff helper on transient failures."""
    try:
        resp = requests.get(url, timeout=timeout,
                            headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    except (requests.ConnectionError, requests.Timeout):
        return http_get(url, retries=2, timeout=timeout)
    if resp.status_code == 404:
        return None
    if resp.status_code in (429, 500, 502, 503, 504):
        return http_get(url, retries=2, timeout=timeout)
    resp.raise_for_status()
    return resp


def _decode(content: bytes) -> str:
    """MOF files are Shift_JIS or UTF-8 depending on age; try both."""
    for enc in ("utf-8-sig", "cp932", "euc_jp"):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


# --- Press-release XML (10/20-day + monthly) --------------------------------

def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def flatten_xml_records(root: ET.Element) -> list[tuple[str, dict]]:
    """Schema-tolerant record extraction.

    A record is any element that carries at least two scalar fields, where a
    field is an attribute or a leaf child element. Fields are stored under
    their tag/attribute names; a leaf child's own attributes are stored as
    ``tag@attr``. Returns (path, fields) so the section an item came from
    (area table vs. commodity table) is recoverable from the element path.
    """
    records: list[tuple[str, dict]] = []

    def walk(elem: ET.Element, path: str) -> None:
        tag = _strip_ns(elem.tag)
        here = f"{path}/{tag}"
        fields: dict[str, str] = {k: v.strip() for k, v in elem.attrib.items()}
        text = (elem.text or "").strip()
        if text and not len(elem):
            fields["#text"] = text
        for child in elem:
            if len(child):
                continue
            ctag = _strip_ns(child.tag)
            ctext = (child.text or "").strip()
            if ctext or not child.attrib:
                fields[ctag] = ctext
            for k, v in child.attrib.items():
                fields[f"{ctag}@{k}"] = v.strip()
        if len(fields) >= 2:
            records.append((here, fields))
        for child in elem:
            if len(child) or (child.attrib and len(fields) < 2):
                walk(child, here)

    walk(root, "")
    return records


NAME_HINTS = ("name", "title", "item", "commodity", "area", "country", "label",
              "品目", "品名", "国", "地域", "名")
VALUE_HINTS = ("value", "amount", "amt", "価額", "金額", "額")
YOY_HINTS = ("rate", "ratio", "change", "yoy", "伸率", "伸び率", "前年")
IMPORT_HINTS = ("import", "imp", "輸入")
EXPORT_HINTS = ("export", "exp", "輸出")


def _pick(fields: dict, hints: tuple[str, ...], numeric: bool | None) -> tuple[str, str]:
    """First (key, value) whose key mentions a hint and whose value matches
    the numeric expectation (None = don't care)."""
    for key, val in fields.items():
        lk = key.lower()
        if not any(h in lk for h in hints):
            continue
        is_num = parse_number(val) is not None
        if numeric is None or is_num == numeric:
            return key, val
    return "", ""


def normalize_press_records(records: list[tuple[str, dict]], yyyymm: str,
                            period_type: str, stage: str, lang: str,
                            retrieved_at: str) -> list[dict]:
    """Turn flattened records into long rows. Name/value/yoy detection uses
    field-name hints and falls back to 'first non-numeric field' / 'largest
    numeric field', so an unexpected schema still yields usable rows while
    extra_json keeps every field for a later exact parser."""
    rows: list[dict] = []
    for path, fields in records:
        _, name = _pick(fields, NAME_HINTS, numeric=False)
        if not name:
            non_numeric = [v for v in fields.values()
                           if v and parse_number(v) is None and not v.isdigit()]
            name = non_numeric[0] if non_numeric else ""
        numerics = [(k, parse_number(v)) for k, v in fields.items()
                    if parse_number(v) is not None]
        if not name or not numerics:
            continue
        _, value = _pick(fields, VALUE_HINTS, numeric=True)
        if not value:
            value = fmt(max(v for _, v in numerics))
        _, yoy = _pick(fields, YOY_HINTS, numeric=True)
        lpath = path.lower()
        imex = ""
        if any(h in lpath for h in IMPORT_HINTS):
            imex = "I"
        elif any(h in lpath for h in EXPORT_HINTS):
            imex = "E"
        rows.append({
            "yyyymm": yyyymm,
            "period_type": period_type,
            "stage": stage,
            "lang": lang,
            "section": path.strip("/"),
            "imex": imex,
            "name": name,
            "value": fmt(parse_number(value)),
            "yoy_pct": fmt(parse_number(yoy)) if yoy else "",
            "extra_json": json.dumps(fields, ensure_ascii=False, sort_keys=True),
            "retrieved_at": retrieved_at,
        })
    return rows


def parse_press_xml(content: bytes, yyyymm: str, period_type: str, stage: str,
                    lang: str, retrieved_at: str) -> list[dict]:
    root = ET.fromstring(content)
    return normalize_press_records(flatten_xml_records(root), yyyymm,
                                   period_type, stage, lang, retrieved_at)


def press_url(cfg: dict, yyyymm: str, stage: str, lang: str) -> str:
    pr = cfg["press_release"]
    lang_cfg = pr["languages"][lang]
    return pr["url_template"].format(year=yyyymm[:4], yyyymm=yyyymm,
                                     stage=stage, **lang_cfg)


def fetch_press_release(start_iso: str | None = None, end_iso: str | None = None,
                        stages: list[str] | None = None,
                        langs: tuple[str, ...] = ("en",)) -> int:
    """Fetch every press-release window in a month range.

    Unpublished windows 404 and are skipped; a published window that parses
    to zero rows raises after saving the raw file, so a schema change is
    loud rather than an empty CSV.
    """
    cfg = _load_config()
    today = dt.date.today()
    if end_iso is None:
        end_iso = today.strftime("%Y-%m")
    if start_iso is None:
        start_iso = (today.replace(day=1) - dt.timedelta(days=1)).strftime("%Y-%m")
    stage_map = cfg["press_release"]["stages"]
    stages = stages or list(stage_map)
    retrieved_at = today.isoformat()

    added_total = 0
    unparsed: list[str] = []
    for month in month_range(start_iso, end_iso):
        yyyymm = month.replace("-", "")
        for stage in stages:
            for lang in langs:
                url = press_url(cfg, yyyymm, stage, lang)
                resp = _get_optional(url)
                if resp is None:
                    print(f"  {yyyymm} stage {stage} ({lang}): not published")
                    continue
                raw_name = f"press_{yyyymm}{stage}{lang}.xml"
                _save_raw(raw_name, resp.content)
                try:
                    rows = parse_press_xml(resp.content, month, stage_map[stage],
                                           stage, lang, retrieved_at)
                except ET.ParseError as err:
                    unparsed.append(f"{raw_name}: {err}")
                    continue
                if not rows:
                    unparsed.append(f"{raw_name}: 0 rows")
                    continue
                added = append_dedup_csv(
                    OUT_DIR / "press_release.csv", PRESS_HEADER, rows,
                    ["yyyymm", "stage", "lang", "section", "name"])
                print(f"  {yyyymm} stage {stage} ({lang}): {len(rows)} rows, {added} new")
                added_total += added
                time.sleep(1.0)
    if unparsed:
        raise RuntimeError(
            "press release: payloads saved under data/japan/raw/ but not parsed: "
            + "; ".join(unparsed))
    return added_total


# --- Time-series CSVs -------------------------------------------------------

JP_MONTH_RE = re.compile(r"(\d{4})\s*[年/.-]\s*(\d{1,2})\s*月?")


def _yyyymm_from_label(label: str) -> str:
    """'2026年7月', '2026/07', '202607', 'Jul.2026' -> '2026-07'."""
    label = label.strip()
    match = JP_MONTH_RE.search(label)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}"
    match = re.fullmatch(r"(\d{4})(\d{2})", label)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    match = re.search(r"([A-Za-z]{3})[a-z]*\.?\s*(\d{4})", label)
    if match and match.group(1).title() in MONTHS:
        return f"{int(match.group(2)):04d}-{MONTHS.index(match.group(1).title()) + 1:02d}"
    return ""


def parse_time_series_csv(text: str, series: str, retrieved_at: str) -> list[dict]:
    """Long-format rows from a MOF time-series CSV.

    Two layouts are handled without knowing which one a file uses: a wide
    table whose header names months (one row per series, one column per
    month) and a long table with a year/month column per row. Everything
    that cannot be classified is skipped rather than guessed.
    """
    reader = list(csv.reader(io.StringIO(text)))
    rows: list[dict] = []
    if not reader:
        return rows
    header = [h.strip() for h in reader[0]]
    month_cols = {i: _yyyymm_from_label(h) for i, h in enumerate(header)}
    month_cols = {i: m for i, m in month_cols.items() if m}

    if len(month_cols) >= 3:  # wide layout
        label_cols = [i for i in range(len(header)) if i not in month_cols]
        for rec in reader[1:]:
            if not any(cell.strip() for cell in rec):
                continue
            labels = [rec[i].strip() for i in label_cols if i < len(rec)]
            imex = ""
            joined = " ".join(labels + [h for i, h in enumerate(header) if i in label_cols])
            if any(h in joined for h in ("輸入", "Import", "IMPORT")):
                imex = "I"
            elif any(h in joined for h in ("輸出", "Export", "EXPORT")):
                imex = "E"
            code = next((l for l in labels if re.fullmatch(r"\d{1,9}", l)), "")
            name = next((l for l in labels if l and l != code and parse_number(l) is None), "")
            for i, month in month_cols.items():
                if i >= len(rec):
                    continue
                value = parse_number(rec[i])
                if value is None:
                    continue
                rows.append({
                    "series": series, "imex": imex, "area": "",
                    "code": code, "name": name, "yyyymm": month,
                    "value_jpy_k": fmt(value), "quantity": "",
                    "retrieved_at": retrieved_at,
                })
        return rows

    # long layout: find a column whose cells look like year-months
    period_col = None
    for i in range(len(header)):
        sample = [rec[i] for rec in reader[1:20] if i < len(rec)]
        if sample and sum(bool(_yyyymm_from_label(s)) for s in sample) >= len(sample) * 0.6:
            period_col = i
            break
    if period_col is None:
        return rows
    value_cols = [i for i, h in enumerate(header)
                  if any(k in h.lower() for k in ("value", "価額", "金額", "額"))]
    qty_cols = [i for i, h in enumerate(header)
                if any(k in h.lower() for k in ("quantity", "数量"))]
    text_cols = [i for i in range(len(header))
                 if i != period_col and i not in value_cols and i not in qty_cols]
    for rec in reader[1:]:
        if period_col >= len(rec):
            continue
        month = _yyyymm_from_label(rec[period_col])
        if not month:
            continue
        labels = [rec[i].strip() for i in text_cols if i < len(rec)]
        joined = " ".join(labels)
        imex = "I" if any(h in joined for h in ("輸入", "Import", "IMPORT", " 2")) else (
            "E" if any(h in joined for h in ("輸出", "Export", "EXPORT", " 1")) else "")
        code = next((l for l in labels if re.fullmatch(r"\d{1,9}", l)), "")
        name = next((l for l in labels if l and l != code and parse_number(l) is None), "")
        if value_cols:
            value = parse_number(rec[value_cols[0]]) if value_cols[0] < len(rec) else None
        else:
            nums = [parse_number(rec[i]) for i in range(len(rec)) if i != period_col]
            nums = [n for n in nums if n is not None]
            value = max(nums) if nums else None
        if value is None:
            continue
        qty = parse_number(rec[qty_cols[0]]) if qty_cols and qty_cols[0] < len(rec) else None
        rows.append({
            "series": series, "imex": imex, "area": "", "code": code,
            "name": name, "yyyymm": month, "value_jpy_k": fmt(value),
            "quantity": fmt(qty), "retrieved_at": retrieved_at,
        })
    return rows


def fetch_time_series() -> int:
    cfg = _load_config()["time_series"]
    retrieved_at = dt.date.today().isoformat()
    added_total = 0
    problems: list[str] = []
    for series, filename in cfg["files"].items():
        resp = _get_optional(cfg["base_url"] + filename)
        if resp is None:
            problems.append(f"{filename}: 404")
            continue
        _save_raw(filename, resp.content)
        rows = parse_time_series_csv(_decode(resp.content), series, retrieved_at)
        if not rows:
            problems.append(f"{filename}: 0 rows parsed")
            continue
        added = append_dedup_csv(OUT_DIR / "time_series.csv", TS_HEADER, rows,
                                 ["series", "imex", "code", "name", "yyyymm"])
        print(f"  {series} ({filename}): {len(rows)} rows, {added} new")
        added_total += added
        time.sleep(1.0)
    if problems:
        raise RuntimeError("time series: " + "; ".join(problems)
                           + " (raw files kept under data/japan/raw/)")
    return added_total


# --- e-Stat monthly HS-level CSV -------------------------------------------

STAT_ID_RE = re.compile(r"stat[_-]?inf[_-]?id=(\d{10,14})", re.IGNORECASE)
JP_MONTH_TITLE_RE = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月")


def parse_estat_listing(html: str) -> list[dict]:
    """Return [{stat_inf_id, yyyymm, title}] for every download link on an
    e-Stat listing page, newest first. The month is taken from the nearest
    'YYYY年M月' in the surrounding text; links without one are kept with an
    empty month so nothing is silently dropped."""
    found: dict[str, dict] = {}
    for match in STAT_ID_RE.finditer(html):
        sid = match.group(1)
        window = html[max(0, match.start() - 1500): match.end() + 1500]
        window_text = re.sub(r"<[^>]+>", " ", window)
        months = JP_MONTH_TITLE_RE.findall(window_text)
        yyyymm = ""
        if months:
            # Prefer the month mentioned closest before the link.
            before = re.sub(r"<[^>]+>", " ", html[max(0, match.start() - 1500): match.start()])
            prior = JP_MONTH_TITLE_RE.findall(before)
            y, m = (prior[-1] if prior else months[0])
            yyyymm = f"{int(y):04d}-{int(m):02d}"
        title_match = re.search(r"([^<>]*統計品別表[^<>]*)", window_text)
        title = title_match.group(1).strip() if title_match else ""
        entry = found.setdefault(sid, {"stat_inf_id": sid, "yyyymm": yyyymm, "title": title})
        if not entry["yyyymm"] and yyyymm:
            entry["yyyymm"] = yyyymm
        if not entry["title"] and title:
            entry["title"] = title
    return sorted(found.values(), key=lambda e: e["yyyymm"], reverse=True)


def parse_estat_commodity_csv(text: str, hs_prefixes: list[str], stage: str,
                              source_file: str, retrieved_at: str) -> list[dict]:
    """Rows for configured HS prefixes from a 統計品別表 CSV.

    Header (documented): Exp or Imp, Year, HS, Unit1, Unit2, Quantity1-Year,
    Quantity2-Year, Value-Year, then Quantity1-Jan, Quantity2-Jan, Value-Jan
    ... Value-Dec. Columns are resolved by name so reordering is harmless.
    """
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return []
    cols = {name.strip().lower(): name for name in reader.fieldnames}

    def col(*candidates: str) -> str | None:
        for cand in candidates:
            if cand.lower() in cols:
                return cols[cand.lower()]
        return None

    c_imex = col("Exp or Imp", "expimp", "imex")
    c_year = col("Year")
    c_hs = col("HS", "Code", "Commodity")
    c_unit1, c_unit2 = col("Unit1"), col("Unit2")
    if not (c_imex and c_year and c_hs):
        return []
    prefixes = [p.replace(".", "") for p in hs_prefixes]
    rows: list[dict] = []
    for rec in reader:
        hs = (rec.get(c_hs) or "").strip().strip("'\"")
        if not hs or not any(hs.startswith(p) for p in prefixes):
            continue
        imex_raw = (rec.get(c_imex) or "").strip()
        imex = "E" if imex_raw in ("1", "E", "Export", "輸出") else (
            "I" if imex_raw in ("2", "I", "Import", "輸入") else imex_raw)
        year = (rec.get(c_year) or "").strip()
        for idx, mon in enumerate(MONTHS, start=1):
            c_val = col(f"Value-{mon}")
            if not c_val:
                continue
            value = parse_number(rec.get(c_val))
            if value is None:
                continue
            q1 = parse_number(rec.get(col(f"Quantity1-{mon}") or ""))
            q2 = parse_number(rec.get(col(f"Quantity2-{mon}") or ""))
            if value == 0 and not q1 and not q2:
                continue  # month not yet published in this file
            rows.append({
                "yyyymm": f"{year}-{idx:02d}", "imex": imex, "hs_code": hs,
                "stage": stage, "value_jpy_k": fmt(value),
                "quantity1": fmt(q1), "unit1": (rec.get(c_unit1) or "").strip() if c_unit1 else "",
                "quantity2": fmt(q2), "unit2": (rec.get(c_unit2) or "").strip() if c_unit2 else "",
                "source_file": source_file, "retrieved_at": retrieved_at,
            })
    return rows


def fetch_estat(months_back: int = 1) -> int:
    """Download the newest 統計品別表 CSV(s) for exports and imports and keep
    the configured HS prefixes. One listing page + one CSV per direction."""
    cfg = _load_config()
    est = cfg["estat"]
    prefixes = [k for k in cfg["hs_codes"] if not k.startswith("_")]
    retrieved_at = dt.date.today().isoformat()
    added_total = 0
    problems: list[str] = []
    for imex, tclass2 in est["tclass2"].items():
        listing_url = est["listing_url_template"].format(tclass2=tclass2)
        resp = _get_optional(listing_url)
        if resp is None:
            problems.append(f"listing {imex}: 404")
            continue
        _save_raw(f"estat_listing_{imex}.html", resp.content, PAGES_DIR)
        entries = parse_estat_listing(_decode(resp.content))
        if not entries:
            problems.append(f"listing {imex}: no statInfId links found "
                            f"(saved data/japan/raw/pages/estat_listing_{imex}.html)")
            continue
        for entry in entries[:months_back]:
            url = est["download_url_template"].format(stat_inf_id=entry["stat_inf_id"])
            csv_resp = _get_optional(url)
            if csv_resp is None:
                problems.append(f"{imex} {entry['stat_inf_id']}: 404")
                continue
            fname = f"estat_{imex}_{entry['yyyymm'] or 'unknown'}_{entry['stat_inf_id']}.csv"
            _save_raw(fname, csv_resp.content)
            stage = "DETAILED" if "確報" in entry["title"] else (
                "PROV9" if "速報" in entry["title"] else "")
            rows = parse_estat_commodity_csv(_decode(csv_resp.content), prefixes,
                                             stage, fname, retrieved_at)
            if not rows:
                problems.append(f"{fname}: 0 rows for configured HS prefixes")
                continue
            added = append_dedup_csv(OUT_DIR / "trade_monthly_hs.csv", HS_HEADER, rows,
                                     ["yyyymm", "imex", "hs_code", "stage"])
            print(f"  e-Stat {imex} {entry['yyyymm']} ({entry['stat_inf_id']}): "
                  f"{len(rows)} rows, {added} new")
            added_total += added
            time.sleep(2.0)
    if problems:
        raise RuntimeError("e-Stat: " + "; ".join(problems))
    return added_total


# --- Capture ----------------------------------------------------------------

def capture() -> None:
    """Snapshot every source raw for parser development. Read-only GETs
    against static files; safe to run from CI where the hosts are reachable."""
    cfg = _load_config()
    today = dt.date.today()
    months = month_range((today.replace(day=1) - dt.timedelta(days=40)).strftime("%Y-%m"),
                         today.strftime("%Y-%m"))
    targets: dict[str, str] = dict(cfg["press_release"]["index_pages"])
    for month in months:
        yyyymm = month.replace("-", "")
        for stage in cfg["press_release"]["stages"]:
            for lang in ("en", "ja"):
                targets[f"press_{yyyymm}{stage}{lang}.xml"] = press_url(cfg, yyyymm, stage, lang)
    for series, filename in cfg["time_series"]["files"].items():
        targets[filename] = cfg["time_series"]["base_url"] + filename
    for imex, tclass2 in cfg["estat"]["tclass2"].items():
        targets[f"estat_listing_{imex}.html"] = cfg["estat"]["listing_url_template"].format(
            tclass2=tclass2)
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in targets.items():
        try:
            resp = _get_optional(url, timeout=60)
        except Exception as err:  # noqa: BLE001 - keep capturing the rest
            print(f"capture {name}: {type(err).__name__}: {err}")
            continue
        if resp is None:
            print(f"capture {name}: 404")
            continue
        out = name if "." in name else f"{name}.html"
        (PAGES_DIR / out).write_bytes(resp.content[:2_000_000])
        print(f"captured {out}: {len(resp.content)} bytes "
              f"{resp.headers.get('Content-Type', '')}")
        time.sleep(1.0)


# --- CLI --------------------------------------------------------------------

def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd = argv[0]
    if cmd == "flash":
        if len(argv) >= 3:
            fetch_press_release(argv[1], argv[2])
        else:
            fetch_press_release()
    elif cmd == "flash-backfill":
        start, end = argv[1], argv[2]
        year = int(start[:4])
        while year <= int(end[:4]):
            chunk_start = start if year == int(start[:4]) else f"{year}-01"
            chunk_end = end if year == int(end[:4]) else f"{year}-12"
            print(f"--- chunk {chunk_start}..{chunk_end}")
            try:
                fetch_press_release(chunk_start, chunk_end)
            except Exception as err:  # noqa: BLE001 - one chunk must not abort the walk
                print(f"    chunk failed ({type(err).__name__}: {err}); continuing")
            year += 1
            time.sleep(5.0)
    elif cmd == "timeseries":
        fetch_time_series()
    elif cmd == "estat":
        fetch_estat(int(argv[1]) if len(argv) > 1 else 1)
    elif cmd == "capture":
        capture()
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
