from scanner.data import company_name, load_securities, sector_groups
from tests.conftest import RESEARCH_TICKERS


def test_every_research_ticker_has_a_name_and_sector():
    sec = load_securities()
    for t in RESEARCH_TICKERS:
        assert sec.at[t, "name"] and sec.at[t, "sector"], t


def test_unknown_ticker_has_no_name():
    assert company_name("NOTREAL") == ""


def test_sector_groups_limited_to_available():
    groups = sector_groups(["FCMB", "ETI", "PZ"])
    assert groups == {"Consumer Goods": ["PZ"], "Financial Services": ["ETI", "FCMB"]}
