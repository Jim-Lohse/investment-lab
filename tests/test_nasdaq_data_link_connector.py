"""Connector tests with a mocked Nasdaq Data Link export endpoint.

The mock serves zipped CSVs the way ``export_table`` does, honoring the
``lastupdated={'gte': ...}`` filter, so bulk load, incremental upsert,
schema drift, replace-strategy tables, and status all run without a key.
"""

import csv
import io
import zipfile

import duckdb
import pytest

from connectors.nasdaq_data_link import config, connector
from connectors.nasdaq_data_link.config import TABLES, resolve_tables

SF1 = TABLES["sf1"]
ACTIONS = TABLES["actions"]

BULK_ROWS = [
    # ticker, dimension, datekey, reportperiod, revenue, lastupdated
    {"ticker": "AAPL", "dimension": "ARQ", "datekey": "2026-05-01",
     "reportperiod": "2026-03-31", "revenue": "100", "lastupdated": "2026-05-01"},
    {"ticker": "MSFT", "dimension": "ARQ", "datekey": "2026-04-25",
     "reportperiod": "2026-03-31", "revenue": "200", "lastupdated": "2026-04-25"},
    {"ticker": "DLST", "dimension": "ARQ", "datekey": "2026-02-10",
     "reportperiod": "2025-12-31", "revenue": "50", "lastupdated": "2026-02-10"},
]

# One amendment (AAPL revenue restated) and one new filing, both stamped later.
# The datatable holds one current row per key, so the amended AAPL row
# replaces the original in the table state served by the fake.
INCREMENTAL_ROWS = [
    {"ticker": "AAPL", "dimension": "ARQ", "datekey": "2026-05-01",
     "reportperiod": "2026-03-31", "revenue": "110", "lastupdated": "2026-08-01"},
    {"ticker": "NVDA", "dimension": "ARQ", "datekey": "2026-07-30",
     "reportperiod": "2026-06-30", "revenue": "300", "lastupdated": "2026-08-01"},
]

UPDATED_TABLE = [r for r in BULK_ROWS if r["ticker"] != "AAPL"] + INCREMENTAL_ROWS


class FakeExporter:
    """Stands in for nasdaqdatalink.export_table."""

    def __init__(self, rows_by_code):
        self.rows_by_code = rows_by_code
        self.calls = []

    def __call__(self, code, filename=None, **filters):
        self.calls.append((code, filters))
        rows = self.rows_by_code[code]
        if "lastupdated" in filters:
            gte = filters["lastupdated"]["gte"]
            rows = [r for r in rows if r["lastupdated"] >= gte]
        fields = list(rows[0].keys()) if rows else ["ticker", "lastupdated"]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        with zipfile.ZipFile(filename, "w") as zf:
            zf.writestr(f"{code.split('/')[-1]}.csv", buf.getvalue())


@pytest.fixture
def db_path(tmp_path):
    # Named to match the default DB file: catalog "sharadar" must never
    # collide with table references (regression for the schema/catalog
    # ambiguity DuckDB raised when a schema shared the catalog's name).
    return str(tmp_path / "sharadar.duckdb")


def install_exporter(monkeypatch, rows_by_code):
    exporter = FakeExporter(rows_by_code)
    monkeypatch.setattr(connector, "fetch_csvs", connector.fetch_csvs)
    import nasdaqdatalink

    monkeypatch.setattr(nasdaqdatalink, "export_table", exporter)
    return exporter


def test_bulk_then_incremental_upsert(monkeypatch, db_path):
    exporter = install_exporter(monkeypatch, {"SHARADAR/SF1": list(BULK_ROWS)})

    con = connector.connect(db_path)
    mode, rows = connector.sync_table(con, SF1)
    assert (mode, rows) == ("full", 3)
    assert exporter.calls[-1] == ("SHARADAR/SF1", {})

    exporter.rows_by_code["SHARADAR/SF1"] = UPDATED_TABLE
    mode, rows = connector.sync_table(con, SF1)
    assert mode == "incremental"
    # Filter must start at the stored watermark (max lastupdated = 2026-05-01).
    assert exporter.calls[-1] == ("SHARADAR/SF1", {"lastupdated": {"gte": "2026-05-01"}})
    assert rows == 2

    data = dict(
        con.execute('SELECT ticker, revenue FROM sf1').fetchall()
    )
    assert data == {"AAPL": 110, "MSFT": 200, "DLST": 50, "NVDA": 300}
    assert con.execute('SELECT count(*) FROM sf1').fetchone()[0] == 4
    con.close()


