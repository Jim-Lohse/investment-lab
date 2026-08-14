"""Offline tests for the signals parsers and signal math.

Fixtures mirror the documented formats of each source (open-data CSV headers,
MOPS Big5 archive table shape, data.go.kr XML envelope). No network.

Run:  python -m unittest discover tests
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from signals import common, compute_signals, korea_customs, taiwan_mops

OPEN_CSV = """出表日期,資料年月,公司代號,公司名稱,產業別,營業收入-當月營收,營業收入-上月營收,營業收入-去年當月營收,營業收入-上月比較增減(%),營業收入-去年同月增減(%),累計營業收入-當月累計營收,累計營業收入-去年累計營收,累計營業收入-前期比較增減(%),備註
1150810,11507,2330,台積電,半導體業,320000000,290000000,256000000,10.34,25.00,2100000000,1600000000,31.25,-
1150810,11507,2049,上銀,電機機械,2100000,2000000,2100000,5.00,0.00,14000000,13500000,3.70,-
1150810,11507,1590,亞德客-KY,電機機械,2500000,2400000,2000000,4.17,25.00,17000000,15000000,13.33,-
"""

ARCHIVE_HTML = """
<html><body>
<table><tr><td>產業別：半導體業</td></tr></table>
<table>
<tr><th>公司代號</th><th>公司名稱</th><th>當月營收</th><th>上月營收</th><th>去年當月營收</th><th>上月比較增減(%)</th><th>去年同月增減(%)</th><th>當月累計營收</th><th>去年累計營收</th><th>前期比較增減(%)</th><th>備註</th></tr>
<tr><td>2330</td><td>台積電</td><td>280,000,000</td><td>270,000,000</td><td>210,000,000</td><td>3.70</td><td>33.33</td><td>1,780,000,000</td><td>1,344,000,000</td><td>32.44</td><td>-</td></tr>
<tr><td>合計</td><td></td><td>999</td><td>999</td><td>999</td><td>1</td><td>1</td><td>9</td><td>9</td><td>9</td><td></td></tr>
</table>
<table><tr><td>產業別：電機機械</td></tr></table>
<table>
<tr><td>2049</td><td>上銀</td><td>1,900,000</td><td>1,850,000</td><td>2,000,000</td><td>2.70</td><td>-5.00</td><td>11,900,000</td><td>11,500,000</td><td>3.48</td><td>-</td></tr>
</table>
</body></html>
"""

KOREA_MONTHLY_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<response><header><resultCode>00</resultCode><resultMsg>NORMAL SERVICE.</resultMsg></header>
<body><items>
<item><year>2026.06</year><hsCd>8542</hsCd><statKor>\xec\xa0\x84\xec\x9e\x90\xec\xa7\x91\xec\xa0\x81\xed\x9a\x8c\xeb\xa1\x9c</statKor><expDlr>12345678901</expDlr><impDlr>4567890123</impDlr><balPayments>7777788778</balPayments></item>
<item><year>\xec\xb4\x9d\xea\xb3\x84</year><hsCd></hsCd><expDlr>99</expDlr></item>
</items></body></response>
"""

KOREA_FLASH_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<response><header><resultCode>00</resultCode></header><body><items>
<item><priodTitle>2026.08.01 ~ 2026.08.10</priodTitle><korePrlstNm>\xeb\xb0\x98\xeb\x8f\x84\xec\xb2\xb4</korePrlstNm><expDlr>11000000</expDlr></item>
<item><priodTitle>2026.08.01 ~ 2026.08.10</priodTitle><korePrlstNm>\xec\xa0\x84\xec\xb2\xb4</korePrlstNm><expDlr>19800000</expDlr></item>
</items></body></response>
"""

KOREA_ERROR_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<response><header><resultCode>30</resultCode><resultMsg>SERVICE KEY IS NOT REGISTERED ERROR.</resultMsg></header></response>
"""


