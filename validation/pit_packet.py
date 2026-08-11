"""Build point-in-time evidence packets from the local Sharadar DuckDB.

Constitution Section 18 ("evidence in, verdicts out"): a blind rerun context
may receive only evidence knowable on the cutoff date — no verdicts, no
outcomes, no identity. This script produces that packet as one self-contained
markdown file, ready to attach to a fresh chat.

Point-in-time rules applied here:
- Fundamentals come from SF1 as-reported dimensions (default ARQ) filtered on
  ``datekey <= cutoff``: datekey is the filing date, so those rows were public
  knowledge on the cutoff date, and restatements arrive as new datekey rows.
- Valuation comes from DAILY at the last date on or before the cutoff.
- Insider activity comes from SF2 filtered on ``filingdate <= cutoff``.
- Prices (SEP) are included only with --unmasked: Section 7 masks share-price
  performance during first scoring.

Masking (Section 7): company name, ticker, exchange, industry and geography
are withheld; monetary figures are coarsened to two significant figures;
share counts are omitted. A separate key file records the label -> ticker
mapping for later scoring. NEVER attach the key file to a rerun chat.

Usage:
    python -m validation.pit_packet AAPL --cutoff 2025-11-01
    python -m validation.pit_packet AJINY IBDNF --cutoff 2025-11-01 --unmasked
"""

import argparse
import datetime as dt
import os
import re
import string

import duckdb

DEFAULT_DB_PATH = "data/sharadar.duckdb"
DEFAULT_OUT_DIR = "packets"

TASK_BLOCK = """\
## TASK

Using only the evidence in this packet, produce:

1. A one-page thesis or anti-thesis for each company presented.
2. A decision per company: ACT / PASS / WATCH (with an intended position
   size band if ACT).
3. Two to five explicit probability forecasts, each with a resolution date.
4. The single most important falsifier: what observable fact would kill the
   thesis?

Do not attempt to identify the company. Evaluate the economics exactly as
presented. Assume nothing beyond the packet and general knowledge a careful
analyst had on the cutoff date.
"""


# ---------------------------------------------------------------- helpers


def _columns(con, table: str) -> set:
    rows = con.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'main' AND table_name = ?",
        [table],
    ).fetchall()
    return {r[0] for r in rows}


def _table_exists(con, table: str) -> bool:
    return bool(_columns(con, table))


def _rows(con, sql: str, params: list) -> list[dict]:
    cur = con.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _money(x, masked: bool) -> str:
    """$1.23B-style rendering; coarsened to 2 significant figures if masked."""
    if x is None:
        return "n/a"
    x = float(x)
    sign = "-" if x < 0 else ""
    v = abs(x)
    if masked and v > 0:
        exp = len(str(int(v))) - 1
        v = round(v, -(exp - 1)) if exp >= 1 else v
    for unit, scale in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if v >= scale:
            return f"{sign}${v / scale:.4g}{unit}"
    return f"{sign}${v:.4g}"


def _pct(x) -> str:
    return "n/a" if x is None else f"{float(x) * 100:.1f}%"


def _ratio(x) -> str:
    return "n/a" if x is None else f"{float(x):.1f}"


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join(" --- " for _ in headers) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


# ---------------------------------------------------------------- sections


def profile_section(con, ticker: str, masked: bool) -> str:
    if not _table_exists(con, "tickers"):
        return "_No ticker master data available._"
    cols = _columns(con, "tickers")
    rows = _rows(
        con,
        'SELECT * FROM tickers WHERE ticker = ? ORDER BY "table" LIMIT 1',
        [ticker],
    )
    if not rows:
        return "_No profile row found._"
    row = rows[0]
    out = []
    if masked:
        keep = [("scalemarketcap", "Market-cap scale"),
                ("scalerevenue", "Revenue scale"),
                ("category", "Security category")]
        for col, label in keep:
            if col in cols and row.get(col):
                out.append(f"- {label}: {row[col]}")
        if row.get("firstpricedate"):
            out.append(f"- Listed since: ~{str(row['firstpricedate'])[:4]}")
        out.append("- Name, exchange, industry, and geography withheld (masked packet)")
    else:
        for col, label in [("name", "Name"), ("exchange", "Exchange"),
                           ("sector", "Sector"), ("industry", "Industry"),
                           ("famaindustry", "Fama industry"),
                           ("location", "Location"),
                           ("scalemarketcap", "Market-cap scale"),
                           ("firstpricedate", "First price date")]:
            if col in cols and row.get(col):
                out.append(f"- {label}: {row[col]}")
    return "\n".join(out) if out else "_No profile fields available._"


