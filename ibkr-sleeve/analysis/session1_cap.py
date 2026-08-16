#!/usr/bin/env python3
"""Session 1 (rev 2, post-rulings): derive the drawdown cap X, validate the
dataset against known fills, and backtest the cap's firing frequency on
sleeve history.

Rules: CLAUDE.md (repo root). Labeled inputs are printed BEFORE any computed
output (Section 5.8). Zero fabrication: every market number is read from the
CSVs under ibkr-sleeve/data/ (EODHD; IBKR for the ISP Milan line and
corporate actions), or is a labeled household/policy input.

Rev 2 changes (Jim's rulings, 2026-08-16):
  #1 cash leg accrues at the 3-month T-bill rate (data/rates/UST_BILL_3M.csv)
     instead of 0%.
  #2 dividends come from data/dividends_reconciled/<KEY>.csv — EODHD merged
     with IBKR corporate-action records and company declarations, disputes
     resolved with evidence (see reconcile_dividends.py).
  #3 total return is rebuilt from RAW closes + reconciled NET dividends with
     per-venue withholding (Italy 26% — IBKR default absent treaty relief;
     Canada 15% treaty; UK 0%; US-listed SCCO 0% withheld), replacing
     EODHD's gross-dividend adjusted_close. A gross/net comparison is
     printed to quantify the change.

ISP source: IBKR Milan (BVME) closes from 2021-08-16; XETRA line (same ISIN,
EUR) spliced in front as the labeled proxy for earlier history (accepted with
label, Jim 2026-08-16). Both are EUR prices of the same share; the splice is
direct concatenation at 2021-08-16, flagged.
"""

import json
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

# Labeled anchor — a JUDGMENT CALL, not a household input (recorded per Jim's
# ruling #5): 4.0% = classic sustainable-withdrawal boundary (Bengen 1994 /
# Trinity study). X is sensitive to it; see sensitivity_of_X().
W_MAX = 0.040

# Labeled mandate input (CLAUDE.md Section 3): active ex-US is capped at 50%
# of household liquid assets. Using the guardrail MAXIMUM is the conservative
# choice: the largest deployment the rules permit forces the tightest sleeve
# cap; any smaller actual deployment makes X looser than needed, never
# tighter. See sensitivity_of_X().
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
        print(f"        w_max={W_MAX:.1%} (Bengen/Trinity anchor — judgment call)"
              f"  sleeve share at full scale={SLEEVE_SHARE_FULL_SCALE:.0%}"
              f" (mandate guardrail maximum)")
        print(f"Implied liquid assets today A0 = T/(1+r_req)^H = ${A0:,.0f}")
        print(f"Bound A (solvency): 1-(1+{R_SAFE_14Y:.3%})^-{H} = {D_solvency:.1%}")
        print(f"Bound B (income):   1-{W:.1%}/{W_MAX:.1%}       = {D_income:.1%}")
        print(f"Household tolerance = min(A,B) = {D_household:.1%}")
        print(f"Sleeve cap X = {D_household:.1%} / {SLEEVE_SHARE_FULL_SCALE:.0%} "
              f"= {X:.1%} max peak-to-trough, USD total-return NAV")
        sensitivity_of_X()
    return X

def sensitivity_of_X():
    """Which input moves X to 20% or 30% (Jim's ruling #5)."""
    print("Sensitivity of X (income bound binding throughout — it stops"
          " binding only if w_max >= 6.85%, implausible):")
    for x_target in (0.20, 0.30):
        # holding s=50%: X = (1 - w/w_max)/s  ->  w_max = w / (1 - s*X)
        wm = W / (1 - SLEEVE_SHARE_FULL_SCALE * x_target)
        # holding w_max=4.0%: s = (1 - w/w_max)/X
        s = (1 - W / W_MAX) / x_target
        print(f"  X={x_target:.0%} needs w_max={wm:.3%} (s fixed 50%)"
              f"  OR  s={s:.1%} (w_max fixed 4.0%)"
              f"{'  — s>50% not permitted by mandate' if s > 0.5001 else ''}")
    print(f"  Gradient: +0.1pp in w_max moves X by ~+{0.001*W/(W_MAX**2*SLEEVE_SHARE_FULL_SCALE):.1%}p"
          f" around the base point — w_max is the driving assumption.")

# ----------------------------------------------------------------------------
# PART 2 — Load dataset, validate against known fills (Section 5.9)
# ----------------------------------------------------------------------------

