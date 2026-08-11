"""PIT packet builder tests against a synthetic Sharadar DuckDB.

The two properties that make the tool valid at all: nothing dated after the
cutoff appears in the packet, and a masked packet carries no identity.
"""

import duckdb
import pytest

from validation.pit_packet import build_packet

CUTOFF = "2025-11-01"
# Values chosen to be greppable: each appears nowhere else.
PRE_REVENUE = 94100000000        # filed before cutoff -> must appear
POST_REVENUE = 77700000000       # filed after cutoff -> must never appear


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "sharadar.duckdb")
    con = duckdb.connect(path)
    con.execute("""
        CREATE TABLE sf1 (ticker VARCHAR, dimension VARCHAR, datekey DATE,
            reportperiod DATE, revenue BIGINT, netinc BIGINT,
            grossmargin DOUBLE, lastupdated DATE);
        CREATE TABLE tickers ("table" VARCHAR, ticker VARCHAR, name VARCHAR,
            exchange VARCHAR, sector VARCHAR, industry VARCHAR,
            location VARCHAR, scalemarketcap VARCHAR, firstpricedate DATE);
        CREATE TABLE daily (ticker VARCHAR, date DATE, marketcap DOUBLE,
            ev DOUBLE, pe DOUBLE, pb DOUBLE);
        CREATE TABLE sep (ticker VARCHAR, date DATE, closeadj DOUBLE);
        CREATE TABLE sf2 (ticker VARCHAR, filingdate DATE,
            transactioncode VARCHAR, transactionvalue DOUBLE);
    """)
    con.execute("INSERT INTO sf1 VALUES "
                f"('AAPL','ARQ','2025-08-01','2025-06-30',{PRE_REVENUE},23000000000,0.46,'2025-08-01'),"
                f"('AAPL','ARQ','2026-01-30','2025-12-31',{POST_REVENUE},31000000000,0.47,'2026-01-30'),"
                # Different dimension must be excluded even when pre-cutoff.
                f"('AAPL','MRY','2025-08-01','2025-06-30',1234500000,1,0.4,'2025-08-01')")
    con.execute("INSERT INTO tickers VALUES "
                "('SF1','AAPL','Apple Inc','NASDAQ','Technology',"
                "'Consumer Electronics','California; U.S.A','6 - Mega','1986-01-01')")
    con.execute("INSERT INTO daily VALUES "
                "('AAPL','2025-10-31',3400000.0,3500000.0,34.5,52.1),"   # pre-cutoff
                "('AAPL','2025-12-31',9999999.0,9999999.0,99.9,99.9)")   # post-cutoff
    con.execute("INSERT INTO sep VALUES "
                "('AAPL','2025-10-31',255.31),('AAPL','2025-12-30',311.11)")
    con.execute("INSERT INTO sf2 VALUES "
                "('AAPL','2025-06-15','S',12000000.0),"
                "('AAPL','2025-12-15','P',88000000.0)")   # post-cutoff filing
    con.close()
    return path


def test_no_post_cutoff_data_leaks(db_path):
    packet, _ = build_packet(db_path, ["AAPL"], CUTOFF, masked=False)
    assert "2025-06-30" in packet                 # pre-cutoff quarter present
    assert str(POST_REVENUE) not in packet
    assert "2026" not in packet                   # no post-cutoff dates at all
    assert "99.9" not in packet                   # post-cutoff valuation row
    assert "311.11" not in packet                 # post-cutoff price
    assert "buys" not in packet.lower()           # post-cutoff insider filing
    assert "34.5" in packet                       # pre-cutoff P/E present


def test_masked_packet_carries_no_identity(db_path):
    packet, key = build_packet(db_path, ["AAPL"], CUTOFF, masked=True)
    for leak in ["AAPL", "Apple", "NASDAQ", "Consumer Electronics", "California"]:
        assert leak not in packet
    assert "Company A" in packet
    assert "Adj close" not in packet              # no price history when masked
    # Coarsened revenue: 94.1B -> 94B; the exact raw digits must be gone.
    assert "$94B" in packet
    assert "94.1" not in packet
    # The key maps the label back to the ticker, for the scorer only.
    assert "Company A" in key and "AAPL" in key


def test_unmasked_dimension_filter_and_prices(db_path):
    packet, _ = build_packet(db_path, ["AAPL"], CUTOFF, masked=False)
    assert "$94.1B" in packet                     # exact figure when unmasked
    assert "1.2345" not in packet                 # MRY dimension row excluded
    assert "255.31" in packet                     # pre-cutoff price included
    assert "Apple Inc" in packet


def test_unknown_ticker_fails_clearly(db_path):
    with pytest.raises(SystemExit, match="not found"):
        build_packet(db_path, ["NOPE"], CUTOFF)


def test_label_count_mismatch(db_path):
    with pytest.raises(ValueError, match="labels"):
        build_packet(db_path, ["AAPL"], CUTOFF, labels=["A", "B"])
