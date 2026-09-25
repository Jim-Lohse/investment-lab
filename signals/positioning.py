"""Positioning intelligence: prime-brokerage notes as they surface in the press,
a loudness gauge for that chatter, and a calendar of the predictable events.

Goldman, Morgan Stanley and JPMorgan prime-brokerage notes go to clients
first and reach Reuters, the FT, Bloomberg, Barron's and others days later,
quoted with fixed phrases ("prime brokerage data show"). The searches in
signals/config/positioning.json catch those pickups through Google News
search feeds. This is situational awareness: early evidence that puts things
on the watch list, never grounds for a decision on its own.

Holdings never enter this module's committed output: the repository is
public. `match` reads a git-ignored holdings file at run time and prints
matches; the same-day alert Routine does the rest (POSITIONING_SUMMARY.md).

Subcommands:
    news       fetch the searches (last 3 days), append new headlines;
               skips Saturday and Sunday (U.S. Eastern) unless --force
    backfill N fetch the last N weeks one week at a time (baseline + a test
               of which searches actually return stories)
    weekly     recompute the weekly counts, loudness and the brief
    calendar   recompute the upcoming-events calendar
    match      print this week's headlines that name a holding (reads the
               git-ignored holdings file; prints only, writes nothing)

Outputs:
    data/positioning/headlines.csv          append-only, one row per (story, search)
    data/derived/positioning_weekly.csv     distinct stories per week, per search and total
    data/derived/positioning_calendar.csv   upcoming events, U.S. Eastern dates
    data/derived/positioning_brief.md       the numbers the Friday digest quotes
"""

from __future__ import annotations

import datetime as dt
import email.utils
import json
import re
import statistics
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo

from .common import CONFIG_DIR, DATA_DIR, REPO_ROOT, append_dedup_csv, read_csv_dicts, write_csv

ET_TZ = ZoneInfo("America/New_York")
CONFIG_PATH = CONFIG_DIR / "positioning.json"
HEADLINES = DATA_DIR / "positioning" / "headlines.csv"
DERIVED = DATA_DIR / "derived"
WEEKLY = DERIVED / "positioning_weekly.csv"
CALENDAR = DERIVED / "positioning_calendar.csv"
BRIEF = DERIVED / "positioning_brief.md"

HEADLINE_FIELDS = ["story_id", "query_id", "published_et", "first_seen_et", "outlet",
                   "title", "link", "banks", "direction", "topics", "extreme"]


def load_config(path: Path = CONFIG_PATH) -> dict:
    return json.loads(path.read_text("utf-8"))


def today_et(now: dt.datetime | None = None) -> dt.date:
    return (now or dt.datetime.now(dt.timezone.utc)).astimezone(ET_TZ).date()


# --- Feed parsing -------------------------------------------------------------

def feed_url(cfg: dict, query: str) -> str:
    return cfg["feed_template"].format(query=urllib.parse.quote_plus(query))


def normalize_title(title: str) -> str:
    """Lower-case letters and digits only, so one story syndicated with small
    punctuation differences counts once."""
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def story_id(title: str) -> str:
    import hashlib
    return hashlib.sha1(normalize_title(title).encode("utf-8")).hexdigest()[:16]


def split_outlet(title: str, source: str) -> tuple[str, str]:
    """Google News titles end in ' - Outlet'; strip it when it matches <source>."""
    if source and title.endswith(" - " + source):
        return title[: -len(source) - 3].strip(), source
    if " - " in title and not source:
        head, _, tail = title.rpartition(" - ")
        return head.strip(), tail.strip()
    return title.strip(), source


def parse_feed(xml_text: str) -> list[dict]:
    """RSS 2.0 items -> [{title, outlet, link, published_et}]."""
    root = ET.fromstring(xml_text)
    out = []
    for item in root.iter("item"):
        raw_title = (item.findtext("title") or "").strip()
        source = (item.findtext("source") or "").strip()
        title, outlet = split_outlet(raw_title, source)
        pub = item.findtext("pubDate")
        published = ""
        if pub:
            try:
                published = email.utils.parsedate_to_datetime(pub).astimezone(ET_TZ).date().isoformat()
            except (TypeError, ValueError):
                published = ""
        if title:
            out.append({"title": title, "outlet": outlet,
                        "link": (item.findtext("link") or "").strip(), "published_et": published})
    return out


