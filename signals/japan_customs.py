"""Japan Ministry of Finance / Customs trade-statistics fetcher (no key needed).

Japan is the supply side of the AI build-out: semiconductor-equipment and
materials exports (HS 8486, 3818, 2804.61) plus optical components (8541,
8517, 9001, 9013). MOF publishes on the same three-revision cadence as
Korea — first 10 days, first 20 days, monthly provisional, then detailed —
so the by-window YoY logic from the Korea leg carries over unchanged.

Sources (all free, no registration; verified against live payloads 2026-09-02):
  1. Press-release XML on customs.go.jp:
       https://www.customs.go.jp/toukei/shinbun/trade-st_e/<YYYY>/<YYYYMM><stage>e.xml
     stage 1 = first 10 days, 2 = first 20 days, 4 = monthly provisional,
     5 = exports detailed / imports 9-digit provisional. The 10/20-day files
     carry TOTALS ONLY (exports, imports, balance; current, year-ago, % change).
     The monthly files carry the full principal-commodity breakdown for the
     world and for USA / EU / Asia / China / Korea / ASEAN / Middle East /
     Russia, each row with value (million yen), quantity, YoY, share and
     contribution. Index: https://www.customs.go.jp/toukei/shinbun/happyou_e.htm
  2. Time-series CSVs on customs.go.jp (thousand yen, Shift_JIS):
       d41ma.csv  world monthly exports/imports totals from 1979
       d51ma.csv  world monthly EXPORTS by press-release commodity from 1988
       d61ma.csv  world monthly IMPORTS by press-release commodity from 1988
  3. e-Stat monthly "Values by Commodity" (統計品別表) CSV: value and quantity
     per 9-digit statistical code, one file per month carrying Jan..latest of
     its year. Reached through the listing page -> month page -> file link.

Every raw payload is saved under data/japan/raw/ before parsing; zero parsed
rows raises instead of writing an empty file; `reparse` rebuilds the CSV
stores from those raw files after any parser fix.

Output (append-only, first print wins):
  data/japan/press_release.csv    — totals, area and commodity rows per window
  data/japan/time_series.csv      — long-format monthly series (thousand yen)
  data/japan/trade_monthly_hs.csv — monthly value/quantity per 9-digit code
                                    for the configured HS prefixes

Usage:
    python -m signals.japan_customs flash            # last 3 months, all stages
    python -m signals.japan_customs flash 2026-06 2026-08
    python -m signals.japan_customs flash-backfill 2021-01 2026-08
    python -m signals.japan_customs timeseries
    python -m signals.japan_customs estat [months_back]
    python -m signals.japan_customs capture          # snapshot everything raw
    python -m signals.japan_customs reparse          # rebuild CSVs from raw
"""

from __future__ import annotations

import csv
import datetime as dt
import html
import io
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

from .common import (CONFIG_DIR, DATA_DIR, USER_AGENT, append_dedup_csv, fmt,
                     http_get, month_range, parse_number, write_csv)

OUT_DIR = DATA_DIR / "japan"
RAW_DIR = OUT_DIR / "raw"
PAGES_DIR = RAW_DIR / "pages"

PRESS_HEADER = ["yyyymm", "period_type", "stage", "lang", "section", "imex",
                "area", "name", "level", "value_jpy_m", "value_year_ago_jpy_m",
                "yoy_pct", "quantity", "unit", "qty_yoy_pct", "share_pct",
                "contribution_pt", "extra_json", "retrieved_at"]
PRESS_KEY = ["yyyymm", "stage", "lang", "section", "imex", "area", "name"]
TS_HEADER = ["series", "imex", "area", "code", "name", "yyyymm", "value_jpy_k",
             "quantity", "unit", "retrieved_at"]
TS_KEY = ["series", "imex", "area", "code", "name", "yyyymm"]
HS_HEADER = ["yyyymm", "imex", "hs_code", "stage", "value_jpy_k", "quantity1",
             "unit1", "quantity2", "unit2", "source_file", "retrieved_at"]
