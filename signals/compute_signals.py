"""Compute demand signals from the stored Taiwan, Korea and Japan data.

Outputs (regenerated in full each run — derived data, not a record):
  data/derived/taiwan_signals.csv  — per (month, group): aggregate YoY, median
                                     YoY, breadth (share of members growing)
  data/derived/korea_signals.csv   — per (period, item): exports and YoY where
                                     a year-ago observation exists
  data/derived/japan_signals.csv   — per (period, window, item): MOF press-
                                     release prints (with published YoY), the
                                     monthly time series, and HS-prefix sums
                                     from the e-Stat 9-digit tables, each with
                                     YoY against the store's own history
  data/derived/latest_report.md    — human-readable snapshot of the newest data

Aggregate YoY uses the report's own year-ago figures (each Taiwan monthly
report carries the same-month-last-year revenue), so a single month's file is
self-sufficient and immune to membership drift across files.

Usage:
    python -m signals.compute_signals
"""

from __future__ import annotations

import datetime as dt
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from .common import CONFIG_DIR, DATA_DIR, read_csv_dicts, write_csv

TAIWAN_DIR = DATA_DIR / "taiwan" / "monthly_revenue"
KOREA_DIR = DATA_DIR / "korea"
JAPAN_DIR = DATA_DIR / "japan"
DERIVED_DIR = DATA_DIR / "derived"

TAIWAN_SIGNAL_HEADER = [
    "report_month", "group", "n_members_reporting", "rev_sum_twd_k",
    "rev_sum_year_ago_twd_k", "agg_yoy_pct", "median_yoy_pct", "breadth_pct",
]
KOREA_SIGNAL_HEADER = [
    "period", "period_type", "item", "value_usd_k",
    "value_usd_k_year_ago", "yoy_pct",
]
JAPAN_SIGNAL_HEADER = [
    "period", "period_type", "source", "item", "value_jpy_m",
    "value_jpy_m_year_ago", "yoy_pct", "yoy_pct_published",
]


def _f(value: str | None) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except ValueError:
        return None


# --- Taiwan -----------------------------------------------------------------

def load_taiwan_months() -> dict[str, dict[str, dict]]:
    """{month: {company_id: row}} across all stored per-month files."""
    months: dict[str, dict[str, dict]] = defaultdict(dict)
    for path in sorted(TAIWAN_DIR.glob("*.csv")):
        for row in read_csv_dicts(path):
            months[row["report_month"]][row["company_id"]] = row
    return months


def taiwan_signals(months: dict[str, dict[str, dict]]) -> list[list]:
    groups = json.loads((CONFIG_DIR / "watchgroups.json").read_text("utf-8"))["groups"]
    out: list[list] = []
    for month in sorted(months):
        companies = months[month]
        for group_key, group in list(groups.items()) + [
            ("all_listed", {"members": {c: "" for c in companies}})
        ]:
            rows = [companies[c] for c in group["members"] if c in companies]
            pairs = [(_f(r["rev_month_twd_k"]), _f(r["rev_year_ago_month_twd_k"]))
                     for r in rows]
            pairs = [(a, b) for a, b in pairs if a is not None and b is not None and b > 0]
            if not pairs:
                continue
            cur = sum(a for a, _ in pairs)
            ago = sum(b for _, b in pairs)
            yoys = [(a / b - 1.0) * 100.0 for a, b in pairs]
            out.append([
                month, group_key, len(pairs), f"{cur:.0f}", f"{ago:.0f}",
                f"{(cur / ago - 1.0) * 100.0:.2f}",
                f"{statistics.median(yoys):.2f}",
                f"{100.0 * sum(1 for y in yoys if y > 0) / len(yoys):.1f}",
            ])
    return out


# --- Korea ------------------------------------------------------------------

