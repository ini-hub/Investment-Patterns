"""Step definitions for the Gherkin acceptance specifications (docs/SCOPE.md 11.3)."""

import io

import pandas as pd
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from scanner.config import load_config
from scanner.data import load_csv
from scanner.engine import CLASS_ORDER, NONE, no_data_message, scan_many, scan_ticker
from scanner.report import year_detail

scenarios("scan.feature", "csv_import.feature")

STAT_KEYS = ["n", "up", "streak", "median", "worst", "beat_market", "median_dip", "worst_dip"]


@pytest.fixture
def ctx():
    return {}


# ------------------------------------------------------------------ scan steps
@given("the NairaDB dataset snapshot ending 2025-12-19 is loaded")
def dataset(universe, ctx):
    assert max(s.index[-1] for s in universe.values()) == pd.Timestamp("2025-12-19")
    ctx["universe"] = universe


@given("default classification thresholds are in use")
def defaults(ctx):
    ctx["cfg"] = load_config(overrides={"significance": {"runs": 0}})


@given(parsers.parse("the permutation seed is {seed:d} and runs are {runs:d}"))
def perm_settings(ctx, seed, runs):
    ctx["cfg"] = load_config(overrides={"significance": {"runs": runs, "seed": seed}})


@when(parsers.parse('I scan the ticker "{ticker}"'))
def scan_one(ctx, market, ticker):
    ctx["result"] = scan_ticker(ticker, ctx["universe"][ticker], market, ctx["cfg"])


@when(parsers.parse('I scan the ticker "{ticker}" twice'))
def scan_twice(ctx, market, ticker):
    ctx["runs"] = [scan_ticker(ticker, ctx["universe"][ticker], market, ctx["cfg"]) for _ in range(2)]


@when(parsers.parse('I scan the tickers "{tickers}"'))
def scan_list(ctx, market, tickers):
    ctx["many"] = scan_many([t.strip() for t in tickers.split(",")], ctx["universe"], market, ctx["cfg"])


@when(parsers.parse('I open the year detail for window "{window}"'))
def open_detail(ctx, window):
    ctx["detail"] = year_detail(ctx["result"].yearly, window)


def stat(ctx, window):
    s = ctx["result"].stats
    return s[s["window"] == window].iloc[0]


@then(parsers.parse("the report contains {n:d} windows"))
def n_windows(ctx, n):
    assert len(ctx["result"].stats) == n


@then("every window shows n, up, streak, median, worst, beat market and dip statistics")
def has_stats(ctx):
    assert set(STAT_KEYS) <= set(ctx["result"].stats.columns)
    assert ctx["result"].stats[["n", "up", "streak"]].notna().all().all()


@then(parsers.parse('the window "{window}" is classified as "{klass}"'))
def window_class(ctx, window, klass):
    ctx["window"] = window
    assert stat(ctx, window)["class"] == klass


@then(parsers.parse("it shows {up:d} up years out of {n:d}"))
def up_out_of(ctx, up, n):
    r = stat(ctx, ctx["window"])
    assert (r["up"], r["n"]) == (up, n)


@then(parsers.parse("its median return is {pct:f}% within a tolerance of 0.1 percentage points"))
def median_is(ctx, pct):
    assert stat(ctx, ctx["window"])["median"] == pytest.approx(pct / 100, abs=0.001)


@then("no window ending in December 2025 is included")
def no_dec_2025(ctx):
    assert (pd.to_datetime(ctx["result"].yearly["exit_date"]) < pd.Timestamp("2025-12-01")).all()


@then(parsers.parse('the last complete month is "{month}"'))
def last_complete(ctx, month):
    assert ctx["result"].meta["last_complete_month"] == month


@then(parsers.parse("the report states that {month} is incomplete"))
def states_incomplete(ctx, month):
    assert f"{month} is incomplete" in ctx["result"].meta["completeness"]