# --- Tagging ----------------------------------------------------------------

def _has(text: str, phrase: str) -> bool:
    return re.search(r"(?<![A-Za-z0-9])" + re.escape(phrase) + r"(?![A-Za-z0-9])",
                     text, re.IGNORECASE) is not None


def tag(title: str, tags: dict) -> dict:
    banks = [b for b, words in tags["bank"].items() if any(_has(title, w) for w in words)]
    dirs = [d for d, words in tags["direction"].items() if any(_has(title, w) for w in words)]
    topics = [t for t, words in tags["topic"].items() if any(_has(title, w) for w in words)]
    extreme = any(_has(title, w) for w in tags["extreme"])
    return {"banks": ";".join(banks),
            "direction": dirs[0] if len(dirs) == 1 else ("mixed" if dirs else ""),
            "topics": ";".join(topics), "extreme": "yes" if extreme else ""}


def rows_for(items: list[dict], query_id: str, cfg: dict, seen: dt.date) -> list[dict]:
    rows = []
    for it in items:
        row = {"story_id": story_id(it["title"]), "query_id": query_id,
               "published_et": it["published_et"], "first_seen_et": seen.isoformat(),
               "outlet": it["outlet"], "title": it["title"], "link": it["link"]}
        row.update(tag(it["title"], cfg["tags"]))
        rows.append(row)
    return rows


# --- Fetching ---------------------------------------------------------------

def fetch_query(cfg: dict, q: str) -> list[dict]:
    from .common import http_get
    return parse_feed(http_get(feed_url(cfg, q), timeout=30).text)


def collect(cfg: dict, window: str, seen: dt.date) -> tuple[int, list[str]]:
    """Run every search with `window` appended; return (rows added, failures)."""
    added, failures = 0, []
    for q in cfg["queries"]:
        try:
            items = fetch_query(cfg, f"{q['q']} {window}")
        except Exception as err:  # one failing search must not stop the others
            failures.append(f"{q['id']}: {err}")
            continue
        n = append_dedup_csv(HEADLINES, HEADLINE_FIELDS, rows_for(items, q["id"], cfg, seen),
                             ["story_id", "query_id"])
        print(f"  {q['id']:14s} {len(items):3d} items, {n} new")
        added += n
    return added, failures


# --- Weekly counts and loudness ----------------------------------------------

def week_ending(day: dt.date) -> dt.date:
    """The Sunday that ends day's Monday-to-Sunday week."""
    return day + dt.timedelta(days=6 - day.weekday())


def weekly_counts(rows: list[dict], query_ids: list[str],
                  through: dt.date | None = None) -> list[dict]:
    """Distinct stories per week, per search and in total (a story caught by
    two searches counts once in the total). With `through`, the table runs to
    that day's week, so a silent current week shows as zero rather than
    dropping off the end."""
    per: dict[str, dict[str, set]] = {}
    for r in rows:
        if not r.get("published_et"):
            continue
        wk = week_ending(dt.date.fromisoformat(r["published_et"])).isoformat()
        bucket = per.setdefault(wk, {})
        bucket.setdefault(r["query_id"], set()).add(r["story_id"])
        bucket.setdefault("_total", set()).add(r["story_id"])
    if not per:
        return []
    # Fill empty weeks between first and last so a silent week counts as zero.
    first = dt.date.fromisoformat(min(per))
    last = dt.date.fromisoformat(max(per))
    if through is not None:
        last = max(last, week_ending(through))
    out, wk = [], first
    while wk <= last:
        b = per.get(wk.isoformat(), {})
        row = {"week_ending": wk.isoformat(), "total": len(b.get("_total", ()))}
        for qid in query_ids:
            row[qid] = len(b.get(qid, ()))
        out.append(row)
        wk += dt.timedelta(days=7)
    return out


