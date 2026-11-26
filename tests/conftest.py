import os

import numpy as np
import pandas as pd
import pytest

from scanner.config import load_config


def make_monthly_series(values: dict, start_day_offset: int = 0) -> pd.Series:
    """Daily business-day series where every day in a month equals that month's value.

    values: {"2020-01": 10.0, ...}. Month-end close therefore equals the value.
    """
    parts = []
    for month, price in values.items():
        p = pd.Period(month, freq="M")
        days = pd.bdate_range(p.to_timestamp(how="start"), p.to_timestamp(how="end").normalize())
        parts.append(pd.Series(float(price), index=days[start_day_offset:]))
    return pd.concat(parts).sort_index()


def seasonal_series(years=range(2014, 2026), up_months=(11, 12, 1), up=0.06, down=-0.01, start=10.0) -> pd.Series:
    """Prices that rise in `up_months` and drift down otherwise, every year."""
    vals, price = {}, start
    for y in years:
        for m in range(1, 13):
            price *= 1 + (up if m in up_months else down)
            vals[f"{y}-{m:02d}"] = round(price, 6)
    return make_monthly_series(vals)


@pytest.fixture
def cfg():
    return load_config()


@pytest.fixture
def cfg_fast():
    return load_config(overrides={"significance": {"runs": 0}})


@pytest.fixture(scope="session")
def universe():
    """The pinned NairaDB snapshot. Downloads on first use; skipped if unavailable.

    Set REQUIRE_DATASET=1 (as CI does) to fail instead of skipping.
    """
    from scanner.data import DatasetUnavailable, load_universe

    try:
        return load_universe()
    except DatasetUnavailable as exc:
        if os.environ.get("REQUIRE_DATASET") == "1":
            raise
        pytest.skip(f"NairaDB dataset not available: {exc}")


@pytest.fixture(scope="session")
def market(universe):
    from scanner.engine import MarketBenchmark

    return MarketBenchmark(universe)


RESEARCH_TICKERS = ["VITAFOAM", "FCMB", "LEARNAFRCA", "ETI", "ETERNA", "PZ", "IKEJAHOTEL", "CONOIL",
                    "HONYFLOUR", "FTNCOCOA", "BUACEMENT", "BUAFOODS", "CWG"]


@pytest.fixture(scope="session")
def research_scan(universe, market):
    from scanner.engine import scan_many

    cfg = load_config(overrides={"significance": {"runs": 0}})
    return scan_many(RESEARCH_TICKERS, universe, market, cfg)


__all__ = ["make_monthly_series", "seasonal_series", "np"]
