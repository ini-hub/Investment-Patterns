import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as stx

from scanner import __version__
from scanner.config import load_config, settings_hash
from scanner.engine import completeness_note, scan_ticker
from scanner.engine.significance import _MonthlyGrid, _shuffle_within_year, describe, permutation_test
from scanner.engine.windows import Window, window_returns
from scanner.report import calendar_table, next_dates, pdf_report, run_manifest, stats_csv, yearly_csv
from tests.conftest import make_monthly_series, seasonal_series

CFG = load_config()
C = CFG["classification"]


def test_permutation_detects_strong_seasonality():
    s = seasonal_series()
    lc = pd.Period("2025-12", "M")
    res = permutation_test({"X": s}, {"X": lc}, [1, 2, 3], C, runs=50, seed=1)
    assert res["actual"] >= 3
    assert res["share_at_or_above"] <= 0.1
    assert "unlikely to be pure chance" in describe(res)


def test_permutation_is_reproducible():
    s = seasonal_series()
    lc = pd.Period("2025-12", "M")
    a = permutation_test({"X": s}, {"X": lc}, [1, 2, 3], C, runs=30, seed=5)
    b = permutation_test({"X": s}, {"X": lc}, [1, 2, 3], C, runs=30, seed=5)
    assert a == b


def test_constant_series_has_no_patterns():
    vals = {f"{y}-{m:02d}": 10 for y in range(2014, 2026) for m in range(1, 13)}
    res = permutation_test({"X": make_monthly_series(vals)}, {"X": pd.Period("2025-12", "M")}, [1, 2, 3], C, runs=10)
    assert res["actual"] == 0


def test_shuffle_keeps_yearly_totals():
    import numpy as np

    s = seasonal_series()
    g = _MonthlyGrid(s, pd.Period("2025-12", "M"))
    shuffled = _shuffle_within_year(g, np.random.default_rng(0))
    for y in set(g.years):
        mask = g.years == y
        assert np.nansum(shuffled[mask]) == pytest.approx(np.nansum(g.lr[mask]))


@settings(max_examples=30, deadline=None)
@given(scale=stx.floats(min_value=0.01, max_value=1000))
def test_returns_invariant_to_price_scale(scale):
    s = seasonal_series(years=range(2020, 2024))
    a = window_returns(s, Window(11, 3))["ret"].to_numpy()
    b = window_returns(s * scale, Window(11, 3))["ret"].to_numpy()
    assert a == pytest.approx(b, rel=1e-9)


@settings(max_examples=25, deadline=None)
@given(stx.lists(stx.floats(min_value=0.5, max_value=2.0), min_size=36, max_size=36))
def test_hit_rate_bounds(factors):
    vals, p = {}, 10.0
    for i, f in enumerate(factors):
        p *= f
        vals[f"{2020 + i // 12}-{i % 12 + 1:02d}"] = p
    res = scan_ticker("X", make_monthly_series(vals), None, load_config(overrides={"significance": {"runs": 0}}))
    hr = res.stats["hit_rate"].dropna()
    assert ((hr >= 0) & (hr <= 1)).all()


def test_seasonal_stock_end_to_end():
    res = scan_ticker("SEAS", seasonal_series(), None, load_config(overrides={"significance": {"runs": 20}}))
    nov_jan = res.stats[res.stats["window"] == "Nov-Jan"].iloc[0]
    assert nov_jan["up"] == nov_jan["n"] and nov_jan["n"] >= 10
    assert nov_jan["class"] == "Tier 2"  # no market benchmark, so capped below Tier 1
    worst = res.stats[res.stats["window"] == "Jun"].iloc[0]
    assert worst["class"] == "Insufficient history" or worst["up"] == 0


def test_next_dates():
    e, x, status = next_dates(12, 2, pd.Timestamp("2026-11-26"))
    assert (e.date().isoformat(), x.date().isoformat(), status) == ("2026-11-30", "2027-01-29", "Upcoming")
    e, x, status = next_dates(10, 3, pd.Timestamp("2026-11-26"))
    assert status == "Open now" and e.date().isoformat() == "2026-09-30"


