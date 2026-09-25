"""Offline tests for the positioning collector: feed parsing, tagging, weekly
counts, loudness, the calendar rules and holdings matching."""

from __future__ import annotations

import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from signals import positioning as P

CFG = P.load_config()

FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>x</title>
<item><title>HEDGE FLOW-Hedge funds cut US stock exposure at fastest pace since 2023 - Reuters</title>
<link>https://news.google.com/rss/articles/abc</link>
<pubDate>Tue, 22 Sep 2026 02:30:00 GMT</pubDate>
<source url="https://www.reuters.com">Reuters</source></item>
<item><title>Hedge funds pile back into megacap tech, Goldman prime brokerage data show - MarketWatch</title>
<link>https://news.google.com/rss/articles/def</link>
<pubDate>Wed, 23 Sep 2026 14:00:00 GMT</pubDate>
<source url="https://www.marketwatch.com">MarketWatch</source></item>
</channel></rss>"""


class FeedTests(unittest.TestCase):
    def test_parse_strips_outlet_and_converts_to_eastern(self):
        items = P.parse_feed(FEED)
        self.assertEqual(items[0]["title"],
                         "HEDGE FLOW-Hedge funds cut US stock exposure at fastest pace since 2023")
        self.assertEqual(items[0]["outlet"], "Reuters")
        # 02:30 GMT Tuesday is Monday evening in New York.
        self.assertEqual(items[0]["published_et"], "2026-09-21")

    def test_story_id_ignores_punctuation(self):
        self.assertEqual(P.story_id("Hedge funds cut tech!"), P.story_id("hedge funds  cut tech"))

    def test_tags(self):
        a, b = P.parse_feed(FEED)
        ta, tb = P.tag(a["title"], CFG["tags"]), P.tag(b["title"], CFG["tags"])
        self.assertEqual(ta["direction"], "selling")
        self.assertEqual(ta["extreme"], "yes")
        self.assertEqual(tb["banks"], "Goldman Sachs")
        self.assertEqual(tb["direction"], "buying")
        self.assertIn("tech", tb["topics"])

    def test_whole_word_matching(self):
        # "cut" must not match inside "execute"; "AI" must not match inside "said".
        t = P.tag("Fund said it will execute plan", CFG["tags"])
        self.assertEqual(t["direction"], "")
        self.assertNotIn("tech", t["topics"])

    def test_config_keeps_the_six_proven_searches_verbatim(self):
        qs = {q["id"]: q["q"] for q in CFG["queries"]}
        self.assertEqual(qs["hedge_flow"], 'site:reuters.com "HEDGE FLOW"')
        self.assertEqual(qs["pb_data"],
                         '"prime brokerage data" OR "prime brokerage data show" hedge funds')
        self.assertEqual(len(qs), 6)


def row(sid, qid, day):
    return {"story_id": sid, "query_id": qid, "published_et": day}


class WeeklyTests(unittest.TestCase):
    def test_story_counted_once_in_total_and_empty_weeks_are_zero(self):
        rows = [row("a", "pb_data", "2026-09-01"), row("a", "mspb", "2026-09-02"),
                row("b", "mspb", "2026-09-17")]
        w = P.weekly_counts(rows, ["pb_data", "mspb"])
        self.assertEqual([x["week_ending"] for x in w], ["2026-09-06", "2026-09-13", "2026-09-20"])
        self.assertEqual(w[0]["total"], 1)
        self.assertEqual(w[0]["mspb"], 1)
        self.assertEqual(w[1]["total"], 0)

    def test_loudness_needs_history_then_bands(self):
        few = [{"total": 3}] * 3
        self.assertIn("building a baseline", P.loudness(few, CFG)["label"])
        weeks = [{"total": 4}] * 12 + [{"total": 12}]
        out = P.loudness(weeks, CFG)
        self.assertEqual(out["ratio"], 3.0)
        self.assertEqual(out["label"], "much busier than usual")
        self.assertEqual(P.loudness([{"total": 4}] * 13, CFG)["label"], "about normal")


class CalendarTests(unittest.TestCase):
    def test_holidays_2026(self):
        h = P.nyse_holidays(2026)
        self.assertIn(dt.date(2026, 4, 3), h)    # Good Friday
        self.assertIn(dt.date(2026, 7, 3), h)    # July 4 is a Saturday
        self.assertIn(dt.date(2026, 11, 26), h)  # Thanksgiving
        self.assertNotIn(dt.date(2027, 12, 31), P.nyse_holidays(2028))  # Sat New Year: no Friday close

    def test_13f_deadline_rolls_past_weekend(self):
        ev = P.calendar_events(dt.date(2026, 9, 25), CFG)
        f = [e for e in ev if e["kind"] == "13f"]
        self.assertEqual(f[0]["start"], "2026-11-16")  # Nov 14 2026 is a Saturday

    def test_expiry_and_month_end_window(self):
        self.assertEqual(P.quarterly_expiry(2026, 12), dt.date(2026, 12, 18))
        self.assertEqual(P.last_trading_days(2026, 9, 5)[0], dt.date(2026, 9, 24))
        # Good Friday 2027 falls on March 26: not an expiry day here, but the rule holds.
        self.assertEqual(P.quarterly_expiry(2027, 3), dt.date(2027, 3, 19))

    def test_trend_monitor_is_labelled_an_estimate(self):
        ev = [e for e in P.calendar_events(dt.date(2026, 9, 25), CFG) if e["kind"] == "trend_monitor"]
        self.assertTrue(ev[0]["label"].startswith("Estimated"))
        self.assertEqual((ev[0]["start"], ev[0]["end"]), ("2026-11-19", "2026-11-26"))


class MatchTests(unittest.TestCase):
    def test_alias_and_short_symbol(self):
        rows = [{"title": "Foxconn shares hit as hedge funds sell Asia"},
                {"title": "Hedge funds ON the move"}]
        h = [{"name": "Hon Hai", "aliases": ["Foxconn"], "us_symbol": ""},
             {"name": "Onsemi", "aliases": [], "us_symbol": "ON"}]
        m = P.match_holdings(rows, h)
        self.assertEqual([(r["title"][:7], x["name"]) for r, x in m], [("Foxconn", "Hon Hai")])


if __name__ == "__main__":
    unittest.main()
