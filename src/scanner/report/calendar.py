"""Seasonal calendar: when each qualifying window next opens and closes."""
from __future__ import annotations

import pandas as pd

from ..engine.windows import MONTHS


def _last_bday(period: pd.Period) -> pd.Timestamp:
    return pd.bdate_range(period.to_timestamp(how="start"), period.to_timestamp(how="end").normalize())[-1]


def next_dates(start_month: int, length: int, as_of: pd.Timestamp) -> tuple[pd.Timestamp, pd.Timestamp, str]:
    """(entry date, exit date, status) for the next or current occurrence of a window.

    Entry is the close of the last business day of the month before the window;
    exit is the close of the last business day of its last month. NGX holidays are
    not modelled, so treat dates as approximate.
    """
    as_of = pd.Timestamp(as_of).normalize()
    for year in (as_of.year - 1, as_of.year, as_of.year + 1):
        first = pd.Period(year=year, month=start_month, freq="M")
        entry, exit_ = _last_bday(first - 1), _last_bday(first + (length - 1))
        if as_of <= entry:
            return entry, exit_, "Upcoming"
        if entry < as_of <= exit_:
            return entry, exit_, "Open now"
    raise RuntimeError("unreachable")


def calendar_table(stats: pd.DataFrame, as_of: pd.Timestamp, classes=("Tier 1", "Tier 2", "Watch", "Negative")) -> pd.DataFrame:
    rows = []
    for _, s in stats[stats["class"].isin(classes)].iterrows():
        if s["length"] >= 12:
            continue
        entry, exit_, status = next_dates(int(s["start_month"]), int(s["length"]), as_of)
        rows.append({
            "Stock": s["ticker"],
            "Window": s["window"],
            "Class": s["class"],
            "Status": status,
            "Entry (close of)": entry.date(),
            "Exit (close of)": exit_.date(),
            "Days to entry": max((entry - pd.Timestamp(as_of).normalize()).days, 0),
            "Median": s["median"],
            "Years up": f"{int(s['up'])} / {int(s['n'])}",
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["Status", "Days to entry"], ascending=[True, True]).reset_index(drop=True)
    return df


def month_strip(stats: pd.DataFrame, classes=("Tier 1", "Tier 2", "Watch", "Negative")) -> pd.DataFrame:
    """Matrix of qualifying windows (rows) by calendar month (columns), marking months the window covers."""
    rows = {}
    for _, s in stats[stats["class"].isin(classes)].iterrows():
        if s["length"] >= 12:
            continue
        covered = [((int(s["start_month"]) - 1 + i) % 12) for i in range(int(s["length"]))]
        mark = "+" if s["class"] != "Negative" else "-"
        label = f"{s['ticker']} {s['window']} ({s['class']})"
        rows[label] = [mark if i in covered else "" for i in range(12)]
    return pd.DataFrame.from_dict(rows, orient="index", columns=MONTHS)
