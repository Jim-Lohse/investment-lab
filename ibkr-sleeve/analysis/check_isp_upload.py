#!/usr/bin/env python3
"""Cross-check Jim's uploaded Milan-native ISP.MI daily file (2026-08-19,
Yahoo-Finance-style columns, EUR) against (a) the IBKR SMART-routed Milan
bars used in the pipeline, (b) the Section 5.9 ISP fill, and (c) the
reconciled EUR dividend table via the upload's own Adj Close ratios.
Read-only diagnostic; prints evidence, changes nothing."""

import os
import pandas as pd

DATA = os.path.join(os.path.dirname(__file__), "..", "data")

def load(name):
    df = pd.read_csv(os.path.join(DATA, "prices", f"{name}.csv"))
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date").sort_index()

up = load("ISP.MI.upload")
ib = load("ISP.BVME.ibkr")

print(f"Upload coverage: {up.index[0].date()} -> {up.index[-1].date()},"
      f" {len(up)} rows, {int(up['close'].isna().sum())} null rows"
      f" ({', '.join(str(d.date()) for d in up.index[up['close'].isna()])})")

# (a) close-vs-close on the overlap
both = up[["close"]].dropna().join(ib[["close"]], rsuffix="_ibkr", how="inner")
rel = both["close"] / both["close_ibkr"] - 1
print(f"\nOverlap with IBKR daily bars: {len(both)} days"
      f" ({both.index[0].date()} -> {both.index[-1].date()})")
print(f"  close diff: mean {rel.mean():+.3%}, mean|.| {rel.abs().mean():.3%},"
      f" max|.| {rel.abs().max():.3%} on {rel.abs().idxmax().date()}"
      f" (upload {both.loc[rel.abs().idxmax(), 'close']}"
      f" vs IBKR {both.loc[rel.abs().idxmax(), 'close_ibkr']})")
print(f"  days with |diff| > 0.5%: {(rel.abs() > 0.005).sum()}")
print("  IBKR has bars on the upload's null dates:",
      ", ".join(f"{d.date()}={ib.loc[d, 'close']}" for d in
                up.index[up["close"].isna()] if d in ib.index))

# (b) the known fill
r = up.loc[pd.Timestamp("2026-08-06")]
ok = r["low"] <= 6.843 <= r["high"]
print(f"\nFill check 2026-08-06 BUY 545 @ 6.843:"
      f" upload O={r['open']} H={r['high']} L={r['low']} C={r['close']}"
      f" -> {'PASS (inside range)' if ok else 'FAIL'}")

# (c) dividends implied by the upload's Adj Close column
ratio = up["adj_close"] / up["close"]
implied = []
for d in up.index[1:]:
    prev_close = up["close"].shift(1).loc[d]
    prev_ratio = ratio.shift(1).loc[d]
    div = prev_close * (1 - ratio.loc[d] / prev_ratio)
    if pd.notna(div) and abs(div) > 0.05:  # below that is 6-decimal rounding noise
        implied.append((d.date(), round(float(div), 3)))
print("\nDividend events implied by upload Adj Close ratio changes"
      " (|amount| > 0.05; amounts carry ~±0.01 rounding noise):", implied)
rec = pd.read_csv(os.path.join(DATA, "dividends_reconciled", "ISP.csv"))
rec["date"] = pd.to_datetime(rec["date"])
inwin = rec[(rec["date"] >= up.index[0]) & (rec["date"] <= up.index[-1])]
print("Reconciled table in the same window:",
      [(d.date(), v) for d, v in zip(inwin["date"], inwin["value"])])
