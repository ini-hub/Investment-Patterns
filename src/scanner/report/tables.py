"""Display tables built from scan statistics."""
from __future__ import annotations

import pandas as pd

PATTERN_COLUMNS = {
    "ticker": "Stock",
    "window": "Window",
    "class": "Class",
    "up_n": "Years up",
    "streak": "Streak",
    "median": "Median",
    "worst": "Worst year",
    "best": "Best year",
    "std": "Std dev",
    "market_n": "Beat market",
    "own_n": "Beat own avg",
    "median_dip": "Median dip",
    "worst_dip": "Worst dip",
    "flags": "Flags",
    "note": "Note",
}

PCT = ["median", "worst", "best", "std", "median_dip", "worst_dip", "mean", "median_ex_market", "median_ex_own"]


def _ratio(a, b) -> str:
    if pd.isna(a) or pd.isna(b) or not b:
        return "n/a"
    return f"{int(a)} / {int(b)}"


def pattern_table(stats: pd.DataFrame, classes: list[str] | None = None, include_ticker: bool = False) -> pd.DataFrame:
    df = stats if classes is None else stats[stats["class"].isin(classes)]
    out = pd.DataFrame({
        "ticker": df["ticker"],
        "window": df["window"],
        "class": df["class"],
        "up_n": [_ratio(u, n) for u, n in zip(df["up"], df["n"])],
        "streak": df["streak"],
        "median": df["median"],
        "worst": df["worst"],
        "best": df["best"],
        "std": df["std"],
        "market_n": [_ratio(b, n) for b, n in zip(df["beat_market"], df["market_n"])],
        "own_n": [_ratio(b, n) for b, n in zip(df["beat_own"], df["own_n"])],
        "median_dip": df["median_dip"],
        "worst_dip": df["worst_dip"],
        "flags": df["flags"],
        "note": df["note"],
    })
    if not include_ticker:
        out = out.drop(columns="ticker")
    return out.rename(columns=PATTERN_COLUMNS).reset_index(drop=True)


def fmt_pct(x, digits: int = 1) -> str:
    return "n/a" if pd.isna(x) else f"{x:+.{digits}%}"


def year_detail(yearly: pd.DataFrame, window: str) -> pd.DataFrame:
    d = yearly[yearly["window"] == window].copy()
    return pd.DataFrame({
        "Year": d["year"],
        "Entry date": pd.to_datetime(d["entry_date"]).dt.date,
        "Entry close": d["entry_price"],
        "Exit date": pd.to_datetime(d["exit_date"]).dt.date,
        "Exit close": d["exit_price"],
        "Return": d["return"],
        "Dip inside window": d["dip"],
        "Market": d["market"],
        "Own average": d["own_average"],
    }).reset_index(drop=True)
