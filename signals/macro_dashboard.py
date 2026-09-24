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
    """Share of earlier weekly readings strictly below `value` (the latest week,
    which holds `value` itself, is left out)."""
    hist = sorted(v for _, v in wk[:-1])
    if len(hist) < 52:
        return None
    return round(100.0 * bisect.bisect_left(hist, value) / len(hist))


def move_rank(wk: list[tuple[str, float]], change: str) -> float | None:
    """How big the latest 4-week move is (either direction) against every
    earlier 4-week move in the series, as a share of those moves it exceeds."""
    vals = [v for _, v in wk]
    moves = []
    for i in range(4, len(vals)):
        a, b = vals[i - 4], vals[i]
        if change == "pct":
            if a:
                moves.append(abs(b / a - 1))
        else:
            moves.append(abs(b - a))
    if len(moves) < 53:
        return None
    latest, earlier = moves[-1], sorted(moves[:-1])
    return round(100.0 * bisect.bisect_left(earlier, latest) / len(earlier))


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
    item["move4_rank_pct"] = move_rank(wk, change)
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


# --- Takeaways ---------------------------------------------------------------
# Plain sentences built from the numbers by fixed rules, so the wording is the
# same week to week and never goes beyond what the data says. Descriptive
# only: no buy or sell language.

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]


def month_year(iso: str) -> str:
    y, m = iso[:4], int(iso[5:7])
    return f"{MONTHS[m - 1]} {y}"


def bp(change_pts: float | None) -> str:
    """Percentage-point change as basis points, e.g. 0.24 -> '24 bp'."""
    return f"{abs(round(change_pts * 100))} bp" if change_pts is not None else "an unknown amount"


def moved(c: float | None, unit: str) -> str:
    if c is None:
        return "has no comparison yet"
    if abs(c) < (0.05 if unit == "pts" else 0.5):
        return "is little changed"
    word = "up" if c > 0 else "down"
    return f"is {word} {bp(c)}" if unit == "pts" else f"is {word} {abs(c):.1f}%"


def find(items: list[dict], prefix: str) -> dict | None:
    return next((i for i in items if i["name"].startswith(prefix)), None)


def rates_takeaway(p: dict) -> list[str]:
    y2, y10 = find(p["items"], "2-year"), find(p["items"], "10-year")
    g = find(p["items"], "Gap: 10-year minus 2-year")
    if not (y2 and y10 and g):
        return []
    c2, c10 = y2["changes"]["13w"], y10["changes"]["13w"]
    out = [f"The 2-year yield is {y2['value']:.2f}% and {moved(c2, 'pts')} over 13 weeks; "
           f"the 10-year is {y10['value']:.2f}% and {moved(c10, 'pts')}."]
    what = {"2-year": "where markets expect the Federal Reserve to take rates",
            "10-year": "long-term borrowing costs, including mortgage rates"}
    for it, label in ((y2, "2-year"), (y10, "10-year")):
        c4, r = it["changes"]["4w"], it.get("move4_rank_pct")
        if c4 is not None and r is not None and r >= 90:
            out.append(f"The {label} yield {'rose' if c4 > 0 else 'fell'} {bp(c4)} in the last "
                       f"4 weeks, larger than {r}% of 4-week moves since {it['since'][:4]}: an "
                       f"unusually quick repricing of {what[label]}.")
    since = f" since {month_year(g['streak']['since'])}" if g.get("streak") else ""
    if g["value"] >= 0:
        out.append(f"The 10-year pays {g['value']:.2f} percentage points more than the 2-year, "
                   f"so the curve is not inverted; it has been positive{since}.")
    else:
        out.append(f"The 2-year pays {abs(g['value']):.2f} points more than the 10-year: the curve "
                   f"is inverted{since}. Markets are pricing rate cuts ahead, usually because they "
                   f"expect the economy to slow.")
    gc = g["changes"]["13w"]
    if gc is not None and c2 is not None and c10 is not None:
        if gc <= -0.15:
            why = ("short-term rates rose faster than long-term ones, which usually means markets "
                   "expect the Federal Reserve to keep rates high" if c2 > 0 else
                   "long-term rates fell faster than short-term ones, which usually means markets "
                   "expect slower growth ahead")
            out.append(f"The gap narrowed by {bp(gc)} over 13 weeks (a flattening curve): {why}.")
        elif gc >= 0.15:
            why = ("short-term rates fell faster, which usually means markets expect rate cuts"
                   if c2 < 0 else
                   "long-term rates rose faster, which often reflects worries about inflation or "
                   "heavy government borrowing")
            out.append(f"The gap widened by {bp(gc)} over 13 weeks (a steepening curve): {why}.")
        else:
            out.append("The shape of the curve barely changed over 13 weeks.")
    return out


