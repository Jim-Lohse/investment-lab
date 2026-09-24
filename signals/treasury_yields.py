"""Daily U.S. Treasury yields: the 2-year, the 10-year and the gaps between them.

The 2-year yield tracks what the bond market expects the Federal Reserve's
policy rate to be over the next two years; the 10-year reflects long-run growth
and inflation expectations plus a premium for lending that long. The gap
between them (10-year minus 2-year) is the slope of the yield curve: normally
positive, negative ("inverted") when the market expects rate cuts ahead,
usually because it expects a slowdown. The 3-month-to-10-year gap is the
version most Federal Reserve research uses.

Source: the U.S. Treasury's daily par yield curve (keyless, primary record),
one CSV per calendar year. Fallback: FRED (St. Louis Fed), which republishes
the same Treasury series (DGS3MO, DGS2, DGS5, DGS10, DGS30) in one keyless CSV
covering the whole history; used for any day Treasury did not supply, and the
source of each row is recorded. Treasury's site throttles some cloud runners,
so its requests fail fast rather than hang.
Treasury file:
  https://home.treasury.gov/resource-center/data-chart-center/interest-rates/
  daily-treasury-rates.csv/{year}/all?type=daily_treasury_yield_curve&...
Columns are found by header name ("3 Mo", "2 Yr", "10 Yr", ...), never by
position, because Treasury has added tenors over the years (the 2-month in
2018, the 4-month in 2022, the 1.5-month in 2025).

Output:
  data/rates/treasury_daily.csv — date, 3m, 2y, 5y, 10y, 30y (percent),
      2s10s and 3m10y gaps (percentage points). Rebuilt by merging each
      fetched year over what is stored, so a revised day is picked up and
      years not refetched are kept.

Usage:
    python -m signals.treasury_yields latest             # this year (and last, in January)
    python -m signals.treasury_yields backfill 1990      # every year from 1990
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
import sys
import time

import requests

from .common import CONFIG_DIR, DATA_DIR, USER_AGENT, fmt, parse_number, write_csv

OUT = DATA_DIR / "rates" / "treasury_daily.csv"
HEADER = ["date", "y3m", "y2y", "y5y", "y10y", "y30y", "gap_2s10s", "gap_3m10y", "source"]
FRED_IDS = {"y3m": "DGS3MO", "y2y": "DGS2", "y5y": "DGS5", "y10y": "DGS10", "y30y": "DGS30"}
TENORS = {"y3m": "3 mo", "y2y": "2 yr", "y5y": "5 yr", "y10y": "10 yr", "y30y": "30 yr"}


def _load_config() -> dict:
    return json.loads((CONFIG_DIR / "treasury_endpoints.json").read_text("utf-8"))


def parse_treasury_csv(text: str) -> list[dict]:
    """Treasury yearly CSV -> rows. A day missing the 2-year or 10-year is kept
    with those fields blank; gaps are computed only when both legs exist."""
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    if not reader.fieldnames:
        return []
    cols = {name.strip().lower(): name for name in reader.fieldnames}
    date_col = cols.get("date")
    if not date_col:
        return []
    rows = []
    for rec in reader:
        try:
            day = dt.datetime.strptime(rec[date_col].strip(), "%m/%d/%Y").date().isoformat()
        except (ValueError, AttributeError):
            continue
        row = {"date": day}
        for key, label in TENORS.items():
            src = cols.get(label)
            row[key] = parse_number(rec.get(src)) if src else None
        row["gap_2s10s"] = (row["y10y"] - row["y2y"]
                            if row["y10y"] is not None and row["y2y"] is not None else None)
        row["gap_3m10y"] = (row["y10y"] - row["y3m"]
                            if row["y10y"] is not None and row["y3m"] is not None else None)
        rows.append(row)
    return rows


def parse_fred_csv(text: str) -> list[dict]:
    """FRED fredgraph CSV (first column the date, one column per series id,
    '.' or blank for a missing day) -> rows in the same shape as Treasury's."""
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    if not reader.fieldnames:
        return []
    date_col = reader.fieldnames[0]
    cols = {name.strip().upper(): name for name in reader.fieldnames}
    rows = []
    for rec in reader:
        day = (rec.get(date_col) or "").strip()
        if len(day) != 10 or day[4] != "-":
            continue
        row = {"date": day}
        for key, sid in FRED_IDS.items():
            src = cols.get(sid)
            row[key] = parse_number(rec.get(src)) if src else None
        if row["y2y"] is None and row["y10y"] is None:
            continue  # a holiday row with no readings
        row["gap_2s10s"] = (row["y10y"] - row["y2y"]
                            if row["y10y"] is not None and row["y2y"] is not None else None)
        row["gap_3m10y"] = (row["y10y"] - row["y3m"]
                            if row["y10y"] is not None and row["y3m"] is not None else None)
        rows.append(row)
    return rows


