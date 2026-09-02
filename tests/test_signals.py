"""Offline tests for the signals parsers and signal math.

Fixtures mirror the documented formats of each source (open-data CSV headers,
MOPS Big5 archive table shape, data.go.kr XML envelope, MOF hodoxml press
release, MOF 推移 CSV, e-Stat 統計品別表 CSV and listing pages). No network.

Run:  python -m unittest discover tests
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import datetime as dt

from signals import (common, compute_signals, japan_customs, korea_customs,
                     korea_tradedata, taiwan_mops)

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


TRADEDATA_HTML = """
<html><body>
<table>
<thead><tr><th rowspan="2">Sort</th><th colspan="2">Previous month(Jan.~Jul.)</th>
<th colspan="2">Current month(Aug.1~Aug.10)</th>
<th colspan="2">Annual Record(Jan.1~Aug.10)</th></tr>
<tr><th>Cumulative Total</th><th>Year-on-year Rate</th><th>Total</th>
<th>Year-on-year Rate</th><th>Cumulative Total</th><th>Year-on-year Rate</th></tr></thead>
<tbody>
<tr><td>Export</td><td>493,463</td><td>44.9</td><td>18,653</td><td>15.3</td><td>512,116</td><td>43.6</td></tr>
<tr><td>Import</td><td>358,391</td><td>16.6</td><td>15,046</td><td>△2.1</td><td>373,437</td><td>15.7</td></tr>
</tbody></table>
<table><tr><td>Export</td><td>18,653</td><td>15.3</td></tr></table>
</body></html>
"""


class TestTradedata(unittest.TestCase):
    RETRIEVED = dt.date(2026, 8, 14)

    def test_parse_window(self):
        self.assertEqual(korea_tradedata.parse_window("Aug.1~Aug.10", self.RETRIEVED),
                         ("2026-08", "D10"))
        self.assertEqual(korea_tradedata.parse_window("Jun.1 ~ Jun.30", self.RETRIEVED),
                         ("2026-06", "FULL"))
        self.assertEqual(korea_tradedata.parse_window("Aug.1~Aug.20", self.RETRIEVED),
                         ("2026-08", "D20"))
        # December window read in early January belongs to the prior year.
        self.assertEqual(korea_tradedata.parse_window("Dec.1~Dec.31", dt.date(2027, 1, 2)),
                         ("2026-12", "FULL"))

    def test_parse_chart_breakdown(self):
        payload = {"items": [
            # Month total row (lwprId, no uprId); full month not yet published.
            {"curTitle": "2026년 08월", "lwprId": "202608",
             "itemUsdAmt1": "21285723", "itemUsdAmt2": "55206635",
             "itemUsdAmt3": "0"},
            # Breakdown rows carry their own names.
            {"uprId": "202608", "curTitle": "반도체",
             "itemUsdAmt1": "8000000", "itemUsdAmt2": "20000000",
             "itemUsdAmt3": "36000000"},
            {"uprId": "202608", "curTitle": "승용차",
             "itemUsdAmt1": "1,500,000", "itemUsdAmt2": "", "itemUsdAmt3": ""},
        ]}
        rows = korea_tradedata.parse_chart_breakdown(
            payload, "item", "E", "2026-09-01")
        semis = [r for r in rows if r["name"] == "반도체"]
        self.assertEqual(len(semis), 3)  # D10, D20, FULL
        d10 = [r for r in semis if r["period_type"] == "D10"][0]
        self.assertEqual((d10["yyyymm"], d10["value_usd_k"], d10["dimension"]),
                         ("2026-08", "8000000", "item"))
        totals = [r for r in rows if r["dimension"] == "total"]
        self.assertEqual(len(totals), 2)  # zero FULL window skipped
        self.assertEqual(totals[0]["name"], "TOTAL")
        # Comma-formatted values parse; empty windows are skipped.
        cars = [r for r in rows if r["name"] == "승용차"]
        self.assertEqual(len(cars), 1)
        self.assertEqual(cars[0]["value_usd_k"], "1500000")

    def test_parse_dashboard(self):
        rows = korea_tradedata.parse_dashboard(TRADEDATA_HTML, self.RETRIEVED)
        self.assertEqual(len(rows), 2)  # 3-cell mobile duplicate table ignored
        exp = rows[0]
        self.assertEqual((exp["metric"], exp["yyyymm"], exp["period_type"]),
                         ("Export", "2026-08", "D10"))
        self.assertEqual(exp["value_usd_m"], "18653")
        self.assertEqual(exp["yoy_pct"], "15.30")
        imp = rows[1]
        self.assertEqual(imp["yoy_pct"], "-2.10")  # △ notation -> negative


# Real shapes captured from customs.go.jp / e-Stat on 2026-09-02 (trimmed).
JAPAN_PRESS_10DAY_XML = b"""<?xml version="1.0" encoding="UTF-8" standalone="no"?><?xml-stylesheet href="d1101e.xsl" type="text/xsl"?><hodoxml><sogakutsuki name="pg1"><kohyoymd>August 28, 2026</kohyoymd><title>Value of Exports and Imports August 2026 (First 10 days Provisional)</title><taishoymtonen>August 2026</taishoymtonen><taishoymzennen>August 2025</taishoymzennen><export><sogakutonen>3,678,584</sogakutonen><sogakuzennen>3,185,248</sogakuzennen><nobiritsu>15.5</nobiritsu></export><import><sogakutonen>3,461,278</sogakutonen><sogakuzennen>2,750,735</sogakuzennen><nobiritsu>25.8</nobiritsu></import><sashihiki><sogakutonen>217,306</sogakutonen><sogakuzennen>434,513</sogakuzennen><nobiritsu>-50.0</nobiritsu></sashihiki><chushaku>1</chushaku><page>(1)</page></sogakutsuki><pdf href="2026081e.pdf"/></hodoxml>"""

JAPAN_PRESS_MONTHLY_XML = b"""<?xml version="1.0" encoding="UTF-8" standalone="no"?><hodoxml>
<sogakutsuki name="pg1"><title>Value of Exports and Imports July 2026 (Provisional)</title><taishoymtonen>July 2026</taishoymtonen><export><sogakutonen>11,511,798</sogakutonen><sogakuzennen>9,344,799</sogakuzennen><nobiritsu>23.2</nobiritsu></export><import><sogakutonen>12,146,298</sogakutonen><sogakuzennen>9,501,083</sogakuzennen><nobiritsu>27.8</nobiritsu></import><sashihiki><sogakutonen>\xe2\x96\xb3634,500</sogakutonen><sogakuzennen>\xe2\x96\xb3156,284</sogakuzennen><nobiritsu>306.0</nobiritsu></sashihiki></sogakutsuki>
<chiikikunisogaku name="pg2"><title>Value of Exports and Imports by Area(Country)</title>
<chiikikunisogakuinfo><chiikikunikbn>0</chiikikunikbn><chiikikuni>Grand Total</chiikikuni><exportkagakue>11,511,798</exportkagakue><exportnobiritsu>23.2</exportnobiritsu><importkagakue>12,146,298</importkagakue><importnobiritsu>27.8</importnobiritsu><sashihikikagakue>-634,500</sashihikikagakue><sashihikinobiritsu>306.0</sashihikinobiritsu></chiikikunisogakuinfo>
<chiikikunisogakuinfo><chiikikunikbn>2</chiikikunikbn><chiikikuni>TAIWAN</chiikikuni><exportkagakue>929,521</exportkagakue><exportnobiritsu>46.4</exportnobiritsu><importkagakue>630,016</importkagakue><importnobiritsu>49.1</importnobiritsu><sashihikikagakue>299,505</sashihikikagakue><sashihikinobiritsu>41.1</sashihikinobiritsu></chiikikunisogakuinfo>
</chiikikunisogaku>
<shuyochiikikunihin name="pg3"><title>Exports by Principal Commodity(WORLD)</title><taishokikan>July 2026</taishokikan>
<shuyochiikikunihininfo><shuyoshohin>Grand Total</shuyoshohin><shuyoshohinbunrui>0</shuyoshohinbunrui><tani>   </tani><suryo /><suryonobiritsu /><kagaku>11,511,798</kagaku><koseihi>100.0</koseihi><kagakunobiritsu>23.2</kagakunobiritsu><zogenkiyodo>23.2</zogenkiyodo></shuyochiikikunihininfo>
<shuyochiikikunihininfo><shuyoshohin>SEMICON MACHINERY ETC</shuyoshohin><shuyoshohinbunrui>2</shuyoshohinbunrui><tani>MT</tani><suryo>15,586</suryo><suryonobiritsu>36.4</suryonobiritsu><kagaku>494,437</kagaku><koseihi>4.3</koseihi><kagakunobiritsu>40.9</kagakunobiritsu><zogenkiyodo>1.5</zogenkiyodo></shuyochiikikunihininfo>
<shuyochiikikunihininfo><shuyoshohin>SHIPS</shuyoshohin><shuyoshohinbunrui>2</shuyoshohinbunrui><tani>GT</tani><suryo>-</suryo><suryonobiritsu>ZENGEN</suryonobiritsu><kagaku>-</kagaku><koseihi>0.0</koseihi><kagakunobiritsu>ZENGEN</kagakunobiritsu><zogenkiyodo>-0.6</zogenkiyodo></shuyochiikikunihininfo>
</shuyochiikikunihin>
<shuyochiikikunihin name="pg8"><title>Exports by Principal Commodity by Area(Country)(CHINA)</title>
<shuyochiikikunihininfo><shuyoshohin>SEMICON MACHINERY ETC</shuyoshohin><shuyoshohinbunrui>2</shuyoshohinbunrui><tani>MT</tani><suryo>6,162</suryo><suryonobiritsu>-0.4</suryonobiritsu><kagaku>157,063</kagaku><koseihi>8.6</koseihi><kagakunobiritsu>-10.2</kagakunobiritsu><zogenkiyodo>-1.2</zogenkiyodo></shuyochiikikunihininfo>
</shuyochiikikunihin>
<shuyochiikikunihin name="pg4"><title>Imports by Principal Commodity(WORLD)</title>
<shuyochiikikunihininfo><shuyoshohin>SEMICONDUCTORS ETC</shuyoshohin><shuyoshohinbunrui>2</shuyoshohinbunrui><tani></tani><suryo/><suryonobiritsu/><kagaku>554,095</kagaku><koseihi>4.9</koseihi><kagakunobiritsu>49.2</kagakunobiritsu><zogenkiyodo>2.0</zogenkiyodo></shuyochiikikunihininfo>
</shuyochiikikunihin>
</hodoxml>"""

JAPAN_TS_COMMODITY_CSV = """《世界》  【月別】  （輸出）,,,,,,,,,
WORLD Monthly Data  (Export),,,,,,,,,
報道発表品目名,総額,１．食料品,,,,,,半導体等製造装置,
概況品名,,,,食料品及び動物,,飲料及びたばこ,,半導体等製造装置,
概況品コード,'0'～'9','0'+'1',,'0',,'1',,'70131',
,金額,数量,金額,数量,金額,数量,金額,数量,金額
Years/Months,(千円),(単位),(千円),(単位),(千円),(単位),(千円),(単位：KG),(千円)
2025/07,9345000000 ,-,14091115 ,-,13192617 ,-,898498 ,11424000 ,350900000 
2026/07,11509373578 ,-,15860521 ,-,14816029 ,-,1044492 ,15561810 ,493949821 
2026/08,-,-,-,-,-,-,-,-,-
"""

JAPAN_TS_TOTAL_CSV = """《世界》  【月別】　（単位：千円） ,,
WORLD  Monthly Data  (a thousand yen) ,,
Years/Months,Exp-Total,Imp-Total
,,
2026/07,11509373578 ,12146000000 
2026/08,0 ,0 
"""

JAPAN_ESTAT_CSV = """Exp or Imp,Year,HS,Unit1,Unit2,Quantity1-Year,Quantity2-Year,Value-Year,Quantity1-Jan,Quantity2-Jan,Value-Jan,Quantity1-Feb,Quantity2-Feb,Value-Feb,Quantity1-Mar,Quantity2-Mar,Value-Mar
1,2026,'848610000',  ,KG,0,300,9000,0,100,4000,0,200,5000,0,0,0
1,2026,'854142000',  ,NO,0,30,900,0,10,400,0,20,500,0,0,0
1,2026,'010110000',  ,NO,0,1,1,0,1,1,0,0,0,0,0,0
"""

JAPAN_ESTAT_LISTING_HTML = (
    '<a tabindex="22" href="/stat-search/files?page=1&amp;layout=datalist&amp;data=1&amp;'
    'metadata=1&amp;cycle=1&amp;toukei=00350300&amp;tstat=000001013141&amp;tclass1=000001013183'
    '&amp;tclass2=000001013184&amp;tclass3val=0&amp;year=20260&amp;month=23070907&amp;result_back=1"'
    ' class="stat-item_child">7月</a>'
    '<a href="/stat-search/files?page=1&amp;layout=datalist&amp;cycle=1&amp;toukei=00350300&amp;'
    'tstat=000001013141&amp;tclass1=000001013183&amp;tclass2=000001013184&amp;tclass3val=0&amp;'
    'year=20250&amp;month=24101212&amp;result_back=1" class="stat-item_child">12月</a>'
)

JAPAN_ESTAT_MONTH_HTML = (
    '<div class="stat-dataset_list-body"><span>確報 26-01 2026年7月分 統計品別表 (輸出 1-7月：確報)</span>'
    '<a href="/stat-search/file-download?statInfId=000040500123&amp;fileKind=1" class="stat-dl_icon">CSV</a></div>'
)


class TestJapan(unittest.TestCase):
    def test_press_10day_totals_only(self):
        rows = japan_customs.parse_press_xml(
            JAPAN_PRESS_10DAY_XML, "2026-08", "D10", "1", "en", "2026-09-02")
        self.assertEqual([(r["section"], r["imex"]) for r in rows],
                         [("TOTAL", "E"), ("TOTAL", "I"), ("TOTAL", "BAL")])
        exp = rows[0]
        self.assertEqual((exp["value_jpy_m"], exp["value_year_ago_jpy_m"], exp["yoy_pct"]),
                         ("3678584", "3185248", "15.50"))
        self.assertEqual(exp["period_type"], "D10")
        self.assertIn("First 10 days Provisional", exp["extra_json"])

    def test_press_monthly_breakdown(self):
        rows = japan_customs.parse_press_xml(
            JAPAN_PRESS_MONTHLY_XML, "2026-07", "MONTH_PROV", "4", "en", "2026-09-02")
        by = {(r["section"], r["imex"], r["area"], r["name"]): r for r in rows}
        bal = by[("TOTAL", "BAL", "WORLD", "Grand Total")]
        self.assertEqual(bal["value_jpy_m"], "-634500")           # △ -> negative
        tw = by[("AREA", "E", "TAIWAN", "TAIWAN")]
        self.assertEqual((tw["value_jpy_m"], tw["yoy_pct"], tw["level"]), ("929521", "46.40", "2"))
        semi = by[("COMMODITY", "E", "WORLD", "SEMICON MACHINERY ETC")]
        self.assertEqual((semi["value_jpy_m"], semi["yoy_pct"], semi["quantity"], semi["unit"],
                          semi["qty_yoy_pct"], semi["share_pct"], semi["contribution_pt"]),
                         ("494437", "40.90", "15586", "MT", "36.40", "4.30", "1.50"))
        china = by[("COMMODITY", "E", "CHINA", "SEMICON MACHINERY ETC")]
        self.assertEqual(china["yoy_pct"], "-10.20")
        imp = by[("COMMODITY", "I", "WORLD", "SEMICONDUCTORS ETC")]
        self.assertEqual(imp["value_jpy_m"], "554095")
        self.assertNotIn(("COMMODITY", "E", "WORLD", "SHIPS"), by)  # '-' value dropped
        self.assertEqual(len(rows), 3 + 6 + 4)

    def test_press_zero_rows_is_not_silent(self):
        rows = japan_customs.parse_press_xml(
            b"<root><a/><b/></root>", "2026-08", "D10", "1", "en", "2026-09-02")
        self.assertEqual(rows, [])  # the fetcher raises on this

    def test_time_series_commodity_layout(self):
        rows = japan_customs.parse_time_series_csv(JAPAN_TS_COMMODITY_CSV, "x", "2026-09-02")
        semi = [r for r in rows if r["code"] == "70131"]
        self.assertEqual([(r["yyyymm"], r["value_jpy_k"], r["quantity"], r["unit"]) for r in semi],
                         [("2025-07", "350900000", "11424000", "KG"),
                          ("2026-07", "493949821", "15561810", "KG")])
        self.assertEqual(semi[0]["imex"], "E")
        total = [r for r in rows if r["code"] == "0～9"]
        self.assertEqual((total[0]["name"], total[0]["value_jpy_k"]), ("総額", "9345000000"))
        food = [r for r in rows if r["code"] == "0"]
        self.assertEqual(food[0]["name"], "食料品及び動物")  # 概況品名 beats 報道発表品目名
        self.assertFalse([r for r in rows if r["yyyymm"] == "2026-08"])  # '-' skipped

    def test_time_series_total_layout(self):
        rows = japan_customs.parse_time_series_csv(JAPAN_TS_TOTAL_CSV, "world_total", "d")
        self.assertEqual([(r["imex"], r["yyyymm"], r["value_jpy_k"]) for r in rows],
                         [("E", "2026-07", "11509373578"), ("I", "2026-07", "12146000000")])

    def test_estat_csv_prefix_filter(self):
        rows = japan_customs.parse_estat_commodity_csv(
            JAPAN_ESTAT_CSV, ["8486", "8541"], "DETAILED", "f.csv", "2026-09-02")
        self.assertEqual(len(rows), 4)  # two codes x Jan, Feb; Mar unpublished; 0101 excluded
        first = rows[0]
        self.assertEqual((first["yyyymm"], first["imex"], first["hs_code"]),
                         ("2026-01", "E", "848610000"))
        self.assertEqual((first["value_jpy_k"], first["quantity2"], first["unit2"]),
                         ("4000", "100", "KG"))

    def test_estat_navigation(self):
        months = japan_customs.parse_estat_listing(JAPAN_ESTAT_LISTING_HTML)
        self.assertEqual([m["yyyymm"] for m in months], ["2026-07", "2025-12"])
        self.assertTrue(months[0]["url"].startswith("https://www.e-stat.go.jp/stat-search/files?"))
        self.assertIn("&month=23070907", months[0]["url"])
        self.assertEqual(japan_customs.estat_month_code(7), "23070907")
        self.assertEqual(japan_customs.estat_month_code(12), "24101212")
        parent = ('<a href="/stat-search/files?toukei=00350300&amp;tstat=000001013141&amp;'
                  'tclass1=000001013183&amp;tclass2=000001013184" target="_blank">輸出</a>'
                  '<a href="/stat-search/files?toukei=00350300&amp;tstat=000001013141&amp;'
                  'tclass1=000001013183&amp;tclass2=000001013199" target="_blank">輸入</a>')
        self.assertEqual(japan_customs.discover_tclass2(parent, "輸入"), "000001013199")
        self.assertEqual(japan_customs.discover_tclass2(parent, "再輸出"), "")
        files = japan_customs.parse_estat_month_page(JAPAN_ESTAT_MONTH_HTML)
        self.assertEqual(files[0]["stat_inf_id"], "000040500123")
        self.assertIn("確報", files[0]["title"])
        self.assertEqual(japan_customs._stage_from_title(files[0]["title"]), "DETAILED")
        mixed = "2026年7月分 統計品別表 (輸入 1-6月：確報、7月：輸入9桁速報)"
        self.assertEqual(japan_customs.stages_by_month(mixed),
                         {1: "DETAILED", 2: "DETAILED", 3: "DETAILED", 4: "DETAILED",
                          5: "DETAILED", 6: "DETAILED", 7: "PROV9"})
        self.assertEqual(japan_customs.stages_by_month("(輸出 1-7月：確報)"),
                         {m: "DETAILED" for m in range(1, 8)})
        rows = japan_customs.parse_estat_commodity_csv(
            JAPAN_ESTAT_CSV, ["8486"], {1: "DETAILED", 2: "PROV9"}, "f", "d")
        self.assertEqual([r["stage"] for r in rows], ["DETAILED", "PROV9"])

    def test_japan_signal_yoy(self):
        with tempfile.TemporaryDirectory() as tmp:
            def press(yyyymm, ptype, stage, lang, section, imex, area, name, value, yoy):
                return [yyyymm, ptype, stage, lang, section, imex, area, name, "",
                        value, "", yoy, "", "", "", "", "", "{}", "d"]
            common.write_csv(Path(tmp) / "press_release.csv", japan_customs.PRESS_HEADER, [
                press("2025-07", "MONTH_PROV", "4", "en", "COMMODITY", "E", "WORLD",
                      "SEMICON MACHINERY ETC", "350913", "10.0"),
                press("2026-07", "MONTH_PROV", "4", "en", "COMMODITY", "E", "WORLD",
                      "SEMICON MACHINERY ETC", "494437", "40.9"),
                press("2026-07", "MONTH_PROV", "4", "en", "COMMODITY", "E", "CHINA",
                      "SEMICON MACHINERY ETC", "157063", "-10.2"),
                press("2026-07", "MONTH_PROV", "4", "ja", "COMMODITY", "E", "世界",
                      "半導体等製造装置", "494437", "40.9"),
            ])
            common.write_csv(Path(tmp) / "trade_monthly_hs.csv", japan_customs.HS_HEADER, [
                ["2025-06", "E", "848610000", "DETAILED", "1000", "", "", "", "", "a", "d"],
                ["2025-06", "E", "848620000", "DETAILED", "1000", "", "", "", "", "a", "d"],
                ["2026-06", "E", "848610000", "DETAILED", "1500", "", "", "", "", "b", "d"],
                ["2026-06", "E", "848620000", "DETAILED", "1500", "", "", "", "", "b", "d"],
                ["2026-06", "E", "848620000", "PROV9", "999", "", "", "", "", "c", "d"],
            ])
            orig = compute_signals.JAPAN_DIR
            compute_signals.JAPAN_DIR = Path(tmp)
            try:
                out = compute_signals.japan_signals()
            finally:
                compute_signals.JAPAN_DIR = orig
        press_rows = [r for r in out if r[2] == "press_release"]
        self.assertEqual(len(press_rows), 2)  # ja rows and by-country tables excluded
        latest = [r for r in press_rows if r[0] == "2026-07"][0]
        self.assertEqual((latest[1], latest[3], latest[6], latest[7]),
                         ("MONTH", "E:SEMICON MACHINERY ETC", "40.90", "40.9"))
        hs = [r for r in out if r[2].startswith("estat_hs") and r[0] == "2026-06"][0]
        self.assertEqual((hs[3], hs[4], hs[6]), ("E:HS8486", "3", "50.00"))  # DETAILED wins over PROV9


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
