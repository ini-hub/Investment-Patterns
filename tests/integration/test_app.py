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