def loudness(weeks: list[dict], cfg: dict, key: str = "total") -> dict:
    """Latest complete-or-current week against the median of earlier weeks."""
    p = cfg["loudness"]
    if not weeks:
        return {"count": 0, "baseline": None, "ratio": None, "label": "no stories stored yet"}
    count = weeks[-1][key]
    hist = [w[key] for w in weeks[:-1]][-p["baseline_weeks"]:]
    if len(hist) < p["min_weeks"]:
        return {"count": count, "baseline": None, "ratio": None,
                "label": f"building a baseline ({len(hist)} of {p['min_weeks']} weeks)"}
    base = statistics.median(hist)
    ratio = count / base if base else (None if count == 0 else float("inf"))
    label = "about normal"
    if ratio is not None:
        for band in p["bands"]:
            if band["below"] is None or ratio < band["below"]:
                label = band["label"]
                break
    return {"count": count, "baseline": base, "ratio": None if ratio in (None, float("inf"))
            else round(ratio, 2), "label": label}


# --- Calendar ---------------------------------------------------------------

def _nth_weekday(year: int, month: int, weekday: int, n: int) -> dt.date:
    d = dt.date(year, month, 1)
    d += dt.timedelta(days=(weekday - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def _last_weekday(year: int, month: int, weekday: int) -> dt.date:
    d = dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)
    return d - dt.timedelta(days=(d.weekday() - weekday) % 7)


def _easter(year: int) -> dt.date:
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return dt.date(year, month, day)


def _observed(d: dt.date) -> dt.date | None:
    if d.weekday() == 5:
        # NYSE does not close the Friday before a Saturday New Year's Day.
        return None if (d.month, d.day) == (1, 1) else d - dt.timedelta(days=1)
    if d.weekday() == 6:
        return d + dt.timedelta(days=1)
    return d


def nyse_holidays(year: int) -> set[dt.date]:
    """NYSE full-day closures by rule (special closures, e.g. a national day of
    mourning, are not predictable and are not included)."""
    fixed = [dt.date(year, 1, 1), dt.date(year, 6, 19), dt.date(year, 7, 4), dt.date(year, 12, 25)]
    days = {o for o in (_observed(d) for d in fixed) if o}
    days |= {_nth_weekday(year, 1, 0, 3), _nth_weekday(year, 2, 0, 3),
             _easter(year) - dt.timedelta(days=2), _last_weekday(year, 5, 0),
             _nth_weekday(year, 9, 0, 1), _nth_weekday(year, 11, 3, 4)}
    return days


def is_trading_day(d: dt.date) -> bool:
    return d.weekday() < 5 and d not in nyse_holidays(d.year)


def next_business_day_on_or_after(d: dt.date) -> dt.date:
    while not is_trading_day(d):
        d += dt.timedelta(days=1)
    return d


def add_business_days(d: dt.date, n: int) -> dt.date:
    while n > 0:
        d += dt.timedelta(days=1)
        if is_trading_day(d):
            n -= 1
    return d


def last_trading_days(year: int, month: int, n: int) -> list[dt.date]:
    d = dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)
    out = []
    while len(out) < n:
        if is_trading_day(d):
            out.append(d)
        d -= dt.timedelta(days=1)
    return sorted(out)


def quarterly_expiry(year: int, month: int) -> dt.date:
    """Third Friday; the trading day before it when that Friday is a holiday."""
    d = _nth_weekday(year, month, 4, 3)
    while not is_trading_day(d):
        d -= dt.timedelta(days=1)
    return d


def short_interest_settlements(year: int, month: int) -> list[dt.date]:
    """Settlement dates by FINRA's rule of thumb: the 15th (or the trading day
    before it) and the last trading day of the month."""
    mid = dt.date(year, month, 15)
    while not is_trading_day(mid):
        mid -= dt.timedelta(days=1)
    return [mid, last_trading_days(year, month, 1)[0]]


