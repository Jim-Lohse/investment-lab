"""Offline tests for the lead-lag statistics (stdlib implementations)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from signals import cftc_leadlag as L


class StatsTests(unittest.TestCase):
    def test_ranks_share_ties(self):
        self.assertEqual(L.ranks([10, 20, 20, 30]), [1.0, 2.5, 2.5, 4.0])

    def test_spearman_perfect_and_none(self):
        x = list(range(100))
        rho, t = L.spearman_nw(x, [v * 3 + 1 for v in x], lag=1)
        self.assertAlmostEqual(rho, 1.0, places=6)
        rho, _ = L.spearman_nw(x, [(v * 37) % 101 for v in x], lag=1)
        self.assertLess(abs(rho), 0.2)

    def test_ols_recovers_known_coefficients(self):
        xs = [[i % 7, (i * 3) % 11] for i in range(200)]
        ys = [1.0 + 2.0 * a - 0.5 * b + (0.01 if i % 2 else -0.01) for i, (a, b) in enumerate(xs)]
        b, t = L.ols_nw(xs, ys, lag=2)
        self.assertAlmostEqual(b[1], 2.0, places=2)
        self.assertAlmostEqual(b[2], -0.5, places=2)
        self.assertGreater(abs(t[1]), 100)

    def test_crowding_rank_uses_only_earlier_weeks(self):
        base = L.dt.date(2010, 1, 5)
        rows = [{"report_date": (base + L.dt.timedelta(weeks=i)).isoformat(),
                 "net": str(i), "open_interest": "1000", "net_change": "1"}
                for i in range(150)]
        full = L.build_signals(rows)
        cut = L.build_signals(rows[:120])
        self.assertEqual([r["crowd"] for r in cut], [r["crowd"] for r in full[:120]])
        self.assertEqual(full[-1]["crowd"], 100.0)  # a new high ranks above all earlier weeks


if __name__ == "__main__":
    unittest.main()
