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
                     korea_tradedata, taiwan_mops, us_census)

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
                # 2026-06: the detailed stage appended BEFORE a provisional
                # re-fetch; the detailed value must still win.
                press("2026-06", "MONTH_DP", "5", "en", "TOTAL", "E", "WORLD",
                      "EXPORT TOTAL", "9500000", "5.0"),
                press("2026-06", "MONTH_PROV", "4", "en", "TOTAL", "E", "WORLD",
                      "EXPORT TOTAL", "9400000", "4.0"),
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
        self.assertEqual(len(press_rows), 3)  # ja rows and by-country tables excluded
        june = [r for r in press_rows if r[0] == "2026-06"][0]
        self.assertEqual((june[1], june[4], june[7]), ("MONTH", "9500000", "5.0"))
        latest = [r for r in press_rows if r[0] == "2026-07"][0]
        self.assertEqual((latest[1], latest[3], latest[6], latest[7]),
                         ("MONTH", "E:SEMICON MACHINERY ETC", "40.90", "40.9"))
        hs = [r for r in out if r[2].startswith("estat_hs") and r[0] == "2026-06"][0]
        self.assertEqual((hs[3], hs[4], hs[6]), ("E:HS8486", "3", "50.00"))  # DETAILED wins over PROV9


# Census International Trade API shape (documented list-of-lists; header row first).
US_CENSUS_JSON = [
    ["CTY_CODE", "CTY_NAME", "GEN_VAL_MO", "CON_VAL_MO", "GEN_QY1_MO", "UNIT_QY1",
     "AIR_VAL_MO", "VES_VAL_MO", "I_COMMODITY_SDESC", "SUMMARY_LVL", "I_COMMODITY",
     "COMM_LVL", "YEAR", "MONTH"],
    ["-", "TOTAL FOR ALL COUNTRIES", "900000000", "880000000", "1200000", "NO",
     "850000000", "50000000", "TRANSMISSION APPARATUS, OTHER", "DET", "8517620090",
     "HS10", "2026", "07"],
    ["5700", "CHINA", "300000000", "290000000", "400000", "NO", "280000000", "20000000",
     "TRANSMISSION APPARATUS, OTHER", "DET", "8517620090", "HS10", "2026", "07"],
    ["5490", "THAILAND", "200000000", "200000000", "250000", "NO", "199000000", "1000000",
     "TRANSMISSION APPARATUS, OTHER", "DET", "8517620090", "HS10", "2026", "07"],
    ["0014", "ASIA", "650000000", "640000000", "800000", "NO", "600000000", "50000000",
     "TRANSMISSION APPARATUS, OTHER", "CGP", "8517620090", "HS10", "2026", "07"],
    ["5230", "OMAN", "0", "0", "0", "NO", "0", "0",
     "TRANSMISSION APPARATUS, OTHER", "DET", "8517620090", "HS10", "2026", "07"],
]

# Shape of the live hts.usitc.gov exportList payload (a bare list; units is a
# list or null), captured 2026-09-11.
US_HTS_JSON = [
    {"htsno": "8517.62.00", "statisticalSuffix": "", "indent": "2",
     "description": "Machines for the reception, conversion and transmission or regeneration of voice, images or other data, including switching and routing apparatus",
     "general": "Free", "units": None, "footnotes": []},
    {"htsno": "8517.62.00.90", "statisticalSuffix": "90", "indent": "3",
     "description": "Other", "general": "", "units": ["No."], "footnotes": []},
]