def market_takeaway(p: dict) -> list[str]:
    out = []
    for it in p["items"]:
        c13, c52 = it["changes"]["13w"], it["changes"]["52w"]
        big = it.get("move4_rank_pct") is not None and it["move4_rank_pct"] >= 90
        if it["unit"] == "USD":
            s = f"{it['name']} {moved(c13, '%')} over 13 weeks"
            s += f" and {abs(c52):.1f}% {'higher' if c52 >= 0 else 'lower'} than a year ago." if c52 is not None else "."
            if big:
                s += (f" Its latest 4-week move is larger than {it['move4_rank_pct']}% of past "
                      f"4-week moves, which is unusually large.")
            out.append(s)
        elif it["unit"] == "tonnes":
            c4 = it["changes"]["4w"]
            if c4 is not None:
                flow = "money flowing in" if c4 > 0 else "money flowing out"
                s = f"Gold held by GLD {moved(c4, '%')} over 4 weeks: {flow}."
                if big:
                    s += (f" That is larger than {it['move4_rank_pct']}% of past 4-week moves. "
                          f"In the lab's test, flows this strong tended to keep going the same way "
                          f"for several weeks.")
                out.append(s)
        elif it["unit"] == "contracts" and it.get("rank_pct") is not None:
            r = it["rank_pct"]
            if r >= 90 or r <= 10:
                side = "long (betting on a rise)" if it["value"] > 0 else "short (betting on a fall)"
                where = f"higher than {r}%" if r >= 90 else f"lower than {100 - r}%"
                out.append(f"{it['name']}: net {side}, {where} of weeks since "
                           f"{it['since'][:4]}, a crowded position. Crowding shows where a sharp "
                           f"reversal could start, not when.")
    return out


def trade_takeaway(p: dict) -> list[str]:
    parts = []
    for it in p["items"]:
        if it.get("value") is None:
            continue
        country = it["name"].split(":")[0]
        s = f"{country} {abs(it['value']):.0f}% {'higher' if it['value'] >= 0 else 'lower'}"
        if it.get("value_usd") is not None:
            s += f" ({abs(it['value_usd']):.0f}% in U.S. dollars)"
        parts.append(s)
    if not parts:
        return []
    out = ["Compared with the same period last year: " + "; ".join(parts) + "."]
    jp = find(p["items"], "Japan")
    if jp and jp.get("value_usd") is not None and jp["value"] - jp["value_usd"] >= 3:
        out.append(f"About {jp['value'] - jp['value_usd']:.0f} points of Japan's export growth "
                   f"is only the weaker yen; the dollar figure is the truer read of demand.")
    return out


def headlines(panels: list[dict]) -> list[str]:
    """The few takeaways worth reading first: the curve, then anything unusual."""
    out = []
    rates = next((p for p in panels if p["id"] == "rates"), None)
    if rates and rates.get("takeaway"):
        out.extend(rates["takeaway"][:1])
        out.extend(t for t in rates["takeaway"][1:] if "unusually quick" in t)
        out.extend(t for t in rates["takeaway"] if "curve is" in t)
    for p in panels:
        if p["id"] in ("rates", "trade"):
            continue
        out.extend(t for t in p.get("takeaway", []) if "unusually large" in t
                   or "crowded" in t or "tended to keep going" in t)
    trade = next((p for p in panels if p["id"] == "trade"), None)
    if trade and trade.get("takeaway"):
        out.append(trade["takeaway"][0])
    if len(out) <= 3:
        out.append("No other series made an unusually large move over the past four weeks.")
    return out[:6]


# --- Build ------------------------------------------------------------------

def build(today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    panels = [rates_panel(), *market_panels(), trade_panel()]
    for p in panels:
        p["takeaway"] = (rates_takeaway(p) if p["id"] == "rates" else
                         trade_takeaway(p) if p["id"] == "trade" else market_takeaway(p))
        if p["id"] not in ("rates", "trade") and not p["takeaway"]:
            p["takeaway"] = ["No unusually large moves or crowded positions here this week."]
    return {"generated": today.isoformat(),
            "headlines": headlines(panels),
            "panels": panels,
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
