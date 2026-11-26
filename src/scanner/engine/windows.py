"""Calendar windows and window returns (docs/SCOPE.md 8.1 and 8.2)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


@dataclass(frozen=True)
class Window:
    start_month: int  # 1..12
    length: int  # months

    @property
    def name(self) -> str:
        if self.length == 12 and self.start_month == 1:
            return "Full year"
        if self.length == 1:
            return MONTHS[self.start_month - 1]
        end = (self.start_month + self.length - 2) % 12
        return f"{MONTHS[self.start_month - 1]}-{MONTHS[end]}"

    @property
    def kind(self) -> str:
        return {1: "Single month", 2: "Rolling 2-month", 3: "Rolling 3-month"}.get(self.length, "Full year")

    @property
    def is_quarter(self) -> bool:
        return self.length == 3 and self.start_month in (1, 4, 7, 10)

    def months(self) -> list[int]:
        return [((self.start_month - 1 + i) % 12) + 1 for i in range(self.length)]

    def periods(self, year: int) -> tuple[pd.Period, pd.Period, pd.Period]:
        """(entry month, first month, last month) for the window starting in `year`."""
        first = pd.Period(year=year, month=self.start_month, freq="M")
        return first - 1, first, first + (self.length - 1)


def standard_windows(single_month=True, rolling_2_month=True, rolling_3_month=True, full_year=True) -> list[Window]:
    out: list[Window] = []
    if single_month:
        out += [Window(m, 1) for m in range(1, 13)]
    if rolling_2_month:
        out += [Window(m, 2) for m in range(1, 13)]
    if rolling_3_month:
        out += [Window(m, 3) for m in range(1, 13)]
    if full_year:
        out.append(Window(1, 12))
    return out


def windows_from_config(cfg: dict) -> list[Window]:
    return standard_windows(**cfg["windows"])


def month_end_prices(series: pd.Series) -> pd.Series:
    """Last available close in each calendar month, indexed by monthly Period."""
    return series.groupby(series.index.to_period("M")).last()


def last_complete_month(last_date: pd.Timestamp) -> pd.Period:
    """The latest month whose month-end close is final.

    A month counts as complete only if the data reaches its last business day.
    Example: data ending Fri 19 Dec 2025 means November 2025 is the last complete month.
    """
    last_date = pd.Timestamp(last_date).normalize()
    month = last_date.to_period("M")
    last_bday = pd.bdate_range(month.to_timestamp(how="start"), month.to_timestamp(how="end").normalize())[-1]
    return month if last_date >= last_bday else month - 1


def window_returns(
    series: pd.Series,
    window: Window,
    last_complete: pd.Period | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
) -> pd.DataFrame:
    """One row per complete window-year.

    Columns: year, entry_date, entry_price, exit_date, exit_price, ret, dip.
    ret = exit month-end close / entry month-end close - 1, where entry is the
    month before the window starts. dip = lowest daily close inside the window
    divided by the entry close, minus 1. Years are labelled by window start.
    """
    cols = ["year", "entry_date", "entry_price", "exit_date", "exit_price", "ret", "dip"]
    if series.empty:
        return pd.DataFrame(columns=cols)
    if last_complete is None:
        last_complete = last_complete_month(series.index[-1])
    periods = series.index.to_period("M")
    grouped = series.groupby(periods)
    me_price, me_date = grouped.last(), grouped.apply(lambda s: s.index[-1])

    rows = []
    first_year = periods[0].year
    for year in range(first_year, last_complete.year + 1):
        if start_year is not None and year < start_year:
            continue
        if end_year is not None and year > end_year:
            continue
        entry, first, last = window.periods(year)
        if last > last_complete or entry not in me_price.index or last not in me_price.index:
            continue
        p0, p1 = float(me_price[entry]), float(me_price[last])
        inside = series[(periods >= first) & (periods <= last)]
        dip = float(inside.min() / p0 - 1) if len(inside) else np.nan
        rows.append((year, me_date[entry], p0, me_date[last], p1, p1 / p0 - 1, dip))
    return pd.DataFrame(rows, columns=cols)