def korea_signals() -> list[list]:
    path = KOREA_DIR / "exports_flash.csv"
    monthly_path = KOREA_DIR / "trade_monthly.csv"
    out: list[list] = []

    if path.exists():
        by_key: dict[tuple, float] = {}
        for row in read_csv_dicts(path):
            value = _f(row["value_usd_k"])
            if value is None or not row["yyyymm"]:
                continue
            prefix = "exp" if "export" in row["feed"] else "imp"
            item = f"{prefix}:{row['item_name'] or row['period_label']}"
            # Same month-of-year and window a year earlier is the comparable.
            by_key[(row["yyyymm"], row["period_type"] or row["period_label"], item)] = value
        for (yyyymm, ptype, item), value in sorted(by_key.items()):
            ago_yyyymm = f"{int(yyyymm[:4]) - 1}{yyyymm[4:]}"
            ago = by_key.get((ago_yyyymm, ptype, item))
            yoy = f"{(value / ago - 1.0) * 100.0:.2f}" if ago else ""
            out.append([yyyymm, ptype, item, f"{value:.0f}",
                        f"{ago:.0f}" if ago else "", yoy])

    tradedata_path = KOREA_DIR / "tradedata_flash.csv"
    if tradedata_path.exists():
        for row in read_csv_dicts(tradedata_path):
            value = _f(row["value_usd_m"])
            if value is None or not row["yyyymm"]:
                continue
            prefix = "exp" if row["metric"] == "Export" else "imp"
            out.append([row["yyyymm"], row["period_type"],
                        f"{prefix}:TOTAL (tradedata)", f"{value * 1000.0:.0f}",
                        "", row["yoy_pct"]])

    items_path = KOREA_DIR / "tradedata_items.csv"
    if items_path.exists():
        by_item_key: dict[tuple, float] = {}
        for row in read_csv_dicts(items_path):
            value = _f(row["value_usd_k"])
            if value is None or not row["yyyymm"]:
                continue
            prefix = "exp" if row["imex"] == "E" else "imp"
            by_item_key[(row["yyyymm"], row["period_type"],
                         f"{prefix}:{row['name']}")] = value
        for (yyyymm, ptype, item), value in sorted(by_item_key.items()):
            ago = by_item_key.get((f"{int(yyyymm[:4]) - 1}{yyyymm[4:]}", ptype, item))
            yoy = f"{(value / ago - 1.0) * 100.0:.2f}" if ago else ""
            out.append([yyyymm, ptype, item, f"{value:.0f}",
                        f"{ago:.0f}" if ago else "", yoy])

    if monthly_path.exists():
        by_ym: dict[tuple, float] = {}
        names: dict[str, str] = {}
        for row in read_csv_dicts(monthly_path):
            exp = _f(row["export_usd"])
            if exp is None:
                continue
            ym = row["year_month"][:7].replace(".", "-")
            by_ym[(ym, row["hs_code"])] = exp
            names[row["hs_code"]] = row.get("item_name") or f"HS {row['hs_code']}"
        for (ym, hs_code), exp in sorted(by_ym.items()):
            ago = by_ym.get((f"{int(ym[:4]) - 1}{ym[4:]}", hs_code))
            yoy = f"{(exp / ago - 1.0) * 100.0:.2f}" if ago else ""
            out.append([ym, "MONTH", f"HS{hs_code} {names[hs_code]}"[:60],
                        f"{exp / 1000.0:.0f}", f"{ago / 1000.0:.0f}" if ago else "", yoy])
    return out


# --- Japan ------------------------------------------------------------------

def _year_ago(yyyymm: str) -> str:
    return f"{int(yyyymm[:4]) - 1}{yyyymm[4:]}"


def _japan_interest() -> tuple[list[str], list[str]]:
    cfg = json.loads((CONFIG_DIR / "japan_endpoints.json").read_text("utf-8"))
    items = [s for s in cfg.get("press_release_items_of_interest", [])]
    prefixes = [k.replace(".", "") for k in cfg.get("hs_codes", {}) if not k.startswith("_")]
    return items, prefixes