@then(parsers.parse("the {year:d} row shows entry close {price:f} on {date}"))
def entry_row(ctx, year, price, date):
    r = ctx["detail"][ctx["detail"]["Year"] == year].iloc[0]
    ctx["row"] = r
    assert r["Entry close"] == pytest.approx(price)
    assert str(r["Entry date"]) == date


@then(parsers.parse("exit close {price:f} on {date}"))
def exit_row(ctx, price, date):
    assert ctx["row"]["Exit close"] == pytest.approx(price)
    assert str(ctx["row"]["Exit date"]) == date


@then(parsers.parse("a return of {pct:f}%"))
def return_is(ctx, pct):
    assert ctx["row"]["Return"] == pytest.approx(pct / 100, abs=0.001)


@then(parsers.parse('the report shows the "{text}" warning'))
def warning_shown(ctx, text):
    assert any(text in w for w in ctx["result"].quality.warnings())


@then(parsers.parse('no window is classified above "None" without an "{flag}" label'))
def unreliable(ctx, flag):
    s = ctx["result"].stats
    above = s[s["class"].isin(CLASS_ORDER[: CLASS_ORDER.index(NONE)])]
    assert above["flags"].str.contains(flag).all()


@then(parsers.parse('every window shows the "{flag}" flag'))
def every_flag(ctx, flag):
    assert ctx["result"].stats["flags"].str.contains(flag).all()


@then(parsers.parse('no window is classified as "{a}" or "{b}"'))
def none_classified(ctx, a, b):
    assert not ctx["result"].stats["class"].isin([a, b]).any()


@then(parsers.parse('every window is classified as "{klass}"'))
def all_class(ctx, klass):
    assert ctx["result"].stats["class"].eq(klass).all()


@then("both reports show identical permutation results")
def same_perm(ctx):
    a, b = ctx["runs"]
    assert a.permutation == b.permutation and a.permutation["runs"] == 300


@then(parsers.parse('I see the message "{message}"'))
def missing_message(ctx, message):
    assert message in [no_data_message(t) for t in ctx["many"][3]]


@then("no report is generated")
def no_report(ctx):
    results, combined, perm, _ = ctx["many"]
    assert results == {} and combined.empty and perm is None


# ------------------------------------------------------------------ CSV steps
@given(parsers.parse('a CSV file "{name}" with columns "{header}"'))
def csv_with_header(ctx, name, header):
    ctx["name"], ctx["header"] = name, header


@given("the time column contains Unix seconds")
def unix_rows(ctx):
    rows = ["1735776000,10,11,9,10.5,1000", "1735862400,10.5,11,10,10.8,2000", "1736121600,10.8,11,10,11.0,500"]
    ctx["text"] = ctx["header"] + "\n" + "\n".join(rows) + "\n"


@given(parsers.parse('a CSV file "{name}" containing a close price of 0'))
def csv_with_zero(ctx, name):
    ctx["name"] = name
    ctx["text"] = "date,close\n2025-01-02,5\n2025-01-03,0\n2025-01-06,6\n"


@when("I upload the file")
def upload(ctx):
    f = io.BytesIO(ctx["text"].encode())
    f.name = ctx["name"]
    ctx["series"], ctx["volume"], ctx["report"] = load_csv(f)


@then(parsers.parse('the import succeeds for ticker "{ticker}"'))
def import_ok(ctx, ticker):
    assert ctx["report"].ticker == ticker and len(ctx["series"]) == 3


@then(parsers.parse("the summary shows first date {first} and last date {last}"))
def summary_dates(ctx, first, last):
    assert f"{first} to {last}" in ctx["report"].summary()


@then(parsers.parse("the import reports {n:d} invalid row"))
def invalid_count(ctx, n):
    assert len(ctx["report"].rejected) == n


@then("the row is excluded from analysis")
def excluded(ctx):
    assert pd.Timestamp("2025-01-03") not in ctx["series"].index
