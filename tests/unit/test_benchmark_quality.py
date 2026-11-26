import numpy as np
import pandas as pd
import pytest

from scanner.config import load_config
from scanner.engine.benchmark import IndexBenchmark, MarketBenchmark, own_average
from scanner.engine.quality import check_quality
from scanner.engine.windows import Window, standard_windows
from tests.conftest import make_monthly_series

Q = load_config()["quality"]


def flat_universe(n: int, jan_return_by_stock):
    uni = {}
    for i in range(n):
        vals = {"2020-12": 10.0, "2021-01": 10.0 * (1 + jan_return_by_stock(i)), "2021-02": 10.0}
        uni[f"S{i}"] = make_monthly_series(vals)
    return uni


def test_market_benchmark_trimmed_mean():
    # 30 stocks: 28 return 1%, one +500% and one -90% outlier, which the 10% trim removes
    rets = [0.01] * 28 + [5.0, -0.9]
    uni = flat_universe(30, lambda i: rets[i])
    b = MarketBenchmark(uni, min_stocks=30, trim=0.10)
    assert b.values(Window(1, 1))[2021] == pytest.approx(0.01)


def test_market_benchmark_needs_min_stocks():
    b = MarketBenchmark(flat_universe(10, lambda i: 0.01), min_stocks=30)
    assert not b.available
    assert b.values(Window(1, 1)) == {}


def test_index_benchmark():
    idx = make_monthly_series({"2020-12": 100, "2021-01": 110, "2021-02": 99})
    b = IndexBenchmark(idx, "ASI")
    assert b.values(Window(1, 1))[2021] == pytest.approx(0.10)


def test_own_average_is_mean_of_twelve_windows():
    vals = {f"2020-{m:02d}": 10 * (1.01**m) for m in range(1, 13)}
    vals["2019-12"] = 10.0
    vals.update({f"2021-{m:02d}": vals["2020-12"] for m in range(1, 3)})
    s = make_monthly_series(dict(sorted(vals.items())))
    own = own_average(s, standard_windows(), pd.Period("2021-02", "M"))
    assert own[(1, 2020)] == pytest.approx(0.01)


def test_frozen_price_flag():
    vals = {f"2020-{m:02d}": (5 if m < 9 else 6) for m in range(1, 13)}
    q = check_quality(make_monthly_series(vals), "X", Q)
    assert q.frozen and q.zero_change_share > 0.3
    assert any("Frozen price" in w for w in q.warnings())


def test_corporate_action_gap_missing_year_and_stale():
    vals = {"2018-01": 10, "2018-02": 10, "2020-01": 10, "2020-02": 5}
    s = make_monthly_series(vals)
    q = check_quality(s, "X", Q, as_of=pd.Timestamp("2020-06-30"))
    assert q.missing_years == [2019]
    assert len(q.gaps) == 1
    assert q.corporate_actions and q.corporate_actions[0][1] == pytest.approx(-0.5)
    assert q.stale and q.stale_business_days > 5


def test_ex_dividend_months_recorded():
    s = make_monthly_series({f"2020-{m:02d}": 10 + m for m in range(1, 13)})
    q = check_quality(s, "X", Q, ex_dividend_dates=["2020-02-10", "2021-02-12"])
    assert q.ex_dividend_months == {2: [2020, 2021]}
    assert any("Feb" in w for w in q.warnings())


def test_no_false_frozen_on_moving_series():
    vals = {f"2020-{m:02d}": 10 + m for m in range(1, 13)}
    q = check_quality(make_monthly_series(vals), "X", Q)
    assert not q.frozen and np.isclose(q.zero_change_share, 0.0)
