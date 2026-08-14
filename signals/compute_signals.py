"""Compute demand signals from the stored Taiwan and Korea data.

Outputs (regenerated in full each run — derived data, not a record):
  data/derived/taiwan_signals.csv  — per (month, group): aggregate YoY, median
                                     YoY, breadth (share of members growing)
  data/derived/korea_signals.csv   — per (period, item): exports and YoY where
                                     a year-ago observation exists
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
DERIVED_DIR = DATA_DIR / "derived"

TAIWAN_SIGNAL_HEADER = [
    "report_month", "group", "n_members_reporting", "rev_sum_twd_k",
    "rev_sum_year_ago_twd_k", "agg_yoy_pct", "median_yoy_pct", "breadth_pct",
]
KOREA_SIGNAL_HEADER = [
    "period", "period_type", "item", "value_usd_k",
    "value_usd_k_year_ago", "yoy_pct",
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


# --- Report -----------------------------------------------------------------

def render_report(tw: list[list], kr: list[list]) -> str:
    lines = [
        "# Demand-signal snapshot: Taiwan monthly revenue + Korea exports",
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
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(DERIVED_DIR / "taiwan_signals.csv", TAIWAN_SIGNAL_HEADER, tw)
    write_csv(DERIVED_DIR / "korea_signals.csv", KOREA_SIGNAL_HEADER, kr)
    (DERIVED_DIR / "latest_report.md").write_text(render_report(tw, kr), "utf-8")
    print(f"taiwan_signals: {len(tw)} rows over {len(months)} months; "
          f"korea_signals: {len(kr)} rows; report written.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