def test_incremental_with_no_changes(monkeypatch, db_path):
    exporter = install_exporter(monkeypatch, {"SHARADAR/SF1": list(BULK_ROWS)})
    con = connector.connect(db_path)
    connector.sync_table(con, SF1)

    exporter.rows_by_code["SHARADAR/SF1"] = [
        r for r in BULK_ROWS if r["lastupdated"] < "2026-05-01"
    ]
    mode, rows = connector.sync_table(con, SF1)
    assert (mode, rows) == ("incremental", 0)
    assert con.execute('SELECT count(*) FROM sf1').fetchone()[0] == 3
    con.close()


def test_incremental_handles_new_vendor_column(monkeypatch, db_path):
    exporter = install_exporter(monkeypatch, {"SHARADAR/SF1": list(BULK_ROWS)})
    con = connector.connect(db_path)
    connector.sync_table(con, SF1)

    widened = [dict(r, fxusd="1.0") for r in INCREMENTAL_ROWS]
    exporter.rows_by_code["SHARADAR/SF1"] = (
        [r for r in BULK_ROWS if r["ticker"] != "AAPL"] + widened
    )
    connector.sync_table(con, SF1)

    rows = dict(con.execute('SELECT ticker, fxusd FROM sf1').fetchall())
    assert rows["NVDA"] == 1.0
    assert rows["MSFT"] is None  # pre-existing rows null for the new column
    con.close()


def test_replace_strategy_always_reloads(monkeypatch, db_path):
    actions_v1 = [{"date": "2026-01-05", "action": "split", "ticker": "AAPL"}]
    actions_v2 = [
        {"date": "2026-01-05", "action": "split", "ticker": "AAPL"},
        {"date": "2026-08-01", "action": "delisted", "ticker": "DLST"},
    ]
    exporter = install_exporter(monkeypatch, {"SHARADAR/ACTIONS": actions_v1})
    con = connector.connect(db_path)
    assert connector.sync_table(con, ACTIONS) == ("full", 1)

    exporter.rows_by_code["SHARADAR/ACTIONS"] = actions_v2
    assert connector.sync_table(con, ACTIONS) == ("full", 2)
    # replace tables never send a lastupdated filter
    assert all(filters == {} for _, filters in exporter.calls)
    con.close()


def test_full_flag_forces_reexport(monkeypatch, db_path):
    exporter = install_exporter(monkeypatch, {"SHARADAR/SF1": list(BULK_ROWS)})
    con = connector.connect(db_path)
    connector.sync_table(con, SF1)
    mode, _ = connector.sync_table(con, SF1, full=True)
    assert mode == "full"
    assert exporter.calls[-1] == ("SHARADAR/SF1", {})
    con.close()


def test_status_reports_watermark_and_history(monkeypatch, db_path):
    install_exporter(monkeypatch, {"SHARADAR/SF1": list(BULK_ROWS)})
    con = connector.connect(db_path)
    connector.sync_table(con, SF1)
    con.close()

    (report,) = connector.status(db_path)
    assert report["table"] == "sf1"
    assert report["rows"] == 3
    assert report["watermark"] == "2026-05-01"
    assert report["last_mode"] == "full"


def test_resolve_tables_presets_and_errors():
    assert [s.name for s in resolve_tables("bundle")] == config.PRESETS["bundle"]
    assert [s.name for s in resolve_tables("sf1, sep")] == ["sf1", "sep"]
    with pytest.raises(ValueError, match="Unknown table"):
        resolve_tables("sf1,nope")
