#!/usr/bin/env python3
"""Session 1: derive the drawdown cap X, validate the dataset against known
fills, and backtest the cap's firing frequency on sleeve history.

Rules: CLAUDE.md (repo root). Labeled inputs are printed BEFORE any computed
output (Section 5.8). Zero fabrication: every market number is read from the
CSVs under ibkr-sleeve/data/ fetched from EODHD, or is a labeled household
planning input.
"""

import os
import sys
import pandas as pd

DATA = os.path.join(os.path.dirname(__file__), "..", "data")

# ----------------------------------------------------------------------------
# PART 1 — Derive the drawdown cap X (Section 2 household inputs)
# ----------------------------------------------------------------------------

# Labeled household inputs (CLAUDE.md Section 2 — given, not derived here)
T = 1_970_000          # retirement nominal target, USD
H = 14                 # horizon, years
W = 0.035              # planned withdrawal rate at retirement
R_REQ = 0.0            # required nominal return on liquid accounts (~zero)

# Labeled market input (EODHD US Treasury par yield curve, as of 2026-08-14)
UST_10Y = 0.0468       # 10Y par yield 2026-08-14
UST_20Y = 0.0525       # 20Y par yield 2026-08-14
R_SAFE_14Y = UST_10Y + (UST_20Y - UST_10Y) * (14 - 10) / (20 - 10)

# Labeled literature anchor (the one imported constant, flagged in the memo):
# 4.0% = classic sustainable-withdrawal boundary (Bengen 1994 / Trinity study).
W_MAX = 0.040

# Labeled mandate input (CLAUDE.md Section 3): active ex-US sleeve is capped at
# 50% of household liquid assets at full scale; the remainder is bond-equivalent.
SLEEVE_SHARE_FULL_SCALE = 0.50

def derive_cap(verbose=True):
    # Step 0: r_req ~ 0 over 14y implies liquid assets today ~ target.
    A0 = T / (1 + R_REQ) ** H
    # Bound A (solvency): after an unrecovered household drawdown D, the return
    # needed to still reach T in 14y is (1-D)^(-1/H)-1; tolerable while that
    # stays within the bond-equivalent (no equity risk) rate r_safe.
    D_solvency = 1 - (1 + R_SAFE_14Y) ** (-H)
    # Bound B (income): an unrecovered drawdown D forces the withdrawal rate
    # from w to w/(1-D) for the same income; tolerable while w/(1-D) <= w_max.
    D_income = 1 - W / W_MAX
    # Household tolerance = the tighter bound.
    D_household = min(D_solvency, D_income)
    # Sleeve translation: at full mandate scale the sleeve is at most 50% of
    # household liquid assets and the rest is bond-equivalent (~drawdown-free),
    # so household drawdown = sleeve_share x sleeve drawdown.
    X = D_household / SLEEVE_SHARE_FULL_SCALE
    if verbose:
        print("== PART 1: CAP DERIVATION ==")
        print(f"Inputs: T=${T:,.0f}  H={H}y  w={W:.1%}  r_req={R_REQ:.1%}")
        print(f"        UST 10Y={UST_10Y:.2%} 20Y={UST_20Y:.2%} (2026-08-14)"
              f" -> r_safe(14y interp)={R_SAFE_14Y:.3%}")
        print(f"        w_max={W_MAX:.1%} (Bengen/Trinity anchor)"
              f"  sleeve share at full scale={SLEEVE_SHARE_FULL_SCALE:.0%}")
        print(f"Implied liquid assets today A0 = T/(1+r_req)^H = ${A0:,.0f}")
        print(f"Bound A (solvency): 1-(1+{R_SAFE_14Y:.3%})^-{H} = {D_solvency:.1%}")
        print(f"Bound B (income):   1-{W:.1%}/{W_MAX:.1%}       = {D_income:.1%}")
        print(f"Household tolerance = min(A,B) = {D_household:.1%}")
        print(f"Sleeve cap X = {D_household:.1%} / {SLEEVE_SHARE_FULL_SCALE:.0%} "
              f"= {X:.1%} max peak-to-trough, USD total-return NAV")
    return X

# ----------------------------------------------------------------------------
# PART 2 — Load dataset, validate against known fills (Section 5.9)
# ----------------------------------------------------------------------------

