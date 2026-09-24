"""Offline tests for the CFTC Commitments of Traders fetcher.

Fixtures are trimmed copies of live COMEX gold rows (market 088691) read from
publicreporting.cftc.gov on 2026-09-24, field names and CFTC typos intact.
The HTTP layer is replaced with a fake, so no network is touched.

Run:  python -m unittest discover tests
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from signals import cftc_cot, common

LEGACY_GOLD = {
    "id": "260915088691F",
    "market_and_exchange_names": "GOLD - COMMODITY EXCHANGE INC.",
    "report_date_as_yyyy_mm_dd": "2026-09-15T00:00:00.000",
    "contract_market_name": "GOLD",
    "cftc_contract_market_code": "088691",
    "cftc_commodity_code": "088 ",
    "open_interest_all": "409899",
    "noncomm_positions_long_all": "258059",
    "noncomm_positions_short_all": "27721",
    "noncomm_postions_spread_all": "47963",
    "comm_positions_long_all": "56417",
    "comm_positions_short_all": "318138",
    "nonrept_positions_long_all": "47460",
    "nonrept_positions_short_all": "16077",
}

DISAGG_GOLD = {
    "id": "260825088691F",
    "market_and_exchange_names": "GOLD - COMMODITY EXCHANGE INC.",
    "report_date_as_yyyy_mm_dd": "2026-08-25T00:00:00.000",
    "cftc_contract_market_code": "088691",
    "open_interest_all": "427957",
    "prod_merc_positions_long": "16861",
    "prod_merc_positions_short": "51419",
    "swap_positions_long_all": "16656",
    "swap__positions_short_all": "261683",
    "swap__positions_spread_all": "28936",
    "m_money_positions_long_all": "159819",
    "m_money_positions_short_all": "15072",
    "m_money_positions_spread": "16251",
    "other_rept_positions_long": "117340",
    "other_rept_positions_short": "18753",
    "other_rept_positions_spread": "17369",
    "nonrept_positions_long_all": "54725",
    "nonrept_positions_short_all": "18474",
}


# E-mini S&P 500, TFF futures only, 2026-08-11 (market 13874A).
TFF_ES = {
    "id": "26081113874AF",
    "market_and_exchange_names": "E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE",
    "report_date_as_yyyy_mm_dd": "2026-08-11T00:00:00.000",
    "contract_market_name": "E-MINI S&P 500",
    "cftc_contract_market_code": "13874A",
    "open_interest_all": "2119506",
    "dealer_positions_long_all": "216163",
    "dealer_positions_short_all": "995795",
    "dealer_positions_spread_all": "61405",
    "asset_mgr_positions_long": "1154700",
    "asset_mgr_positions_short": "206219",
    "asset_mgr_positions_spread": "95003",
    "lev_money_positions_long": "205744",
    "lev_money_positions_short": "486190",
    "lev_money_positions_spread": "61420",
    "other_rept_positions_long": "52037",
    "other_rept_positions_short": "71600",
    "other_rept_positions_spread": "471",
    "nonrept_positions_long_all": "272563",
    "nonrept_positions_short_all": "141403",
}


class FakeResponse:
    def __init__(self, status: int, payload):
        self.status_code = status
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


class QueryBuildingTests(unittest.TestCase):
    def test_filters_on_market_code_not_padded_commodity_code(self):
        soql = cftc_cot.build_query(["088691"], since="2024-01-01", limit=10)
        self.assertEqual(
            soql,
            "SELECT * WHERE cftc_contract_market_code IN ('088691') AND "
            "report_date_as_yyyy_mm_dd >= '2024-01-01T00:00:00' "
            "ORDER BY report_date_as_yyyy_mm_dd DESC, id LIMIT 10")
        self.assertNotIn("cftc_commodity_code", soql)

    def test_literals_are_escaped(self):
        self.assertEqual(cftc_cot.soql_literal("O'Neil"), "'O''Neil'")
        soql = cftc_cot.build_query(["x') OR ('1'='1"])
        self.assertIn("'x'') OR (''1''=''1'", soql)

    def test_requires_a_market(self):
        with self.assertRaises(ValueError):
            cftc_cot.build_query([])


class NormalizeTests(unittest.TestCase):
    def test_legacy_groups_and_net(self):
        rows = cftc_cot.normalize("legacy_fut", [LEGACY_GOLD], "2026-09-24")
        by_group = {r["trader_group"]: r for r in rows}
        self.assertEqual(set(by_group), {"noncommercial", "commercial", "nonreportable"})
        spec = by_group["noncommercial"]
        self.assertEqual(spec["report_date"], "2026-09-15")
        self.assertEqual((spec["long"], spec["short"], spec["spread"]),
                         ("258059", "27721", "47963"))
        self.assertEqual(spec["net"], str(258059 - 27721))
        self.assertEqual(spec["open_interest"], "409899")
        self.assertEqual(by_group["commercial"]["spread"], "")

    def test_disaggregated_managed_money(self):
        rows = cftc_cot.normalize("disagg_fut", [DISAGG_GOLD], "2026-09-24")
        mm = next(r for r in rows if r["trader_group"] == "managed_money")
        self.assertEqual((mm["long"], mm["short"], mm["net"]),
                         ("159819", "15072", str(159819 - 15072)))
        swap = next(r for r in rows if r["trader_group"] == "swap_dealer")
        self.assertEqual(swap["short"], "261683")  # the double-underscore field
        self.assertEqual(len(rows), 5)

    def test_missing_field_skips_group_instead_of_zero(self):
        rec = dict(DISAGG_GOLD)
        del rec["m_money_positions_short_all"]
        rows = cftc_cot.normalize("disagg_fut", [rec], "2026-09-24")
        self.assertNotIn("managed_money", {r["trader_group"] for r in rows})

    def test_tff_asset_manager_and_leveraged_money(self):
        rows = cftc_cot.normalize("tff_fut", [TFF_ES], "2026-09-24")
        by_group = {r["trader_group"]: r for r in rows}
        self.assertEqual(set(by_group), {"dealer", "asset_manager", "leveraged_money",
                                         "other_reportable", "nonreportable"})
        am = by_group["asset_manager"]
        self.assertEqual((am["long"], am["short"], am["net"]),
                         ("1154700", "206219", str(1154700 - 206219)))
        lev = by_group["leveraged_money"]
        self.assertEqual(lev["net"], str(205744 - 486190))

    def test_tff_fields_with_all_suffix_do_not_exist(self):
        # The "_all" suffix appears on dealer fields only; a mapping that
        # assumed it everywhere would silently drop these groups.
        self.assertNotIn("asset_mgr_positions_long_all", TFF_ES)
        self.assertNotIn("lev_money_positions_long_all", TFF_ES)

    def test_unmapped_family_yields_nothing(self):
        self.assertEqual(cftc_cot.normalize("legacy_combined", [], "x"), [])
        self.assertEqual(cftc_cot.normalize("unknown_fut", [DISAGG_GOLD], "x"), [])


class FlowsTests(unittest.TestCase):
    WATCH = {"tff_fut": {"13874A": "E-mini S&P 500"}}

    @staticmethod
    def _row(date, net, oi="1000", code="13874A", report="tff_fut"):
        return {"report": report, "market_code": code, "trader_group": "asset_manager",
                "report_date": date, "long": "", "short": "", "net": str(net),
                "open_interest": oi}

    def test_week_over_week_change(self):
        rows = [self._row("2026-09-08", 500), self._row("2026-09-01", 400),
                self._row("2026-09-15", 450)]
        flows = cftc_cot.compute_flows(rows, self.WATCH)
        self.assertEqual([f["report_date"] for f in flows],
                         ["2026-09-01", "2026-09-08", "2026-09-15"])
        self.assertEqual([f["net_change"] for f in flows], ["", "100", "-50"])
        self.assertEqual(flows[2]["net_pct_oi"], "45.0")
        self.assertEqual(flows[0]["label"], "E-mini S&P 500")

    def test_no_change_across_a_missing_week(self):
        rows = [self._row("2026-09-01", 400), self._row("2026-09-15", 450)]
        flows = cftc_cot.compute_flows(rows, self.WATCH)
        self.assertEqual(flows[1]["net_change"], "")

    def test_unwatched_markets_are_left_out(self):
        rows = [self._row("2026-09-01", 1, code="088691", report="disagg_fut")]
        self.assertEqual(cftc_cot.compute_flows(rows, self.WATCH), [])

    def test_config_watch_uses_verified_codes(self):
        watch = cftc_cot.watch_list()
        self.assertEqual(set(watch["tff_fut"]), {"13874A", "209742", "098662"})
        self.assertEqual(set(watch["disagg_fut"]), {"088691", "067651"})


class TransportTests(unittest.TestCase):
    def _run(self, responses, token="", **kwargs):
        calls = []

        def fake_request(method, url, **kw):
            calls.append((method, url, kw))
            return responses.pop(0)

        with mock.patch.object(common.requests, "request", side_effect=fake_request), \
                mock.patch.object(common.time, "sleep"):
            result = cftc_cot.run_query("legacy_fut", "SELECT *", token=token, **kwargs)
        return result, calls

    def test_keyless_goes_to_soda2_get(self):
        (rows, route), calls = self._run([FakeResponse(200, [LEGACY_GOLD])])
        self.assertEqual(route, "soda2")
        method, url, kw = calls[0]
        self.assertEqual(method, "GET")
        self.assertTrue(url.endswith("/resource/6dca-aqww.json"))
        self.assertEqual(kw["params"], {"$query": "SELECT *"})
        self.assertNotIn("X-App-Token", kw["headers"])

    def test_token_goes_to_soda3_post(self):
        (rows, route), calls = self._run([FakeResponse(200, [LEGACY_GOLD])], token="abc")
        method, url, kw = calls[0]
        self.assertEqual((route, method), ("soda3", "POST"))
        self.assertTrue(url.endswith("/api/v3/views/6dca-aqww/query.json"))
        self.assertEqual(kw["json"], {"query": "SELECT *", "includeSynthetic": False})
        self.assertEqual(kw["headers"]["X-App-Token"], "abc")

    def test_refusal_falls_back_to_other_route(self):
        (rows, route), calls = self._run(
            [FakeResponse(403, {"message": "app token required"}),
             FakeResponse(200, [LEGACY_GOLD])], token="bad")
        self.assertEqual(route, "soda2")
        self.assertEqual([c[0] for c in calls], ["POST", "GET"])
        self.assertEqual(len(calls), 2)  # a 403 is not retried

    def test_bad_query_raises_without_fallback(self):
        with self.assertRaises(common.HTTPStatusError):
            self._run([FakeResponse(400, {"message": "no such column"})])

    def test_error_envelope_is_not_read_as_zero_rows(self):
        with self.assertRaises(RuntimeError):
            self._run([FakeResponse(200, {"error": True}),
                       FakeResponse(200, {"error": True})])

    def test_pagination_stops_on_short_page(self):
        with mock.patch.object(cftc_cot, "_load_config") as cfg:
            real = cftc_cot.json.loads(
                (cftc_cot.CONFIG_DIR / "cftc_endpoints.json").read_text("utf-8"))
            real["page_size"] = 2
            cfg.return_value = real
            (rows, _), calls = self._run(
                [FakeResponse(200, [LEGACY_GOLD, LEGACY_GOLD]),
                 FakeResponse(200, [LEGACY_GOLD])], paginate=True)
        self.assertEqual(len(rows), 3)
        self.assertEqual([c[2]["params"]["$query"] for c in calls],
                         ["SELECT * LIMIT 2 OFFSET 0", "SELECT * LIMIT 2 OFFSET 2"])


if __name__ == "__main__":
    unittest.main()