def calendar_events(start: dt.date, cfg: dict) -> list[dict]:
    c = cfg["calendar"]
    end = start + dt.timedelta(days=c["horizon_days"])
    ev: list[dict] = []

    def add(d0, d1, kind, label, basis):
        if d1 >= start and d0 <= end:
            ev.append({"start": d0.isoformat(), "end": d1.isoformat(), "kind": kind,
                       "label": label, "basis": basis})

    y, m = start.year, start.month
    for i in range(-1, c["horizon_days"] // 28 + 3):
        yy, mm = y + (m - 1 + i) // 12, (m - 1 + i) % 12 + 1
        days = last_trading_days(yy, mm, c["month_end_trading_days"])
        quarter_end = mm in (3, 6, 9, 12)
        add(days[0], days[-1], "rebalance",
            ("Quarter-end" if quarter_end else "Month-end") + " rebalancing window: pension "
            "and index funds reset their stock and bond mix, and banks publish estimates of "
            "the buying or selling this forces" + (" (larger at quarter-end)" if quarter_end else ""),
            f"last {c['month_end_trading_days']} trading days of the month")
        if quarter_end:
            exp = quarterly_expiry(yy, mm)
            add(exp, exp, "expiry", "Quarterly options and futures expiry: stock-index "
                "contracts expire together, which can swing prices and trading volume",
                "third Friday of March, June, September, December")
            qend = dt.date(yy, mm, 30 if mm in (6, 9) else 31)
            deadline = next_business_day_on_or_after(qend + dt.timedelta(days=c["form13f_deadline_days"]))
            add(deadline, deadline, "13f", "13F deadline: large funds' quarter-end holdings "
                "become public; expect a wave of \"what hedge funds bought and sold\" stories",
                f"{c['form13f_deadline_days']} days after quarter-end, next business day")
            lo, hi = c["trend_monitor_after_deadline_days"]
            add(deadline + dt.timedelta(days=lo), deadline + dt.timedelta(days=hi), "trend_monitor",
                "Estimated: Goldman Hedge Fund Trend Monitor and its most-crowded-stocks list "
                "reach the press", f"estimate, {lo} to {hi} days after the 13F deadline")
        if not c["finra_short_interest_publication_dates"]:
            for s in short_interest_settlements(yy, mm):
                pub = add_business_days(s, c["short_interest_publish_business_days"])
                add(pub, pub, "short_interest", "Estimated: FINRA short interest published "
                    f"(shares sold short as of {s.isoformat()})",
                    f"estimate, {c['short_interest_publish_business_days']} business days "
                    "after settlement; FINRA's calendar governs")
    for d in c["finra_short_interest_publication_dates"]:
        dd = dt.date.fromisoformat(d)
        add(dd, dd, "short_interest", "FINRA short interest published", "FINRA calendar")
    for d in c["fomc_decision_dates"]:
        dd = dt.date.fromisoformat(d)
        add(dd, dd, "fomc", "Federal Reserve rate decision", "Federal Reserve calendar")
    ev.sort(key=lambda e: (e["start"], e["kind"]))
    return ev


# --- Brief ------------------------------------------------------------------

def notable(rows: list[dict], since: dt.date) -> list[dict]:
    """Distinct stories since `since`, bank-attributed or extreme first."""
    by_story: dict[str, dict] = {}
    for r in rows:
        if r.get("published_et") and r["published_et"] >= since.isoformat():
            by_story.setdefault(r["story_id"], r)
    stories = sorted(by_story.values(), key=lambda r: r["published_et"], reverse=True)
    stories.sort(key=lambda r: (r["extreme"] != "yes", r["banks"] == ""))  # stable: newest first within each
    return stories


def build_brief(cfg: dict, today: dt.date) -> str:
    rows = read_csv_dicts(HEADLINES) if HEADLINES.exists() else []
    qids = [q["id"] for q in cfg["queries"]]
    weeks = weekly_counts(rows, qids, today)
    loud = loudness(weeks, cfg)
    week_start = today - dt.timedelta(days=today.weekday())
    lines = [f"# Positioning brief, {today.isoformat()} (U.S. Eastern)", "",
             f"Stories stored: {len({r['story_id'] for r in rows})}. "
             f"This week (from {week_start.isoformat()}): {loud['count']} distinct stories; "
             f"usual week (median of up to {cfg['loudness']['baseline_weeks']} earlier weeks): "
             f"{loud['baseline'] if loud['baseline'] is not None else 'not enough history'}; "
             f"reading: {loud['label']}.", "",
             "| Search | This week | Usual week |", "|---|---|---|"]
    for q in cfg["queries"]:
        lw = loudness(weeks, cfg, q["id"]) if weeks else {"count": 0, "baseline": None}
        lines.append(f"| {q['label']} | {lw['count']} | "
                     f"{lw['baseline'] if lw['baseline'] is not None else 'not enough history'} |")
    lines += ["", "## Stories this week", "",
              "| Date | Outlet | Headline | Bank | Direction | Record-type wording |",
              "|---|---|---|---|---|---|"]
    stories = notable(rows, week_start)
    for r in stories[:12]:
        lines.append(f"| {r['published_et']} | {r['outlet']} | [{r['title']}]({r['link']}) | "
                     f"{r['banks'] or '-'} | {r['direction'] or '-'} | {r['extreme'] or '-'} |")
    if not stories:
        lines.append("| - | - | No stories this week | - | - | - |")
    lines += ["", "## Coming up (next 21 days)", "", "| Dates | Event | Basis |", "|---|---|---|"]
    for e in calendar_events(today, cfg):
        if e["start"] <= (today + dt.timedelta(days=21)).isoformat():
            dates = e["start"] if e["start"] == e["end"] else f"{e['start']} to {e['end']}"
            lines.append(f"| {dates} | {e['label']} | {e['basis']} |")
    if not cfg["calendar"]["fomc_decision_dates"]:
        lines += ["", "Federal Reserve meeting dates are not loaded yet "
                  "(calendar.fomc_decision_dates in signals/config/positioning.json)."]
    return "\n".join(lines) + "\n"


def write_derived(cfg: dict, today: dt.date) -> None:
    rows = read_csv_dicts(HEADLINES) if HEADLINES.exists() else []
    qids = [q["id"] for q in cfg["queries"]]
    weeks = weekly_counts(rows, qids, today)
    write_csv(WEEKLY, ["week_ending", "total", *qids],
              [[w["week_ending"], w["total"], *[w[q] for q in qids]] for w in weeks])
    ev = calendar_events(today, cfg)
    write_csv(CALENDAR, ["start", "end", "kind", "label", "basis"],
              [[e["start"], e["end"], e["kind"], e["label"], e["basis"]] for e in ev])
    BRIEF.write_text(build_brief(cfg, today), encoding="utf-8")


# --- Holdings matching (private) ----------------------------------------------

def match_holdings(rows: list[dict], holdings: list[dict]) -> list[tuple[dict, dict]]:
    out = []
    for r in rows:
        for h in holdings:
            names = [h.get("name", ""), *h.get("aliases", [])]
            if h.get("us_symbol") and len(h["us_symbol"]) >= 3:
                names.append(h["us_symbol"])
            if any(n and _has(r["title"], n) for n in names):
                out.append((r, h))
    return out


# --- CLI --------------------------------------------------------------------

def main(argv: list[str]) -> int:
    cfg = load_config()
    today = today_et()
    cmd = argv[0] if argv else "weekly"
    if cmd == "news":
        if today.weekday() >= 5 and "--force" not in argv:
            print(f"positioning news: {today} is a weekend day (U.S. Eastern); skipped")
            return 0
        added, failures = collect(cfg, cfg["daily_window"], today)
        print(f"positioning news: {added} new rows")
        for f in failures:
            print(f"  FAILED {f}")
        write_derived(cfg, today)
        return 1 if failures and len(failures) == len(cfg["queries"]) else 0
    if cmd == "backfill":
        n = int(argv[1]) if len(argv) > 1 else 13
        failures = []
        for i in range(n, 0, -1):
            end = today - dt.timedelta(days=7 * (i - 1))
            begin = end - dt.timedelta(days=7)
            print(f"week {begin} to {end}")
            _, f = collect(cfg, f"after:{begin.isoformat()} before:{end.isoformat()}", today)
            failures += f
        write_derived(cfg, today)
        for f in failures:
            print(f"  FAILED {f}")
        return 0
    if cmd in ("weekly", "calendar"):
        write_derived(cfg, today)
        print(BRIEF.read_text("utf-8"))
        return 0
    if cmd == "match":
        path = REPO_ROOT / cfg["holdings_file"]
        if not path.exists():
            print(f"positioning match: no holdings file at {cfg['holdings_file']}")
            return 0
        holdings = json.loads(path.read_text("utf-8")).get("holdings", [])
        since = (today - dt.timedelta(days=int(argv[1]) if len(argv) > 1 else 7)).isoformat()
        rows = [r for r in (read_csv_dicts(HEADLINES) if HEADLINES.exists() else [])
                if r.get("first_seen_et", "") >= since]
        seen = set()
        for r, h in match_holdings(rows, holdings):
            if (r["story_id"], h["name"]) in seen:
                continue
            seen.add((r["story_id"], h["name"]))
            print(f"{r['first_seen_et']}\t{h['name']}\t{r['outlet']}\t{r['title']}\t{r['link']}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
