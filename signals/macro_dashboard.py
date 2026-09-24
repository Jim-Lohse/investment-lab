"""Macro dashboard: one weekly snapshot of rates, the dollar, gold, oil, stocks
and the global trade pulse, for tracking trends over weeks to months.

Every figure the dashboard page shows is computed here from the stored tables,
never typed by hand. For each series: the latest value and its date; the
change over 4, 13 and 52 weeks; where the latest value sits among all weekly
readings in the stored history ("higher than X% of weeks since <start>"); and
a weekly series for the chart (the last reading on or before each Friday).

This is situational awareness, not a signal: data/derived/cftc_leadlag.md found
that CFTC positioning does not lead the funds' prices at 1-4 weeks, and the one
early-warning pattern that held (GLD's own recent flows) is shown as such.

Inputs (all already produced by the workflow):
  data/rates/treasury_daily.csv     signals/treasury_yields.py
  data/prices/etf_daily.csv         signals/etf_prices.py
  data/flows/gld_holdings.csv       signals/etf_prices.py
  data/derived/cftc_flows.csv       signals/cftc_cot.py
  data/derived/{taiwan,korea,japan}_signals.csv   signals/compute_signals.py

Output:
  data/derived/macro_dashboard.json   the numbers
  data/derived/macro_dashboard.html   the page (dashboard/macro_template.html
                                      with the numbers embedded)

Usage:
    python -m signals.macro_dashboard
"""

from __future__ import annotations

import bisect
import csv
import datetime as dt
import json
import sys
from pathlib import Path

from .common import DATA_DIR, REPO_ROOT, parse_number

DERIVED = DATA_DIR / "derived"
TEMPLATE = REPO_ROOT / "dashboard" / "macro_template.html"
CHART_WEEKS = 156  # three years of weekly points per chart


# --- Series helpers -----------------------------------------------------------

def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def daily(rows: list[dict], date_key: str, value_key: str, **match) -> list[tuple[str, float]]:
    out = []
    for r in rows:
        if any(r.get(k) != v for k, v in match.items()):
            continue
        v = parse_number(r.get(value_key))
        if v is not None:
            out.append((r[date_key], v))
    return sorted(out)


