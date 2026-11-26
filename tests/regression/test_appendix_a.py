"""Regression against the research baseline (docs/SCOPE.md Appendix A).

Any change to these numbers fails the build unless the fixtures are deliberately updated.
"""
from pathlib import Path

import pandas as pd
import pytest
import yaml

from scanner.config import load_config
from scanner.engine import Window, permutation_test, window_returns
from scanner.engine.windows import last_complete_month, standard_windows
from tests.conftest import RESEARCH_TICKERS

pytestmark = pytest.mark.regression
FIX = Path(__file__).parent / "fixtures"
A = yaml.safe_load((FIX / "appendix_a.yaml").read_text())
TOL = 0.0015
WINDOWS = {w.name: w for w in standard_windows()}


def row(stats, ticker, window):
    r = stats[(stats["ticker"] == ticker) & (stats["window"] == window)]
    assert len(r) == 1, f"{ticker} {window} missing"
    return r.iloc[0]


@pytest.mark.parametrize("rec", pd.read_csv(FIX / "verified_prices.csv").to_dict("records"),
                         ids=lambda r: f"{r['ticker']}-{r['date']}")
def test_verified_prices(universe, rec):
    s = universe[rec["ticker"]]
    s = s[s.index <= pd.Timestamp(rec["date"])]
    assert s.index[-1] == pd.Timestamp(rec["date"])
    assert s.iloc[-1] == pytest.approx(rec["close"])


@pytest.mark.parametrize("rec", A["window_returns"], ids=lambda r: f"{r['ticker']}-{r['window']}-{r['year']}")
def test_window_return_fixtures(universe, rec):
    df = window_returns(universe[rec["ticker"]], WINDOWS[rec["window"]])
    r = df[df["year"] == rec["year"]].iloc[0]
    assert r["entry_price"] == pytest.approx(rec["entry"]) and r["exit_price"] == pytest.approx(rec["exit"])
    assert pd.Timestamp(r["entry_date"]) == pd.Timestamp(rec["entry_date"])
    assert pd.Timestamp(r["exit_date"]) == pd.Timestamp(rec["exit_date"])
    assert r["ret"] == pytest.approx(rec["ret"], abs=TOL)


@pytest.mark.parametrize("rec", A["market"], ids=lambda r: r["window"])
def test_market_seasonality(market, rec):
    v = list(market.values(WINDOWS[rec["window"]]).values())
    assert len(v) == rec["n"]
    assert sum(x > 0 for x in v) == rec["up"]
    assert pd.Series(v).median() == pytest.approx(rec["median"], abs=TOL)


def test_tier1_exact_list_and_order(research_scan):
    _, combined, _, _ = research_scan
    t1 = combined[combined["class"] == "Tier 1"]
    assert list(zip(t1["ticker"], t1["window"])) == [(r["ticker"], r["window"]) for r in A["tier1"]]
    for rec in A["tier1"]:
        r = row(t1, rec["ticker"], rec["window"])
        for key in ("up", "n", "streak", "beat_market"):
            assert r[key] == rec[key], (rec, key)
        for key in ("median", "worst", "median_dip", "worst_dip"):
            assert r[key] == pytest.approx(rec[key], abs=TOL), (rec, key)


def test_tier2_exact_set(research_scan):
    _, combined, _, _ = research_scan
    t2 = combined[combined["class"] == "Tier 2"]
    assert set(zip(t2["ticker"], t2["window"])) == {(r["ticker"], r["window"]) for r in A["tier2"]}
    for rec in A["tier2"]:
        r = row(t2, rec["ticker"], rec["window"])
        assert (r["up"], r["n"], r["streak"]) == (rec["up"], rec["n"], rec["streak"])
        assert r["median"] == pytest.approx(rec["median"], abs=TOL)
        assert r["worst"] == pytest.approx(rec["worst"], abs=TOL)


def test_watch_and_negative(research_scan):
    _, combined, _, _ = research_scan
    assert (combined["class"] == "Watch").sum() == A["watch_count"]
    neg = combined[combined["class"] == "Negative"]
    assert len(neg) == A["negative_count"]
    top = neg.head(len(A["negative_top"]))
    assert list(zip(top["ticker"], top["window"])) == [(r["ticker"], r["window"]) for r in A["negative_top"]]
    for rec in A["negative_top"]:
        r = row(neg, rec["ticker"], rec["window"])
        assert (r["up"], r["n"]) == (rec["up"], rec["n"])
        assert r["median"] == pytest.approx(rec["median"], abs=TOL)


def test_emerging(research_scan):
    _, combined, _, _ = research_scan
    for rec in A["emerging_includes"]:
        assert row(combined, rec["ticker"], rec["window"])["class"] == "Emerging"


def test_quality_flags(research_scan):
    results, combined, _, _ = research_scan
    for t in A["frozen"]:
        assert results[t].quality.frozen, t
    for t in RESEARCH_TICKERS:
        if t not in A["frozen"]:
            assert not results[t].quality.frozen, t
    for t in A["all_insufficient"]:
        partial = results[t].stats
        assert not partial["class"].isin(["Tier 1", "Tier 2"]).any(), t
    buafoods = results["BUAFOODS"].stats
    assert buafoods["flags"].str.contains("Insufficient history").all()
    assert buafoods["class"].isin(["Insufficient history", "Emerging"]).all()


def test_permutation_actual_count(universe):
    cfg = load_config()
    uni = {t: universe[t] for t in RESEARCH_TICKERS}
    res = permutation_test(uni, {t: last_complete_month(s.index[-1]) for t, s in uni.items()},
                           [1, 2, 3], cfg["classification"], runs=40, seed=7)
    assert res["actual"] == A["permutation"]["actual"]
    assert 5 <= res["null_mean"] <= 14


def test_permutation_full_baseline(universe):
    """Appendix A.6 exactly: 300 runs, seed 7, research stocks combined."""
    p = A["permutation"]
    cfg = load_config()
    uni = {t: universe[t] for t in RESEARCH_TICKERS}
    res = permutation_test(uni, {t: last_complete_month(s.index[-1]) for t, s in uni.items()},
                           [1, 2, 3], cfg["classification"], runs=p["runs"], seed=p["seed"])
    got = {
        "actual": res["actual"],
        "null_mean": round(res["null_mean"], 2),
        "null_p95": res["null_p95"],
        "share_at_or_above": round(res["share_at_or_above"], 3),
    }
    want = {k: p[k] for k in got}
    assert got == want
