"""Offline tests for the fund price and GLD holdings parsers."""

from __future__ import annotations

import io
import sys
import unittest
import zipfile
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


def make_xlsx(*sheets):
    """A minimal .xlsx, one argument per sheet: strings go to the shared-strings table."""
    shared, index, sheet_xml = [], {}, []
    for rows in sheets:
        sheet_xml.append(_sheet_xml(rows, shared, index))
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("xl/sharedStrings.xml",
                    f"<sst {ns}>" + "".join(f"<si><t>{t}</t></si>" for t in shared) + "</sst>")
        for i, xml in enumerate(sheet_xml, 1):
            zf.writestr(f"xl/worksheets/sheet{i}.xml", xml)
    return buf.getvalue()


def _sheet_xml(rows, shared, index):
    xml_rows = []
    for r, row in enumerate(rows, 1):
        cells = []
        for c, v in enumerate(row):
            ref = f"{chr(65 + c)}{r}"
            if isinstance(v, str):
                index.setdefault(v, len(shared))
                if index[v] == len(shared):
                    shared.append(v)
                cells.append(f'<c r="{ref}" t="s"><v>{index[v]}</v></c>')
            else:
                cells.append(f'<c r="{ref}"><v>{v}</v></c>')
        xml_rows.append(f'<row r="{r}">{"".join(cells)}</row>')
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    return f"<worksheet {ns}><sheetData>{''.join(xml_rows)}</sheetData></worksheet>"


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


class GldPayloadTests(unittest.TestCase):
    def test_xlsx_with_excel_serial_dates(self):
        content = make_xlsx([
            ["SPDR Gold Trust"],
            ["Date", "GLD Close", "Total Net Asset Value Ounces in the Trust",
             "Total Net Asset Value Tonnes in the Trust"],
            [46279, 361.2, 31000000.5, 964.21],
            ["15-Sep-2026", "HOLIDAY", "", ""],
            [46281, 362.0, 31100000, 967.32]])
        rows = etf_prices.parse_gld_payload(content)
        self.assertEqual([r["date"] for r in rows], ["2026-09-14", "2026-09-16"])
        self.assertEqual(rows[1]["tonnes"], "967.32")

    def test_real_layout_disclaimer_sheet_then_history(self):
        # Mirrors the 2026-09 archive: a disclaimer sheet, then the history
        # with "Ounces of Gold per Share" before "Total Ounces of Gold in the Trust".
        content = make_xlsx(
            [["Disclaimer"], ["Some legal text"]],
            [["Date", "Closing Price", "Ounces of Gold per Share", "Total Ounces of Gold in the Trust",
              "Tonnes of Gold"],
             ["18-Nov-2004", 44.38, 0.1, 260000.0, 8.09],
             ["22-Sep-2026", 400.07, 0.0917, 33950837.86, 1055.98]])
        rows = etf_prices.parse_gld_payload(content)
        self.assertEqual([r["date"] for r in rows], ["2004-11-18", "2026-09-22"])
        self.assertEqual((rows[1]["tonnes"], rows[1]["ounces"]), ("1055.98", "33950837.86"))

    def test_pdf_bar_list_is_rejected(self):
        self.assertEqual(etf_prices.parse_gld_payload(b"%PDF-1.5 bar list"), [])

    def test_archive_links_found_on_page(self):
        html = ('<a href="/assets/dynamic/GLD/GLD_US_archive_EN.xlsx">Download</a>'
                '<a href="/assets/dynamic/GLD/HSBC_bar_list.pdf">Bars</a>')
        self.assertEqual(etf_prices.archive_links(html, "https://www.spdrgoldshares.com/usa/gld/"),
                         ["https://www.spdrgoldshares.com/assets/dynamic/GLD/GLD_US_archive_EN.xlsx"])

    def test_archive_api_link_found_and_unescaped(self):
        html = '<a href="https://api.spdrgoldshares.com/api/v1/historical-archive?product=gld&amp;exchange=NYSE&amp;lang=en">XLSX</a>'
        self.assertEqual(etf_prices.archive_links(html, "https://www.spdrgoldshares.com/usa/gld/"),
                         ["https://api.spdrgoldshares.com/api/v1/historical-archive?product=gld&exchange=NYSE&lang=en"])

    def test_csv_bytes(self):
        self.assertEqual(len(etf_prices.parse_gld_payload(GLD.encode())), 2)


if __name__ == "__main__":
    unittest.main()