class TestUSCensus(unittest.TestCase):
    def test_parse_rows(self):
        rows = us_census.parse_census_rows(US_CENSUS_JSON, "I", "8517620090", "HS10",
                                           "2026-07", "2026-09-11")
        self.assertEqual(len(rows), 4)  # zero-trade OMAN row dropped
        total = rows[0]
        self.assertEqual((total["cty_code"], total["value_usd"], total["value_cons_usd"]),
                         ("-", "900000000", "880000000"))
        china = rows[1]
        self.assertEqual((china["cty_name"], china["qty1"], china["unit1"],
                          china["air_value_usd"], china["summary_lvl"]),
                         ("CHINA", "400000", "NO", "280000000", "DET"))
        self.assertIn('"I_COMMODITY": "8517620090"', china["extra_json"])
        self.assertEqual(us_census.parse_census_rows([], "I", "x", "HS10", "2026-07", "d"), [])

    def test_export_value_field(self):
        payload = [["CTY_CODE", "CTY_NAME", "ALL_VAL_MO", "QTY_1_MO", "UNIT_QY1"],
                   ["5880", "JAPAN", "12345", "7", "NO"]]
        rows = us_census.parse_census_rows(payload, "E", "854141", "HS6", "2026-07", "d")
        self.assertEqual((rows[0]["value_usd"], rows[0]["qty1"]), ("12345", "7"))

    def test_bad_variable_detection(self):
        requested = ["CTY_CODE", "VES_VAL_MO", "SUMMARY_LVL"]
        self.assertEqual(us_census.bad_variable(
            "error: unknown variable 'VES_VAL_MO'", requested), "VES_VAL_MO")
        self.assertEqual(us_census.bad_variable("error: missing required variable/predicate: time",
                                                requested), "")

    def test_hts_snapshot_and_dotting(self):
        self.assertEqual(us_census._dotted("8517620090"), "8517.62.00.90")
        self.assertEqual(us_census._dotted("851762"), "8517.62")
        rows = us_census.parse_hts_payload(US_HTS_JSON, "8517620090", "d")
        self.assertEqual([r["htsno"] for r in rows], ["8517.62.00", "8517.62.00.90"])
        self.assertEqual(rows[1]["unit1"], "No.")

    def test_default_range(self):
        # On 2026-09-11 the newest published month is July (released Sept 3).
        self.assertEqual(us_census._default_range(dt.date(2026, 9, 11)), ("2026-04", "2026-07"))

    def test_us_signal_share_and_yoy(self):
        with tempfile.TemporaryDirectory() as tmp:
            def row(yyyymm, cty, name, lvl, value):
                return [yyyymm, "I", "8517620090", "HS10", cty, name, lvl, value, "", "",
                        "", "", "", "", "{}", "d"]
            common.write_csv(Path(tmp) / "trade_monthly_hs.csv", us_census.TRADE_HEADER, [
                row("2025-07", "-", "TOTAL FOR ALL COUNTRIES", "DET", "600000000"),
                row("2025-07", "5700", "CHINA", "DET", "300000000"),
                row("2026-07", "-", "TOTAL FOR ALL COUNTRIES", "DET", "900000000"),
                row("2026-07", "5700", "CHINA", "DET", "300000000"),
                row("2026-07", "5490", "THAILAND", "DET", "200000000"),
                row("2026-07", "0014", "ASIA", "CGP", "650000000"),
            ])
            orig = compute_signals.US_DIR
            compute_signals.US_DIR = Path(tmp)
            try:
                out = compute_signals.us_signals()
            finally:
                compute_signals.US_DIR = orig
        by = {(r[0], r[3]): r for r in out}
        self.assertNotIn(("2026-07", "0014"), by)             # grouping excluded
        self.assertEqual(by[("2026-07", "5700")][7], "0.00")   # China flat YoY
        self.assertEqual(by[("2026-07", "5700")][8], "33.3")   # share of code
        self.assertEqual(by[("2026-07", "-")][7], "50.00")     # total YoY


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