def fundamentals_section(con, ticker: str, cutoff: str, masked: bool,
                         dimension: str, quarters: int) -> str:
    if not _table_exists(con, "sf1"):
        return "_No fundamentals table available._"
    cols = _columns(con, "sf1")
    wanted = [c for c in ["reportperiod", "datekey", "revenue", "grossmargin",
                          "netmargin", "opinc", "netinc", "ncfo", "capex",
                          "fcf", "debt", "cashneq", "equity", "roe",
                          "dividends", "epsdil"] if c in cols]
    rows = _rows(
        con,
        f"SELECT {', '.join(wanted)} FROM sf1 "
        "WHERE ticker = ? AND dimension = ? AND datekey <= ? "
        f"ORDER BY datekey DESC LIMIT {int(quarters)}",
        [ticker, dimension, cutoff],
    )
    if not rows:
        return "_No as-reported fundamentals on or before the cutoff._"
    rows.reverse()  # oldest first

    headers, render = [], []
    def add(col, label, fn):
        if col in wanted:
            headers.append(label)
            render.append((col, fn))

    add("reportperiod", "Period", str)
    add("datekey", "Filed", str)
    add("revenue", "Revenue", lambda v: _money(v, masked))
    add("grossmargin", "Gross m.", _pct)
    add("netmargin", "Net m.", _pct)
    add("opinc", "Op income", lambda v: _money(v, masked))
    add("netinc", "Net income", lambda v: _money(v, masked))
    add("fcf", "FCF", lambda v: _money(v, masked))
    add("debt", "Debt", lambda v: _money(v, masked))
    add("cashneq", "Cash", lambda v: _money(v, masked))
    add("equity", "Equity", lambda v: _money(v, masked))
    add("roe", "ROE", _pct)
    add("dividends", "Dividends", lambda v: _money(v, masked))
    if not masked:
        add("epsdil", "EPS (dil)", lambda v: "n/a" if v is None else f"{float(v):.2f}")

    body = [[fn(r.get(col)) for col, fn in render] for r in rows]
    note = ("\nAs-reported figures; each row was public as of its Filed date. "
            "Monetary values coarsened; share counts omitted."
            if masked else
            "\nAs-reported figures; each row was public as of its Filed date.")
    return _md_table(headers, body) + note


def valuation_section(con, ticker: str, cutoff: str, masked: bool) -> str:
    if not _table_exists(con, "daily"):
        return "_No daily valuation table available._"
    cols = _columns(con, "daily")
    wanted = [c for c in ["date", "marketcap", "ev", "pe", "pb", "ps",
                          "evebitda"] if c in cols]
    rows = _rows(
        con,
        f"SELECT {', '.join(wanted)} FROM daily "
        "WHERE ticker = ? AND date <= ? ORDER BY date DESC LIMIT 1",
        [ticker, cutoff],
    )
    if not rows:
        return "_No valuation snapshot on or before the cutoff._"
    r = rows[0]
    out = [f"- Snapshot date: {r.get('date')}"]
    if "marketcap" in r:
        out.append(f"- Market cap: {_money((r['marketcap'] or 0) * 1e6, masked)}")
    if "ev" in r:
        out.append(f"- Enterprise value: {_money((r['ev'] or 0) * 1e6, masked)}")
    for col, label in [("pe", "P/E"), ("pb", "P/B"), ("ps", "P/S"),
                       ("evebitda", "EV/EBITDA")]:
        if col in r:
            out.append(f"- {label}: {_ratio(r[col])}")
    return "\n".join(out)


def insider_section(con, ticker: str, cutoff: str) -> str:
    if not _table_exists(con, "sf2"):
        return "_No insider table available._"
    cols = _columns(con, "sf2")
    if not {"filingdate", "transactioncode"} <= cols:
        return "_Insider table lacks expected columns._"
    value_expr = ("sum(transactionvalue)" if "transactionvalue" in cols
                  else "NULL")
    since = (dt.date.fromisoformat(cutoff) - dt.timedelta(days=365)).isoformat()
    rows = _rows(
        con,
        f"SELECT transactioncode, count(*) AS n, {value_expr} AS total_value "
        "FROM sf2 WHERE ticker = ? AND filingdate <= ? AND filingdate >= ? "
        "AND transactioncode IN ('P', 'S') GROUP BY transactioncode",
        [ticker, cutoff, since],
    )
    if not rows:
        return "_No open-market insider buys or sells filed in the year before the cutoff._"
    label = {"P": "Open-market buys", "S": "Open-market sells"}
    out = []
    for r in sorted(rows, key=lambda x: x["transactioncode"]):
        line = f"- {label[r['transactioncode']]}: {r['n']} filings"
        if r.get("total_value") is not None:
            line += f", total {_money(r['total_value'], masked=True)}"
        out.append(line)
    return "\n".join(out)