def _store_row(r: dict, source: str) -> dict:
    out = {k: (r[k] if k == "date" else fmt(round(r[k], 4)) if r[k] is not None else "")
           for k in HEADER if k != "source"}
    out["source"] = source
    return out


def get_text(url: str, deadline: float) -> str:
    """GET with a hard limit on the whole download, not just on each read.

    requests' timeout applies per socket read, so a server that trickles bytes
    (as Treasury's does for some cloud runners) can hold a request open far
    longer; this reads in chunks and gives up once `deadline` seconds pass.
    """
    start = time.monotonic()
    with requests.get(url, stream=True, timeout=min(20, deadline),
                      headers={"User-Agent": USER_AGENT, "Accept": "*/*"}) as resp:
        resp.raise_for_status()
        chunks = []
        for chunk in resp.iter_content(chunk_size=65536):
            chunks.append(chunk)
            if time.monotonic() - start > deadline:
                raise TimeoutError(f"download exceeded {deadline:.0f} s")
        return b"".join(chunks).decode(resp.encoding or "utf-8", "replace")


def _read_store() -> dict[str, dict]:
    if not OUT.exists():
        return {}
    with OUT.open(encoding="utf-8", newline="") as fh:
        return {r["date"]: r for r in csv.DictReader(fh)}


def fetch_years(years: list[int]) -> int:
    cfg = _load_config()
    store = _read_store()
    fetched, failed = 0, []
    missed_years = []
    for i, year in enumerate(years):
        url = cfg["year_csv_template"].format(year=year)
        try:
            rows = parse_treasury_csv(get_text(url, deadline=30))
        except Exception as err:  # noqa: BLE001 - one bad year must not stop the walk
            failed.append(f"{year}: {type(err).__name__}: {err}")
            print(f"  treasury {year}: {type(err).__name__}: {err}", flush=True)
            missed_years.append(year)
            if i == 0 and len(years) > 3:
                # The first year failing usually means the site is refusing this
                # runner: skip the rest and let FRED supply the history.
                missed_years = list(years)
                break
            continue
        if not rows:
            failed.append(f"{year}: no rows parsed")
            missed_years.append(year)
            continue
        for r in rows:
            store[r["date"]] = _store_row(r, "treasury")
        fetched += len(rows)
        if len(years) > 1:
            time.sleep(1.0)  # polite pause between yearly files
    if missed_years:
        wanted = {str(y) for y in missed_years}
        try:
            rows = parse_fred_csv(get_text(cfg["fred_csv_url"], deadline=120))
            added = 0
            for r in rows:
                # FRED only fills days Treasury did not supply this run or before.
                if r["date"][:4] in wanted and store.get(r["date"], {}).get("source") != "treasury":
                    store[r["date"]] = _store_row(r, "fred")
                    added += 1
            fetched += added
            print(f"  FRED fallback: {added} days for {len(wanted)} year(s) Treasury did not supply")
        except Exception as err:  # noqa: BLE001
            failed.append(f"FRED fallback: {type(err).__name__}: {err}")
    if store:
        write_csv(OUT, HEADER, [[store[d][k] for k in HEADER] for d in sorted(store)])
    last = max(store) if store else "none"
    print(f"treasury_daily.csv: {len(store)} days, {fetched} fetched this run, latest {last}")
    if failed:
        print("  failed: " + "; ".join(failed))
        if not fetched:
            raise RuntimeError("treasury: no year fetched")
    return fetched


def main(argv: list[str]) -> int:
    today = dt.date.today()
    if argv[:1] == ["latest"]:
        years = [today.year - 1, today.year] if today.month == 1 else [today.year]
        fetch_years(years)
    elif argv[:1] == ["backfill"]:
        start = int(argv[1]) if len(argv) > 1 else 1990
        fetch_years(list(range(start, today.year + 1)))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
