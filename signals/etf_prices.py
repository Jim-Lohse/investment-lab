"""Daily prices for the funds the CFTC markets stand in for, plus GLD's gold holdings.

The CFTC weekly summary asks whether positioning shifts come before moves in
SPY, QQQ, GLD, USO and UUP. That needs the funds' own history: adjusted daily
closes (dividends and splits folded in) for price moves, and a flow series for
money going in or out. The only free, primary flow history among the five is
GLD's: the trust publishes the gold it holds every day, and a change in tonnes
held is creation or redemption of shares, i.e. money in or out. The others
publish only today's shares outstanding.

Sources (keyless, see signals/config/etf_endpoints.json):
  prices  Yahoo Finance chart API (adjusted close), stooq CSV as fallback
  GLD     spdrgoldshares.com daily archive CSV

Output (rebuilt from the raw payloads each run, so a revision is picked up):
  data/prices/etf_daily.csv   — date, ticker, close, adj_close, source
  data/flows/gld_holdings.csv — date, tonnes, ounces
  data/prices/raw/, data/flows/raw/ — the payloads as fetched

Usage:
    python -m signals.etf_prices fetch
    python -m signals.etf_prices reparse
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
import sys

from .common import CONFIG_DIR, DATA_DIR, fmt, http_get, parse_number, write_csv

PRICES_DIR = DATA_DIR / "prices"
FLOWS_DIR = DATA_DIR / "flows"
PRICES_HEADER = ["date", "ticker", "close", "adj_close", "source"]
GLD_HEADER = ["date", "tonnes", "ounces"]


def _load_config() -> dict:
    return json.loads((CONFIG_DIR / "etf_endpoints.json").read_text("utf-8"))


# --- Parsing ----------------------------------------------------------------

def parse_yahoo_chart(payload: dict, ticker: str) -> list[dict]:
    """Yahoo v8 chart JSON -> daily rows. A day missing its close is dropped."""
    try:
        result = payload["chart"]["result"][0]
        stamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
        adj = result["indicators"].get("adjclose", [{}])[0].get("adjclose") or closes
        offset = int(result.get("meta", {}).get("gmtoffset", 0))
    except (KeyError, IndexError, TypeError):
        return []
    rows = []
    for ts, close, adj_close in zip(stamps, closes, adj):
        if close is None or adj_close is None:
            continue
        day = dt.datetime.fromtimestamp(ts + offset, tz=dt.timezone.utc).date()
        rows.append({"date": day.isoformat(), "ticker": ticker, "close": fmt(round(close, 4)),
                     "adj_close": fmt(round(adj_close, 4)), "source": "yahoo"})
    return rows


def parse_stooq_csv(text: str, ticker: str) -> list[dict]:
    """stooq daily CSV (Date,Open,High,Low,Close,Volume). stooq's close is
    already adjusted for splits and dividends, so it fills both columns."""
    rows = []
    for rec in csv.DictReader(io.StringIO(text)):
        close = parse_number(rec.get("Close"))
        date = (rec.get("Date") or "").strip()
        if close is None or len(date) != 10:
            continue
        rows.append({"date": date, "ticker": ticker, "close": fmt(close),
                     "adj_close": fmt(close), "source": "stooq"})
    return rows


def parse_gld_archive(text: str) -> list[dict]:
    """GLD daily archive CSV -> date, tonnes, ounces.

    The file has a few preamble lines, then a header row naming the columns.
    Columns are found by name ("Date", "Tonnes", "Ounces"), not position, and
    days marked as holidays or with no figure are dropped rather than filled.
    """
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines)
                  if line.lower().lstrip('"').startswith("date") and "tonne" in line.lower()), None)
    if start is None:
        return []
    reader = csv.reader(lines[start:])
    header = [h.strip().lower() for h in next(reader)]
    i_date = header.index(next(h for h in header if h.startswith("date")))
    i_tonnes = next((i for i, h in enumerate(header) if "tonne" in h), None)
    i_oz = next((i for i, h in enumerate(header) if "ounce" in h), None)
    rows = []
    for rec in reader:
        if len(rec) <= max(i_date, i_tonnes or 0, i_oz or 0):
            continue
        day = _parse_date(rec[i_date])
        tonnes = parse_number(rec[i_tonnes]) if i_tonnes is not None else None
        if day is None or tonnes is None or tonnes <= 0:
            continue
        ounces = parse_number(rec[i_oz]) if i_oz is not None else None
        rows.append({"date": day, "tonnes": fmt(tonnes), "ounces": fmt(ounces)})
    return sorted({r["date"]: r for r in rows}.values(), key=lambda r: r["date"])


def _parse_date(text: str) -> str | None:
    text = text.strip()
    for pattern in ("%d-%b-%Y", "%d-%b-%y", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return dt.datetime.strptime(text, pattern).date().isoformat()
        except ValueError:
            continue
    return None


# --- Fetching ---------------------------------------------------------------

def fetch() -> None:
    cfg = _load_config()
    (PRICES_DIR / "raw").mkdir(parents=True, exist_ok=True)
    (FLOWS_DIR / "raw").mkdir(parents=True, exist_ok=True)
    start = int(dt.datetime.fromisoformat(cfg["start"]).replace(tzinfo=dt.timezone.utc).timestamp())
    end = int(dt.datetime.now(dt.timezone.utc).timestamp())
    failed = []
    for ticker in cfg["tickers"]:
        got = False
        try:
            url = cfg["yahoo_template"].format(ticker=ticker, start=start, end=end)
            resp = http_get(url)
            if parse_yahoo_chart(resp.json(), ticker):
                (PRICES_DIR / "raw" / f"yahoo_{ticker}.json").write_bytes(resp.content)
                got = True
        except Exception as err:  # noqa: BLE001 - fall back, report at the end
            print(f"  {ticker} yahoo: {type(err).__name__}: {err}")
        if not got:
            try:
                resp = http_get(cfg["stooq_template"].format(ticker=ticker.lower()))
                if parse_stooq_csv(resp.text, ticker):
                    (PRICES_DIR / "raw" / f"stooq_{ticker}.csv").write_bytes(resp.content)
                    got = True
            except Exception as err:  # noqa: BLE001
                print(f"  {ticker} stooq: {type(err).__name__}: {err}")
        if not got:
            failed.append(ticker)
    try:
        resp = http_get(cfg["gld_archive_url"])
        (FLOWS_DIR / "raw" / "gld_archive.csv").write_bytes(resp.content)
    except Exception as err:  # noqa: BLE001
        failed.append("GLD holdings")
        print(f"  GLD holdings: {type(err).__name__}: {err}")
    reparse()
    if failed:
        print("etf_prices: failed for " + ", ".join(failed))


def reparse() -> None:
    rows: list[dict] = []
    raw = PRICES_DIR / "raw"
    for path in sorted(raw.glob("yahoo_*.json")) if raw.exists() else []:
        rows += parse_yahoo_chart(json.loads(path.read_text("utf-8")), path.stem.split("_", 1)[1])
    have = {r["ticker"] for r in rows}
    for path in sorted(raw.glob("stooq_*.csv")) if raw.exists() else []:
        ticker = path.stem.split("_", 1)[1]
        if ticker not in have:  # stooq only fills a ticker Yahoo did not
            rows += parse_stooq_csv(path.read_text("utf-8", "replace"), ticker)
    rows.sort(key=lambda r: (r["ticker"], r["date"]))
    if rows:
        write_csv(PRICES_DIR / "etf_daily.csv", PRICES_HEADER,
                  [[r[c] for c in PRICES_HEADER] for r in rows])
    counts = {}
    for r in rows:
        counts[r["ticker"]] = counts.get(r["ticker"], 0) + 1
    print(f"etf_daily.csv: {len(rows)} rows {counts}")
    gld_raw = FLOWS_DIR / "raw" / "gld_archive.csv"
    if gld_raw.exists():
        gld = parse_gld_archive(gld_raw.read_text("utf-8-sig", "replace"))
        if gld:
            write_csv(FLOWS_DIR / "gld_holdings.csv", GLD_HEADER,
                      [[r[c] for c in GLD_HEADER] for r in gld])
        print(f"gld_holdings.csv: {len(gld)} rows"
              + (f", {gld[0]['date']} to {gld[-1]['date']}" if gld else " (parser found no rows)"))


def main(argv: list[str]) -> int:
    if argv[:1] == ["fetch"]:
        fetch()
    elif argv[:1] == ["reparse"]:
        reparse()
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
