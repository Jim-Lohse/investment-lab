"""Do CFTC positioning shifts come before moves and flows in the matching funds?

A test of the weekly CFTC summary's premise, run on 2006-2026 history before
the summary leans on it. For each watched series (institutions and hedge funds
in the S&P 500, Nasdaq-100 and dollar-index futures; hedge funds in gold and
crude) it asks whether a positioning signal known at a date lines up with the
fund's price move, and for GLD its gold holdings (money in or out), over the
following 1, 2, 3 and 4 weeks (weekly to monthly, the window the
summary is meant to serve).

No look-ahead. Positions are as of Tuesday. The report is normally public
Friday afternoon but slips to Monday in holiday weeks, so the main test acts at
the close of the first trading day on or after the Monday after the as-of date
(T + 6 days), when it is always public. A Friday-close variant (T + 3) is run
only as a sensitivity check. Every threshold (percentile ranks, top and bottom
fifths) uses only weeks before the one being scored, with at least two years
of history.

Signals, per series and week T (net = long minus short, OI = open interest):
  chg1     one-week change in net, as a share of OI
  chg4     four-week change in net, as a share of OI
  crowd    net's percentile rank against the previous three years; a high
           value means unusually long for that group, low unusually short
  turn     +1 when net sits in the bottom fifth of its past three years and
           has risen over four weeks (a crowded short starting to unwind),
           -1 for the mirror image, else 0

Statistics, per signal and horizon:
  rho      Spearman rank correlation between signal and forward move
  t        its Newey-West t-statistic (Bartlett, lag = horizon), because
           overlapping multi-week windows are not independent
  top-bot  mean forward move after weeks whose signal ranked in the top fifth
           of its own past, minus after the bottom fifth
  halves   rho in 2006-2015 and 2016-2026 separately
A result counts as "consistent" only with |t| >= 2.5 AND the same sign in both
halves.

Control test (GLD flows only, where a flow series exists): the forward change
in GLD's gold holdings is regressed on the CFTC signal together with two things
already known on the entry day, GLD's own holdings change and its price return
over the previous four weeks, with Newey-West t-statistics. A signal that only
repeats what those already say shows up here as no longer significant. With 8 series x 4 signals x 4 horizons (plus GLD flows) about 7
results would pass |t| >= 2 by chance alone, so the stricter bar matters.

This is an information test, not a trading backtest: it measures whether the
signal carries information about what came next. No costs, slippage or
position sizing are applied, and nothing here is a strategy. Survivorship and
corporate actions: the five funds were chosen today and all survived the
period; prices are adjusted closes (dividends, and splits such as USO's 1-for-8
in 2020). USO changed how it holds crude futures in April 2020, which is a
structural break in its price behaviour.

Output:
  data/derived/cftc_leadlag.csv  every statistic
  data/derived/cftc_leadlag.md   plain-language summary

Usage:
    python -m signals.cftc_leadlag
"""

from __future__ import annotations

import bisect
import csv
import datetime as dt
import math
import sys
from pathlib import Path

from .common import DATA_DIR, fmt, parse_number, write_csv

DERIVED = DATA_DIR / "derived"

SERIES = [
    # (report, market code, trader group, ticker, name, who)
    ("tff_fut", "13874A", "asset_manager", "SPY", "S&P 500", "Institutions"),
    ("tff_fut", "13874A", "leveraged_money", "SPY", "S&P 500", "Hedge funds"),
    ("tff_fut", "209742", "asset_manager", "QQQ", "Nasdaq-100", "Institutions"),
    ("tff_fut", "209742", "leveraged_money", "QQQ", "Nasdaq-100", "Hedge funds"),
    ("tff_fut", "098662", "asset_manager", "UUP", "Dollar index", "Institutions"),
    ("tff_fut", "098662", "leveraged_money", "UUP", "Dollar index", "Hedge funds"),
    ("disagg_fut", "088691", "managed_money", "GLD", "Gold", "Hedge funds"),
    ("disagg_fut", "067651", "managed_money", "USO", "Crude oil", "Hedge funds"),
]
HORIZONS = [1, 2, 3, 4]         # weekly to monthly: the window the summary serves
SIGNALS = ["chg1", "chg4", "crowd", "turn"]
MIN_HISTORY = 104          # weeks before any percentile or fifth is scored
CROWD_WINDOW = 156         # three years
SPLIT = "2016-01-01"
T_BAR = 2.5

