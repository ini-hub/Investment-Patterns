import io

import pandas as pd
import pytest

from scanner.data import CSVFormatError, load_csv, ticker_from_filename


def as_file(text: str, name: str):
    f = io.BytesIO(text.encode("utf-8"))
    f.name = name
    return f


@pytest.mark.parametrize(
    "name, ticker",
    [
        ("NSENG_FCMB, 1D.csv", "FCMB"),
        ("fcmb.csv", "FCMB"),
        ("NSENG:VITAFOAM.csv", "VITAFOAM"),
        ("data/learnafrca.csv", "LEARNAFRCA"),
    ],
)
def test_ticker_from_filename(name, ticker):
    assert ticker_from_filename(name) == ticker


def test_tradingview_unix_seconds():
    text = "time,open,high,low,close,Volume\n1735776000,10,11,9,10.5,1000\n1735862400,10.5,11,10,10.8,2000\n"
    s, vol, rep = load_csv(as_file(text, "NSENG_FCMB, 1D.csv"))
    assert rep.ticker == "FCMB"
    assert s.index[0] == pd.Timestamp("2025-01-02") and s.iloc[-1] == 10.8
    assert vol.tolist() == [1000, 2000]


def test_iso_and_ddmmyyyy_dates():
    s1, _, _ = load_csv(as_file("Date,Close\n2025-01-02,5\n2025-01-03,6\n", "x.csv"))
    s2, _, _ = load_csv(as_file("date,price\n02/01/2025,5\n03/01/2025,6\n", "x.csv"))
    assert s1.index.equals(s2.index)


def test_invalid_rows_rejected_and_duplicates_removed():
    text = "date,close\n2025-01-02,5\n2025-01-03,0\n2025-01-06,abc\n2025-01-07,7\n2025-01-07,8\n"
    s, _, rep = load_csv(as_file(text, "x.csv"))
    assert s.tolist() == [5.0, 8.0]
    assert len(rep.rejected) == 2 and rep.duplicates_removed == 1
    assert "invalid close" in rep.rejected[0]


def test_unsorted_input_is_sorted():
    s, _, _ = load_csv(as_file("date,close\n2025-01-07,7\n2025-01-02,5\n", "x.csv"))
    assert s.index.is_monotonic_increasing


def test_missing_columns_error():
    with pytest.raises(CSVFormatError):
        load_csv(as_file("day,value\n2025-01-02,5\n", "x.csv"))


def test_unreadable_dates_error():
    with pytest.raises(CSVFormatError):
        load_csv(as_file("date,close\nyesterday,5\n", "x.csv"))


def test_gap_reported():
    s, _, rep = load_csv(as_file("date,close\n2025-01-02,5\n2025-03-03,6\n", "x.csv"))
    assert len(rep.gaps) == 1 and "gap" in rep.summary()