HS_KEY = ["yyyymm", "imex", "hs_code", "stage"]

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
    """MOF CSVs are Shift_JIS (cp932); e-Stat and XML are UTF-8."""
    for enc in ("utf-8-sig", "cp932", "euc_jp"):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _num(text: str | None) -> str:
    """Formatted number or '' (handles '△' negatives, '-', ZENZO/ZENGEN)."""
    return fmt(parse_number(text))


# --- Press-release XML (10/20-day + monthly) --------------------------------

def _text(elem: ET.Element | None, tag: str) -> str:
    if elem is None:
        return ""
    return (elem.findtext(tag) or "").strip()


def _page_direction(title: str) -> str:
    low = title.lower()
    if low.startswith("import") or title.startswith("主要商品別輸入") or "商品別輸入" in title:
        return "I"
    if low.startswith("export") or "輸出" in title:
        return "E"
    return ""


def _page_area(title: str) -> str:
    """'Exports by Principal Commodity by Area(Country)(USA)' -> 'USA';
    '主要商品別輸出(世界)' -> '世界'."""
    groups = re.findall(r"[（(]\s*([^()（）]+?)\s*[)）]", title)
    return groups[-1].strip() if groups else ""


def parse_press_xml(content: bytes, yyyymm: str, period_type: str, stage: str,
                    lang: str, retrieved_at: str) -> list[dict]:
    """Exact parser for MOF's hodoxml press-release format.

    Pages: sogakutsuki (totals), chiikikunisogaku (area/country totals),
    shuyochiikikunihin (principal commodity tables per area), shisu /
    chiikishisu (trade indexes, not stored). Values are million yen.
    """
    root = ET.fromstring(content)
    rows: list[dict] = []

    def base(section: str, imex: str, area: str, name: str, fields: dict) -> dict:
        return {
            "yyyymm": yyyymm, "period_type": period_type, "stage": stage,
            "lang": lang, "section": section, "imex": imex, "area": area,
            "name": name, "level": "", "value_jpy_m": "",
            "value_year_ago_jpy_m": "", "yoy_pct": "", "quantity": "",
            "unit": "", "qty_yoy_pct": "", "share_pct": "", "contribution_pt": "",
            "extra_json": json.dumps(fields, ensure_ascii=False, sort_keys=True),
            "retrieved_at": retrieved_at,
        }

    def leaf_fields(elem: ET.Element) -> dict:
        return {child.tag: (child.text or "").strip() for child in elem if not len(child)}

    for total in root.iter("sogakutsuki"):
        for tag, imex in (("export", "E"), ("import", "I"), ("sashihiki", "BAL")):
            node = total.find(tag)
            if node is None:
                continue
            fields = leaf_fields(node)
            fields["title"] = _text(total, "title")
            fields["taishoymtonen"] = _text(total, "taishoymtonen")
            row = base("TOTAL", imex, "WORLD", "Grand Total", fields)
            row["value_jpy_m"] = _num(fields.get("sogakutonen"))
            row["value_year_ago_jpy_m"] = _num(fields.get("sogakuzennen"))
            row["yoy_pct"] = _num(fields.get("nobiritsu"))
            if row["value_jpy_m"]:
                rows.append(row)

    for page in root.iter("chiikikunisogaku"):
        for info in page.iter("chiikikunisogakuinfo"):
            fields = leaf_fields(info)
            area = fields.get("chiikikuni", "")
            if not area:
                continue
            for prefix, imex in (("export", "E"), ("import", "I"), ("sashihiki", "BAL")):
                row = base("AREA", imex, area, area, fields)
                row["level"] = fields.get("chiikikunikbn", "")
                row["value_jpy_m"] = _num(fields.get(f"{prefix}kagakue"))
                row["yoy_pct"] = _num(fields.get(f"{prefix}nobiritsu"))
                if row["value_jpy_m"]:
                    rows.append(row)

    for page in root.iter("shuyochiikikunihin"):
        title = _text(page, "title")
        imex = _page_direction(title)
        area = _page_area(title) or "WORLD"
        for info in page.iter("shuyochiikikunihininfo"):
            fields = leaf_fields(info)
            name = fields.get("shuyoshohin", "")
            if not name:
                continue
            fields["page_title"] = title
            row = base("COMMODITY", imex, area, name, fields)
            row["level"] = fields.get("shuyoshohinbunrui", "")
            row["value_jpy_m"] = _num(fields.get("kagaku"))
            row["yoy_pct"] = _num(fields.get("kagakunobiritsu"))
            row["quantity"] = _num(fields.get("suryo"))
            row["unit"] = fields.get("tani", "")
            row["qty_yoy_pct"] = _num(fields.get("suryonobiritsu"))
            row["share_pct"] = _num(fields.get("koseihi"))
            row["contribution_pt"] = _num(fields.get("zogenkiyodo"))
            if row["value_jpy_m"]:
                rows.append(row)
    return rows