class TestIntel(unittest.TestCase):
    """signals/intel.py: diff of derived tables and threshold flags."""

    def _write(self, directory, name, rows):
        from signals import compute_signals as cs
        header = {"taiwan": cs.TAIWAN_SIGNAL_HEADER, "korea": cs.KOREA_SIGNAL_HEADER,
                  "japan": cs.JAPAN_SIGNAL_HEADER, "us": cs.US_SIGNAL_HEADER}[name]
        common.write_csv(Path(directory) / f"{name}_signals.csv", header, rows)

    def test_diff_and_flags(self):
        from signals import intel
        with tempfile.TemporaryDirectory() as tmp:
            prev, cur = Path(tmp) / "prev", Path(tmp) / "cur"
            prev.mkdir(); cur.mkdir()
            jp_old = ["2026-06", "MONTH", "press_release", "E:SEMICON MACHINERY ETC",
                      "400000", "", "", "12.0"]
            jp_new = ["2026-07", "MONTH", "press_release", "E:SEMICON MACHINERY ETC",
                      "494437", "", "", "40.9"]
            jp_ts = ["2026-07", "MONTH", "timeseries:world_exports_by_commodity",
                     "E:半導体等製造装置", "493950", "350000", "41.13", ""]
            jp_minor = ["2026-07", "MONTH", "press_release", "E:FISH", "1000", "", "", "99.0"]
            self._write(prev, "japan", [jp_old])
            self._write(cur, "japan", [jp_old, jp_new, jp_ts, jp_minor])
            us_rows = [
                ["2026-06", "I", "8517620090", "-", "ALL COUNTRIES", "6000000", "", "", "100.0", "", ""],
                ["2026-06", "I", "8517620090", "5490", "THAILAND", "2000000", "", "", "33.3", "", ""],
                ["2026-07", "I", "8517620090", "-", "ALL COUNTRIES", "7000000", "4500000", "55.56", "100.0", "", ""],
                ["2026-07", "I", "8517620090", "5490", "THAILAND", "2800000", "1400000", "100.00", "40.0", "", ""],
                ["2026-07", "I", "8517620090", "5230", "OMAN", "20", "5", "300.00", "0.0", "", ""],
            ]
            self._write(prev, "us", us_rows[:2])
            self._write(cur, "us", us_rows)
            self._write(prev, "korea", [["2026-07", "FULL", "exp:TOTAL", "90000000", "", ""]])
            self._write(cur, "korea", [["2026-07", "FULL", "exp:TOTAL", "91000000", "", ""]])
            diff = intel.diff_tables(prev, cur)
            self.assertEqual(diff["japan"]["groups"], {("2026-07", "MONTH"): {"new": 3, "revised": 0}})
            self.assertEqual(diff["korea"]["groups"], {("2026-07", "FULL"): {"new": 0, "revised": 1}})
            self.assertTrue(diff["taiwan"]["baseline"])
            flags = intel.flags_for(diff)
            labels = {(f["source"], f["item"], f["kind"]) for f in flags}
            # Press-release row flags on the published YoY; the time-series
            # duplicate and the non-interest item do not; OMAN is immaterial.
            self.assertIn(("japan", "MONTH press_release E:SEMICON MACHINERY ETC", "yoy"), labels)
            self.assertNotIn(("japan", "MONTH timeseries:world_exports_by_commodity E:半導体等製造装置", "yoy"), labels)
            self.assertNotIn(("japan", "MONTH press_release E:FISH", "yoy"), labels)
            self.assertIn(("us", "I 8517620090 ALL COUNTRIES", "yoy"), labels)
            self.assertIn(("us", "I 8517620090 THAILAND", "yoy"), labels)
            self.assertIn(("us", "I 8517620090 THAILAND", "share"), labels)
            self.assertFalse(any(f["item"].endswith("OMAN") for f in flags))
            markdown, subject = intel.render(diff, flags, "2026-09-12")
            self.assertEqual(subject, "3 new print groups, 1 revised, 4 flags")
            self.assertIn("## FLAGS (4)", markdown)
            self.assertIn("| korea | 2026-07 | FULL | 0 | 1 |", markdown)
            self.assertIn("taiwan: no previous snapshot", markdown)

    def test_no_change_subject(self):
        from signals import intel
        with tempfile.TemporaryDirectory() as tmp:
            prev, cur = Path(tmp) / "prev", Path(tmp) / "cur"
            prev.mkdir(); cur.mkdir()
            row = ["2026-07", "FULL", "exp:TOTAL", "90000000", "", ""]
            self._write(prev, "korea", [row]); self._write(cur, "korea", [row])
            diff = intel.diff_tables(prev, cur)
            markdown, subject = intel.render(diff, intel.flags_for(diff), "2026-09-12")
            self.assertEqual(subject, "no new prints")
            self.assertIn("## No new prints this run", markdown)


# ECB SDMX csvdata shape: units of the currency per EUR, one row per (ccy, day).
# 2026-07-01 is complete; 2026-07-02 has no USD leg (a holiday in the fixture),
# so no cross rate can be formed for it.
FX_ECB_CSV = (
    "KEY,FREQ,CURRENCY,CURRENCY_DENOM,EXR_TYPE,EXR_SUFFIX,TIME_PERIOD,OBS_VALUE,OBS_STATUS\n"
    "EXR.D.JPY.EUR.SP00.A,D,JPY,EUR,SP00,A,2026-07-01,167.50,A\n"
    "EXR.D.KRW.EUR.SP00.A,D,KRW,EUR,SP00,A,2026-07-01,1534.00,A\n"
    "EXR.D.USD.EUR.SP00.A,D,USD,EUR,SP00,A,2026-07-01,1.1800,A\n"
    "EXR.D.JPY.EUR.SP00.A,D,JPY,EUR,SP00,A,2026-07-02,167.80,A\n"
    "EXR.D.KRW.EUR.SP00.A,D,KRW,EUR,SP00,A,2026-07-02,1535.00,A\n"
    "EXR.D.JPY.EUR.SP00.A,D,JPY,EUR,SP00,A,2026-07-15,169.00,A\n"
    "EXR.D.USD.EUR.SP00.A,D,USD,EUR,SP00,A,2026-07-15,1.2000,A\n"
)

