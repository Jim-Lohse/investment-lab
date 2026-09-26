"""Offline tests for the foreign-filings feeds. No network.

Fixtures mirror what each source returned on 2026-09-26: the Yanoshin TDnet
JSON for Musashi (7220), the Investegate company page and a Transaction in
Own Shares notice for IMB, and the documented EDINET v2 / OpenDART envelopes.

Run:  python -m unittest discover tests
"""

from __future__ import annotations

import datetime as dt
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from signals import filings

CFG = filings.load_config()
TOPICS = CFG["topics"]
MUSASHI = CFG["japan"][0]
IMB = CFG["uk"][0]
KTG = CFG["korea"][0]

YANOSHIN = {
    "total_count": 2,
    "items": [
        {"Tdnet": {"id": "1270702", "pubdate": "2026-08-05 15:50:00", "company_code": "72200",
                   "company_name": "武蔵精密", "title": "2027年３月期 第１四半期決算短信【日本基準】(連結)",
                   "document_url": "https://webapi.yanoshin.jp/rd.php?https://www.release.tdnet.info/inbs/140120260805509240.pdf",
                   "url_xbrl": "https://webapi.yanoshin.jp/rd.php?https://www.release.tdnet.info/inbs/081220260805509240.zip"}},
        {"Tdnet": {"id": "1267639", "pubdate": "2026-07-24 17:00:00", "company_code": "72200",
                   "company_name": "武蔵精密", "title": "譲渡制限付株式報酬としての新株式の払込完了に関するお知らせ",
                   "document_url": "https://webapi.yanoshin.jp/rd.php?https://www.release.tdnet.info/inbs/140120260724599194.pdf",
                   "url_xbrl": None}},
    ],
}

INVESTEGATE_PAGE = """
<table class="table">
<tr><td>25 Sep 2026 02:13 PM</td><td>RNS</td>
<td><a class="announcement-link" href="https://www.investegate.co.uk/announcement/rns/imperial-brands--imb/transaction-in-own-shares/9792146">Transaction in Own Shares</a></td></tr>
<tr><td>01 Oct 2026 07:00 AM</td><td>RNS</td>
<td><a href="/announcement/rns/imperial-brands--imb/pre-close-trading-update/9800001">Pre-Close Trading Update</a></td></tr>
<tr><td>01 Oct 2026 07:05 AM</td><td>RNS</td>
<td><a href="/announcement/rns/some-other-plc--xyz/results/9800002">Results</a></td></tr>
</table>
"""

OWN_SHARES = """<div class="news-body"><p>Imperial Brands PLC (the "Company") announces that on 24 September 2026
it purchased for cancellation the following number of its ordinary shares of 10 pence each pursuant
to its GBP 1.45 billion share repurchase programme, details of which were announced on 7 October 2025.</p>
<p>Number of shares repurchased: 150,000</p><p>Date of transaction: 24 September 2026</p>
<p>Average price paid per share: GBp 2,480.0775</p><p>Lowest price paid per share: GBp 2,465.0000</p>
<p>Highest price paid per share: GBp 2,490.0000</p>
<p>the remaining number of ordinary shares in issue will be 760,201,043 (excluding treasury shares).</p></div>"""

EDINET = {
    "metadata": {"status": "200", "message": "OK"},
    "results": [
        {"docID": "S100AAAA", "edinetCode": "E00000", "secCode": "72200", "filerName": "武蔵精密工業株式会社",
         "docTypeCode": "160", "docDescription": "半期報告書－第88期(2026/04/01－2027/03/31)",
         "submitDateTime": "2026-11-13 15:00", "periodStart": "2026-04-01", "periodEnd": "2026-09-30"},
        {"docID": "S100BBBB", "edinetCode": "E11111", "secCode": None, "issuerEdinetCode": "E99999",
         "filerName": "ＥＮＥＯＳホールディングス株式会社", "docTypeCode": "350",
         "docDescription": "変更報告書", "submitDateTime": "2026-10-02 15:30"},
        {"docID": "S100CCCC", "edinetCode": "E22222", "secCode": "99990", "filerName": "Unrelated",
         "docTypeCode": "120", "docDescription": "有価証券報告書", "submitDateTime": "2026-10-02 15:30"},
    ],
}

DART_LIST = {
    "status": "000", "message": "정상",
    "list": [
        {"corp_code": "00244455", "corp_name": "케이티앤지", "stock_code": "033780",
         "report_nm": "현금ㆍ현물배당결정", "rcept_no": "20261015000123", "flr_nm": "케이티앤지",
         "rcept_dt": "20261015", "rm": "유"},
        {"corp_code": "00244455", "corp_name": "케이티앤지", "stock_code": "033780",
         "report_nm": "임원ㆍ주요주주특정증권등소유상황보고서", "rcept_no": "20261014000999",
         "flr_nm": "홍길동", "rcept_dt": "20261014", "rm": ""},
    ],
}