def press_url(cfg: dict, yyyymm: str, stage: str, lang: str) -> str:
    pr = cfg["press_release"]
    lang_cfg = pr["languages"][lang]
    return pr["url_template"].format(year=yyyymm[:4], yyyymm=yyyymm,
                                     stage=stage, **lang_cfg)


def _default_range(today: dt.date, months_back: int = 2) -> tuple[str, str]:
    start = today.replace(day=1)
    for _ in range(months_back):
        start = (start - dt.timedelta(days=1)).replace(day=1)
    return start.strftime("%Y-%m"), today.strftime("%Y-%m")


def fetch_press_release(start_iso: str | None = None, end_iso: str | None = None,
                        stages: list[str] | None = None,
                        langs: tuple[str, ...] = ("en",)) -> int:
    """Fetch every press-release window in a month range.

    Unpublished windows 404 and are skipped. A published window that parses
    to zero rows raises after the raw file is saved, so a schema change is a
    red step rather than an empty CSV. Default range is the last three
    months: the detailed monthly file for month M lands at the end of M+1.
    """
    cfg = _load_config()
    today = dt.date.today()
    default_start, default_end = _default_range(today)
    start_iso = start_iso or default_start
    end_iso = end_iso or default_end
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
                added = append_dedup_csv(OUT_DIR / "press_release.csv", PRESS_HEADER,
                                         rows, PRESS_KEY)
                print(f"  {yyyymm} stage {stage} ({lang}): {len(rows)} rows, {added} new")
                added_total += added
                time.sleep(1.0)
    if unparsed:
        raise RuntimeError(
            "press release: payloads saved under data/japan/raw/ but not parsed: "
            + "; ".join(unparsed))
    return added_total


# --- Time-series CSVs -------------------------------------------------------

DATA_ROW_RE = re.compile(r"^(\d{4})/(\d{1,2})$")