def load_prices(name):
    df = pd.read_csv(os.path.join(DATA, "prices", f"{name}.csv"))
    df.columns = [c.strip().lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date").sort_index()

FILLS = [  # (ticker file, date, side, fill price in venue quote units, label)
    ("ISP.BVME.ibkr", "2026-08-06", "BUY 545",      6.843,  "EUR (Milan, IBKR)"),
    ("IMB.LSE",       "2026-08-14", "BUY 26",       2629.0, "GBX (pence)"),
    ("EUAD.US",       "2026-08-14", "SELL 25.5427", 47.86,  "USD"),
    ("INDA.US",       "2026-08-14", "SELL 21",      49.775, "USD"),
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
WEIGHTS = {"ISP": 0.376, "RR.LSE": 0.162, "IMB.LSE": 0.158,
           "FFH.TO": 0.141, "SCCO.US": 0.099}
CASH_W = 0.064  # accrues at the 3M T-bill rate (ruling #1)

FX_FOR = {"ISP": ("EURUSD.FOREX", 1.0), "RR.LSE": ("GBPUSD.FOREX", 0.01),
          "IMB.LSE": ("GBPUSD.FOREX", 0.01), "FFH.TO": ("CADUSD.FOREX", 1.0),
          "SCCO.US": (None, 1.0)}  # scale 0.01 converts GBX pence -> GBP

# Per-venue dividend withholding (ruling #3, labeled policy inputs):
# Italy 26% (IBKR default absent filed treaty relief — per Jim), Canada 15%
# treaty rate, UK 0%, US-listed SCCO 0% withheld (taxable but not at source).
WITHHOLDING = {"ISP": 0.26, "RR.LSE": 0.0, "IMB.LSE": 0.0,
               "FFH.TO": 0.15, "SCCO.US": 0.0}
# Reconciled dividend values are in GBP for LSE names; closes are pence.
DIV_UNIT_SCALE = {"RR.LSE": 100.0, "IMB.LSE": 100.0}

def raw_close(name):
    """Raw (unadjusted) local close series per logical name. ISP = XETRA raw
    close before 2021-08-16 (labeled proxy) spliced with IBKR Milan close
    from 2021-08-16 (direct concatenation — same ISIN, same EUR price)."""
    if name == "ISP":
        milan = load_prices("ISP.BVME.ibkr")["close"]
        xetra = load_prices("IES.XETRA")["close"]
        return pd.concat([xetra[xetra.index < milan.index[0]], milan])
    return load_prices(name)["close"]

def split_factors(name, idx):
    """Cumulative split-adjustment factor per date (EODHD splits table;
    format 'new/old' at the effective date; dates BEFORE it scale by
    old/new). Only RR.LSE has an event (2020-10-28 rights-issue factor)."""
    fname = {"ISP": "IES.XETRA"}.get(name, name)
    path = os.path.join(DATA, "splits", f"{fname}.csv")
    fac = pd.Series(1.0, index=idx)
    if not os.path.exists(path):
        return fac
    sp = pd.read_csv(path)
    if sp.empty:
        return fac
    sp.columns = [c.strip().lower() for c in sp.columns]
    date_col = "date" if "date" in sp.columns else sp.columns[0]
    ratio_col = [c for c in sp.columns if c != date_col][0]
    for _, r in sp.iterrows():
        new, old = (float(x) for x in str(r[ratio_col]).split("/"))
        fac[fac.index < pd.Timestamp(r[date_col])] *= old / new
    return fac

def load_reconciled_divs(name):
    path = os.path.join(DATA, "dividends_reconciled", f"{name}.csv")
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"])
    return df

def tr_local(name, net=True):
    """Local-currency total-return index from raw closes + reconciled
    dividends (net of withholding unless net=False), split-adjusted.
    Ex-dates falling on non-trading days roll to the next trading day."""
    px_raw = raw_close(name)
    fac = split_factors(name, px_raw.index)
    px = px_raw * fac
    d = pd.Series(0.0, index=px.index)
    scale = DIV_UNIT_SCALE.get(name, 1.0)
    keep = 1.0 - (WITHHOLDING[name] if net else 0.0)
    for _, r in load_reconciled_divs(name).iterrows():
        ex, val = r["date"], float(r["value"])
        if ex < px.index[0] or ex > px.index[-1]:
            continue
        pos = px.index.searchsorted(ex)
        d.iloc[pos] += val * scale * keep * fac.iloc[pos]
    gross_ret = (px + d) / px.shift(1)
    gross_ret.iloc[0] = 1.0
    return gross_ret.cumprod() * px.iloc[0]

def cash_index(idx):
    """Cash leg: accrues at the 3M T-bill coupon-equivalent rate (ruling #1),
    previous available rate applied over the calendar days to the next
    trading date (point-in-time; no look-ahead)."""
    df = pd.read_csv(os.path.join(DATA, "rates", "UST_BILL_3M.csv"))
    df.columns = [c.strip().lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"])
    rate_cols = [c for c in df.columns if "coupon" in c] or \
                [c for c in df.columns if "rate" in c or "yield" in c or "close" in c]
    if not rate_cols:
        raise RuntimeError(f"no rate column found in UST_BILL_3M.csv: {list(df.columns)}")
    r = df.set_index("date")[rate_cols[0]].astype(float).sort_index()
    r = r.reindex(idx.union(r.index)).ffill().reindex(idx) / 100.0
    days = idx.to_series().diff().dt.days.fillna(0)
    daily = (1 + r.shift(1)) ** (days / 365.0)
    daily.iloc[0] = 1.0
    return daily.cumprod(), rate_cols[0]

def build_usd_series(net=True):
    """USD total-return per name. Calendar rule (Section 5.7, stated): union
    of the equity venues' trading dates; each local series and FX rate
    forward-filled over its own venue's holidays. No inner join."""
    px, fx = {}, {}
    for name in WEIGHTS:
        px[name] = tr_local(name, net=net)
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
    return pd.DataFrame(usd).dropna()

def firing_stats(nav, X):
    peak = nav.cummax()
    dd = nav / peak - 1
    breached = dd <= -X
    episodes = int((breached & ~breached.shift(fill_value=False)).sum())
    return episodes, int(breached.sum()), float(dd.min())

def quantify_gross_vs_net():
    """Ruling #3: quantify the withholding thumb-on-the-scale per name."""
    print("\nGross vs net-of-withholding total return (local currency, full"
          " series, annualized drag):")
    for name in WEIGHTS:
        g, n = tr_local(name, net=False), tr_local(name, net=True)
        yrs = (g.index[-1] - g.index[0]).days / 365.25
        cg = (g.iloc[-1] / g.iloc[0]) ** (1 / yrs) - 1
        cn = (n.iloc[-1] / n.iloc[0]) ** (1 / yrs) - 1
        print(f"  {name}: gross {cg:+.2%}/y  net {cn:+.2%}/y "
              f" drag {(cg-cn)*100:.2f}pp/y (withholding {WITHHOLDING[name]:.0%})")

def one_window(usd, cash_idx, start, label, X):
    u = usd[usd.index >= start]
    c = cash_idx.reindex(u.index)
    rel = u / u.iloc[0]
    nav = rel.mul(pd.Series(WEIGHTS)).sum(axis=1) + CASH_W * (c / c.iloc[0])
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

def backtest(X):
    print("\n== PART 3: SLEEVE HISTORY AND CAP FIRING (rev 2: net dividends,"
          " T-bill cash) ==")
    usd = build_usd_series(net=True)
    cash, rate_col = cash_index(usd.index)
    print("Raw inputs (Section 5.8) — USD net-total-return series coverage:")
    for name in usd.columns:
        s = usd[name]
        print(f"  {name}: {s.index[0].date()} -> {s.index[-1].date()}"
              f"  first={s.iloc[0]:.4f} last={s.iloc[-1]:.4f}  n={len(s)}")
    print(f"Cash leg: 3M T-bill accrual, column '{rate_col}',"
          f" cumulative x{cash.iloc[-1]:.4f} over the full window")
    print(f"Weights: {WEIGHTS} cash={CASH_W}")
    print("Construction: buy-and-hold, seeded at current weights on window"
          " start; no rebalancing, so no trading frictions inside the window"
          " (entry frictions scale NAV and cancel out of drawdown).")
    quantify_gross_vs_net()
    end = usd.index[-1]
    one_window(usd, cash, usd.index[0],
               "full window — ISP pre-2021 = XETRA proxy segment (labeled)", X)
    one_window(usd, cash, end - pd.DateOffset(years=5), "trailing 5y", X)
    one_window(usd, cash, end - pd.DateOffset(years=2), "trailing 2y", X)

if __name__ == "__main__":
    X = derive_cap()
    ok = validate_fills()
    if not ok and "--force" not in sys.argv:
        print("\nSTOP: fill validation failed — reconcile before any backtest"
              " (Section 5.9). Rerun with --force only to inspect.")
        sys.exit(1)
    backtest(X)
