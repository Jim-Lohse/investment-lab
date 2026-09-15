"""What changed in this run: diff the derived tables against the previous run.

Runs at the end of the update-signals workflow, after compute_signals, with
the pre-run copy of data/derived/ as the baseline. It answers three things
mechanically so the daily intelligence brief (and a human skimming the run
page) does not have to re-derive them:

  1. Which (source, period, window) got new rows this run, and how many
     rows were revised (a later stage overwriting an earlier print).
  2. Which of the headline rows crossed a flag threshold: a new print whose
     YoY is beyond FLAG_YOY_PCT either way, or an origin whose share of a
     U.S. code moved by FLAG_SHARE_PT or more versus the prior month.
  3. A one-line subject for the data commit ("3 new prints, 2 flags").

Flags are screening arithmetic, not judgment: constitution §21 Tier 1 input.
They open watch items for the brief to look at; they never open decision
windows (§13.7). The brief's "So what" and "What now" sections are written
by the daily Routine, not here.

Outputs:
  data/derived/whats_new.md   — the diff, headline rows and flags
  $GITHUB_STEP_SUMMARY        — the same markdown, appended when set
  stdout (last line)          — the commit subject

Usage:
    python -m signals.intel --previous /path/to/previous/derived
    python -m signals.intel --previous /path/to/previous/derived --today 2026-09-12
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

from .common import CONFIG_DIR, DATA_DIR, read_csv_dicts

DERIVED_DIR = DATA_DIR / "derived"

FLAG_YOY_PCT = 25.0     # |YoY| at or beyond this on a headline row is a flag
FLAG_SHARE_PT = 5.0     # origin share of a U.S. code moving this much m/m is a flag
US_MIN_SHARE_PCT = 5.0  # a U.S. origin row is material only at this share of its code
US_MIN_VALUE_K = 5000.0  # ... and at least USD 5m in the month
US_ORIGIN_YOY_PCT = 50.0  # origin rows (noisier than code totals) need a bigger YoY move

# Per table: file name, key columns, value column, YoY column (or None).
TABLES = {
    "taiwan": ("taiwan_signals.csv", ["report_month", "group"], "agg_yoy_pct", "agg_yoy_pct"),
    "korea": ("korea_signals.csv", ["period", "period_type", "item"], "value_usd_k", "yoy_pct"),
    "japan": ("japan_signals.csv", ["period", "period_type", "source", "item"],
              "value_jpy_m", "yoy_pct"),
    "us": ("us_signals.csv", ["period", "imex", "code", "cty_code"], "value_usd_k", "yoy_pct"),
}

KOREA_HEADLINE_TOKENS = ("TOTAL", "반도체", "SEMICON", "정밀기기", "무선통신기기", "컴퓨터")


def _f(value: str | None) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except ValueError:
        return None


def _load(directory: Path, name: str) -> dict[tuple, dict]:
    filename, key_cols, _, _ = TABLES[name]
    path = directory / filename
    if not path.exists():
        return {}
    return {tuple(r[c] for c in key_cols): r for r in read_csv_dicts(path)}


def _period_of(name: str, key: tuple) -> tuple[str, str]:
    """(period, window) for grouping the diff; Taiwan and U.S. have no window."""
    if name == "taiwan":
        return key[0], "MONTH"
    if name == "us":
        return key[0], key[1]  # period, I/E
    return key[0], key[1]


# --- Headline filters --------------------------------------------------------

def _japan_headline(row: dict, items_of_interest: list[str]) -> bool:
    item = row["item"]
    if row["source"].startswith("estat_hs"):
        return True
    if row["source"] == "timeseries:world_total" or item.endswith("AREA Grand Total"):
        return False
    if "TOTAL" in item.upper() or "総額" in item:
        return True
    return any(tag.lower() in item.lower() for tag in items_of_interest)


def _korea_headline(row: dict) -> bool:
    item = row["item"].upper()
    return any(tok.upper() in item for tok in KOREA_HEADLINE_TOKENS)


def _us_headline(row: dict, share_codes: set[str], top_origins: set[tuple]) -> bool:
    if row["cty_code"] == "-":
        return True
    return row["code"] in share_codes and (row["period"], row["imex"], row["code"],
                                           row["cty_code"]) in top_origins


def _us_top_origins(current: dict[tuple, dict], share_codes: set[str], n: int = 6) -> set[tuple]:
    """The n largest origins per (period, I/E, share code) by value."""
    buckets: dict[tuple, list[tuple[float, tuple]]] = {}
    for key, row in current.items():
        if row["cty_code"] == "-" or row["code"] not in share_codes:
            continue
        value = _f(row["value_usd_k"]) or 0.0
        buckets.setdefault(key[:3], []).append((value, key))
    keep: set[tuple] = set()
    for entries in buckets.values():
        keep |= {k for _, k in sorted(entries, key=lambda e: -e[0])[:n]}
    return keep


def _headline_filter(name: str, current: dict[tuple, dict]):
    if name == "japan":
        cfg = json.loads((CONFIG_DIR / "japan_endpoints.json").read_text("utf-8"))
        items = cfg.get("press_release_items_of_interest", [])
        return lambda row: _japan_headline(row, items)
    if name == "korea":
        return _korea_headline
    if name == "us":
        cfg = json.loads((CONFIG_DIR / "us_endpoints.json").read_text("utf-8"))
        share_codes = set(cfg.get("origin_share_codes", []))
        top = _us_top_origins(current, share_codes)
        return lambda row: _us_headline(row, share_codes, top)
    return lambda row: True


# --- Diff ---------------------------------------------------------------------

def diff_tables(previous_dir: Path, current_dir: Path = DERIVED_DIR) -> dict:
    """Per source: new rows, revised rows, and the headline subset of each."""
    out: dict = {}
    for name in TABLES:
        prev = _load(previous_dir, name)
        cur = _load(current_dir, name)
        _, _, value_col, _ = TABLES[name]
        is_headline = _headline_filter(name, cur)
        new_rows = {k: r for k, r in cur.items() if k not in prev}
        revised = {}
        for k, r in cur.items():
            if k in prev and prev[k].get(value_col, "") != r.get(value_col, ""):
                revised[k] = (prev[k], r)
        groups: dict[tuple, dict] = {}
        for k in new_rows:
            g = groups.setdefault(_period_of(name, k), {"new": 0, "revised": 0})
            g["new"] += 1
        for k in revised:
            g = groups.setdefault(_period_of(name, k), {"new": 0, "revised": 0})
            g["revised"] += 1
        out[name] = {
            "baseline": not prev,
            "new": new_rows,
            "revised": revised,
            "groups": groups,
            "headline_new": {k: r for k, r in new_rows.items() if is_headline(r)},
            "headline_revised": {k: v for k, v in revised.items() if is_headline(v[1])},
            "current": cur,
        }
    return out


# --- Flags --------------------------------------------------------------------

def _us_prior_share(current: dict[tuple, dict], key: tuple) -> float | None:
    period, imex, code, cty = key
    y, m = int(period[:4]), int(period[5:7])
    y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    prior = current.get((f"{y:04d}-{m:02d}", imex, code, cty))
    return _f(prior["share_of_code_pct"]) if prior else None


def flags_for(diff: dict) -> list[dict]:
    """Threshold crossings among the headline rows that are new this run."""
    flags: list[dict] = []
    for name, d in diff.items():
        if d["baseline"]:
            continue
        _, _, value_col, yoy_col = TABLES[name]
        for key, row in sorted(d["headline_new"].items()):
            label = _label(name, row)
            yoy = _f(row.get(yoy_col))
            threshold = FLAG_YOY_PCT
            if name == "japan":
                if row["source"].startswith("timeseries"):
                    continue  # same numbers as the press release; flag once
                if yoy is None:
                    yoy = _f(row.get("yoy_pct_published"))  # store history < 1 year
            if name == "us" and row["cty_code"] != "-":
                share = _f(row.get("share_of_code_pct")) or 0.0
                prior = _us_prior_share(d["current"], key) or 0.0
                value = _f(row.get(value_col)) or 0.0
                if max(share, prior) < US_MIN_SHARE_PCT or value < US_MIN_VALUE_K:
                    continue  # immaterial origin: noise, not a watch item
                threshold = US_ORIGIN_YOY_PCT
            if yoy is not None and abs(yoy) >= threshold:
                detail = f"{yoy:+.1f}% YoY"
                # For Japan, say straight away how much of that is the yen, so
                # the brief can grade a currency-driven print as noise.
                yoy_usd = _f(row.get("yoy_pct_usd"))
                fx_pt = _f(row.get("fx_effect_pt"))
                if yoy_usd is not None:
                    detail += f" ({yoy_usd:+.1f}% in USD"
                    detail += f", {fx_pt:+.1f} pt currency)" if fx_pt is not None else ")"
                flags.append({"source": name, "period": key[0], "item": label,
                              "kind": "yoy", "detail": detail,
                              "value": row.get(value_col, "")})
            if name == "us" and row["cty_code"] != "-":
                share = _f(row.get("share_of_code_pct"))
                prior = _us_prior_share(d["current"], key)
                if share is not None and prior is not None and abs(share - prior) >= FLAG_SHARE_PT:
                    flags.append({"source": name, "period": key[0], "item": label,
                                  "kind": "share",
                                  "detail": f"share {prior:.1f}% -> {share:.1f}% of code m/m",
                                  "value": row.get(value_col, "")})
    order = {name: i for i, name in enumerate(TABLES)}
    flags.sort(key=lambda fl: (order[fl["source"]], fl["period"],
                               -abs(_f(fl["value"]) or 0.0)))
    return flags


def _label(name: str, row: dict) -> str:
    if name == "taiwan":
        return f"{row['group']} (n={row['n_members_reporting']}, breadth {row['breadth_pct']}%)"
    if name == "korea":
        return f"{row['period_type']} {row['item']}"
    if name == "japan":
        return f"{row['period_type']} {row['source']} {row['item']}"
    return f"{row['imex']} {row['code']} {row['cty_name']}"


# --- Render -------------------------------------------------------------------

UNITS = {"taiwan": "agg YoY %", "korea": "USD k", "japan": "JPY m", "us": "USD k"}


def render(diff: dict, flags: list[dict], today: str) -> tuple[str, str]:
    """Returns (markdown, commit subject)."""
    n_groups = sum(len(d["groups"]) for d in diff.values() if not d["baseline"])
    n_new = sum(len(d["new"]) for d in diff.values() if not d["baseline"])
    n_rev = sum(len(d["revised"]) for d in diff.values() if not d["baseline"])
    lines = [f"# What's new — signals run {today}", ""]
    if flags:
        lines += [f"## FLAGS ({len(flags)}) — watch items for the brief to grade", ""]
        for fl in flags:
            lines.append(f"- **{fl['source'].upper()} {fl['period']}** {fl['item']}: "
                         f"{fl['detail']} (value {fl['value']})")
        lines.append("")
    else:
        lines += ["## No flags this run", ""]
    if n_groups:
        lines += [f"## New prints ({n_groups} source/period groups; {n_new} rows new, "
                  f"{n_rev} revised)", "",
                  "| Source | Period | Window | New rows | Revised rows |",
                  "|---|---|---|---:|---:|"]
        for name, d in diff.items():
            if d["baseline"]:
                continue
            for (period, window), g in sorted(d["groups"].items(), reverse=True):
                lines.append(f"| {name} | {period} | {window} | {g['new']} | {g['revised']} |")
        lines.append("")
    else:
        lines += ["## No new prints this run", ""]
    for name, d in diff.items():
        if d["baseline"]:
            lines += [f"_{name}: no previous snapshot; baseline established, nothing graded._", ""]
            continue
        rows = sorted(d["headline_new"].items(), reverse=True)
        if rows:
            _, _, value_col, yoy_col = TABLES[name]
            lines += [f"### {name}: headline rows new this run ({UNITS[name]})", "",
                      "| Period | Item | Value | YoY % |", "|---|---|---:|---:|"]
            for key, row in rows[:40]:
                lines.append(f"| {key[0]} | {_label(name, row)} | {row.get(value_col, '')} | "
                             f"{row.get(yoy_col, '')} |")
            if len(rows) > 40:
                lines.append(f"| … | {len(rows) - 40} more | | |")
            lines.append("")
        revs = sorted(d["headline_revised"].items(), reverse=True)
        if revs:
            _, _, value_col, _ = TABLES[name]
            lines += [f"### {name}: headline rows revised this run ({UNITS[name]})", "",
                      "| Period | Item | Was | Now |", "|---|---|---:|---:|"]
            for key, (old, new) in revs[:20]:
                lines.append(f"| {key[0]} | {_label(name, new)} | {old.get(value_col, '')} | "
                             f"{new.get(value_col, '')} |")
            lines.append("")
    lines += ["---",
              "How to read this. A flag is raised when a headline figure grew or shrank by "
              f"{FLAG_YOY_PCT:.0f}% or more against the same month a year earlier, or when a "
              f"country's share of what the United States bought moved by {FLAG_SHARE_PT:.0f} "
              "points or more in a single month. That is arithmetic, not judgement: a flag "
              "says a number moved, not that the move matters. The daily summary decides "
              "which ones matter. Flags are early evidence that put things on the watch "
              "list; on their own they are not grounds for a decision.", ""]
    if n_groups == 0 and not flags:
        subject = "no new prints"
    else:
        subject = f"{n_groups} new print group{'s' if n_groups != 1 else ''}"
        if n_rev:
            subject += f", {n_rev} revised"
        subject += f", {len(flags)} flag{'s' if len(flags) != 1 else ''}"
    return "\n".join(lines), subject


def main(argv: list[str]) -> int:
    previous = None
    today = dt.date.today().isoformat()
    args = list(argv)
    while args:
        arg = args.pop(0)
        if arg == "--previous" and args:
            previous = Path(args.pop(0))
        elif arg == "--today" and args:
            today = args.pop(0)
        else:
            print(__doc__)
            return 2
    if previous is None:
        print(__doc__)
        return 2
    diff = diff_tables(previous)
    flags = flags_for(diff)
    markdown, subject = render(diff, flags, today)
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    (DERIVED_DIR / "whats_new.md").write_text(markdown, "utf-8")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as fh:
            fh.write(markdown + "\n")
    print(markdown)
    print(subject)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