def parse_time_series_csv(text: str, series: str, retrieved_at: str) -> list[dict]:
    """Long-format rows from a MOF 推移 CSV.

    Layout (cp932): title row with 《area》 and (輸出)/(輸入), an English title
    row, then header rows keyed by their first cell — 報道発表品目名 (press
    item), 概況品名 (principal commodity), 概況品コード (code), a 金額/数量
    kind row and a unit row — followed by data rows 'YYYY/MM,...'. Column 1
    is the grand total (value only); every other item is a (数量, 金額) pair
    whose label sits on the 数量 column. d41ma has plain Exp-Total/Imp-Total
    columns. Unpublished months are '-' or 0 and are skipped.
    """
    reader = list(csv.reader(io.StringIO(text)))
    rows: list[dict] = []
    header_rows: list[list[str]] = []
    data_rows: list[list[str]] = []
    for rec in reader:
        if rec and DATA_ROW_RE.match(rec[0].strip()):
            data_rows.append(rec)
        elif not data_rows:
            header_rows.append([c.strip() for c in rec])
    if not data_rows:
        return rows

    title = " ".join(header_rows[0]) if header_rows else ""
    area_match = re.search(r"《([^》]+)》", title)
    area = area_match.group(1) if area_match else "WORLD"
    file_imex = "I" if ("輸入" in title or "Import" in title) else (
        "E" if ("輸出" in title or "Export" in title) else "")

    def find_row(label: str) -> list[str]:
        for rec in header_rows:
            if rec and rec[0] == label:
                return rec
        return []

    def cell(rec: list[str], j: int) -> str:
        return rec[j] if j < len(rec) else ""

    press_row, pc_row, code_row = (find_row("報道発表品目名"), find_row("概況品名"),
                                   find_row("概況品コード"))
    kind_row = next((r for r in header_rows if len(r) > 1 and r[0] == ""
                     and "金額" in r and set(r[1:]) <= {"金額", "数量", ""}), [])
    unit_row = next((r for r in header_rows if r and r[0].startswith("Years")
                     and any("単位" in c for c in r)), [])
    width = max(len(r) for r in data_rows)

    # (value col, qty col, code, name, unit)
    columns: list[tuple[int, int | None, str, str, str]] = []
    if kind_row:
        for j in range(1, width):
            name = cell(pc_row, j) or cell(press_row, j)
            if not name:
                continue
            code = cell(code_row, j).replace("'", "")
            kind = cell(kind_row, j)
            if kind == "数量":
                unit = re.sub(r"[()（）単位：:\s]", "", cell(unit_row, j))
                columns.append((j + 1, j, code, name, unit))
            else:
                columns.append((j, None, code, name, ""))
    else:
        head = next((r for r in header_rows if len(r) > 1 and any(r[1:])), [])
        for j in range(1, width):
            label = cell(head, j)
            if label:
                columns.append((j, None, "", label, ""))

    for rec in data_rows:
        match = DATA_ROW_RE.match(rec[0].strip())
        yyyymm = f"{int(match.group(1)):04d}-{int(match.group(2)):02d}"
        for vcol, qcol, code, name, unit in columns:
            value = parse_number(cell(rec, vcol))
            if value is None or value == 0:
                continue
            imex = file_imex
            if not imex:
                low = name.lower()
                imex = "I" if low.startswith("imp") else ("E" if low.startswith("exp") else "")
            qty = parse_number(cell(rec, qcol)) if qcol is not None else None
            rows.append({
                "series": series, "imex": imex, "area": area, "code": code,
                "name": name, "yyyymm": yyyymm, "value_jpy_k": fmt(value),
                "quantity": fmt(qty), "unit": unit, "retrieved_at": retrieved_at,
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
        added = append_dedup_csv(OUT_DIR / "time_series.csv", TS_HEADER, rows, TS_KEY)
        print(f"  {series} ({filename}): {len(rows)} rows, {added} new")
        added_total += added
        time.sleep(1.0)
    if problems:
        raise RuntimeError("time series: " + "; ".join(problems)
                           + " (raw files kept under data/japan/raw/)")
    return added_total


# --- e-Stat monthly HS-level CSV -------------------------------------------

ESTAT_BASE = "https://www.e-stat.go.jp"
MONTH_LINK_RE = re.compile(
    r'href="([^"]*stat-search/files\?[^"]*year=(\d{4})0&(?:amp;)?month=(\d{8})[^"]*)"')
STAT_ID_RE = re.compile(r"stat[_-]?inf[_-]?id=(\d{10,14})", re.IGNORECASE)
TCLASS2_LINK_RE = re.compile(r'<a[^>]+href="([^"]*tclass2=(\d{12})[^"]*)"[^>]*>([^<]*)</a>')
JP_MONTH_TITLE_RE = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月")


def estat_month_code(month: int) -> str:
    """e-Stat's month parameter: half, quarter, quarter start, quarter end,
    month — e.g. July = 2 3 07 09 07 -> '23070907'."""
    quarter = (month - 1) // 3 + 1
    half = 1 if month <= 6 else 2
    return f"{half}{quarter}{(quarter - 1) * 3 + 1:02d}{quarter * 3:02d}{month:02d}"


def parse_estat_listing(html_text: str) -> list[dict]:
    """[{yyyymm, url}] for every year/month drill-down link, newest first."""
    found: dict[str, str] = {}
    for match in MONTH_LINK_RE.finditer(html_text):
        href, year, month_code = match.groups()
        yyyymm = f"{year}-{month_code[-2:]}"
        url = html.unescape(href)
        if url.startswith("/"):
            url = ESTAT_BASE + url
        found.setdefault(yyyymm, url)
    return [{"yyyymm": k, "url": v} for k, v in sorted(found.items(), reverse=True)]


def parse_estat_month_page(html_text: str) -> list[dict]:
    """[{stat_inf_id, title}] for every file on a month page. The title is
    the nearest 統計品別表 text around the link (carries 確報/速報)."""
    found: dict[str, dict] = {}
    for match in STAT_ID_RE.finditer(html_text):
        sid = match.group(1)
        window = html_text[max(0, match.start() - 2500): match.end() + 2500]
        window_text = html.unescape(re.sub(r"<[^>]+>", " ", window))
        title_match = re.search(r"([^\s][^<>|]{0,80}統計品別表[^<>|]{0,60})", window_text)
        title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else ""
        entry = found.setdefault(sid, {"stat_inf_id": sid, "title": title})
        if not entry["title"] and title:
            entry["title"] = title
    return list(found.values())


def discover_tclass2(html_text: str, label: str) -> str:
    """tclass2 of the child whose link text mentions `label` (輸出/輸入).

    Tries a clean <a href=...>label</a> first, then any tclass2 within the
    500 characters before the label (e-Stat nests spans inside its links)."""
    for match in TCLASS2_LINK_RE.finditer(html_text):
        if label in match.group(3):
            return match.group(2)
    for match in re.finditer(re.escape(label), html_text):
        window = html_text[max(0, match.start() - 500): match.start()]
        ids = re.findall(r"tclass2=(\d{12})", window)
        if ids:
            return ids[-1]
    return ""


STAGE_WORDS = (("確定", "FIXED"), ("確々報", "REVISED"), ("確報", "DETAILED"),
               ("9桁速報", "PROV9"), ("速報", "PROV9"))
TITLE_SPAN_RE = re.compile(r"(\d{1,2})\s*(?:[-～]\s*(\d{1,2}))?\s*月\s*[：:]\s*([^、,)）]+)")


def _stage_word(text: str) -> str:
    for word, stage in STAGE_WORDS:
        if word in text:
            return stage
    return ""


def _stage_from_title(title: str) -> str:
    """Whole-file stage (the strongest word wins for the summary label)."""
    return _stage_word(title)


def stages_by_month(title: str) -> dict[int, str]:
    """Per-month stage from a title like
    '2026年7月分 統計品別表 (輸入 1-6月：確報、7月：輸入9桁速報)' ->
    {1..6: DETAILED, 7: PROV9}. Empty when the title carries no spans."""
    out: dict[int, str] = {}
    for start, end, label in TITLE_SPAN_RE.findall(title):
        stage = _stage_word(label)
        if not stage:
            continue
        for month in range(int(start), int(end or start) + 1):
            out[month] = stage
    return out


def parse_estat_commodity_csv(text: str, hs_prefixes: list[str],
                              stage: str | dict[int, str], source_file: str,
                              retrieved_at: str) -> list[dict]:
    """Rows for configured HS prefixes from a 統計品別表 CSV.

    Header: Exp or Imp, Year, HS, Unit1, Unit2, Quantity1-Year, Quantity2-Year,
    Value-Year, then Quantity1-Jan, Quantity2-Jan, Value-Jan ... Value-Dec
    (value = thousand yen). Columns are resolved by name so reordering is
    harmless; HS arrives quoted like '848610000'. `stage` is one label for
    the whole file or a {month: label} map (import files mix detailed months
    with a 9-digit provisional latest month).
    """
    stage_map = stage if isinstance(stage, dict) else {}
    default_stage = stage if isinstance(stage, str) else ""
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
                "stage": stage_map.get(idx, default_stage), "value_jpy_k": fmt(value),
                "quantity1": fmt(q1), "unit1": (rec.get(c_unit1) or "").strip() if c_unit1 else "",
                "quantity2": fmt(q2), "unit2": (rec.get(c_unit2) or "").strip() if c_unit2 else "",
                "source_file": source_file, "retrieved_at": retrieved_at,
            })
    return rows


