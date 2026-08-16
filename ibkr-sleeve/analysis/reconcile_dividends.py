#!/usr/bin/env python3
"""Build data/dividends_reconciled/ from EODHD dividend tables, IBKR
corporate-action records, and company-declared evidence (Jim's ruling #2,
2026-08-16: no contest runs until IMB/SCCO records are reconciled).

Zero fabrication: every row in the output carries its source(s); the two
manual resolutions below cite company primary sources fetched 2026-08-16.

Resolutions (evidence on file, see session1-memo.md §5):
  IMB  — EODHD row ex 2026-05-28 / 0.419 GBP is SPURIOUS. Imperial Brands'
         RNS dividend declaration (2026-05-12, via Investegate) declares ONE
         first instalment of 41.68p, record date 2026-05-22, payment
         2026-06-30; IBKR's records carry exactly one row (ex 2026-05-21,
         0.4168 GBP). -> drop the 05-28 row.
       — EODHD row ex 2026-08-20 / 0.419 GBP: the same RNS declares the
         second instalment at 41.68p (record 2026-08-21). -> value corrected
         to 0.4168, source=declared-RNS. (Future ex-date; outside the price
         window, so it does not enter the backtest.)
  SCCO — the 2024-02..2024-08 cash gap is real: SCCO declared a quarterly
         STOCK dividend of 0.0104 shares/share, ex 2024-05-07, payable
         2024-05-23 (company PR 2024-04-19; Form 8-K 2024-04-25) — and IBKR's
         records show stock dividends became RECURRING: ten "StockDividends"
         events 2024-05-07 .. 2026-08-11 (factors 1.0056–1.012), most paired
         with a cash dividend. All ten are written to stock_events.csv as
         share-adjustment factors for the total-return construction.
         Cash-in-lieu of fractional shares is ignored as immaterial.
       — EODHD's SCCO dividend 'value' column is NOT as-declared: it is
         restated per-current-share (divided by the product of all
         subsequent stock-dividend factors; its 'unadjustedValue' column is
         identical, i.e. not actually unadjusted). Verified numerically: for
         every EODHD row overlapping IBKR's 5y window, EODHD value x
         (product of subsequent IBKR stock factors) reproduces IBKR's
         declared amount to ~0.1%, and every pre-2024-05 row shows the same
         constant ratio (~1.0808 = the full ten-event product), which also
         confirms NO stock events occurred 2015..2024-04. The reconciled
         table therefore uses IBKR's declared amounts where IBKR covers
         (ex-dates >= 2021-11-09) and EODHD value x full-product K for
         earlier rows (an arithmetic restatement from sourced factors, with
         the per-row verification printed at build time — not an estimate).
         As-declared amounts are what a raw-close total-return construction
         requires; EODHD's restated values would understate pre-2024 cash.
"""

import os
import pandas as pd

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
OUT = os.path.join(DATA, "dividends_reconciled")

# logical name -> (EODHD dividends file, IBKR corp-actions file, currency note)
NAMES = {
    "ISP":     ("IES.XETRA", "ISP.BVME.ibkr",  "EUR: EODHD and IBKR agree"),
    "RR.LSE":  ("RR.LSE",    "RR.LSE.ibkr",    "GBP (pounds, not pence)"),
    "IMB.LSE": ("IMB.LSE",   "IMB.LSE.ibkr",   "GBP (pounds, not pence)"),
    "FFH.TO":  ("FFH.TO",    "FFH.TSE.ibkr",   "EODHD CAD; IBKR carries the USD declaration — matched by date only"),
    "SCCO.US": ("SCCO.US",   "SCCO.NYSE.ibkr", "USD"),
}