def weekly(series: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """Last reading on or before each Friday, labelled with that Friday."""
    if not series:
        return []
    out: dict[str, float] = {}
    for day, v in series:
        d = dt.date.fromisoformat(day)
        friday = d + dt.timedelta(days=(4 - d.weekday()) % 7)
        out[friday.isoformat()] = v  # later days in the week overwrite earlier ones
    return sorted(out.items())


def value_weeks_ago(wk: list[tuple[str, float]], weeks: int) -> float | None:
    if len(wk) <= weeks:
        return None
    return wk[-1 - weeks][1]


def rank_pct(wk: list[tuple[str, float]], value: float) -> float | None:
    """Share of all weekly readings in the history strictly below `value`."""
    hist = sorted(v for _, v in wk)
    if len(hist) < 52:
        return None
    return round(100.0 * bisect.bisect_left(hist, value) / len(hist))


def describe(name: str, series: list[tuple[str, float]], unit: str,
             change: str = "abs", note: str = "") -> dict | None:
    """Latest value, 4/13/52-week changes, rank in history, chart points.

    change="abs" gives changes in the series' own unit (yields, positions);
    change="pct" gives percent changes (prices, holdings).
    """
    if not series:
        return None
    wk = weekly(series)
    last_day, last = series[-1]
    item = {"name": name, "unit": unit, "as_of": last_day, "value": last, "note": note,
            "since": wk[0][0], "rank_pct": rank_pct(wk, last), "changes": {}}
    for label, n in (("4w", 4), ("13w", 13), ("52w", 52)):
        past = value_weeks_ago(wk, n)
        if past is None:
            item["changes"][label] = None
        elif change == "pct":
            item["changes"][label] = round(100.0 * (last / past - 1), 2) if past else None
        else:
            item["changes"][label] = round(last - past, 4)
    item["change_kind"] = change
    item["chart"] = [[d, round(v, 4)] for d, v in wk[-CHART_WEEKS:]]
    return item


# --- Panels -----------------------------------------------------------------

def rates_panel() -> dict:
    rows = read_csv(DATA_DIR / "rates" / "treasury_daily.csv")
    items = []
    for key, name in (("y2y", "2-year Treasury yield"), ("y10y", "10-year Treasury yield"),
                      ("gap_2s10s", "Gap: 10-year minus 2-year"),
                      ("gap_3m10y", "Gap: 10-year minus 3-month")):
        s = daily(rows, "date", key)
        d = describe(name, s, "percentage points" if key.startswith("gap") else "%", "abs")
        if d:
            if key.startswith("gap"):
                d["inverted"] = d["value"] < 0
                d["streak"] = sign_streak(s)
            items.append(d)
    return {"id": "rates", "title": "Interest rates and the yield curve", "items": items,
            "explainer": ("The 2-year yield tracks where the bond market expects the Federal "
                          "Reserve's rate to be over the next two years. The 10-year reflects "
                          "long-run growth and inflation expectations. When the gap between them "
                          "turns negative (an inverted curve), the market expects rate cuts, "
                          "usually because it expects a slowdown. Inversions have come before most "
                          "U.S. recessions of the past 50 years, with lead times from months to "
                          "about two years, and some false alarms.")}


def sign_streak(series: list[tuple[str, float]]) -> dict | None:
    """How long the gap has been on its current side of zero."""
    if not series:
        return None
    sign = series[-1][1] >= 0
    start = series[-1][0]
    for day, v in reversed(series):
        if (v >= 0) != sign:
            break
        start = day
    return {"positive": sign, "since": start}


def cftc(flows: list[dict], report: str, code: str, group: str) -> list[tuple[str, float]]:
    return daily(flows, "report_date", "net", report=report, market_code=code, trader_group=group)


def market_panels() -> list[dict]:
    prices = read_csv(DATA_DIR / "prices" / "etf_daily.csv")
    flows = read_csv(DERIVED / "cftc_flows.csv")
    gld = read_csv(DATA_DIR / "flows" / "gld_holdings.csv")

    def price(t, name):
        return describe(name, daily(prices, "date", "adj_close", ticker=t), "USD", "pct",
                        "Price including dividends.")

    def pos(report, code, group, name):
        return describe(name, cftc(flows, report, code, group), "contracts", "abs",
                        "Contracts betting on a rise minus contracts betting on a fall, as of "
                        "Tuesday. Situational awareness only: tested, it does not lead prices.")

    return [
        {"id": "dollar", "title": "Dollar", "items": [x for x in (
            price("UUP", "Dollar fund (UUP)"),
            pos("tff_fut", "098662", "leveraged_money", "Hedge funds, dollar-index futures"),
            pos("tff_fut", "098662", "asset_manager", "Institutions, dollar-index futures"),
        ) if x]},
        {"id": "gold", "title": "Gold", "items": [x for x in (
            price("GLD", "Gold fund (GLD)"),
            describe("Gold held by GLD", daily(gld, "date", "tonnes"), "tonnes", "pct",
                     "Money into or out of GLD, measured in gold held. Tested: money moving in "
                     "or out tends to keep moving the same way for weeks."),
            pos("disagg_fut", "088691", "managed_money", "Hedge funds, gold futures"),
        ) if x]},
        {"id": "oil", "title": "Oil", "items": [x for x in (
            price("USO", "Oil fund (USO)"),
            pos("disagg_fut", "067651", "managed_money", "Hedge funds, WTI crude futures"),
        ) if x]},
        {"id": "stocks", "title": "Stocks", "items": [x for x in (
            price("SPY", "S&P 500 fund (SPY)"),
            price("QQQ", "Nasdaq-100 fund (QQQ)"),
            pos("tff_fut", "13874A", "asset_manager", "Institutions, S&P 500 futures"),
            pos("tff_fut", "13874A", "leveraged_money", "Hedge funds, S&P 500 futures"),
            pos("tff_fut", "209742", "asset_manager", "Institutions, Nasdaq-100 futures"),
            pos("tff_fut", "209742", "leveraged_money", "Hedge funds, Nasdaq-100 futures"),
        ) if x]},
    ]


def trade_panel() -> dict:
    """Headline growth rates, compared with the same period a year earlier."""
    items = []
    tw = [r for r in read_csv(DERIVED / "taiwan_signals.csv") if r["group"] == "all_listed"]
    tw.sort(key=lambda r: r["report_month"])
    if tw:
        items.append(trade_item("Taiwan: revenue of all listed companies", tw,
                                "report_month", "agg_yoy_pct", None,
                                "Monthly, filed by the 10th of the next month."))
    kr = [r for r in read_csv(DERIVED / "korea_signals.csv") if r["item"] == "exp:TOTAL"]
    kr.sort(key=lambda r: (r["period"], {"D10": 0, "D20": 1, "MONTH": 2}.get(r["period_type"], 3)))
    if kr:
        items.append(trade_item("Korea: total exports", kr, "period", "yoy_pct", "period_type",
                                "The earliest read each month: the first 10 days, the first 20, "
                                "then the full month. Already in U.S. dollars."))
    jp = [r for r in read_csv(DERIVED / "japan_signals.csv")
          if r["item"] == "E:Grand Total" and r["source"] == "press_release"]
    jp.sort(key=lambda r: (r["period"], {"D10": 0, "D20": 1, "MONTH": 2}.get(r["period_type"], 3)))
    if jp:
        it = trade_item("Japan: total exports", jp, "period", "yoy_pct", "period_type",
                        "Growth in yen and in U.S. dollars; the difference is the weaker yen.")
        it["value_usd"] = parse_number(jp[-1].get("yoy_pct_usd"))
        items.append(it)
    return {"id": "trade", "title": "Global trade pulse", "items": items,
            "explainer": ("Growth compared with the same period a year earlier, from the lab's "
                          "existing Taiwan, Korea and Japan data. Strong readings here mostly "
                          "reflect AI-hardware demand.")}


WINDOW_LABEL = {"D10": "first 10 days", "D20": "first 20 days", "MONTH": "full month"}


def trade_item(name, rows, period_key, value_key, window_key, note) -> dict:
    last = rows[-1]
    prev = rows[-2] if len(rows) > 1 else None
    window = WINDOW_LABEL.get(last.get(window_key, ""), "") if window_key else "month"
    return {"name": name, "kind": "trade", "period": last[period_key], "window": window,
            "value": parse_number(last.get(value_key)), "note": note,
            "previous": ({"period": prev[period_key],
                          "window": WINDOW_LABEL.get(prev.get(window_key, ""), "")
                          if window_key else "month",
                          "value": parse_number(prev.get(value_key))} if prev else None)}


# --- Build ------------------------------------------------------------------

def build(today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    return {"generated": today.isoformat(),
            "panels": [rates_panel(), *market_panels(), trade_panel()],
            "closing": ("This is early evidence that puts things on the watch list; on its own "
                        "it is not grounds for a decision.")}


def render(data: dict) -> str:
    template = TEMPLATE.read_text("utf-8")
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    return template.replace("/*__DASHBOARD_DATA__*/null", payload)


def main(argv: list[str]) -> int:
    data = build()
    (DERIVED / "macro_dashboard.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
    if TEMPLATE.exists():
        (DERIVED / "macro_dashboard.html").write_text(render(data), encoding="utf-8")
    n = sum(len(p["items"]) for p in data["panels"])
    print(f"macro_dashboard: {n} items across {len(data['panels'])} panels")
    for p in data["panels"]:
        for it in p["items"]:
            print(f"  {p['id']:7s} {it['name'][:44]:44s} {it.get('value')} "
                  f"({it.get('as_of') or it.get('period')})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
