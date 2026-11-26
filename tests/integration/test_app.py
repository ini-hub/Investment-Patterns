"""Smoke tests for the web app: each screen renders without errors (docs/SCOPE.md 11.1, integration).

Needs the NairaDB snapshot, like the regression suite.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

pytestmark = pytest.mark.regression
APP = str(Path(__file__).resolve().parents[2] / "app" / "streamlit_app.py")


def _text(at) -> str:
    return "\n".join(m.value for m in at.markdown)


def _start(universe, tickers, mode):
    at = AppTest.from_file(APP, default_timeout=300)
    at.session_state["w_s_runs"] = 20  # keep the chance check quick
    at.session_state["w_mode"] = mode
    at.session_state["w_tickers"] = tickers
    at.run()
    assert not at.exception, at.exception
    return at


def _click(at, label):
    [button] = [b for b in at.button if b.label == label]
    button.click().run()
    assert not at.exception, at.exception


def test_scan_screen_renders(universe):
    at = _start(universe, ["FCMB"], "Single report")
    assert "Scan stocks for seasonal patterns" in _text(at)
    assert [b.label for b in at.button if b.label == "Run scan"]


def test_single_stock_results(universe):
    at = _start(universe, ["FCMB"], "Single report")
    _click(at, "Run scan")
    text = _text(at)
    assert "FCMB" in text and "FCMB Group Plc" in text
    assert "Oct-Dec, Jan, Dec-Jan" in text  # FCMB's Tier 1 windows (Appendix A.2)
    labels = [t.label for t in at.tabs]
    assert labels[0].startswith("Patterns (") and labels[1].startswith("Exit or avoid (")


def test_compare_screen(universe):
    at = _start(universe, ["FCMB", "VITAFOAM"], "Compare")
    _click(at, "Compare 2 stocks")
    text = _text(at)
    assert "Comparing 2 stocks" in text
    assert "Window by window" in [s.value for s in at.subheader]


def test_unknown_ticker_message(universe):
    at = _start(universe, ["NOTREAL"], "Single report")
    _click(at, "Run scan")
    assert "No price data found for NOTREAL" in [e.value for e in at.error]


MANY = ["FCMB", "VITAFOAM", "ETI", "IKEJAHOTEL", "LEARNAFRCA", "CONOIL", "CWG", "FTNCOCOA"]


def _stock_table(at):
    [table] = [d for d in at.dataframe if "Stock" in d.value.columns and "Tier 1" in d.value.columns]
    return table.value


def test_compare_many_uses_tables_and_filters(universe):
    at = _start(universe, MANY, "Compare")
    _click(at, f"Compare {len(MANY)} stocks")
    assert f"Comparing {len(MANY)} stocks" in _text(at)
    assert set(_stock_table(at)["Stock"]) == set(MANY)  # above 6 stocks: a table, not cards
    assert "Ranked patterns" in [s.value for s in at.subheader]
    [ranked] = [d.value for d in at.dataframe if "Window" in d.value.columns]
    assert len(ranked) > 0 and set(ranked["Class"]) <= {"Tier 1", "Tier 2", "Watch", "Emerging"}

    at.session_state["w_cmp_filters"] = ["Exclude frozen price"]
    at.run()
    assert not at.exception, at.exception
    text = _text(at)
    assert "Showing 6 of 8 stocks." in text  # CWG and FTNCOCOA are frozen (Appendix A.5)
    assert ">CWG<" not in text and ">FTNCOCOA<" not in text  # back to cards, without the frozen stocks
    assert "Window by window" in [s.value for s in at.subheader]

    at.session_state["w_cmp_filters"] = ["Exclude frozen price", "Exclude no rising pattern"]
    at.session_state["w_cmp_sort"] = "Ticker A to Z"
    at.run()
    assert not at.exception, at.exception
    assert "Showing 6 of 8 stocks." in _text(at)  # all six remaining have a rising pattern