FX_FRANKFURTER_JSON = {
    "amount": 1.0, "base": "USD", "start_date": "2026-07-01", "end_date": "2026-07-02",
    "rates": {"2026-07-01": {"JPY": 141.95, "KRW": 1300.0},
              "2026-07-02": {"JPY": 142.10, "KRW": 1301.5, "GBP": 0.79}},
}


class TestFxRates(unittest.TestCase):
    """signals/fx_rates.py: cross rates, fallback shape, window averaging."""

    def test_parse_ecb_cross_rate(self):
        from signals import fx_rates
        rows = fx_rates.parse_ecb_csv(FX_ECB_CSV, "d", ["JPY", "KRW"])
        by = {(r["date"], r["quote"]): r for r in rows}
        # 167.50 yen per EUR / 1.18 USD per EUR = 141.95 yen per USD
        self.assertAlmostEqual(float(by[("2026-07-01", "JPY")]["rate_per_usd"]), 141.95, places=2)
        self.assertAlmostEqual(float(by[("2026-07-01", "KRW")]["rate_per_usd"]), 1300.00, places=2)
        self.assertAlmostEqual(float(by[("2026-07-15", "JPY")]["rate_per_usd"]), 140.83, places=2)
        # No USD leg on 07-02, so no cross rate is invented for that date.
        self.assertNotIn(("2026-07-02", "JPY"), by)
        self.assertEqual({r["source"] for r in rows}, {"ecb"})
        # USD itself is never stored as a quote against itself.
        self.assertNotIn("USD", {r["quote"] for r in rows})

    def test_parse_ecb_rejects_wrong_shape(self):
        from signals import fx_rates
        self.assertEqual(fx_rates.parse_ecb_csv("not,a,rate,file\n1,2,3,4\n", "d", ["JPY"]), [])
        self.assertEqual(fx_rates.parse_ecb_csv("", "d", ["JPY"]), [])

    def test_parse_frankfurter(self):
        from signals import fx_rates
        rows = fx_rates.parse_frankfurter_json(FX_FRANKFURTER_JSON, "d", ["JPY", "KRW"])
        self.assertEqual(len(rows), 4)  # GBP is not a configured quote
        by = {(r["date"], r["quote"]): float(r["rate_per_usd"]) for r in rows}
        self.assertAlmostEqual(by[("2026-07-02", "JPY")], 142.10, places=2)
        self.assertEqual({r["source"] for r in rows}, {"frankfurter"})

    def test_window_average_matches_the_published_window(self):
        from signals import fx_rates
        rates = {"JPY": {"2026-07-03": 140.0, "2026-07-08": 142.0,   # inside days 1-10
                         "2026-07-17": 150.0,                        # inside 1-20 only
                         "2026-07-28": 160.0}}                       # month only
        self.assertAlmostEqual(fx_rates.window_average(rates, "JPY", "2026-07", "D10"), 141.0)
        self.assertAlmostEqual(fx_rates.window_average(rates, "JPY", "2026-07", "D20"), 144.0)
        self.assertAlmostEqual(fx_rates.window_average(rates, "JPY", "2026-07", "MONTH"), 148.0)
        # A month with nothing stored returns None rather than a guess.
        self.assertIsNone(fx_rates.window_average(rates, "JPY", "2025-07", "MONTH"))
        self.assertIsNone(fx_rates.window_average(rates, "KRW", "2026-07", "MONTH"))

    def test_japan_signals_separate_currency_from_trade(self):
        """A 40% yen rise on a 10% weaker yen is ~27% in USD, ~13 pt currency."""
        from signals import compute_signals, fx_rates
        with tempfile.TemporaryDirectory() as tmp:
            common.write_csv(Path(tmp) / "press_release.csv", japan_customs.PRESS_HEADER, [
                [m, "MONTH_PROV", "4", "en", "COMMODITY", "E", "WORLD",
                 "SEMICON MACHINERY ETC", "", v, "", "", "", "", "", "", "", "{}", "d"]
                for m, v in (("2025-07", "350000"), ("2026-07", "490000"))
            ])
            fx = Path(tmp) / "rates_daily.csv"
            common.write_csv(fx, fx_rates.RATES_HEADER, [
                ["2025-07-15", "JPY", "140.00", "ecb", "d"],
                ["2026-07-15", "JPY", "154.00", "ecb", "d"],
            ])
            orig_jp, orig_fx = compute_signals.JAPAN_DIR, fx_rates.OUT_DIR
            compute_signals.JAPAN_DIR, fx_rates.OUT_DIR = Path(tmp), Path(tmp)
            try:
                out = compute_signals.japan_signals()
            finally:
                compute_signals.JAPAN_DIR, fx_rates.OUT_DIR = orig_jp, orig_fx
        row = [r for r in out if r[0] == "2026-07" and r[2] == "press_release"][0]
        self.assertEqual(len(row), len(compute_signals.JAPAN_SIGNAL_HEADER))
        self.assertEqual(row[6], "40.00")           # yen YoY, as published
        self.assertEqual(row[8], "154.00")          # rate used for the window
        self.assertEqual(row[9], "3181818")         # 490,000m yen in USD k
        self.assertEqual(row[10], "27.27")          # USD YoY: the real move
        self.assertEqual(row[11], "12.73")          # the yen's share, in points
        # The customs rate is the market average from two weeks earlier, and
        # the fixture stores one rate per year, so both years resolve to it.
        self.assertEqual(row[12], "154.00")
        self.assertEqual(row[13], "27.27")

    def test_customs_rate_is_the_market_average_two_weeks_earlier(self):
        """Japan Customs fixes a week's rate from the market two weeks before."""
        from signals import fx_rates
        # 2025-09-07 is a Sunday; its customs week draws on 2025-08-24..08-30.
        rates = {"JPY": {"2025-08-25": 147.0, "2025-08-26": 147.5,
                         "2025-08-27": 147.2, "2025-08-28": 147.6,
                         "2025-08-29": 147.7,
                         # Inside the applicable week itself: must be ignored.
                         "2025-09-08": 160.0, "2025-09-09": 161.0}}
        import datetime as dt
        for day in ("2025-09-07", "2025-09-10", "2025-09-13"):
            rate = fx_rates.customs_rate_for_day(rates, "JPY", dt.date.fromisoformat(day))
            self.assertAlmostEqual(rate, 147.4, places=2,
                                   msg=f"{day} should use the 2025-08-24 week")
        # Two weeks later the source window has moved on to the week of
        # 2025-09-07, so the same fixture yields the later pair instead.
        self.assertAlmostEqual(fx_rates.customs_rate_for_day(
            rates, "JPY", dt.date.fromisoformat("2025-09-21")), 160.5, places=2)
        # A week whose source window holds nothing computes to nothing.
        self.assertIsNone(fx_rates.customs_rate_for_day(
            rates, "JPY", dt.date.fromisoformat("2026-05-10")))
        self.assertIsNone(fx_rates.customs_rate_for_day(
            rates, "USD", dt.date.fromisoformat("2025-09-10")))

    def test_customs_window_average_covers_every_day_of_the_window(self):
        from signals import fx_rates
        # Two source weeks feed September 2026's first ten days.
        rates = {"JPY": {"2026-08-18": 150.0, "2026-08-19": 150.0,
                         "2026-08-25": 160.0, "2026-08-26": 160.0}}
        # Sept 1-5 sit in the week starting Aug 30, sourced from Aug 16;
        # Sept 6-10 sit in the week starting Sept 6, sourced from Aug 23.
        avg = fx_rates.customs_window_average(rates, "JPY", "2026-09", "D10")
        self.assertAlmostEqual(avg, 155.0, places=2)
        self.assertIsNone(fx_rates.customs_window_average(rates, "JPY", "2024-01"))

    def test_japan_signals_leave_currency_blank_without_rates(self):
        from signals import compute_signals, fx_rates
        with tempfile.TemporaryDirectory() as tmp:
            common.write_csv(Path(tmp) / "press_release.csv", japan_customs.PRESS_HEADER, [
                ["2026-07", "MONTH_PROV", "4", "en", "TOTAL", "E", "WORLD", "EXPORT TOTAL",
                 "", "490000", "", "", "", "", "", "", "", "{}", "d"]])
            orig_jp, orig_fx = compute_signals.JAPAN_DIR, fx_rates.OUT_DIR
            compute_signals.JAPAN_DIR, fx_rates.OUT_DIR = Path(tmp), Path(tmp)
            try:
                out = compute_signals.japan_signals()
            finally:
                compute_signals.JAPAN_DIR, fx_rates.OUT_DIR = orig_jp, orig_fx
        self.assertEqual(out[0][8:], ["", "", "", "", "", ""])
