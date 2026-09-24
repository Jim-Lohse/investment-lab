"""CFTC Commitments of Traders: who holds the futures, long and short, each week.

Every Tuesday the CFTC records the positions large traders hold in each U.S.
futures market and publishes them on Friday. For gold (COMEX, market code
088691) that says how many contracts speculative funds ("managed money") hold
long versus short, against the producers and swap dealers on the other side.

Source: the CFTC Public Reporting Environment, a Socrata site. Two routes to
the same rows (see signals/config/cftc_endpoints.json):

  soda3  POST /api/v3/views/{dataset}/query.json with a SoQL body.
         Socrata documents an app token as required here; set CFTC_APP_TOKEN.
  soda2  GET /resource/{dataset}.json?$query=... — keyless.

With no token the keyless route goes first; with one, SODA3 goes first. Either
falls back to the other on a refusal (401/403) or a network failure.

Output (append-only, first print wins):
  data/cftc/positions.csv  — report, date, market, trader group, long/short/spread
  data/cftc/raw/           — the JSON payloads, so a parser fix can be replayed

Usage:
    python -m signals.cftc_cot latest                        # last 10 weeks, gold, both reports
    python -m signals.cftc_cot latest disagg_fut 088691
    python -m signals.cftc_cot backfill 2015-01-01 disagg_fut 088691
    python -m signals.cftc_cot query legacy_fut "SELECT * WHERE contract_market_name = 'GOLD' ORDER BY report_date_as_yyyy_mm_dd DESC LIMIT 10"
    python -m signals.cftc_cot reparse
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys

from .common import (CONFIG_DIR, DATA_DIR, HTTPStatusError, append_dedup_csv,
                     fmt, http_request, parse_number, write_csv)

OUT_DIR = DATA_DIR / "cftc"
RAW_DIR = OUT_DIR / "raw"

POSITIONS_HEADER = ["report", "report_date", "market_code", "market_and_exchange",
                    "trader_group", "long", "short", "spread", "net",
                    "open_interest", "retrieved_at"]
POSITIONS_KEY = ["report", "report_date", "market_code", "trader_group"]

DEFAULT_REPORTS = ["legacy_fut", "disagg_fut"]
DEFAULT_MARKETS = ["088691"]
DATE_FIELD = "report_date_as_yyyy_mm_dd"

# Trader groups per report family: (long field, short field, spread field).
# Field names are copied from live rows (2026-09-24), typos included — the
# CFTC spells it "noncomm_postions_spread_all" and "swap__positions_short_all".
# TFF is left out until a live row has been checked; its rows still land in
# raw/ and can be normalized later with `reparse`.
GROUP_FIELDS = {
    "legacy": {
        "noncommercial": ("noncomm_positions_long_all", "noncomm_positions_short_all",
                          "noncomm_postions_spread_all"),
        "commercial": ("comm_positions_long_all", "comm_positions_short_all", None),
        "nonreportable": ("nonrept_positions_long_all", "nonrept_positions_short_all", None),
    },
    "disagg": {
        "producer_merchant": ("prod_merc_positions_long", "prod_merc_positions_short", None),
        "swap_dealer": ("swap_positions_long_all", "swap__positions_short_all",
                        "swap__positions_spread_all"),
        "managed_money": ("m_money_positions_long_all", "m_money_positions_short_all",
                          "m_money_positions_spread"),
        "other_reportable": ("other_rept_positions_long", "other_rept_positions_short",
                             "other_rept_positions_spread"),
        "nonreportable": ("nonrept_positions_long_all", "nonrept_positions_short_all", None),
    },
}


def _load_config() -> dict:
    return json.loads((CONFIG_DIR / "cftc_endpoints.json").read_text("utf-8"))


def _dataset(cfg: dict, report: str) -> str:
    try:
        return cfg["reports"][report]["dataset"]
    except KeyError:
        known = ", ".join(sorted(cfg["reports"]))
        raise ValueError(f"unknown report {report!r}; known: {known}") from None


# --- SoQL -------------------------------------------------------------------

def soql_literal(value: str) -> str:
    """Quote a string for SoQL: single quotes, embedded quotes doubled."""
    return "'" + str(value).replace("'", "''") + "'"


def build_query(market_codes: list[str], since: str | None = None,
                until: str | None = None, limit: int | None = None) -> str:
    """SoQL for the given contract markets, newest first.

    Filters on cftc_contract_market_code because cftc_commodity_code is padded
    inconsistently ('088' on older rows, '088 ' on recent ones), so an equality
    test on '088' silently drops the recent weeks.
    `id` breaks ties so paging is stable.
    """
    if not market_codes:
        raise ValueError("at least one market code is required")
    codes = ", ".join(soql_literal(c) for c in market_codes)
    where = [f"cftc_contract_market_code IN ({codes})"]
    if since:
        where.append(f"{DATE_FIELD} >= {soql_literal(since + 'T00:00:00')}")
    if until:
        where.append(f"{DATE_FIELD} <= {soql_literal(until + 'T00:00:00')}")
    soql = f"SELECT * WHERE {' AND '.join(where)} ORDER BY {DATE_FIELD} DESC, id"
    if limit:
        soql += f" LIMIT {int(limit)}"
    return soql


# --- Transport --------------------------------------------------------------

# page_number=None runs the query exactly as written, with no paging added.

def _soda3(cfg: dict, dataset: str, soql: str, token: str,
           page_number: int | None, page_size: int) -> list[dict]:
    url = cfg["base_url"] + cfg["soda3_path"].format(dataset=dataset)
    body: dict = {"query": soql, "includeSynthetic": False}
    if page_number is not None:
        body["page"] = {"pageNumber": page_number, "pageSize": page_size}
    headers = {"X-App-Token": token} if token else {}
    return _rows(http_request("POST", url, json_body=body, headers=headers).json())


def _soda2(cfg: dict, dataset: str, soql: str, token: str,
           page_number: int | None, page_size: int) -> list[dict]:
    url = cfg["base_url"] + cfg["soda2_path"].format(dataset=dataset)
    if page_number is not None:
        soql = f"{soql} LIMIT {page_size} OFFSET {(page_number - 1) * page_size}"
    headers = {"X-App-Token": token} if token else {}
    return _rows(http_request("GET", url, params={"$query": soql}, headers=headers).json())


def _rows(payload) -> list[dict]:
    """Both routes answer with a JSON array of flat records; anything else is
    an error envelope and is raised, never read as zero rows."""
    if isinstance(payload, list) and all(isinstance(r, dict) for r in payload):
        return payload
    raise RuntimeError(f"cftc: unexpected response shape: {str(payload)[:300]}")


def _routes(token: str) -> list[tuple[str, object]]:
    if token:
        return [("soda3", _soda3), ("soda2", _soda2)]
    return [("soda2", _soda2), ("soda3", _soda3)]


def run_query(report: str, soql: str, *, paginate: bool = False,
              token: str | None = None) -> tuple[list[dict], str]:
    """Run a SoQL query against a report. Returns (rows, route used).

    With paginate=False the query runs once, as written (its own LIMIT
    applies; with none, the server's default page). With paginate=True pages
    are walked until a short one, so the query must not carry its own LIMIT.
    """
    cfg = _load_config()
    dataset = _dataset(cfg, report)
    token = os.environ.get("CFTC_APP_TOKEN", "") if token is None else token
    page_size = int(cfg.get("page_size", 1000))
    problems: list[str] = []
    for name, route in _routes(token):
        try:
            if not paginate:
                return route(cfg, dataset, soql, token, None, page_size), name
            rows: list[dict] = []
            page = 1
            while True:
                batch = route(cfg, dataset, soql, token, page, page_size)
                rows += batch
                if len(batch) < page_size:
                    return rows, name
                page += 1
        except HTTPStatusError as err:
            if err.status not in (401, 403):
                raise  # a 400 is a bad query; the other route would refuse it too
            problems.append(f"{name}: {err}")
        except RuntimeError as err:
            problems.append(f"{name}: {err}")
    raise RuntimeError("cftc: every route failed — " + "; ".join(problems))


# --- Parsing ----------------------------------------------------------------

def report_family(report: str) -> str:
    return report.split("_", 1)[0]


def normalize(report: str, records: list[dict], retrieved_at: str) -> list[dict]:
    """Raw COT records -> one row per (date, market, trader group).

    A group whose long or short field is absent is skipped, not zero-filled:
    a missing field means the mapping is wrong, and a zero would read as a
    real position.
    """
    groups = GROUP_FIELDS.get(report_family(report), {})
    rows: list[dict] = []
    for rec in records:
        date = str(rec.get(DATE_FIELD, ""))[:10]
        code = str(rec.get("cftc_contract_market_code", "")).strip()
        if not date or not code:
            continue
        for group, (f_long, f_short, f_spread) in groups.items():
            long_ = parse_number(rec.get(f_long))
            short = parse_number(rec.get(f_short))
            if long_ is None or short is None:
                continue
            spread = parse_number(rec.get(f_spread)) if f_spread else None
            rows.append({
                "report": report, "report_date": date, "market_code": code,
                "market_and_exchange": str(rec.get("market_and_exchange_names", "")).strip(),
                "trader_group": group, "long": fmt(long_), "short": fmt(short),
                "spread": fmt(spread), "net": fmt(long_ - short),
                "open_interest": fmt(parse_number(rec.get("open_interest_all"))),
                "retrieved_at": retrieved_at,
            })
    return rows


# --- Fetching ---------------------------------------------------------------

def _save_raw(report: str, label: str, records: list[dict]) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{report}_{label}.json"
    path.write_text(json.dumps(records, indent=1, sort_keys=True), encoding="utf-8")


def fetch(report: str, market_codes: list[str], since: str | None = None,
          until: str | None = None) -> int:
    soql = build_query(market_codes, since, until)
    records, route = run_query(report, soql, paginate=True)
    retrieved_at = dt.date.today().isoformat()
    label = f"{'-'.join(market_codes)}_{since or 'start'}_{until or retrieved_at}"
    _save_raw(report, label, records)
    rows = normalize(report, records, retrieved_at)
    added = append_dedup_csv(OUT_DIR / "positions.csv", POSITIONS_HEADER, rows,
                             POSITIONS_KEY)
    latest = max((r["report_date"] for r in rows), default="none")
    print(f"cftc {report} {','.join(market_codes)} via {route}: {len(records)} records, "
          f"{len(rows)} group rows, {added} new, latest {latest}")
    return added


def latest(reports: list[str], market_codes: list[str], weeks: int = 10) -> int:
    since = (dt.date.today() - dt.timedelta(weeks=weeks)).isoformat()
    return sum(fetch(r, market_codes, since) for r in reports)


def reparse() -> None:
    """Rebuild data/cftc/positions.csv from the raw payloads on disk."""
    cfg = _load_config()
    retrieved_at = dt.date.today().isoformat()
    rows: list[dict] = []
    for path in sorted(RAW_DIR.glob("*.json")) if RAW_DIR.exists() else []:
        report = next((r for r in cfg["reports"] if path.name.startswith(r + "_")), None)
        if report:
            rows += normalize(report, json.loads(path.read_text("utf-8")), retrieved_at)
    out = OUT_DIR / "positions.csv"
    write_csv(out, POSITIONS_HEADER, [])
    added = append_dedup_csv(out, POSITIONS_HEADER, rows, POSITIONS_KEY)
    print(f"positions.csv: rebuilt with {added} rows")


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "latest":
        reports = [rest[0]] if rest else DEFAULT_REPORTS
        latest(reports, rest[1:] or DEFAULT_MARKETS)
    elif cmd == "backfill" and len(rest) >= 2:
        fetch(rest[1], rest[2:] or DEFAULT_MARKETS, since=rest[0])
    elif cmd == "query" and len(rest) == 2:
        rows, route = run_query(rest[0], rest[1])
        print(json.dumps(rows, indent=1))
        print(f"{len(rows)} rows via {route}", file=sys.stderr)
    elif cmd == "reparse":
        reparse()
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