def load_prices(name):
    df = pd.read_csv(os.path.join(DATA, "prices", f"{name}.csv"))
    df.columns = [c.strip().lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date").sort_index()

FILLS = [  # (ticker, date, side, fill price in venue quote units, label)
    ("IES.XETRA",  "2026-08-06", "BUY 545",       6.843,  "EUR"),
    ("IMB.LSE", "2026-08-14", "BUY 26",        2629.0, "GBX (pence)"),
    ("EUAD.US", "2026-08-14", "SELL 25.5427",  47.86,  "USD"),
    ("INDA.US", "2026-08-14", "SELL 21",       49.775, "USD"),
]

def validate_fills():
    print("\n== PART 2: VALIDATION AGAINST KNOWN FILLS (Section 5.9) ==")
    all_ok = True
    for tkr, d, side, fill, unit in FILLS:
        df = load_prices(tkr)
        d = pd.Timestamp(d)
        if d not in df.index:
            print(f"FAIL {tkr} {d.date()}: date missing from dataset")
            all_ok = False
            continue
        row = df.loc[d]
        lo, hi, cl = row["low"], row["high"], row["close"]
        ok = lo <= fill <= hi
        all_ok &= ok
        print(f"{'PASS' if ok else 'FAIL'} {tkr} {d.date()} {side} @ {fill} {unit}"
              f" | raw O={row['open']} H={hi} L={lo} C={cl}"
              f" -> fill {'inside' if ok else 'OUTSIDE'} day range")
    return all_ok

# ----------------------------------------------------------------------------
# PART 3 — Sleeve history and cap firing frequency (Section 9 item 2)
# ----------------------------------------------------------------------------

# Current sleeve weights (CLAUDE.md Section 3, IBKR-verified 2026-08-14)
WEIGHTS = {"IES.XETRA": 0.376, "RR.LSE": 0.162, "IMB.LSE": 0.158,
           "FFH.TO": 0.141, "SCCO.US": 0.099}
CASH_W = 0.064  # earns 0% in this diagnostic (flagged in memo)

FX_FOR = {"IES.XETRA": ("EURUSD.FOREX", 1.0), "RR.LSE": ("GBPUSD.FOREX", 0.01),
          "IMB.LSE": ("GBPUSD.FOREX", 0.01), "FFH.TO": ("CADUSD.FOREX", 1.0),
          "SCCO.US": (None, 1.0)}  # scale 0.01 converts GBX pence -> GBP

def build_usd_series():
    """USD total-return index per name.

    Calendar rule (Section 5.7, stated): union of the five equity venues'
    trading dates; each local adjusted close and each FX rate forward-filled
    over its own venue's holidays. No inner join, no dropped dates.
    Total return: EODHD adjusted_close (split- and dividend-adjusted, gross
    dividends reinvested same day in the same name, local currency), then
    converted to USD at the day's FX rate.
    """
    px, fx = {}, {}
    for name in WEIGHTS:
        df = load_prices(name)
        px[name] = df["adjusted_close"]
        f = FX_FOR[name][0]
        if f and f not in fx:
            fx[f] = load_prices(f)["close"]
    cal = None
    for s in px.values():
        cal = s.index if cal is None else cal.union(s.index)
    usd = {}
    for name, s in px.items():
        f, scale = FX_FOR[name]
        loc = s.reindex(cal).ffill() * scale
        rate = fx[f].reindex(cal).ffill() if f else 1.0
        usd[name] = loc * rate
    out = pd.DataFrame(usd).dropna()  # drop leading dates before all series exist
    return out

def firing_stats(nav, X):
    peak = nav.cummax()
    dd = nav / peak - 1
    breached = dd <= -X
    episodes = int((breached & ~breached.shift(fill_value=False)).sum())
    return episodes, int(breached.sum()), float(dd.min())

def backtest(X):
    usd = build_usd_series()
    print("\n== PART 3: SLEEVE HISTORY AND CAP FIRING ==")
    print("Raw inputs (Section 5.8) — USD total-return series coverage:")
    for name in usd.columns:
        s = usd[name]
        print(f"  {name}: {s.index[0].date()} -> {s.index[-1].date()}"
              f"  first={s.iloc[0]:.4f} last={s.iloc[-1]:.4f}  n={len(s)}")
    print(f"Weights: {WEIGHTS} cash={CASH_W} (cash return 0%)")
    print("Construction: buy-and-hold, seeded at current weights on window start;"
          " no rebalancing, so no trading frictions inside the window (entry"
          " frictions scale NAV and cancel out of peak-to-trough drawdown).")
    windows = {
        "full common window": usd.index[0],
        "trailing 5y": usd.index[-1] - pd.DateOffset(years=5),
        "trailing 2y": usd.index[-1] - pd.DateOffset(years=2),
    }
    for label, start in windows.items():
        u = usd[usd.index >= start]
        rel = u / u.iloc[0]
        nav = rel.mul(pd.Series(WEIGHTS)).sum(axis=1) + CASH_W
        ep, days, mdd = firing_stats(nav, X)
        print(f"\n[{label}] {u.index[0].date()} -> {u.index[-1].date()} "
              f"({len(nav)} trading days, {(u.index[-1]-u.index[0]).days/365.25:.1f}y)")
        print(f"  max drawdown {mdd:.1%}; cap X={X:.1%} fired {ep} time(s), "
              f"{days} day(s) in breach ({days/len(nav):.1%} of days)")
        print("  sensitivity:")
        for x in (0.10, 0.125, 0.15, 0.20, 0.25, 0.30, 0.40):
            ep, days, _ = firing_stats(nav, x)
            print(f"    X={x:>5.1%}: {ep} episode(s), {days} breach day(s)"
                  f" ({days/len(nav):.1%} of days)")

if __name__ == "__main__":
    X = derive_cap()
    ok = validate_fills()
    if not ok and "--force" not in sys.argv:
        print("\nSTOP: fill validation failed — reconcile before any backtest"
              " (Section 5.9). Rerun with --force only to inspect.")
        sys.exit(1)
    backtest(X)
