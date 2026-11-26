"""Classification rules (docs/SCOPE.md 8.6)."""
from __future__ import annotations

import math

TIER1, TIER2, WATCH, EMERGING, NEGATIVE, NONE, INSUFFICIENT = (
    "Tier 1", "Tier 2", "Watch", "Emerging", "Negative", "None", "Insufficient history",
)
CLASS_ORDER = [TIER1, TIER2, WATCH, EMERGING, NEGATIVE, NONE, INSUFFICIENT]


def _ok(x) -> bool:
    return x is not None and not (isinstance(x, float) and math.isnan(x))


def is_candidate(s: dict, c: dict) -> bool:
    return (
        s["length"] < 12
        and s["n"] >= c["min_years"]
        and s["hit_rate"] >= c["candidate_hit_rate"]
        and _ok(s.get("own_rate")) and s["own_rate"] >= c["candidate_own_rate"]
        and s["median"] >= c["candidate_min_median"]
    )


def _is_emerging(s: dict, c: dict) -> bool:
    """Emerging test: a recent unbroken run of up years with a meaningful median."""
    return (
        s["length"] < 12
        and s["streak"] >= c["emerging_min_streak"]
        and _ok(s.get("median")) and s["median"] >= c["emerging_min_median"]
    )


def classify(s: dict, c: dict, market_available: bool = True) -> tuple[str, str]:
    """Return (class, note) for one window's statistics.

    Short histories (n below min_years) are never Tier 1, Tier 2, Watch or Negative,
    but can be Emerging; the scan also flags them "Insufficient history".
    """
    if s["n"] < c["min_years"]:
        short = f"only {s['n']} complete years (minimum {c['min_years']})"
        if _is_emerging(s, c):
            return EMERGING, f"Up in each of the last {s['streak']} years; {short}"
        return INSUFFICIENT, short[0].upper() + short[1:]
    if s["length"] < 12 and is_candidate(s, c):
        if s["streak"] >= c["tier1_min_streak"]:
            if market_available and _ok(s.get("market_rate")):
                if s["market_rate"] >= c["tier1_market_rate"]:
                    return TIER1, ""
            elif not market_available:
                return TIER2, "Tier 1 needs a market benchmark, which is not available"
        return TIER2, ""
    if s["hit_rate"] <= c["negative_max_hit_rate"] and s["median"] <= c["negative_max_median"]:
        return NEGATIVE, ""
    if (
        s["length"] < 12
        and s["hit_rate"] >= c["watch_hit_rate"]
        and s["median"] >= c["watch_min_median"]
        and _ok(s.get("own_rate")) and s["own_rate"] >= c["watch_own_rate"]
        and s["streak"] >= c["watch_min_streak"]
    ):
        return WATCH, ""
    if _is_emerging(s, c):
        return EMERGING, f"Up in each of the last {s['streak']} years"
    return NONE, ""


def score(s: dict, c: dict) -> float:
    w = c["score_weights"]
    own = s.get("own_rate") if _ok(s.get("own_rate")) else 0.0
    mkt = s.get("market_rate") if _ok(s.get("market_rate")) else 0.0
    return w["hit_rate"] * s["hit_rate"] + w["own_rate"] * own + w["market_rate"] * mkt


def sort_stats(df):
    """Order rows: class order, then score (best first); Negative rows by hit rate then median (worst first)."""
    import pandas as pd

    order = {k: i for i, k in enumerate(CLASS_ORDER)}
    df = df.copy()
    df["_o"] = df["class"].map(order)
    neg = df["class"] == NEGATIVE
    df["_k1"] = -df["score"].fillna(-1)
    df["_k2"] = -df["median"]
    df.loc[neg, "_k1"] = df.loc[neg, "hit_rate"]
    df.loc[neg, "_k2"] = df.loc[neg, "median"]
    df = df.sort_values(["_o", "_k1", "_k2"]).drop(columns=["_o", "_k1", "_k2"])
    return df.reset_index(drop=True)