CORPCODE_XML = """<?xml version="1.0" encoding="UTF-8"?><result>
<list><corp_code>00244455</corp_code><corp_name>케이티앤지</corp_name><stock_code>033780</stock_code></list>
<list><corp_code>00126380</corp_code><corp_name>삼성전자</corp_name><stock_code>005930</stock_code></list>
<list><corp_code>99999999</corp_code><corp_name>비상장</corp_name><stock_code> </stock_code></list>
</result>""".encode("utf-8")


class TopicTests(unittest.TestCase):
    def test_japanese_and_english_patterns(self):
        self.assertIn("results", filings.tag_topics("第２四半期決算短信", TOPICS))
        self.assertIn("results", filings.tag_topics("Pre-Close Trading Update", TOPICS))
        self.assertIn("buyback", filings.tag_topics("transaction in own shares", TOPICS))
        self.assertIn("dividend", filings.tag_topics("현금ㆍ현물배당결정", TOPICS))
        self.assertEqual(filings.tag_topics("Notice of AGM", TOPICS), [])


class TdnetTests(unittest.TestCase):
    def test_parse_and_unwrap(self):
        rows = filings.parse_yanoshin(YANOSHIN, "7220", "Musashi Seimitsu", TOPICS,
                                      MUSASHI["priority"], "2026-09-26T00:00:00Z")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["doc_url"],
                         "https://www.release.tdnet.info/inbs/140120260805509240.pdf")
        self.assertEqual(rows[0]["needs_reading"], "yes")
        self.assertEqual(rows[1]["xbrl_url"], "")
        self.assertEqual(rows[1]["needs_reading"], "")


class EdinetTests(unittest.TestCase):
    def test_filter_to_watched_and_subject(self):
        watch = {c["code"]: dict(c) for c in CFG["japan"]}
        watch["5016"]["edinet_code"] = "E99999"  # JX as the subject of ENEOS's report
        rows = filings.parse_edinet_list(EDINET, watch, TOPICS, "t")
        self.assertEqual([r["doc_id"] for r in rows], ["S100AAAA", "S100BBBB"])
        self.assertEqual(rows[0]["doc_type"], "half-year report")
        self.assertIn("results", rows[0]["topics"])
        self.assertEqual(rows[1]["company"], "JX Advanced Metals")
        self.assertIn("ownership", rows[1]["topics"])
        self.assertEqual(rows[1]["needs_reading"], "yes")

    def test_codelist(self):
        csv_text = ("ダウンロード実行日,2026年09月26日現在,件数,11000件\n"
                    "ＥＤＩＮＥＴコード,提出者種別,上場区分,連結の有無,資本金,決算日,提出者名,提出者名（英字）,提出者名（ヨミ）,所在地,提出者業種,証券コード,提出者法人番号\n"
                    "E02230,内国法人・組合,上場,有,1000,3月31日,武蔵精密工業株式会社,MUSASHI SEIMITSU,,愛知県,輸送用機器,72200,\n"
                    "E39999,内国法人・組合,上場,有,1000,3月31日,ＪＸ金属株式会社,JX Advanced Metals,,東京都,非鉄金属,50160,\n"
                    "E00001,内国法人・組合,非上場,有,1000,3月31日,Other,Other,,東京都,,,\n")
        codes = filings.parse_edinet_codelist(csv_text.encode("cp932"), {"7220", "5016"})
        self.assertEqual(codes, {"7220": "E02230", "5016": "E39999"})

    def test_skips_without_key(self):
        with mock.patch.dict("os.environ", {}, clear=True), \
             mock.patch.object(filings, "record_status") as rec:
            self.assertEqual(filings.fetch_edinet(CFG), 0)
            rec.assert_called_with("edinet", "waiting for key")


class DartTests(unittest.TestCase):
    def test_list(self):
        rows = filings.parse_dart_list(DART_LIST, KTG, TOPICS, "t")
        self.assertEqual(rows[0]["needs_reading"], "yes")
        self.assertIn("dividend", rows[0]["topics"])
        self.assertEqual(rows[1]["needs_reading"], "")
        self.assertTrue(rows[0]["link"].endswith("20261015000123"))

    def test_no_data_and_errors(self):
        self.assertEqual(filings.parse_dart_list({"status": "013"}, KTG, TOPICS, "t"), [])
        with self.assertRaises(RuntimeError):
            filings.parse_dart_list({"status": "010", "message": "bad key"}, KTG, TOPICS, "t")

    def test_english_titles(self):
        self.assertEqual(filings.english_title("현금ㆍ현물배당결정"), "dividend declared (현금ㆍ현물배당결정)")
        self.assertTrue(filings.english_title("2027年３月期 第２四半期決算短信〔日本基準〕(連結)")
                        .startswith("quarterly earnings release"))
        self.assertEqual(filings.english_title("Pre-Close Trading Update"), "Pre-Close Trading Update")

    def test_corp_codes(self):
        codes = filings.parse_dart_corp_codes(CORPCODE_XML, {"033780", "005930"})
        self.assertEqual(codes, {"033780": "00244455", "005930": "00126380"})