def fetch_estat(months_back: int = 1) -> int:
    """Download the newest 統計品別表 CSV(s) for exports and imports and keep
    the configured HS prefixes: parent page (to find the 輸出/輸入 children),
    listing page (year/month links), month page (file ids), then the CSV."""
    cfg = _load_config()
    est = cfg["estat"]
    prefixes = [k for k in cfg["hs_codes"] if not k.startswith("_")]
    retrieved_at = dt.date.today().isoformat()
    added_total = 0
    problems: list[str] = []

    parent = _get_optional(est["parent_url"])
    parent_html = _decode(parent.content) if parent is not None else ""
    if parent is not None:
        _save_raw("estat_parent.html", parent.content, PAGES_DIR)

    for imex, label in (("E", "輸出"), ("I", "輸入")):
        tclass2 = discover_tclass2(parent_html, label) or est["tclass2"][imex]
        listing_url = est["listing_url_template"].format(tclass2=tclass2)
        resp = _get_optional(listing_url)
        if resp is None:
            problems.append(f"listing {imex}: 404")
            continue
        _save_raw(f"estat_listing_{imex}.html", resp.content, PAGES_DIR)
        months = parse_estat_listing(_decode(resp.content))
        if not months:
            problems.append(f"listing {imex}: no year/month links "
                            f"(saved data/japan/raw/pages/estat_listing_{imex}.html)")
            continue
        for month in months[:months_back]:
            page = _get_optional(month["url"])
            if page is None:
                problems.append(f"{imex} {month['yyyymm']}: month page 404")
                continue
            _save_raw(f"estat_month_{imex}_{month['yyyymm']}.html", page.content, PAGES_DIR)
            files = parse_estat_month_page(_decode(page.content))
            if not files:
                problems.append(f"{imex} {month['yyyymm']}: no file ids on month page")
                continue
            for entry in files:
                url = est["download_url_template"].format(stat_inf_id=entry["stat_inf_id"])
                csv_resp = _get_optional(url)
                if csv_resp is None:
                    problems.append(f"{imex} {entry['stat_inf_id']}: 404")
                    continue
                fname = f"estat_{imex}_{month['yyyymm']}_{entry['stat_inf_id']}.csv"
                _save_raw(fname, csv_resp.content)
                stage = stages_by_month(entry["title"]) or _stage_from_title(entry["title"])
                rows = parse_estat_commodity_csv(_decode(csv_resp.content), prefixes,
                                                 stage, fname, retrieved_at)
                if not rows:
                    problems.append(f"{fname}: 0 rows for configured HS prefixes")
                    continue
                added = append_dedup_csv(OUT_DIR / "trade_monthly_hs.csv", HS_HEADER,
                                         rows, HS_KEY)
                label = stage if isinstance(stage, str) else "/".join(sorted(set(stage.values())))
                print(f"  e-Stat {imex} {month['yyyymm']} {entry['stat_inf_id']} "
                      f"[{label or 'stage?'}]: {len(rows)} rows, {added} new")
                added_total += added
                time.sleep(2.0)
    if problems:
        raise RuntimeError("e-Stat: " + "; ".join(problems))
    return added_total