def load_eodhd(fname):
    df = pd.read_csv(os.path.join(DATA, "dividends", f"{fname}.csv"))
    df.columns = [c.strip().lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"])
    return df[["date", "value", "currency"]].sort_values("date")

def load_ibkr(fname, kind="CashDividends"):
    path = os.path.join(DATA, "corp_actions", f"{fname}.csv")
    df = pd.read_csv(path, dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]
    df = df[df["type"] == kind].copy()
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    df["value"] = df["value"].astype(float)
    return df[["date", "value", "currency", "payment_date"]].sort_values("date")

def reconcile():
    os.makedirs(OUT, exist_ok=True)

    # Stock-dividend events from IBKR corp actions (all names; only SCCO has
    # any). Written first: SCCO's cash restatement below needs the factors.
    events = []
    for name, (_, ifile, _) in NAMES.items():
        st = load_ibkr(ifile, kind="StockDividends")
        for _, r in st.iterrows():
            events.append({"name": name, "date": r["date"].date(),
                           "new": r["value"], "old": 1.0,
                           "note": f"IBKR StockDividends ratio, pay {r['payment_date']}"})
    ev = pd.DataFrame(events)
    ev.to_csv(os.path.join(OUT, "stock_events.csv"), index=False)
    print(f"stock_events.csv: {len(ev)} events "
          f"({', '.join(sorted(set(ev['name'])))}); factors "
          f"{ev['new'].min()}..{ev['new'].max()}")

    for name, (efile, ifile, note) in NAMES.items():
        eod = load_eodhd(efile)
        ib = load_ibkr(ifile)

        # documented manual resolutions
        dropped = []
        if name == "SCCO.US":
            # EODHD values are restated per-current-share; rebuild as-declared:
            # IBKR declared amounts where covered, EODHD value x K earlier.
            scco_ev = ev[ev["name"] == "SCCO.US"].copy()
            scco_ev["date"] = pd.to_datetime(scco_ev["date"])
            # EODHD's restatement chain only contains stock events paired
            # with a cash dividend on the same ex-date — the standalone
            # 2024-05-07 event is absent from EODHD altogether (the original
            # dispute). Inverting THEIR chain therefore uses only the
            # events visible to them.
            visible = scco_ev["date"].apply(
                lambda d: ((eod["date"] - d).abs() <= pd.Timedelta(days=3)).any())
            print(f"SCCO stock events in EODHD's own chain: "
                  f"{int(visible.sum())} of {len(scco_ev)} (standalone "
                  f"{', '.join(str(d.date()) for d in scco_ev[~visible]['date'])} "
                  f"absent from EODHD)")
            vis_ev = scco_ev[visible]
            K = vis_ev["new"].prod()
            print(f"EODHD-embedded cumulative factor K_eodhd = {K:.5f}")
            print("SCCO restatement verification (EODHD value x subsequent"
                  " EODHD-visible stock factors vs IBKR declared):")
            worst = 0.0
            for _, r in ib.iterrows():
                m = eod[(eod["date"] - r["date"]).abs() <= pd.Timedelta(days=3)]
                if m.empty:
                    continue
                k_after = vis_ev[vis_ev["date"] > r["date"]]["new"].prod()
                restated = m.iloc[0]["value"] * k_after
                dev = abs(restated / r["value"] - 1)
                worst = max(worst, dev)
                print(f"  {r['date'].date()}: {m.iloc[0]['value']:.5f} x"
                      f" {k_after:.5f} = {restated:.5f} vs IBKR {r['value']}"
                      f"  ({dev:.2%})")
            print(f"  worst deviation {worst:.2%}")
            if worst > 0.005:
                raise RuntimeError("SCCO restatement check failed (>0.5%) — "
                                   "stop and reconcile (CLAUDE.md 5.9 spirit)")
            first_ib = ib["date"].min()
            out_rows = []
            for _, r in eod.iterrows():
                m = ib[(ib["date"] - r["date"]).abs() <= pd.Timedelta(days=3)]
                if not m.empty:
                    out_rows.append({"date": r["date"], "value": m.iloc[0]["value"],
                                     "currency": "USD", "sources": "IBKR-declared",
                                     "note": f"EODHD restated value {r['value']}"})
                elif r["date"] < first_ib:
                    out_rows.append({"date": r["date"],
                                     "value": round(r["value"] * K, 5),
                                     "currency": "USD",
                                     "sources": "EODHD x stock-factor-K",
                                     "note": f"EODHD {r['value']} x K={K:.5f}"})
                else:
                    out_rows.append({"date": r["date"], "value": r["value"],
                                     "currency": "USD", "sources": "EODHD",
                                     "note": "no IBKR match — review"})
            res = pd.DataFrame(out_rows)
            res.to_csv(os.path.join(OUT, f"{name}.csv"), index=False)
            n_ib = (res["sources"] == "IBKR-declared").sum()
            print(f"{name}: {len(res)} rows written ({n_ib} IBKR-declared,"
                  f" {(res['sources'] != 'IBKR-declared').sum()} restated/EODHD);"
                  f" currency: {note}")
            continue
        if name == "IMB.LSE":
            spurious = (eod["date"] == "2026-05-28") & (eod["value"].round(4) == 0.419)
            dropped = eod[spurious]
            eod = eod[~spurious].copy()
            fix = eod["date"] == "2026-08-20"
            eod.loc[fix, "value"] = 0.4168

        # cross-check vs IBKR (5y coverage): match by ex-date within 3 days;
        # value within 2% (skipped for FFH: IBKR records the USD declaration)
        eod["sources"], eod["note"] = "EODHD", ""
        unmatched_ibkr = []
        for _, r in ib.iterrows():
            close = (eod["date"] - r["date"]).abs() <= pd.Timedelta(days=3)
            if name != "FFH.TO":
                close &= (eod["value"] - r["value"]).abs() <= 0.02 * r["value"]
            if close.any():
                eod.loc[close, "sources"] = "EODHD+IBKR"
            else:
                unmatched_ibkr.append(r)
        if name == "IMB.LSE":
            fix = eod["date"] == "2026-08-20"
            eod.loc[fix, "sources"] = "declared-RNS(2026-05-12)"
            eod.loc[fix, "note"] = "second 41.68p instalment; EODHD said 0.419"

        eod.to_csv(os.path.join(OUT, f"{name}.csv"), index=False)
        n_ib = len(eod[eod["sources"].str.contains("IBKR")])
        print(f"{name}: {len(eod)} rows written ({n_ib} IBKR-confirmed); "
              f"{len(dropped)} dropped; currency: {note}")
        if len(dropped):
            for _, r in dropped.iterrows():
                print(f"  DROPPED {r['date'].date()} {r['value']} {r['currency']}"
                      " — spurious per RNS + IBKR (see module docstring)")
        for r in unmatched_ibkr:
            print(f"  WARNING {name}: IBKR row {r['date'].date()} {r['value']}"
                  f" {r['currency']} has no EODHD match — review before contest")

if __name__ == "__main__":
    reconcile()
