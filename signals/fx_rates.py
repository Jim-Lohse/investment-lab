"""Daily reference exchange rates, so a currency move can be told from a real one.

Japan's MOF publishes trade values in yen. When the yen weakens, every yen
figure grows without a single extra machine leaving the country. This module
stores a daily USD cross rate so `compute_signals` can restate the Japanese
series in dollars and report both growth rates side by side: the published yen
YoY, the USD YoY, and the gap between them, which is the currency's share of
the move.

Source: the ECB Data Portal's daily euro reference rates (keyless), cross-rated
through USD per EUR. frankfurter.app, a keyless wrapper over the same ECB data,
is the fallback. See signals/config/fx_endpoints.json for the caveats — chiefly
that these are market reference rates, not customs valuation rates.

Output (append-only, first print wins):
  data/fx/rates_daily.csv   — date, quote, rate per USD, source
  data/fx/raw/              — the payloads, so a parser fix can be replayed

Usage:
    python -m signals.fx_rates daily                  # last 10 days, idempotent
    python -m signals.fx_rates daily 2026-01-01 2026-09-15
    python -m signals.fx_rates backfill 2015-01-01 2026-09-15
    python -m signals.fx_rates reparse
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
import sys
from pathlib import Path

from .common import (CONFIG_DIR, DATA_DIR, append_dedup_csv, fmt, http_get,
                     parse_number, write_csv)

OUT_DIR = DATA_DIR / "fx"
RAW_DIR = OUT_DIR / "raw"

RATES_HEADER = ["date", "quote", "rate_per_usd", "source", "retrieved_at"]
RATES_KEY = ["date", "quote"]

# Window definitions must match the Japan press release's publication windows.
WINDOW_DAYS = {"D10": (1, 10), "D20": (1, 20)}


def _load_config() -> dict:
    return json.loads((CONFIG_DIR / "fx_endpoints.json").read_text("utf-8"))


def _quotes(cfg: dict) -> list[str]:
    return [q for q in cfg["quotes"] if not q.startswith("_")]


# --- Parsing ----------------------------------------------------------------

def parse_ecb_csv(text: str, retrieved_at: str, quotes: list[str]) -> list[dict]:
    """ECB SDMX csvdata -> rows of <quote> per USD.

    The response carries one observation per (currency, date) as units of that
    currency per EUR. USD is requested alongside so each date can be cross-rated;
    a date missing either leg is dropped rather than guessed.
    """
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return []
    names = {n.strip().upper(): n for n in reader.fieldnames}
    c_cur = names.get("CURRENCY")
    c_date = names.get("TIME_PERIOD")
    c_val = names.get("OBS_VALUE")
    if not (c_cur and c_date and c_val):
        return []
    per_eur: dict[str, dict[str, float]] = {}
    for rec in reader:
        currency = (rec.get(c_cur) or "").strip().upper()
        date = (rec.get(c_date) or "").strip()
        value = parse_number(rec.get(c_val))
        if not currency or not date or value is None or value <= 0:
            continue  # ECB marks holidays with an empty or 'NaN' observation
        per_eur.setdefault(date, {})[currency] = value
    rows: list[dict] = []
    for date in sorted(per_eur):
        usd_per_eur = per_eur[date].get("USD")
        if not usd_per_eur:
            continue
        for quote in quotes:
            quote_per_eur = per_eur[date].get(quote.upper())
            if not quote_per_eur:
                continue
            rows.append({
                "date": date, "quote": quote.upper(),
                "rate_per_usd": fmt(quote_per_eur / usd_per_eur),
                "source": "ecb", "retrieved_at": retrieved_at,
            })
    return rows


def parse_frankfurter_json(payload, retrieved_at: str, quotes: list[str]) -> list[dict]:
    """frankfurter.app -> rows of <quote> per USD (already quoted per USD)."""
    if not isinstance(payload, dict):
        return []
    rates = payload.get("rates")
    if not isinstance(rates, dict):
        return []
    wanted = {q.upper() for q in quotes}
    rows: list[dict] = []
    for date in sorted(rates):
        day = rates[date]
        if not isinstance(day, dict):
            continue
        for quote, value in day.items():
            if quote.upper() not in wanted:
                continue
            try:
                rate = float(value)
            except (TypeError, ValueError):
                continue
            if rate <= 0:
                continue
            rows.append({
                "date": date, "quote": quote.upper(), "rate_per_usd": fmt(rate),
                "source": "frankfurter", "retrieved_at": retrieved_at,
            })
    return rows


def parse_payload(kind: str, body: bytes, retrieved_at: str,
                  quotes: list[str]) -> list[dict]:
    if kind == "ecb_sdmx_csv":
        return parse_ecb_csv(body.decode("utf-8-sig", "replace"), retrieved_at, quotes)
    if kind == "frankfurter_json":
        try:
            return parse_frankfurter_json(json.loads(body or b"{}"), retrieved_at, quotes)
        except ValueError:
            return []
    return []


# --- Window averages --------------------------------------------------------

def load_rates(path: Path | None = None) -> dict[str, dict[str, float]]:
    """{quote: {date: rate}} from the store; {} when nothing is stored yet."""
    path = path or (OUT_DIR / "rates_daily.csv")
    out: dict[str, dict[str, float]] = {}
    if not path.exists():
        return out
    with path.open(encoding="utf-8", newline="") as fh:
        for rec in csv.DictReader(fh):
            rate = parse_number(rec.get("rate_per_usd"))
            if rate is None or rate <= 0:
                continue
            out.setdefault(rec["quote"], {})[rec["date"]] = rate
    return out


def window_average(rates: dict[str, dict[str, float]], quote: str, yyyymm: str,
                   period_type: str = "MONTH") -> float | None:
    """Mean rate over the days a published window covers.

    A 10-day or 20-day customs window is averaged over those days only, so a
    flash print is converted on the rate that actually applied to it rather
    than on the whole month's. Only the business days present are averaged;
    a window with no observation at all returns None and the caller leaves the
    USD columns empty rather than inventing a rate.
    """
    by_date = rates.get(quote.upper())
    if not by_date or len(yyyymm) < 7:
        return None
    first, last = WINDOW_DAYS.get(period_type, (1, 31))
    prefix = yyyymm[:7]
    values = [rate for date, rate in by_date.items()
              if date.startswith(prefix) and first <= _day_of(date) <= last]
    return sum(values) / len(values) if values else None


def _day_of(date: str) -> int:
    try:
        return int(date[8:10])
    except ValueError:
        return 0


# --- Fetching ---------------------------------------------------------------

def _save_raw(name: str, content: bytes) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / name).write_bytes(content)


def _default_range(today: dt.date | None = None) -> tuple[str, str]:
    """Last 10 days: long enough to cover a holiday weekend, short enough to be cheap."""
    today = today or dt.date.today()
    return (today - dt.timedelta(days=10)).isoformat(), today.isoformat()


def fetch_range(start: str, end: str) -> int:
    cfg = _load_config()
    quotes = _quotes(cfg)
    retrieved_at = dt.date.today().isoformat()
    problems: list[str] = []
    rows: list[dict] = []
    used = ""
    for source in cfg["sources"]:
        url = source["url_template"].format(
            quotes="+".join(quotes) if source["kind"] == "ecb_sdmx_csv" else ",".join(quotes),
            start=start, end=end)
        try:
            resp = http_get(url)
        except Exception as err:  # noqa: BLE001 - try the next source, report at the end
            problems.append(f"{source['name']}: {type(err).__name__}: {err}")
            continue
        _save_raw(f"{source['name']}_{start}_{end}.txt", resp.content)
        rows = parse_payload(source["kind"], resp.content, retrieved_at, quotes)
        if rows:
            used = source["name"]
            break
        problems.append(f"{source['name']}: HTTP {resp.status_code}, no rows parsed")
    if not rows:
        raise RuntimeError("fx: no source returned rates — " + "; ".join(problems))
    added = append_dedup_csv(OUT_DIR / "rates_daily.csv", RATES_HEADER, rows, RATES_KEY)
    got = {q: sum(1 for r in rows if r["quote"] == q) for q in quotes}
    print(f"fx {start}..{end} via {used}: {len(rows)} rows ({got}), {added} new")
    if problems:
        print("  fell back after: " + "; ".join(problems))
    return added


def fetch_daily(start: str | None = None, end: str | None = None) -> int:
    if start and end:
        return fetch_range(start, end)
    default_start, default_end = _default_range()
    return fetch_range(start or default_start, end or default_end)


def backfill(start: str, end: str) -> int:
    """Year-sized chunks: one polite request per year, and one bad year cannot
    abort the walk."""
    total = 0
    for year in range(int(start[:4]), int(end[:4]) + 1):
        chunk_start = start if year == int(start[:4]) else f"{year}-01-01"
        chunk_end = end if year == int(end[:4]) else f"{year}-12-31"
        try:
            total += fetch_range(chunk_start, chunk_end)
        except Exception as err:  # noqa: BLE001
            print(f"  {year} failed ({type(err).__name__}: {err}); continuing")
    return total


def reparse() -> None:
    """Rebuild data/fx/rates_daily.csv from the raw payloads on disk."""
    cfg = _load_config()
    quotes = _quotes(cfg)
    kinds = {s["name"]: s["kind"] for s in cfg["sources"]}
    retrieved_at = dt.date.today().isoformat()
    rows: list[dict] = []
    for path in sorted(RAW_DIR.glob("*.txt")) if RAW_DIR.exists() else []:
        name = path.name.split("_")[0]
        kind = kinds.get(name)
        if not kind:
            continue
        rows += parse_payload(kind, path.read_bytes(), retrieved_at, quotes)
    out = OUT_DIR / "rates_daily.csv"
    if rows:
        write_csv(out, RATES_HEADER, [])
        added = append_dedup_csv(out, RATES_HEADER, rows, RATES_KEY)
        print(f"rates_daily.csv: rebuilt with {added} rows")
    elif out.exists():
        out.unlink()
        print("rates_daily.csv: removed (no raw payloads)")


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd = argv[0]
    if cmd == "daily":
        fetch_daily(*(argv[1:3] or []))
    elif cmd == "backfill":
        if len(argv) < 3:
            print(__doc__)
            return 2
        backfill(argv[1], argv[2])
    elif cmd == "reparse":
        reparse()
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