def japan_signals() -> list[list]:
    """Long table of Japan series with YoY from the store's own history.

    Press-release rows keep the YoY MOF published alongside the computed one
    (they should agree once a year of history exists — a cheap parser check).
    Values are normalised to million yen: the press release publishes million
    yen, the CSV sources thousand yen.
    """
    out: list[list] = []
    items_of_interest, prefixes = _japan_interest()

    press_path = JAPAN_DIR / "press_release.csv"
    if press_path.exists():
        press = read_csv_dicts(press_path)
        langs = {r["lang"] for r in press}
        lang = "en" if "en" in langs else (sorted(langs)[0] if langs else "")
        by_key: dict[tuple, tuple[float, str]] = {}
        for row in press:
            value = _f(row["value_jpy_m"])
            if value is None or not row["yyyymm"] or row["lang"] != lang:
                continue
            if row["section"] == "COMMODITY" and row["area"] != "WORLD":
                continue  # by-country commodity tables stay in the store only
            item = f"{row['imex'] or '?'}:{row['name']}"
            if row["section"] == "AREA":
                item = f"{row['imex']}:AREA {row['name']}"
            # Later stages of the same month overwrite earlier ones (MONTH_DP
            # beats MONTH_PROV); 10/20-day windows are separate period types.
            by_key[(row["yyyymm"], row["period_type"].replace("MONTH_DP", "MONTH")
                    .replace("MONTH_PROV", "MONTH"), item)] = (value, row["yoy_pct"])
        for (yyyymm, ptype, item), (value, published) in sorted(by_key.items()):
            ago = by_key.get((_year_ago(yyyymm), ptype, item))
            yoy = f"{(value / ago[0] - 1.0) * 100.0:.2f}" if ago and ago[0] else ""
            out.append([yyyymm, ptype, "press_release", item, f"{value:.0f}",
                        f"{ago[0]:.0f}" if ago else "", yoy, published])

    ts_path = JAPAN_DIR / "time_series.csv"
    if ts_path.exists():
        by_ts: dict[tuple, float] = {}
        for row in read_csv_dicts(ts_path):
            value = _f(row["value_jpy_k"])
            if value is None or not row["yyyymm"]:
                continue
            label = row["name"] or row["code"] or row["series"]
            item = f"{row['imex'] or '?'}:{label}"
            by_ts[(row["yyyymm"], row["series"], item)] = value
        for (yyyymm, series, item), value in sorted(by_ts.items()):
            ago = by_ts.get((_year_ago(yyyymm), series, item))
            yoy = f"{(value / ago - 1.0) * 100.0:.2f}" if ago else ""
            out.append([yyyymm, "MONTH", f"timeseries:{series}", item,
                        f"{value / 1000.0:.0f}", f"{ago / 1000.0:.0f}" if ago else "",
                        yoy, ""])

    hs_path = JAPAN_DIR / "trade_monthly_hs.csv"
    if hs_path.exists():
        sums: dict[tuple, float] = {}
        for row in read_csv_dicts(hs_path):
            value = _f(row["value_jpy_k"])
            if value is None or not row["yyyymm"]:
                continue
            for prefix in prefixes:
                if row["hs_code"].startswith(prefix):
                    key = (row["yyyymm"], row["imex"], row["stage"], prefix)
                    sums[key] = sums.get(key, 0.0) + value
        # One stage per (month, direction, prefix): DETAILED beats PROV9.
        best: dict[tuple, tuple[str, float]] = {}
        for (yyyymm, imex, stage, prefix), value in sums.items():
            rank = {"DETAILED": 2, "PROV9": 1}.get(stage, 0)
            cur = best.get((yyyymm, imex, prefix))
            if cur is None or rank > {"DETAILED": 2, "PROV9": 1}.get(cur[0], 0):
                best[(yyyymm, imex, prefix)] = (stage, value)
        for (yyyymm, imex, prefix), (stage, value) in sorted(best.items()):
            ago = best.get((_year_ago(yyyymm), imex, prefix))
            yoy = f"{(value / ago[1] - 1.0) * 100.0:.2f}" if ago and ago[1] else ""
            out.append([yyyymm, "MONTH", f"estat_hs:{stage}", f"{imex}:HS{prefix}",
                        f"{value / 1000.0:.0f}", f"{ago[1] / 1000.0:.0f}" if ago else "",
                        yoy, ""])
    return out