class TestCommon(unittest.TestCase):
    def test_roc_dates(self):
        self.assertEqual(common.roc_to_iso_month("115/07"), "2026-07")
        self.assertEqual(common.roc_to_iso_month("11507"), "2026-07")
        self.assertEqual(common.iso_to_roc("2026-07"), (115, 7))

    def test_parse_number(self):
        self.assertEqual(common.parse_number("1,234,567"), 1234567.0)
        self.assertEqual(common.parse_number("(5.2)"), -5.2)
        self.assertIsNone(common.parse_number("不適用"))
        self.assertIsNone(common.parse_number("-"))

    def test_month_range(self):
        self.assertEqual(common.month_range("2025-11", "2026-02"),
                         ["2025-11", "2025-12", "2026-01", "2026-02"])

    def test_append_dedup(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.csv"
            header = ["k", "v"]
            n1 = common.append_dedup_csv(path, header, [{"k": "a", "v": "1"}], ["k"])
            n2 = common.append_dedup_csv(
                path, header, [{"k": "a", "v": "9"}, {"k": "b", "v": "2"}], ["k"])
            self.assertEqual((n1, n2), (1, 1))
            rows = common.read_csv_dicts(path)
            self.assertEqual(rows[0]["v"], "1")  # first write wins (append-only)


class TestTaiwan(unittest.TestCase):
    def test_open_csv(self):
        month, rows = taiwan_mops.parse_open_csv(OPEN_CSV, "sii")
        self.assertEqual(month, "2026-07")
        self.assertEqual(len(rows), 3)
        tsmc = rows[0]
        self.assertEqual(tsmc[2], "2330")
        self.assertEqual(tsmc[5], "320000000")   # rev_month_twd_k
        self.assertEqual(tsmc[7], "256000000")   # year-ago month
        self.assertEqual(tsmc[9], "25")          # yoy_pct

    def test_archive_html(self):
        rows = taiwan_mops.parse_archive_html(ARCHIVE_HTML, "sii", "2026-06")
        self.assertEqual(len(rows), 2)  # totals row filtered out
        self.assertEqual(rows[0][2], "2330")
        self.assertEqual(rows[0][4], "半導體業")   # industry carried from label row
        self.assertEqual(rows[1][4], "電機機械")
        self.assertEqual(rows[1][5], "1900000")
        self.assertEqual(rows[1][9], "-5")        # negative yoy preserved


class TestKorea(unittest.TestCase):
    def test_monthly_xml(self):
        rows = korea_customs.parse_monthly_xml(KOREA_MONTHLY_XML, "2026-08-11")
        self.assertEqual(len(rows), 1)  # totals row skipped
        self.assertEqual(rows[0]["year_month"], "2026-06")
        self.assertEqual(rows[0]["hs_code"], "8542")
        self.assertEqual(rows[0]["export_usd"], "12345678901")

    def test_flash_xml(self):
        rows = korea_customs.parse_flash_xml(
            KOREA_FLASH_XML, "flash_exports_10day", "2026-08-11")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["item_name"], "반도체")
        self.assertEqual(rows[0]["value_usd_k"], "11000000")
        self.assertEqual(rows[0]["yyyymm"], "2026-08")
        self.assertEqual(rows[0]["period_type"], "D10")
        self.assertIn("priodTitle", rows[0]["extra_json"])  # nothing dropped

    def test_classify_period(self):
        cases = {
            "2026.08.01 ~ 2026.08.10": "D10",
            "2026.08.01~2026.08.20": "D20",
            "2026.07.01 ~ 2026.07.31": "FULL",
            "1일~10일": "D10",
            "2026.08": "",
        }
        for label, expected in cases.items():
            self.assertEqual(korea_customs.classify_period(label), expected, label)

    def test_flash_yoy_math(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            flash = Path(tmp) / "exports_flash.csv"
            common.write_csv(flash, korea_customs.FLASH_HEADER, [
                ["2025-08", "2025.08.01 ~ 2025.08.10", "D10", "flash_exports_10day",
                 "반도체", "10000000", "{}", "2025-08-11"],
                ["2026-08", "2026.08.01 ~ 2026.08.10", "D10", "flash_exports_10day",
                 "반도체", "11000000", "{}", "2026-08-11"],
            ])
            orig = compute_signals.KOREA_DIR
            compute_signals.KOREA_DIR = Path(tmp)
            try:
                out = compute_signals.korea_signals()
            finally:
                compute_signals.KOREA_DIR = orig
            latest = [r for r in out if r[0] == "2026-08"][0]
            self.assertEqual(latest[2], "exp:반도체")
            self.assertEqual(latest[5], "10.00")  # 11.0/10.0 - 1

    def test_api_error_raises(self):
        with self.assertRaises(RuntimeError):
            korea_customs.parse_monthly_xml(KOREA_ERROR_XML, "2026-08-11")


class TestSignals(unittest.TestCase):
    def test_taiwan_group_math(self):
        month, rows = taiwan_mops.parse_open_csv(OPEN_CSV, "sii")
        months = {month: {r[2]: dict(zip(taiwan_mops.HEADER, r)) for r in rows}}
        out = compute_signals.taiwan_signals(months)
        by_group = {r[1]: r for r in out}
        # robotics_motion = 2049 + 1590: (2.1+2.5)/(2.1+2.0)-1 = 12.20%
        robo = by_group["robotics_motion"]
        self.assertEqual(robo[2], 2)
        self.assertEqual(robo[5], "12.20")
        self.assertEqual(robo[7], "50.0")  # one of two members growing
        self.assertIn("all_listed", by_group)


if __name__ == "__main__":
    unittest.main()
