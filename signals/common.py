"""Shared helpers for the signals pipeline: HTTP with retries, date math, CSV I/O.

Stdlib + requests only, by design: this runs in GitHub Actions on a schedule
and anywhere else with Python 3.10+ and outbound HTTPS.
"""

from __future__ import annotations

import csv
import re
import time
from html.parser import HTMLParser
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
CONFIG_DIR = Path(__file__).resolve().parent / "config"

USER_AGENT = (
    "investment-lab-signals/1.0 (+https://github.com/JimmyD7205/investment-lab; "
    "research use; contact via repo issues)"
)


def http_get(url: str, *, params: dict | None = None, retries: int = 3,
             backoff: float = 2.0, timeout: float = 60.0) -> requests.Response:
    """GET with polite headers and exponential backoff on transient failures."""
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(
                url, params=params, timeout=timeout,
                headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
            )
            if resp.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {resp.status_code}", response=resp)
            resp.raise_for_status()
            return resp
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as err:
            last_err = err
            if attempt < retries:
                time.sleep(backoff * (2 ** attempt))
    raise RuntimeError(f"GET {url} failed after {retries + 1} attempts: {last_err}")


# --- Date helpers -----------------------------------------------------------

def roc_to_iso_month(roc: str) -> str:
    """'115/07', '11507' or '115-7' (ROC calendar) -> '2026-07'."""
    digits = "".join(ch for ch in roc if ch.isdigit())
    if len(digits) < 4:
        raise ValueError(f"unparseable ROC year-month: {roc!r}")
    year, month = int(digits[:-2]), int(digits[-2:])
    return f"{year + 1911:04d}-{month:02d}"


def iso_to_roc(iso_month: str) -> tuple[int, int]:
    """'2026-07' -> (115, 7)."""
    year, month = iso_month.split("-")
    return int(year) - 1911, int(month)


def month_range(start: str, end: str) -> list[str]:
    """Inclusive list of 'YYYY-MM' between start and end."""
    sy, sm = (int(x) for x in start.split("-"))
    ey, em = (int(x) for x in end.split("-"))
    out = []
    y, m = sy, sm
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def prev_year_month(iso_month: str) -> str:
    y, m = iso_month.split("-")
    return f"{int(y) - 1:04d}-{m}"


# --- Number parsing ---------------------------------------------------------

def parse_number(text: str | None) -> float | None:
    """'1,234,567' -> 1234567.0; '', '-', '不適用', 'N/A' -> None."""
    if text is None:
        return None
    cleaned = text.strip().replace(",", "").replace("%", "")
    if cleaned in ("", "-", "--", "不適用", "N/A", "NA", "null"):
        return None
    if cleaned.startswith("(") and cleaned.endswith(")"):  # accounting negatives
        cleaned = "-" + cleaned[1:-1]
    if cleaned[:1] in ("△", "▲"):  # Korean statistical notation for negative
        cleaned = "-" + cleaned[1:]
    try:
        return float(cleaned)
    except ValueError:
        return None


def fmt(value: float | None) -> str:
    if value is None:
        return ""
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}"


# --- HTML tables ------------------------------------------------------------

class TableParser(HTMLParser):
    """Collect all table rows (as text cells) from an HTML document.

    Also remembers the last-seen Taiwanese industry label (產業別: X) so MOPS
    archive rows can carry their section header; harmless elsewhere.
    """

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[tuple[str, list[str]]] = []  # (industry, cells)
        self._cells: list[str] | None = None
        self._buf: list[str] = []
        self._in_cell = False
        self._industry = ""

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._cells = []
        elif tag in ("td", "th") and self._cells is not None:
            self._in_cell = True
            self._buf = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._in_cell:
            self._in_cell = False
            assert self._cells is not None
            self._cells.append("".join(self._buf).strip())
        elif tag == "tr" and self._cells is not None:
            text = " ".join(self._cells)
            match = re.search(r"產業別[:：]\s*(\S+)", text)
            if match:
                self._industry = match.group(1)
            self.rows.append((self._industry, self._cells))
            self._cells = None

    def handle_data(self, data):
        if self._in_cell:
            self._buf.append(data)


# --- CSV I/O ----------------------------------------------------------------

def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)


def read_csv_dicts(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def append_dedup_csv(path: Path, header: list[str], rows: list[dict],
                     key_fields: list[str]) -> int:
    """Append rows to a long-format CSV, skipping rows whose key already exists.

    Returns the number of rows actually added. Keeps the file append-only so
    revisions never silently overwrite history (constitution: append-only logs).
    """
    existing_keys: set[tuple] = set()
    existing_rows: list[dict] = []
    if path.exists():
        existing_rows = read_csv_dicts(path)
        for row in existing_rows:
            existing_keys.add(tuple(row.get(k, "") for k in key_fields))

    added = 0
    out_rows = [[row.get(col, "") for col in header] for row in existing_rows]
    for row in rows:
        key = tuple(str(row.get(k, "")) for k in key_fields)
        if key in existing_keys:
            continue
        existing_keys.add(key)
        out_rows.append([str(row.get(col, "")) for col in header])
        added += 1

    if added or not path.exists():
        write_csv(path, header, out_rows)
    return added
