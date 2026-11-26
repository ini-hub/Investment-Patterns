import numpy as np
import pandas as pd
import pytest

from scanner.config import load_config
from scanner.engine import classify as cl
from scanner.engine.metrics import current_streak, longest_streak, window_stats


def yearly(returns, start=2016):
    years = list(range(start, start + len(returns)))
    return pd.DataFrame({"year": years, "ret": returns, "dip": [min(r, 0) - 0.01 for r in returns]})


def test_streaks():
    assert current_streak([0.1, -0.1, 0.2, 0.3]) == 2
    assert current_streak([0.1, 0.0]) == 0  # zero is not a gain
    assert longest_streak([0.1, 0.2, -0.1, 0.1, 0.1, 0.1, -0.2]) == 3


def test_window_stats_values():
    r = [0.1, 0.2, -0.05, 0.3]
    st = window_stats(
        yearly(r),
        market={2016: 0.0, 2017: 0.3, 2018: -0.1, 2019: 0.1},
        own={2016: 0.05, 2017: 0.1, 2018: 0.0, 2019: 0.0},
    )
    assert st["n"] == 4 and st["up"] == 3 and st["hit_rate"] == 0.75
    assert st["median"] == pytest.approx(0.15)
    assert st["worst"] == -0.05 and st["best"] == 0.3
    assert st["std"] == pytest.approx(np.std(r, ddof=1))
    assert st["variance"] == pytest.approx(st["std"] ** 2)
    assert st["beat_market"] == 3 and st["market_n"] == 4
    assert st["beat_own"] == 3 and st["own_rate"] == 0.75
    assert st["years"].startswith("2016:+10.0%")


def test_window_stats_without_benchmarks():
    st = window_stats(yearly([0.1, 0.2]), None, None)
    assert np.isnan(st["market_rate"]) and np.isnan(st["own_rate"])


def base(**kw):
    s = dict(length=3, n=10, up=9, hit_rate=0.9, own_rate=0.8, market_rate=0.8, median=0.10, streak=6)
    s.update(kw)
    return s


C = load_config()["classification"]


@pytest.mark.parametrize(
    "stats, expected",
    [
        (base(), cl.TIER1),
        (base(streak=3), cl.TIER2),  # streak too short for Tier 1
        (base(market_rate=0.6), cl.TIER2),  # market test fails
        (base(market_rate=6 / 9), cl.TIER1),  # exactly two thirds passes
        (base(n=7, streak=2), cl.INSUFFICIENT),
        (base(n=6, up=6, hit_rate=1.0, streak=6), cl.EMERGING),  # short history can still be Emerging
        (base(n=6, up=5, hit_rate=5 / 6, streak=5, median=0.02), cl.INSUFFICIENT),  # median too small
        (base(hit_rate=0.1, up=1, median=-0.08, own_rate=0.1), cl.NEGATIVE),
        (base(hit_rate=0.1, up=1, median=-0.02, own_rate=0.1, streak=0), cl.NONE),  # not negative enough
        (base(hit_rate=0.7, own_rate=0.6, streak=3), cl.WATCH),
        (base(hit_rate=0.6, own_rate=0.5, streak=5), cl.EMERGING),
        (base(hit_rate=0.6, own_rate=0.5, streak=2), cl.NONE),
        (base(length=12), cl.NONE),  # full year never a candidate
    ],
)
def test_classification_boundaries(stats, expected):
    assert cl.classify(stats, C)[0] == expected


def test_tier1_capped_without_market_benchmark():
    klass, note = cl.classify(base(market_rate=np.nan), C, market_available=False)
    assert klass == cl.TIER2 and "benchmark" in note


def test_sort_stats_negative_order():
    df = pd.DataFrame(
        [
            {**base(hit_rate=0.2, median=-0.2), "class": cl.NEGATIVE, "score": 0.1},
            {**base(hit_rate=0.0, median=-0.1), "class": cl.NEGATIVE, "score": 0.1},
            {**base(), "class": cl.TIER1, "score": 0.9},
        ]
    )
    out = cl.sort_stats(df)
    assert out["class"].tolist() == [cl.TIER1, cl.NEGATIVE, cl.NEGATIVE]
    assert out["hit_rate"].tolist()[1:] == [0.0, 0.2]
