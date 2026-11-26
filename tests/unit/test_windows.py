import numpy as np
import pandas as pd
import pytest

from scanner.engine.windows import Window, last_complete_month, month_end_prices, standard_windows, window_returns
from tests.conftest import make_monthly_series


def test_standard_windows_count_and_names():
    ws = standard_windows()
    assert len(ws) == 37
    names = [w.name for w in ws]
    assert names[:3] == ["Jan", "Feb", "Mar"]
    assert "Dec-Jan" in names and "Nov-Jan" in names and "Dec-Feb" in names
    assert names[-1] == "Full year"
    assert len(set(names)) == 37


def test_quarters_are_flagged():
    quarters = [w.name for w in standard_windows() if w.is_quarter]
    assert quarters == ["Jan-Mar", "Apr-Jun", "Jul-Sep", "Oct-Dec"]


def test_window_selection_flags():
    assert len(standard_windows(rolling_2_month=False, full_year=False)) == 24


def test_periods_cross_year_end():
    entry, first, last = Window(11, 3).periods(2024)
    assert (str(entry), str(first), str(last)) == ("2024-10", "2024-11", "2025-01")
    assert Window(12, 2).months() == [12, 1]


@pytest.mark.parametrize("last_date, expected", [
    ("2025-12-19", "2025-11"),   # research dataset: December incomplete
    ("2025-12-31", "2025-12"),
    ("2025-10-31", "2025-10"),   # Friday, last business day
    ("2025-11-28", "2025-11"),   # Friday 28 Nov is the last business day of Nov 2025
    ("2025-11-27", "2025-10"),
])
def test_last_complete_month(last_date, expected):
    assert str(last_complete_month(pd.Timestamp(last_date))) == expected


def test_month_end_prices_takes_last_close():
    s = pd.Series([1.0, 2.0, 3.0], index=pd.to_datetime(["2024-01-02", "2024-01-31", "2024-02-01"]))
    me = month_end_prices(s)
    assert me[pd.Period("2024-01", "M")] == 2.0


def test_window_return_formula_dates_and_dip():
    s = make_monthly_series({"2020-09": 10, "2020-10": 8, "2020-11": 11, "2020-12": 12, "2021-01": 12})
    df = window_returns(s, Window(10, 3))
    row = df[df["year"] == 2020].iloc[0]
    assert row["entry_price"] == 10 and row["exit_price"] == 12
    assert row["ret"] == pytest.approx(0.2)
    assert row["dip"] == pytest.approx(-0.2)  # lowest close inside the window is 8
    assert pd.Timestamp(row["entry_date"]) == pd.Timestamp("2020-09-30")
    assert pd.Timestamp(row["exit_date"]) == pd.Timestamp("2020-12-31")


def test_cross_year_window_labelled_by_start_year():
    s = make_monthly_series({"2019-10": 3.5, "2019-11": 4, "2019-12": 4.5, "2020-01": 5.5})
    df = window_returns(s, Window(11, 3))
    assert df["year"].tolist() == [2019]
    assert df["ret"].iloc[0] == pytest.approx(5.5 / 3.5 - 1)


def test_incomplete_final_month_excluded():
    s = make_monthly_series({"2024-10": 1, "2024-11": 1, "2024-12": 1})
    s = s[s.index <= "2024-12-19"]
    assert window_returns(s, Window(12, 1)).empty
    assert len(window_returns(s, Window(11, 1))) == 1


def test_missing_month_skips_year():
    vals = {f"2020-{m:02d}": 10 + m for m in range(1, 13)}
    del vals["2020-05"]
    s = make_monthly_series(vals)
    assert 2020 not in window_returns(s, Window(5, 1))["year"].tolist()   # exit month missing
    assert 2020 not in window_returns(s, Window(6, 1))["year"].tolist()   # entry month missing
    assert 2020 in window_returns(s, Window(7, 1))["year"].tolist()


def test_lookback_limits():
    vals = {f"{y}-{m:02d}": 10 + m for y in range(2018, 2022) for m in range(1, 13)}
    s = make_monthly_series(vals)
    years = window_returns(s, Window(3, 1), start_year=2019, end_year=2020)["year"].tolist()
    assert years == [2019, 2020]


def test_empty_series():
    assert window_returns(pd.Series(dtype=float), Window(1, 1)).empty
    assert np.isnan(np.nan)