# --- Capture and reparse ----------------------------------------------------

def capture() -> None:
    """Snapshot every source raw for parser development. Read-only GETs
    against static files; safe to run from CI where the hosts are reachable.
    Data payloads land where the fetchers put them (data/japan/raw/), index
    and listing HTML under data/japan/raw/pages/."""
    cfg = _load_config()
    today = dt.date.today()
    months = month_range(*_default_range(today))
    targets: dict[str, tuple[str, Path]] = {
        f"{name}.html": (url, PAGES_DIR)
        for name, url in cfg["press_release"]["index_pages"].items()}
    for month in months:
        yyyymm = month.replace("-", "")
        for stage in cfg["press_release"]["stages"]:
            for lang in ("en", "ja"):
                targets[f"press_{yyyymm}{stage}{lang}.xml"] = (
                    press_url(cfg, yyyymm, stage, lang), RAW_DIR)
    for series, filename in cfg["time_series"]["files"].items():
        targets[filename] = (cfg["time_series"]["base_url"] + filename, RAW_DIR)
    targets["estat_parent.html"] = (cfg["estat"]["parent_url"], PAGES_DIR)
    for imex, tclass2 in cfg["estat"]["tclass2"].items():
        targets[f"estat_listing_{imex}.html"] = (
            cfg["estat"]["listing_url_template"].format(tclass2=tclass2), PAGES_DIR)
    for name, (url, out_dir) in targets.items():
        try:
            resp = _get_optional(url, timeout=60)
        except Exception as err:  # noqa: BLE001 - keep capturing the rest
            print(f"capture {name}: {type(err).__name__}: {err}")
            continue
        if resp is None:
            print(f"capture {name}: 404")
            continue
        _save_raw(name, resp.content[:2_000_000], out_dir)
        print(f"captured {out_dir.name}/{name}: {len(resp.content)} bytes "
              f"{resp.headers.get('Content-Type', '')}")
        time.sleep(1.0)