def price_section(con, ticker: str, cutoff: str) -> str:
    """Unmasked packets only (Section 7 masks price performance)."""
    if not _table_exists(con, "sep"):
        return "_No price table available._"
    rows = _rows(
        con,
        "SELECT date, closeadj FROM sep WHERE ticker = ? AND date <= ? "
        "ORDER BY date DESC LIMIT 505",
        [ticker, cutoff],
    )
    if not rows:
        return "_No prices on or before the cutoff._"
    monthly, seen = [], set()
    for r in rows:  # newest first; keep last close of each month
        key = str(r["date"])[:7]
        if key not in seen:
            seen.add(key)
            monthly.append(r)
    monthly = list(reversed(monthly[:25]))
    body = [[str(r["date"]), "n/a" if r["closeadj"] is None
             else f"{float(r['closeadj']):.2f}"] for r in monthly]
    return _md_table(["Month end", "Adj close"], body)


# ---------------------------------------------------------------- assembly


def build_packet(db_path: str, tickers: list[str], cutoff: str,
                 masked: bool = True, labels: list[str] | None = None,
                 dimension: str = "ARQ", quarters: int = 12) -> tuple[str, str]:
    """Return (packet_markdown, key_markdown)."""
    dt.date.fromisoformat(cutoff)  # validate early
    if labels and len(labels) != len(tickers):
        raise ValueError("--labels must match the number of tickers")
    if not labels:
        labels = ([f"Company {string.ascii_uppercase[i]}" for i in range(len(tickers))]
                  if masked else list(tickers))

    con = duckdb.connect(db_path, read_only=True)
    try:
        packet = [
            "# POINT-IN-TIME EVIDENCE PACKET",
            "",
            f"**Cutoff date: {cutoff}.** Every fact below was publicly knowable "
            "on or before this date. Nothing in this packet describes later "
            "events or outcomes.",
            "",
            TASK_BLOCK,
        ]
        key = [
            "# PACKET KEY — DO NOT ATTACH TO A RERUN CHAT",
            "",
            f"- Cutoff: {cutoff}",
            f"- Masked: {masked}",
            f"- Source: {db_path} (dimension {dimension}, {quarters} quarters)",
            f"- Generated: {dt.date.today().isoformat()}",
            "- Caveat: the local mirror keeps the vendor's latest view; "
            "in-place error corrections since the cutoff are not excluded "
            "(as-reported restatements are, via datekey).",
            "",
        ]
        for ticker, label in zip(tickers, labels):
            if not _rows(con, "SELECT 1 FROM sf1 WHERE ticker = ? LIMIT 1", [ticker]):
                raise SystemExit(f"Ticker {ticker!r} not found in sf1 — check spelling.")
            key.append(f"- **{label}** = {ticker}")
            packet += [f"---\n\n## {label}", ""]
            packet += ["### Profile", "", profile_section(con, ticker, masked), ""]
            packet += ["### As-reported fundamentals", "",
                       fundamentals_section(con, ticker, cutoff, masked,
                                            dimension, quarters), ""]
            packet += ["### Valuation snapshot", "",
                       valuation_section(con, ticker, cutoff, masked), ""]
            packet += ["### Insider activity (12 months to cutoff)", "",
                       insider_section(con, ticker, cutoff), ""]
            if not masked:
                packet += ["### Price history (month-end adjusted closes)", "",
                           price_section(con, ticker, cutoff), ""]
    finally:
        con.close()
    return "\n".join(packet) + "\n", "\n".join(key) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m validation.pit_packet",
        description="Build a point-in-time evidence packet for blind reruns.",
    )
    parser.add_argument("tickers", nargs="+", help="ticker(s), e.g. AAPL")
    parser.add_argument("--cutoff", required=True, help="cutoff date YYYY-MM-DD")
    parser.add_argument("--db", default=DEFAULT_DB_PATH)
    parser.add_argument("--out", default=DEFAULT_OUT_DIR, help="output directory")
    parser.add_argument("--unmasked", action="store_true",
                        help="include identity and price history (Section 7 off)")
    parser.add_argument("--labels", default=None,
                        help="comma-separated mask labels, one per ticker")
    parser.add_argument("--dimension", default="ARQ",
                        help="SF1 as-reported dimension (default ARQ)")
    parser.add_argument("--quarters", type=int, default=12)
    args = parser.parse_args()

    tickers = [t.upper() for t in args.tickers]
    labels = [l.strip() for l in args.labels.split(",")] if args.labels else None
    masked = not args.unmasked
    packet, keytext = build_packet(args.db, tickers, args.cutoff, masked=masked,
                                   labels=labels, dimension=args.dimension,
                                   quarters=args.quarters)

    os.makedirs(os.path.join(args.out, "keys"), exist_ok=True)
    # Masked packet filenames must not leak the ticker.
    stem_name = (labels[0] if labels else "case") if masked else "-".join(tickers)
    stem = f"{args.cutoff}_{_slug(stem_name)}"
    packet_path = os.path.join(args.out, f"packet_{stem}.md")
    key_path = os.path.join(args.out, "keys", f"key_{stem}.md")
    with open(packet_path, "w") as f:
        f.write(packet)
    with open(key_path, "w") as f:
        f.write(keytext)

    print(f"Packet:  {packet_path}   <- attach THIS to a fresh chat")
    print(f"Key:     {key_path}   <- keep local; never attach")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
