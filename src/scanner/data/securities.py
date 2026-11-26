"""Company names and sectors for display (hand-kept until Phase 2's securities table).

Tickers missing from securities.csv still scan normally; they just show without a name.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

_PATH = Path(__file__).with_name("securities.csv")


@lru_cache(maxsize=1)
def load_securities() -> pd.DataFrame:
    df = pd.read_csv(_PATH, dtype=str).fillna("")
    df["ticker"] = df["ticker"].str.strip().str.upper()
    return df.set_index("ticker")


def company_name(ticker: str) -> str:
    sec = load_securities()
    return sec.at[ticker, "name"] if ticker in sec.index else ""


def sector_groups(available: list[str] | None = None) -> dict[str, list[str]]:
    """{sector: [tickers]}, limited to `available` tickers when given."""
    sec = load_securities()
    if available is not None:
        sec = sec[sec.index.isin(available)]
    return {s: sorted(g.index) for s, g in sec.groupby("sector") if s}