def reparse() -> None:
    """Rebuild the three CSV stores from the raw payloads on disk.

    Raw files are the record; the stores are a parse of them. After a parser
    fix this regenerates every store so history never carries the old bug.
    """
    cfg = _load_config()
    stage_map = cfg["press_release"]["stages"]
    retrieved_at = dt.date.today().isoformat()

    press_rows: list[dict] = []
    seen: set[str] = set()
    for path in sorted(RAW_DIR.glob("press_*.xml")):
        if path.name in seen:
            continue
        seen.add(path.name)
        match = re.fullmatch(r"press_(\d{6})(\d)(en|ja)\.xml", path.name)
        if not match:
            continue
        yyyymm, stage, lang = match.groups()
        month = f"{yyyymm[:4]}-{yyyymm[4:]}"
        press_rows += parse_press_xml(path.read_bytes(), month, stage_map.get(stage, ""),
                                      stage, lang, retrieved_at)
    ts_rows: list[dict] = []
    for series, filename in cfg["time_series"]["files"].items():
        path = RAW_DIR / filename
        if path.exists():
            ts_rows += parse_time_series_csv(_decode(path.read_bytes()), series, retrieved_at)
    hs_rows: list[dict] = []
    prefixes = [k for k in cfg["hs_codes"] if not k.startswith("_")]
    for path in sorted(RAW_DIR.glob("estat_*.csv")):
        match = re.fullmatch(r"estat_([EI])_(\d{4}-\d{2})_(\d+)\.csv", path.name)
        stage: str | dict[int, str] = ""
        if match:
            page = PAGES_DIR / f"estat_month_{match.group(1)}_{match.group(2)}.html"
            if page.exists():
                for entry in parse_estat_month_page(_decode(page.read_bytes())):
                    if entry["stat_inf_id"] == match.group(3):
                        stage = stages_by_month(entry["title"]) or _stage_from_title(entry["title"])
        hs_rows += parse_estat_commodity_csv(_decode(path.read_bytes()), prefixes,
                                             stage, path.name, retrieved_at)

    for name, header, key, rows in (
        ("press_release.csv", PRESS_HEADER, PRESS_KEY, press_rows),
        ("time_series.csv", TS_HEADER, TS_KEY, ts_rows),
        ("trade_monthly_hs.csv", HS_HEADER, HS_KEY, hs_rows),
    ):
        path = OUT_DIR / name
        if rows:
            write_csv(path, header, [])
            added = append_dedup_csv(path, header, rows, key)
            print(f"{name}: rebuilt with {added} rows")
        elif path.exists():
            path.unlink()
            print(f"{name}: removed (no raw payloads to rebuild from)")


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
    elif cmd == "reparse":
        reparse()
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
