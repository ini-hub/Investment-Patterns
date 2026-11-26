"""Benchmarks (docs/SCOPE.md 8.4)."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import trim_mean

from .windows import Window, last_complete_month, month_end_prices, window_returns


class MarketBenchmark:
    """Trimmed mean of all stocks' window returns for each window and year.

    A plain median is not used because most NGX stocks show 0% in many months.
    """

    kind = "market"

    def __init__(self, universe: dict[str, pd.Series], min_stocks: int = 30, trim: float = 0.10):
        self.min_stocks = min_stocks
        self.trim = trim
        self.n_stocks = len(universe)
        last_date = max(s.index[-1] for s in universe.values())
        self.last_complete = last_complete_month(last_date)
        self._me = pd.DataFrame({t: month_end_prices(s) for t, s in universe.items()}).sort_index()
        self._cache: dict[Window, dict[int, float]] = {}
        self.description = (
            f"{int(trim * 100)}% trimmed mean of {self.n_stocks} stocks "
            f"(needs at least {min_stocks} stocks with data for a window-year)"
        )

    @property
    def available(self) -> bool:
        return self.n_stocks >= self.min_stocks

    def values(self, window: Window) -> dict[int, float]:
        if window in self._cache:
            return self._cache[window]
        out: dict[int, float] = {}
        me = self._me
        for year in range(me.index[0].year, self.last_complete.year + 1):
            entry, _, last = window.periods(year)
            if last > self.last_complete or entry not in me.index or last not in me.index:
                continue
            r = (me.loc[last] / me.loc[entry] - 1).dropna()
            if len(r) >= self.min_stocks:
                out[year] = float(trim_mean(r.values, self.trim))
        self._cache[window] = out
        return out


class IndexBenchmark:
    """Benchmark from a single index series, for example the NGX All-Share Index."""

    kind = "index"

    def __init__(self, series: pd.Series, name: str = "Index"):
        self.series = series
        self.name = name
        self.available = len(series) > 0
        self.last_complete = last_complete_month(series.index[-1]) if self.available else None
        self.description = f"{name} (single index series)"
        self._cache: dict[Window, dict[int, float]] = {}

    def values(self, window: Window) -> dict[int, float]:
        if window not in self._cache:
            df = window_returns(self.series, window, self.last_complete)
            self._cache[window] = dict(zip(df["year"], df["ret"], strict=True))
        return self._cache[window]


def own_average(series: pd.Series, windows: list[Window], last_complete: pd.Period) -> dict[tuple[int, int], float]:
    """{(length, year): mean return of the stock's 12 rolling windows of that length in that year}.

    Removes the stock's own trend: a stock that rose every month is not seasonal.
    """
    lengths = sorted({w.length for w in windows if w.length < 12})
    acc: dict[tuple[int, int], list[float]] = {}
    for length in lengths:
        for m in range(1, 13):
            df = window_returns(series, Window(m, length), last_complete)
            for y, r in zip(df["year"], df["ret"], strict=True):
                acc.setdefault((length, int(y)), []).append(float(r))
    return {k: float(np.mean(v)) for k, v in acc.items()}
