"""Offline tests for the Treasury yield-curve parser."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from signals import treasury_yields as T

# Two days from the 2026 file (checked 2026-09-24), newest first as published.
CSV_2026 = ('Date,"1 Mo","1.5 Month","2 Mo","3 Mo","4 Mo","6 Mo","1 Yr","2 Yr","3 Yr","5 Yr",'
            '"7 Yr","10 Yr","20 Yr","30 Yr"\n'
            "09/03/2026,3.83,3.82,3.91,3.89,3.99,3.95,4.11,4.34,4.41,4.52,4.63,4.77,5.25,5.25\n"
            "08/14/2026,3.79,3.80,3.81,3.86,3.88,3.95,3.98,4.17,4.24,4.36,4.51,4.68,5.25,5.25\n")

# An older layout: fewer tenors, a missing 30-year (1990s-style gap).
CSV_1995 = ('Date,"1 Mo","3 Mo","6 Mo","1 Yr","2 Yr","3 Yr","5 Yr","7 Yr","10 Yr","20 Yr","30 Yr"\n'
            "01/03/1995,,5.72,6.29,7.18,7.66,7.78,7.83,7.88,7.88,8.06,\n")


class TreasuryParserTests(unittest.TestCase):
    def test_columns_by_name_and_gaps(self):
        rows = {r["date"]: r for r in T.parse_treasury_csv(CSV_2026)}
        d = rows["2026-09-03"]
        self.assertEqual((d["y3m"], d["y2y"], d["y10y"]), (3.89, 4.34, 4.77))
        self.assertAlmostEqual(d["gap_2s10s"], 0.43, places=6)
        self.assertAlmostEqual(d["gap_3m10y"], 0.88, places=6)
        self.assertEqual(rows["2026-08-14"]["y10y"], 4.68)

    def test_older_layout_and_missing_tenor(self):
        (r,) = T.parse_treasury_csv(CSV_1995)
        self.assertEqual((r["y2y"], r["y10y"]), (7.66, 7.88))
        self.assertIsNone(r["y30y"])
        self.assertAlmostEqual(r["gap_2s10s"], 0.22, places=6)

    def test_garbage_is_empty(self):
        self.assertEqual(T.parse_treasury_csv("<html>error</html>"), [])


if __name__ == "__main__":
    unittest.main()