def japan_highlights(jp: list[list], limit: int = 40) -> list[list]:
    """Rows worth printing: for each source, only its newest period, and only
    totals, configured press-release items and the HS-prefix sums."""
    items_of_interest, _ = _japan_interest()
    latest: dict[tuple, str] = {}
    for row in jp:
        key = (row[1], row[2].split(":")[0])
        latest[key] = max(latest.get(key, ""), row[0])
    keep: list[list] = []
    for row in jp:
        if row[0] != latest[(row[1], row[2].split(":")[0])]:
            continue
        if row[2] == "timeseries:world_total":
            continue  # duplicated by 総額 in the commodity series
        item = row[3]
        if item.endswith("AREA Grand Total"):
            continue  # same number as the TOTAL section
        if row[2].startswith("estat_hs") or "TOTAL" in item.upper() or "総額" in item:
            keep.append(row)
        elif any(tag.lower() in item.lower() for tag in items_of_interest):
            keep.append(row)
    return keep[-limit:]

# --- Report -----------------------------------------------------------------

def render_report(tw: list[list], kr: list[list], jp: list[list] | None = None) -> str:
    jp = jp or []
    lines = [
        "# Demand-signal snapshot: Taiwan monthly revenue + Korea exports + Japan trade",
        "",
        f"_Generated {dt.date.today().isoformat()} by `signals/compute_signals.py`._",
        "_Derived data; the underlying records in `data/` are the source of truth._",
        "",
    ]
    if tw:
        latest = max(row[0] for row in tw)
        lines += [f"## Taiwan monthly revenue — {latest}", "",
                  "| Group | n | Agg YoY % | Median YoY % | Breadth % |",
                  "|---|---:|---:|---:|---:|"]
        for row in tw:
            if row[0] == latest:
                lines.append(f"| {row[1]} | {row[2]} | {row[5]} | {row[6]} | {row[7]} |")
        history = sorted({r[0] for r in tw})[-4:-1]
        for month in reversed(history):
            for row in tw:
                if row[0] == month and row[1] == "ai_compute":
                    lines.append(f"\n_{month} ai_compute agg YoY: {row[5]}%_")
        lines.append("")
    else:
        lines += ["## Taiwan monthly revenue", "", "_No data stored yet — run "
                  "`python -m signals.taiwan_mops current`._", ""]
    if kr:
        lines += ["## Korea trade (KCS)", "",
                  "| Period | Window | Item | USD k | YoY % |",
                  "|---|---|---|---:|---:|"]
        for row in kr[-25:]:
            lines.append(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[5]} |")
        lines.append("")
    else:
        lines += ["## Korea exports (KCS)", "", "_No data stored yet — set "
                  "`DATA_GO_KR_API_KEY` and run `python -m signals.korea_customs "
                  "monthly-latest`._", ""]
    if jp:
        lines += ["## Japan trade (MOF / Customs) — supply side", "",
                  "| Period | Window | Source | Item | JPY m | YoY % (store) | YoY % (published) |",
                  "|---|---|---|---|---:|---:|---:|"]
        for row in japan_highlights(jp):
            lines.append(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | "
                         f"{row[6]} | {row[7]} |")
        lines.append("")
    else:
        lines += ["## Japan trade (MOF / Customs)", "", "_No data stored yet — run "
                  "`python -m signals.japan_customs flash`._", ""]
    lines += [
        "---",
        "Validation status (constitution §21): raw government data, "
        "mechanically aggregated. Tier 1 screening input only; not a thesis, "
        "not advice.", "",
    ]
    return "\n".join(lines)


def main(_argv: list[str]) -> int:
    months = load_taiwan_months()
    tw = taiwan_signals(months)
    kr = korea_signals()
    jp = japan_signals()
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(DERIVED_DIR / "taiwan_signals.csv", TAIWAN_SIGNAL_HEADER, tw)
    write_csv(DERIVED_DIR / "korea_signals.csv", KOREA_SIGNAL_HEADER, kr)
    write_csv(DERIVED_DIR / "japan_signals.csv", JAPAN_SIGNAL_HEADER, jp)
    (DERIVED_DIR / "latest_report.md").write_text(render_report(tw, kr, jp), "utf-8")
    print(f"taiwan_signals: {len(tw)} rows over {len(months)} months; "
          f"korea_signals: {len(kr)} rows; japan_signals: {len(jp)} rows; "
          "report written.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