def test_exports():
    res = scan_ticker("SEAS", seasonal_series(), None, load_config(overrides={"significance": {"runs": 5}}))
    csv = stats_csv(res.stats).decode()
    header = csv.splitlines()[0].split(",")
    assert header[:4] == ["ticker", "window", "kind", "class"]
    assert header[-3:] == ["data_hash", "code_version", "settings_hash"]
    assert {"data_hash", "code_version", "settings_hash"} <= set(
        yearly_csv(res.yearly).decode().splitlines()[0].split(",")
    )
    pdf = pdf_report([res], res.permutation, pd.Timestamp("2026-11-26"), "Test", ["line"])
    assert pdf[:4] == b"%PDF"
    cal = calendar_table(res.stats, pd.Timestamp("2026-11-26"))
    assert {"Entry (close of)", "Exit (close of)", "Status"} <= set(cal.columns)


def test_run_manifest_records_provenance():
    import json

    cfg = load_config(overrides={"significance": {"runs": 5}})
    res = scan_ticker("SEAS", seasonal_series(), None, cfg)
    doc = json.loads(run_manifest([res], res.permutation, pd.Timestamp("2026-11-26"), ["src"], "none"))
    assert doc["settings"] == cfg and doc["settings_hash"] == settings_hash(cfg)
    assert doc["tickers"]["SEAS"]["data_hash"] == res.meta["data_hash"]
    assert doc["code_version"].startswith(__version__)
    assert doc["permutation"]["runs"] == 5


def test_settings_hash_changes_with_settings():
    assert settings_hash(load_config()) == settings_hash(load_config())
    assert settings_hash(load_config()) != settings_hash(load_config(overrides={"significance": {"seed": 8}}))


def test_completeness_note():
    assert completeness_note(pd.Timestamp("2025-12-19"), pd.Period("2025-11", freq="M")).startswith(
        "December 2025 is incomplete"
    )
    assert (
        completeness_note(pd.Timestamp("2025-11-28"), pd.Period("2025-11", freq="M"))
        == "Last complete month: November 2025."
    )


def test_short_history_flagged_and_can_be_emerging():
    # Six years of data that rise every December: too short to classify, long enough to be Emerging.
    res = scan_ticker(
        "NEW",
        seasonal_series(years=range(2019, 2026), up_months=(12,), up=0.10, down=0.0),
        None,
        load_config(overrides={"significance": {"runs": 0}}),
    )
    assert res.stats["flags"].str.contains("Insufficient history").all()
    assert not res.stats["class"].isin(["Tier 1", "Tier 2", "Watch", "Negative"]).any()
    dec = res.stats[res.stats["window"] == "Dec"].iloc[0]
    assert dec["class"] == "Emerging" and dec["n"] < 8


def test_frozen_stock_patterns_marked_unreliable():
    vals, p = {}, 10.0
    for y in range(2014, 2026):
        for m in range(1, 13):
            if m == 12:
                p *= 1.10
            vals[f"{y}-{m:02d}"] = p
    res = scan_ticker("FROZ", make_monthly_series(vals), None, load_config(overrides={"significance": {"runs": 0}}))
    assert res.quality.frozen
    dec = res.stats[res.stats["window"] == "Dec"].iloc[0]
    assert dec["class"] in ("Tier 1", "Tier 2")
    assert "Unreliable" in dec["flags"]


def test_frozen_stock_negative_windows_marked_unreliable():
    vals, p = {}, 10.0
    for y in range(2014, 2026):
        for m in range(1, 13):
            if m == 3:
                p *= 0.90
            vals[f"{y}-{m:02d}"] = p
    res = scan_ticker("FROZ", make_monthly_series(vals), None, load_config(overrides={"significance": {"runs": 0}}))
    assert res.quality.frozen
    mar = res.stats[res.stats["window"] == "Mar"].iloc[0]
    assert mar["class"] == "Negative"
    assert "Unreliable" in mar["flags"]