RESULT_HEADER = ["ticker", "name", "who", "target", "entry", "signal", "horizon_weeks",
                 "n", "rho", "t_nw", "top_minus_bottom_pct", "top_n", "bottom_n",
                 "rho_2006_2015", "rho_2016_2026", "consistent"]


# --- Small statistics, stdlib only ------------------------------------------

def ranks(values: list[float]) -> list[float]:
    """Average ranks (ties share the mean rank), 1-based."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return out


def spearman_nw(x: list[float], y: list[float], lag: int) -> tuple[float, float]:
    """Spearman rho and a Newey-West t-statistic for it.

    rho is the slope of standardized y-ranks on standardized x-ranks; its
    variance uses a Bartlett-weighted sum of autocovariances of x*e up to
    `lag`, which corrects for overlapping forward windows.
    """
    n = len(x)
    if n < 30:
        return float("nan"), float("nan")
    rx, ry = ranks(x), ranks(y)
    zx, zy = _standardize(rx), _standardize(ry)
    rho = sum(a * b for a, b in zip(zx, zy)) / n
    resid = [b - rho * a for a, b in zip(zx, zy)]
    u = [a * e for a, e in zip(zx, resid)]
    s = sum(v * v for v in u) / n
    for L in range(1, lag + 1):
        w = 1 - L / (lag + 1)
        s += 2 * w * sum(u[i] * u[i - L] for i in range(L, n)) / n
    sxx = sum(a * a for a in zx) / n
    var = s / (sxx * sxx) / n
    return rho, (rho / math.sqrt(var) if var > 0 else float("nan"))


def _standardize(v: list[float]) -> list[float]:
    m = sum(v) / len(v)
    sd = math.sqrt(sum((a - m) ** 2 for a in v) / len(v)) or 1.0
    return [(a - m) / sd for a in v]


def past_rank(history: list[float], value: float) -> float | None:
    """Percentile of value among earlier values (0-100); None if too few."""
    if len(history) < MIN_HISTORY:
        return None
    return 100.0 * bisect.bisect_left(history, value) / len(history)


# --- Data -------------------------------------------------------------------

def load_prices(path: Path) -> dict[str, tuple[list[str], list[float]]]:
    by: dict[str, dict[str, float]] = {}
    with path.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            v = parse_number(r["adj_close"])
            if v and v > 0:
                by.setdefault(r["ticker"], {})[r["date"]] = v
    return {t: (sorted(d), [d[k] for k in sorted(d)]) for t, d in by.items()}


def load_gld(path: Path) -> tuple[list[str], list[float]] | None:
    if not path.exists():
        return None
    d = {}
    with path.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            v = parse_number(r["tonnes"])
            if v and v > 0:
                d[r["date"]] = v
    return (sorted(d), [d[k] for k in sorted(d)]) if d else None


def value_on_or_after(series: tuple[list[str], list[float]], day: str) -> tuple[str, float] | None:
    dates, values = series
    i = bisect.bisect_left(dates, day)
    if i >= len(dates):
        return None
    # A gap of more than a week means the data ends or has a hole: no value.
    if (dt.date.fromisoformat(dates[i]) - dt.date.fromisoformat(day)).days > 7:
        return None
    return dates[i], values[i]


def build_signals(flows: list[dict]) -> list[dict]:
    """Per-week signal values for one series, oldest first, no look-ahead."""
    rows = sorted(flows, key=lambda r: r["report_date"])
    out = []
    past_net: list[float] = []   # nets of the previous CROWD_WINDOW weeks
    window: list[float] = []
    for i, r in enumerate(rows):
        net = parse_number(r["net"])
        oi = parse_number(r["open_interest"])
        chg = parse_number(r["net_change"])
        rec = {"date": r["report_date"], "chg1": None, "chg4": None, "crowd": None, "turn": None}
        if net is not None and oi:
            if chg is not None:
                rec["chg1"] = chg / oi
            if i >= 4:
                d4 = (dt.date.fromisoformat(r["report_date"])
                      - dt.date.fromisoformat(rows[i - 4]["report_date"])).days
                net4 = parse_number(rows[i - 4]["net"])
                if 25 <= d4 <= 31 and net4 is not None:
                    rec["chg4"] = (net - net4) / oi
            crowd = past_rank(sorted(window), net) if len(window) >= MIN_HISTORY else None
            rec["crowd"] = crowd
            if crowd is not None and rec["chg4"] is not None:
                rec["turn"] = 1.0 if crowd <= 20 and rec["chg4"] > 0 else (
                    -1.0 if crowd >= 80 and rec["chg4"] < 0 else 0.0)
            window.append(net)
            if len(window) > CROWD_WINDOW:
                window.pop(0)
        past_net.append(net if net is not None else 0.0)
        out.append(rec)
    return out


# --- The test ---------------------------------------------------------------

def forward_moves(sig_rows: list[dict], target: tuple[list[str], list[float]],
                  entry_lag_days: int, h: int) -> list[tuple[dict, float]]:
    """(signal row, forward log change) pairs. Entry is the first observation
    on or after T + entry_lag_days; exit the first on or after entry + 7h."""
    pairs = []
    for rec in sig_rows:
        t = dt.date.fromisoformat(rec["date"])
        entry = value_on_or_after(target, (t + dt.timedelta(days=entry_lag_days)).isoformat())
        if entry is None:
            continue
        exit_ = value_on_or_after(target, (dt.date.fromisoformat(entry[0])
                                           + dt.timedelta(days=7 * h)).isoformat())
        if exit_ is None:
            continue
        pairs.append((rec, math.log(exit_[1] / entry[1])))
    return pairs


def score(pairs: list[tuple[dict, float]], signal: str, h: int) -> dict:
    usable = [(r[signal], y, r["date"]) for r, y in pairs if r[signal] is not None]
    x = [a for a, _, _ in usable]
    y = [b for _, b, _ in usable]
    rho, t = spearman_nw(x, y, lag=h)
    first = [(a, b) for a, b, d in usable if d < SPLIT]
    second = [(a, b) for a, b, d in usable if d >= SPLIT]
    rho1 = spearman_nw([a for a, _ in first], [b for _, b in first], h)[0] if first else float("nan")
    rho2 = spearman_nw([a for a, _ in second], [b for _, b in second], h)[0] if second else float("nan")
    # Top and bottom fifth, each week ranked against the signal's own past.
    hist: list[float] = []
    top, bot = [], []
    for a, b, _ in usable:
        pr = past_rank(hist, a) if signal != "turn" else None
        if signal == "turn":
            if a > 0:
                top.append(b)
            elif a < 0:
                bot.append(b)
        elif pr is not None:
            if pr >= 80:
                top.append(b)
            elif pr < 20:
                bot.append(b)
        bisect.insort(hist, a)
    tmb = (sum(top) / len(top) - sum(bot) / len(bot)) * 100 if top and bot else float("nan")
    consistent = (abs(t) >= T_BAR and not math.isnan(rho1) and not math.isnan(rho2)
                  and (rho1 > 0) == (rho2 > 0) == (rho > 0))
    return {"n": len(usable), "rho": rho, "t_nw": t, "top_minus_bottom_pct": tmb,
            "top_n": len(top), "bottom_n": len(bot), "rho_2006_2015": rho1,
            "rho_2016_2026": rho2, "consistent": "yes" if consistent else ""}


def run() -> list[dict]:
    with (DERIVED / "cftc_flows.csv").open(encoding="utf-8", newline="") as fh:
        flows = list(csv.DictReader(fh))
    prices = load_prices(DATA_DIR / "prices" / "etf_daily.csv")
    gld = load_gld(DATA_DIR / "flows" / "gld_holdings.csv")
    results = []
    for report, code, group, ticker, name, who in SERIES:
        recs = [f for f in flows if (f["report"], f["market_code"], f["trader_group"])
                == (report, code, group)]
        sig = build_signals(recs)
        targets = []
        if ticker in prices:
            targets.append(("price", prices[ticker]))
        if ticker == "GLD" and gld:
            targets.append(("gld_tonnes", gld))
        for target_name, target in targets:
            for entry_name, lag in (("monday_after", 6), ("friday_release", 3)):
                for h in HORIZONS:
                    pairs = forward_moves(sig, target, lag, h)
                    for s in SIGNALS:
                        res = score(pairs, s, h)
                        results.append({"ticker": ticker, "name": name, "who": who,
                                        "target": target_name, "entry": entry_name,
                                        "signal": s, "horizon_weeks": h, **res})
    return results


# --- Control test: does the signal add to what is already known? ------------

def _invert(m: list[list[float]]) -> list[list[float]]:
    n = len(m)
    a = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(m)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(a[r][c]))
        a[c], a[p] = a[p], a[c]
        pv = a[c][c]
        a[c] = [v / pv for v in a[c]]
        for r in range(n):
            if r != c:
                f = a[r][c]
                a[r] = [x - f * y for x, y in zip(a[r], a[c])]
    return [row[n:] for row in a]


def ols_nw(x_rows: list[list[float]], y: list[float], lag: int) -> tuple[list[float], list[float]]:
    """OLS with an intercept; coefficients and Newey-West t-statistics."""
    x = [[1.0] + r for r in x_rows]
    n, k = len(y), len(x[0])
    xtx_inv = _invert([[sum(x[i][a] * x[i][b] for i in range(n)) for b in range(k)] for a in range(k)])
    xty = [sum(x[i][a] * y[i] for i in range(n)) for a in range(k)]
    b = [sum(xtx_inv[a][c] * xty[c] for c in range(k)) for a in range(k)]
    e = [y[i] - sum(x[i][a] * b[a] for a in range(k)) for i in range(n)]
    u = [[x[i][a] * e[i] for a in range(k)] for i in range(n)]
    s = [[sum(u[i][a] * u[i][c] for i in range(n)) for c in range(k)] for a in range(k)]
    for lg in range(1, lag + 1):
        w = 1 - lg / (lag + 1)
        for a in range(k):
            for c in range(k):
                s[a][c] += w * sum(u[i][a] * u[i - lg][c] + u[i][c] * u[i - lg][a]
                                   for i in range(lg, n))
    v = [[sum(xtx_inv[a][p] * sum(s[p][q] * xtx_inv[q][c] for q in range(k)) for p in range(k))
          for c in range(k)] for a in range(k)]
    return b, [b[a] / math.sqrt(v[a][a]) if v[a][a] > 0 else float("nan") for a in range(k)]


def controlled_gld(sig_rows: list[dict], gld: tuple, price: tuple, signal: str, h: int) -> dict:
    """Forward GLD holdings change on the signal, past 4-week holdings change and
    past 4-week price return, all standardized; everything known at entry."""
    xs, ys = [], []
    for r in sig_rows:
        if r[signal] is None:
            continue
        t = dt.date.fromisoformat(r["date"])
        entry = value_on_or_after(gld, (t + dt.timedelta(days=6)).isoformat())
        if entry is None:
            continue
        day = dt.date.fromisoformat(entry[0])
        exit_ = value_on_or_after(gld, (day + dt.timedelta(days=7 * h)).isoformat())
        past = value_on_or_after(gld, (day - dt.timedelta(days=28)).isoformat())
        p_now = value_on_or_after(price, entry[0])
        p_past = value_on_or_after(price, (day - dt.timedelta(days=28)).isoformat())
        if not (exit_ and past and p_now and p_past):
            continue
        ys.append(math.log(exit_[1] / entry[1]))
        xs.append([r[signal], math.log(entry[1] / past[1]), math.log(p_now[1] / p_past[1])])
    if len(ys) < 100:
        return {}
    cols = [_standardize(list(c)) for c in zip(*xs)]
    b, t = ols_nw([list(r) for r in zip(*cols)], _standardize(ys), lag=h)
    return {"n": len(ys), "coef_signal": b[1], "t_signal": t[1],
            "t_past_flow": t[2], "t_past_price": t[3]}


def _f(v, digits=3) -> str:
    return "" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:.{digits}f}"


def run_controls() -> list[dict]:
    with (DERIVED / "cftc_flows.csv").open(encoding="utf-8", newline="") as fh:
        flows = list(csv.DictReader(fh))
    gld = load_gld(DATA_DIR / "flows" / "gld_holdings.csv")
    prices = load_prices(DATA_DIR / "prices" / "etf_daily.csv")
    if not gld or "GLD" not in prices:
        return []
    recs = [f for f in flows if (f["report"], f["market_code"], f["trader_group"])
            == ("disagg_fut", "088691", "managed_money")]
    sig = build_signals(recs)
    out = []
    for s in ("chg1", "chg4", "crowd"):
        for h in HORIZONS:
            res = controlled_gld(sig, gld, prices["GLD"], s, h)
            if res:
                out.append({"signal": s, "horizon_weeks": h, **res})
    return out


def write(results: list[dict], controls: list[dict] | None = None) -> None:
    write_csv(DERIVED / "cftc_leadlag.csv", RESULT_HEADER,
              [[_f(r[c]) if isinstance(r[c], float) else r[c] for c in RESULT_HEADER]
               for r in results])
    main = [r for r in results if r["entry"] == "monday_after"]
    hits = [r for r in main if r["consistent"]]
    lines = ["# Does CFTC positioning lead the funds? Test results", "",
             f"Generated {dt.date.today().isoformat()} by `python -m signals.cftc_leadlag`. "
             f"Main test acts at the close of the Monday after each report. "
             f"{len(main)} combinations tested; {len(hits)} pass the bar "
             f"(|t| >= {T_BAR} and the same direction in 2006-2015 and 2016-2026).", ""]
    if hits:
        lines += ["| Fund | Who | Target | Signal | Weeks ahead | rho | t | Top fifth minus bottom fifth, % | rho 2006-15 | rho 2016-26 |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for r in sorted(hits, key=lambda r: -abs(r["t_nw"])):
            lines.append(f"| {r['ticker']} | {r['who']} | {r['target']} | {r['signal']} | "
                         f"{r['horizon_weeks']} | {_f(r['rho'])} | {_f(r['t_nw'], 2)} | "
                         f"{_f(r['top_minus_bottom_pct'], 2)} | {_f(r['rho_2006_2015'])} | "
                         f"{_f(r['rho_2016_2026'])} |")
    else:
        lines.append("No combination passes the bar.")
    if controls:
        lines += ["", "## GLD flows: what the CFTC signal adds beyond what is already known", "",
                  "Forward change in GLD's gold holdings regressed on the signal together with "
                  "GLD's own holdings change and price return over the four weeks before entry "
                  "(both published daily). Newey-West t-statistics.", "",
                  "| Signal | Weeks ahead | n | t, CFTC signal | t, past GLD flow | t, past GLD price |",
                  "|---|---|---|---|---|---|"]
        for c in controls:
            lines.append(f"| {c['signal']} | {c['horizon_weeks']} | {c['n']} | "
                         f"{_f(c['t_signal'], 2)} | {_f(c['t_past_flow'], 2)} | "
                         f"{_f(c['t_past_price'], 2)} |")
    lines += ["", "Full table: `data/derived/cftc_leadlag.csv`. Method and caveats: the "
              "docstring of `signals/cftc_leadlag.py`.", ""]
    (DERIVED / "cftc_leadlag.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


def main(argv: list[str]) -> int:
    write(run(), run_controls())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
