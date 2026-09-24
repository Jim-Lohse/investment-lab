"""Offline tests for the fund price and GLD holdings parsers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from signals import etf_prices

# Two trading days of a Yahoo v8 chart payload (timestamps at the 09:30 ET open).
YAHOO = {"chart": {"result": [{
    "meta": {"gmtoffset": -14400},
    "timestamp": [1789392600, 1789479000, 1789565400],
    "indicators": {"quote": [{"close": [761.69, None, 767.81]}],
                   "adjclose": [{"adjclose": [760.5, None, 767.81]}]}}]}}

STOOQ = "Date,Open,High,Low,Close,Volume\n2026-09-14,759,763.57,749.6,761.69,1\n2026-09-15,,,,,\n"

GLD = """SPDR Gold Trust
Historical data
Date,GLD Close,LBMA Gold Price,NAV per GLD in Gold,NAV/share at 10.30 a.m. NYT,Indicative Price of GLD at 4.15 p.m. NYT,Mid point of bid/ask spread at 4.15 p.m. NYT#,Premium/Discount of GLD mid point v Indicative Value of GLD at 4.15 p.m. NYT,Daily Share Volume,Total Net Asset Value Ounces in the Trust as at 4.15 p.m. NYT,Total Net Asset Value Tonnes in the Trust as at 4.15 p.m. NYT,Total Net Asset Value in the Trust
14-Sep-2026,361.2,3900,0.0926,361.1,361.2,361.2,0.00%,1000,"31,000,000.5",964.21,"1,000"
15-Sep-2026, HOLIDAY,,,,,,,,,,
16-Sep-2026,362.0,3910,0.0926,361.9,362.0,362.0,0.00%,1000,"31,100,000.0",967.32,"1,000"
"""


class EtfParserTests(unittest.TestCase):
    def test_yahoo_uses_local_dates_and_drops_missing_days(self):
        rows = etf_prices.parse_yahoo_chart(YAHOO, "SPY")
        self.assertEqual([r["date"] for r in rows], ["2026-09-14", "2026-09-16"])
        self.assertEqual((rows[0]["close"], rows[0]["adj_close"]), ("761.69", "760.50"))

    def test_yahoo_bad_payload_is_empty_not_an_error(self):
        self.assertEqual(etf_prices.parse_yahoo_chart({"chart": {"result": None}}, "SPY"), [])

    def test_stooq(self):
        rows = etf_prices.parse_stooq_csv(STOOQ, "SPY")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["adj_close"], "761.69")

    def test_gld_archive_finds_columns_by_name_and_skips_holidays(self):
        rows = etf_prices.parse_gld_archive(GLD)
        self.assertEqual([r["date"] for r in rows], ["2026-09-14", "2026-09-16"])
        self.assertEqual(rows[1]["tonnes"], "967.32")
        self.assertEqual(rows[0]["ounces"], "31000000.50")


if __name__ == "__main__":
    unittest.main()
