"""Per-window statistics (docs/SCOPE.md 8.3)."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import binomtest


def current_streak(returns) -> int:
    """Consecutive positive years counting back from the most recent."""
    n = 0
    for r in reversed(list(returns)):
        if r > 0:
            n += 1
        else:
            break
    return n


def longest_streak(returns) -> int:
    best = run = 0
    for r in returns:
        run = run + 1 if r > 0 else 0
        best = max(best, run)
    return best


def _p_greater(k: int, n: int) -> float:
    return float(binomtest(k, n, 0.5, alternative="greater").pvalue) if n else np.nan


def window_stats(yearly: pd.DataFrame, market: dict[int, float] | None, own: dict[int, float] | None) -> dict:
    """Statistics for one window from its year rows (see window_returns)."""
    years = yearly["year"].astype(int).tolist()
    r = yearly["ret"].to_numpy(dtype=float)
    d = yearly["dip"].to_numpy(dtype=float)
    n = len(r)
    up = int((r > 0).sum())
    out = {
        "n": n,
        "up": up,
        "hit_rate": up / n if n else np.nan,
        "streak": current_streak(r),
        "longest_streak": longest_streak(r),
        "median": float(np.median(r)) if n else np.nan,
        "mean": float(np.mean(r)) if n else np.nan,
        "worst": float(r.min()) if n else np.nan,
        "best": float(r.max()) if n else np.nan,
        "std": float(np.std(r, ddof=1)) if n > 1 else np.nan,
        "variance": float(np.var(r, ddof=1)) if n > 1 else np.nan,
        "median_dip": float(np.nanmedian(d)) if n else np.nan,
        "worst_dip": float(np.nanmin(d)) if n else np.nan,
        "p_up": _p_greater(up, n),
        "first_year": min(years) if years else None,
        "last_year": max(years) if years else None,
    }

    def _excess(ref: dict[int, float] | None, prefix: str) -> None:
        if not ref:
            out.update(
                {f"{prefix}_n": 0, f"beat_{prefix}": np.nan, f"{prefix}_rate": np.nan, f"median_ex_{prefix}": np.nan}
            )
            return
        ex = np.array([ri - ref[y] for y, ri in zip(years, r, strict=True) if y in ref])
        m = len(ex)
        beat = int((ex > 0).sum())
        out.update(
            {
                f"{prefix}_n": m,
                f"beat_{prefix}": beat,
                f"{prefix}_rate": beat / m if m else np.nan,
                f"median_ex_{prefix}": float(np.median(ex)) if m else np.nan,
            }
        )
        if prefix == "own":
            out["p_own"] = _p_greater(beat, m)

    _excess(market, "market")
    _excess(own, "own")
    out.setdefault("p_own", np.nan)
    out["years"] = " ".join(f"{y}:{ri:+.1%}" for y, ri in zip(years, r, strict=True))
    return out
