"""Offline tests for the macro dashboard's calculations."""

from __future__ import annotations

import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from signals import macro_dashboard as M


def days(n, start=dt.date(2020, 1, 6), f=lambda i: float(i)):
    return [((start + dt.timedelta(days=i)).isoformat(), f(i)) for i in range(n)]


class DashboardMathTests(unittest.TestCase):
    def test_weekly_takes_last_reading_on_or_before_friday(self):
        # Mon 2020-01-06 .. Sun 2020-01-12: Friday is the 10th; Sat/Sun roll to the next Friday.
        wk = M.weekly(days(7))
        self.assertEqual(wk[0], ("2020-01-10", 4.0))
        self.assertEqual(wk[1], ("2020-01-17", 6.0))

    def test_describe_changes_and_rank(self):
        s = days(7 * 60, f=lambda i: 100.0 + i)          # steadily rising
        it = M.describe("x", s, "USD", "pct")
        self.assertEqual(it["value"], 100.0 + 7 * 60 - 1)
        self.assertEqual(it["rank_pct"], 100)            # a new high beats every earlier week
        self.assertGreater(it["changes"]["4w"], 0)
        self.assertLessEqual(len(it["chart"]), M.CHART_WEEKS)

    def test_move_rank_flags_a_jump(self):
        wk = [(f"w{i}", float(i % 2)) for i in range(80)] + [("last", 50.0)]
        self.assertEqual(M.move_rank(wk, "abs"), 100)

    def test_move_rank_needs_a_year_of_moves(self):
        self.assertIsNone(M.move_rank([(f"w{i}", float(i)) for i in range(20)], "abs"))

    def test_sign_streak(self):
        s = [("2024-01-01", -0.5), ("2024-06-01", -0.1), ("2024-09-01", 0.2), ("2025-01-01", 0.4)]
        self.assertEqual(M.sign_streak(s), {"positive": True, "since": "2024-09-01"})

    def test_render_embeds_data_safely(self):
        html = M.render({"generated": "2026-09-24", "panels": [], "closing": "</script>x"})
        self.assertNotIn("/*__DASHBOARD_DATA__*/null", html)
        self.assertNotIn("</script>x", html)


if __name__ == "__main__":
    unittest.main()