class UkTests(unittest.TestCase):
    def test_company_page(self):
        rows = filings.parse_investegate_company(INVESTEGATE_PAGE, IMB, TOPICS, "t")
        self.assertEqual([r["ann_id"] for r in rows], ["9792146", "9800001"])
        self.assertEqual(rows[0]["routine"], "yes")
        self.assertEqual(rows[0]["needs_reading"], "")
        self.assertEqual(rows[0]["published"], "25 Sep 2026 02:13 PM")
        self.assertEqual(rows[1]["needs_reading"], "yes")
        self.assertTrue(rows[1]["link"].startswith("https://www.investegate.co.uk/announcement/"))

    def test_own_shares(self):
        d = filings.parse_own_shares(OWN_SHARES)
        self.assertEqual(d["shares"], "150000")
        self.assertEqual(d["trade_date"], "24 September 2026")
        self.assertEqual(d["avg_price_gbp_pence"], "2480.0775")
        self.assertEqual(d["low_pence"], "2465.0000")
        self.assertEqual(d["high_pence"], "2490.0000")
        self.assertEqual(d["shares_in_issue"], "760201043")
        self.assertIn("1.45 billion", d["programme"])

    def test_buyback_pace_and_gap(self):
        rows = [{"trade_date": "23 September 2026", "shares": "100000", "avg_price_gbp_pence": "2500"},
                {"trade_date": "24 September 2026", "shares": "150000", "avg_price_gbp_pence": "2480"}]
        p = filings.buyback_pace(rows)
        self.assertEqual(p["shares"], 250000)
        self.assertAlmostEqual(p["spend_gbp"], 100000 * 25.00 + 150000 * 24.80)
        self.assertEqual(p["last_trade"], dt.date(2026, 9, 24))
        # Thu 24 Sep -> Tue 29 Sep: Fri, Mon, Tue = 3 working days
        self.assertEqual(filings.uk_business_days_between(dt.date(2026, 9, 24),
                                                          dt.date(2026, 9, 29)), 3)


class BriefTests(unittest.TestCase):
    def test_brief_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            patches = {
                "FILINGS_DIR": tmp, "STATE_PATH": tmp / "state.json",
                "TDNET_CSV": tmp / "tdnet.csv", "EDINET_CSV": tmp / "edinet.csv",
                "DART_CSV": tmp / "dart.csv", "DART_5PCT_CSV": tmp / "d5.csv",
                "UK_CSV": tmp / "uk.csv", "UK_BUYBACK_CSV": tmp / "ukb.csv",
                "BRIEF_PATH": tmp / "brief.md",
            }
            with mock.patch.multiple(filings, **patches), \
                 mock.patch.dict("os.environ", {}, clear=True):
                seen = "2026-09-26T08:00:00Z"
                rows = filings.parse_yanoshin(YANOSHIN, "7220", "Musashi Seimitsu", TOPICS,
                                              MUSASHI["priority"], seen)
                filings.append_dedup_csv(filings.TDNET_CSV, filings.TDNET_FIELDS, rows, ["tdnet_id"])
                uk = filings.parse_investegate_company(INVESTEGATE_PAGE, IMB, TOPICS, seen)
                filings.append_dedup_csv(filings.UK_CSV, filings.UK_FIELDS, uk, ["ann_id"])
                b = {"ann_id": "9792146", "tidm": "IMB", "first_seen_utc": seen,
                     **filings.parse_own_shares(OWN_SHARES)}
                filings.append_dedup_csv(filings.UK_BUYBACK_CSV, filings.UK_BUYBACK_FIELDS, [b], ["ann_id"])
                filings.record_status("edinet", "waiting for key")
                text = filings.write_brief(CFG, "2026-09-26T07:00:00Z", dt.date(2026, 9, 30))
                self.assertIn("## Bottom line", text)
                # Musashi's August items are older than 10 days: history, not news
                self.assertIn("1 new document(s) touch a question", text)
                self.assertIn("2 older document(s) were loaded as history", text)
                self.assertIn("Pre-Close Trading Update", text)
                self.assertNotIn("| Imperial Brands | UK announcement | [Transaction in Own Shares]", text)
                self.assertIn("150,000", text)
                self.assertIn("no purchase reported for 4 working days", text)
                self.assertIn("EDINET", text)
                # A later run with nothing new
                text2 = filings.write_brief(CFG, "2026-09-27T00:00:00Z", dt.date(2026, 9, 25))
                self.assertIn("Nothing new from the watched companies", text2)
                self.assertLess(len(text.splitlines()), 70)


if __name__ == "__main__":
    unittest.main()
