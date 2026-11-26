"""Permutation test for chance patterns (docs/SCOPE.md 8.5).

Monthly returns are shuffled within each calendar year. This keeps every year's
total trend and destroys any seasonal ordering. The number of windows passing the
candidate filter in real data is compared with the counts from shuffled data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .windows import month_end_prices


class _MonthlyGrid:
    """Monthly log returns laid out on a continuous month grid (NaN where missing)."""

    def __init__(self, series: pd.Series, last_complete: pd.Period, start_year=None, end_year=None):
        me = month_end_prices(series)
        me = me[me.index <= last_complete]
        self.start = me.index[0] + 1
        self.periods = pd.period_range(self.start, last_complete, freq="M")
        full = me.reindex(pd.period_range(me.index[0], last_complete, freq="M"))
        lr = np.log(full).diff().to_numpy()[1:]
        self.lr = lr
        self.years = np.array([p.year for p in self.periods])
        self.months = np.array([p.month for p in self.periods])
        self.start_year, self.end_year = start_year, end_year

    def window_matrix(self, lr: np.ndarray, length: int) -> tuple[np.ndarray, np.ndarray]:
        """Return (year labels, matrix[year, start_month-1]) of simple window returns."""
        n = len(lr)
        sums = np.full(n, np.nan)
        for i in range(n - length + 1):
            seg = lr[i : i + length]
            if not np.isnan(seg).any():
                sums[i] = seg.sum()
        yrs = np.unique(self.years)
        if self.start_year is not None:
            yrs = yrs[yrs >= self.start_year]
        if self.end_year is not None:
            yrs = yrs[yrs <= self.end_year]
        mat = np.full((len(yrs), 12), np.nan)
        row = {y: k for k, y in enumerate(yrs)}
        for i in range(n):
            y = self.years[i]
            if y in row and not np.isnan(sums[i]):
                mat[row[y], self.months[i] - 1] = np.expm1(sums[i])
        return yrs, mat


def _count(grid: _MonthlyGrid, lr: np.ndarray, lengths: list[int], c: dict) -> int:
    count = 0
    for length in lengths:
        _, mat = grid.window_matrix(lr, length)
        with np.errstate(all="ignore"):
            own = np.nanmean(mat, axis=1, keepdims=True)
        for col in range(12):
            r = mat[:, col]
            ok = ~np.isnan(r)
            n = int(ok.sum())
            if n < c["min_years"]:
                continue
            rv, ex = r[ok], (r - own[:, 0])[ok]
            if (
                (rv > 0).mean() >= c["candidate_hit_rate"]
                and (ex > 0).mean() >= c["candidate_own_rate"]
                and np.median(rv) >= c["candidate_min_median"]
            ):
                count += 1
    return count


def _shuffle_within_year(grid: _MonthlyGrid, rng: np.random.Generator) -> np.ndarray:
    lr = grid.lr.copy()
    for y in np.unique(grid.years):
        idx = np.where((grid.years == y) & ~np.isnan(lr))[0]
        lr[idx] = rng.permutation(lr[idx])
    return lr


def permutation_test(
    universe: dict[str, pd.Series],
    last_complete: dict[str, pd.Period],
    lengths: list[int],
    classification: dict,
    runs: int = 300,
    seed: int = 7,
    start_year=None,
    end_year=None,
) -> dict:
    """Run the test on one or more tickers combined."""
    lengths = [L for L in lengths if L < 12]
    grids = {t: _MonthlyGrid(s, last_complete[t], start_year, end_year) for t, s in universe.items() if len(s) > 2}
    actual = sum(_count(g, g.lr, lengths, classification) for g in grids.values())
    rng = np.random.default_rng(seed)
    null = np.array(
        [
            sum(_count(g, _shuffle_within_year(g, rng), lengths, classification) for g in grids.values())
            for _ in range(runs)
        ]
    )
    return {
        "tickers": sorted(grids),
        "actual": int(actual),
        "null_mean": float(null.mean()) if runs else np.nan,
        # A whole number of patterns: the smallest shuffled count at or above the 95% point.
        "null_p95": int(np.percentile(null, 95, method="higher")) if runs else np.nan,
        "share_at_or_above": float((null >= actual).mean()) if runs else np.nan,
        "runs": runs,
        "seed": seed,
    }


def describe(result: dict) -> str:
    """Plain-language reading of a permutation result."""
    share = result["share_at_or_above"]
    base = (
        f"{result['actual']} window(s) passed the pattern filter. Shuffled data with the same yearly trends "
        f"produced {result['null_mean']:.1f} on average; {share:.0%} of {result['runs']} shuffled runs "
        f"produced as many or more."
    )
    if share <= 0.05:
        verdict = " The patterns, as a group, are unlikely to be pure chance."
    elif share <= 0.25:
        verdict = " As a group this is only modest evidence; trust patterns that also have a clear reason."
    else:
        verdict = " As a group these patterns are consistent with chance; treat them with caution."
    return base + verdict
