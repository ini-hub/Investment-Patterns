"""Investment Patterns: NGX seasonal pattern scanner (Phase 1 web app).

Run locally:  streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from scanner import code_version, settings_hash
from scanner.config import load_config
from scanner.data import CSVFormatError, DatasetUnavailable, load_csv, load_universe
from scanner.data.nairadb_loader import PINNED_COMMIT
from scanner.engine import (
    CLASS_ORDER,
    IndexBenchmark,
    MarketBenchmark,
    describe_permutation,
    no_data_message,
    scan_many,
)
from scanner.report import (
    calendar_table,
    heatmap_figure,
    method_markdown,
    month_strip,
    pattern_table,
    pdf_report,
    run_manifest,
    stats_csv,
    year_detail,
    yearly_csv,
)

st.set_page_config(page_title="Investment Patterns", layout="wide")

PCT_COLS = {
    "Median",
    "Worst year",
    "Best year",
    "Std dev",
    "Median dip",
    "Worst dip",
    "Return",
    "Dip inside window",
    "Market",
    "Own average",
}


def show_df(df: pd.DataFrame) -> None:
    if df is None or df.empty:
        st.info("None found.")
        return
    view = df.copy()
    for col in view.columns:
        if col in PCT_COLS:
            view[col] = view[col].map(lambda v: "" if pd.isna(v) else f"{v:+.1%}")
    st.dataframe(view, hide_index=True, width="stretch")


@st.cache_data(show_spinner="Loading the open NGX dataset (first run downloads it)...")
def cached_universe() -> dict[str, pd.Series]:
    return load_universe()


@st.cache_resource(show_spinner="Building the market benchmark...")
def cached_market_benchmark(min_stocks: int, trim: float) -> MarketBenchmark:
    return MarketBenchmark(cached_universe(), min_stocks, trim)


def parse_ex_dividend(text: str) -> tuple[dict[str, list], list[str]]:
    out, errors = {}, []
    for i, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            ticker, date = [x.strip() for x in line.split(",")[:2]]
            out.setdefault(ticker.upper(), []).append(pd.Timestamp(date))
        except Exception:  # noqa: BLE001
            errors.append(f"Line {i}: expected 'TICKER, YYYY-MM-DD', got '{line}'")
    return out, errors


# ---------------------------------------------------------------- sidebar
cfg = load_config()
with st.sidebar:
    st.header("Data")
    source = st.radio(
        "Price source",
        ["Open NGX dataset", "My CSV files", "Both (my CSV files take priority)"],
        help="The open dataset covers about 147 NGX stocks from Dec 2015 to 19 Dec 2025 (unadjusted closes).",
    )
    uploads = []
    if source != "Open NGX dataset":
        uploads = st.file_uploader(
            "Daily price CSV files (one per stock)",
            type=["csv"],
            accept_multiple_files=True,
            help="Needs a date column (date, time or timestamp) and a close column (close, price or last). "
            "The ticker is read from the file name, e.g. 'NSENG_FCMB, 1D.csv' becomes FCMB.",
        )
    index_file = st.file_uploader(
        "Optional: index CSV for the benchmark (e.g. NGX All-Share Index)",
        type=["csv"],
        help="If given, this replaces the market average as the benchmark.",
    )
    exdiv_text = st.text_area(
        "Optional: ex-dividend dates",
        placeholder="VITAFOAM, 2025-02-10\nLEARNAFRCA, 2025-09-15",
        help="One 'TICKER, YYYY-MM-DD' per line. Windows covering these months get a note.",
    )
    as_of = st.date_input("Calendar date", value=dt.date.today())

    st.header("Settings")
    with st.expander("Windows and years"):
        w = cfg["windows"]
        w["single_month"] = st.checkbox("Single months", w["single_month"])
        w["rolling_2_month"] = st.checkbox("Rolling 2-month", w["rolling_2_month"])
        w["rolling_3_month"] = st.checkbox("Rolling 3-month (includes quarters)", w["rolling_3_month"])
        w["full_year"] = st.checkbox("Full year", w["full_year"])
        sy = st.number_input("First year (0 = all)", 0, 2100, 0, step=1)
        ey = st.number_input("Last year (0 = latest complete)", 0, 2100, 0, step=1)
        cfg["lookback"]["start_year"] = int(sy) or None
        cfg["lookback"]["end_year"] = int(ey) or None
    with st.expander("Pattern thresholds"):
        c = cfg["classification"]
        c["min_years"] = st.number_input("Minimum complete years", 3, 30, c["min_years"])
        c["candidate_hit_rate"] = st.slider("Hit rate (share of years up)", 0.5, 1.0, c["candidate_hit_rate"], 0.05)
        c["candidate_own_rate"] = st.slider(
            "Beat own average (share of years)", 0.5, 1.0, c["candidate_own_rate"], 0.05
        )
        c["candidate_min_median"] = st.slider("Minimum median return", 0.0, 0.3, c["candidate_min_median"], 0.01)
        c["tier1_min_streak"] = st.number_input("Tier 1 minimum current streak", 1, 20, c["tier1_min_streak"])
        c["tier1_market_rate"] = st.slider(
            "Tier 1 beat market (share of years)", 0.5, 1.0, c["tier1_market_rate"], 0.001, format="%.3f"
        )
    with st.expander("Watch, Negative and Emerging thresholds"):
        st.caption("Watch")
        c["watch_hit_rate"] = st.slider("Watch: hit rate", 0.5, 1.0, c["watch_hit_rate"], 0.05)
        c["watch_own_rate"] = st.slider("Watch: beat own average (share of years)", 0.5, 1.0, c["watch_own_rate"], 0.05)
        c["watch_min_median"] = st.slider("Watch: minimum median return", 0.0, 0.3, c["watch_min_median"], 0.01)
        c["watch_min_streak"] = st.number_input("Watch: minimum current streak", 0, 20, c["watch_min_streak"])
        st.caption("Negative (exit or avoid)")
        c["negative_max_hit_rate"] = st.slider("Negative: maximum hit rate", 0.0, 0.5, c["negative_max_hit_rate"], 0.05)
        c["negative_max_median"] = st.slider(
            "Negative: maximum median return", -0.3, 0.0, c["negative_max_median"], 0.01
        )
        st.caption("Emerging")
        c["emerging_min_streak"] = st.number_input("Emerging: minimum current streak", 1, 20, c["emerging_min_streak"])
        c["emerging_min_median"] = st.slider(
            "Emerging: minimum median return", 0.0, 0.3, c["emerging_min_median"], 0.01
        )
    with st.expander("Chance check"):
        cfg["significance"]["runs"] = st.number_input(
            "Shuffle runs (0 to skip)", 0, 5000, cfg["significance"]["runs"], 50
        )
        cfg["significance"]["seed"] = st.number_input("Random seed", 0, 10_000, cfg["significance"]["seed"])

# ---------------------------------------------------------------- data assembly
st.title("Investment Patterns")
st.caption("Seasonal pattern scanner for NGX stocks. Research tool, not investment advice.")

universe: dict[str, pd.Series] = {}
import_gaps: dict[str, list] = {}
notes: list[str] = []
dataset_loaded = False
if source != "My CSV files":
    try:
        universe.update(cached_universe())
        dataset_loaded = True
        notes.append(f"Open NGX dataset (NairaDB, commit {PINNED_COMMIT[:7]}): {len(universe)} stocks.")
    except DatasetUnavailable as exc:
        st.error(f"Could not load the open dataset: {exc}")
for f in uploads or []:
    try:
        series, _vol, rep = load_csv(f, gap_business_days=cfg["quality"]["gap_business_days"])
        if len(series) < 2:
            st.warning(f"{f.name}: no usable rows.")
            continue
        universe[rep.ticker] = series
        import_gaps[rep.ticker] = rep.gaps
        notes.append("Upload " + rep.summary() + ".")
        for r in rep.rejected[:5]:
            st.warning(f"{f.name}: {r}")
    except CSVFormatError as exc:
        st.error(str(exc))

benchmark = None
if index_file is not None:
    try:
        idx, _v, _r = load_csv(index_file, ticker="INDEX")
        benchmark = IndexBenchmark(idx, name=index_file.name)
    except CSVFormatError as exc:
        st.error(f"Index file: {exc}")
elif dataset_loaded:
    benchmark = cached_market_benchmark(cfg["benchmark"]["min_stocks"], cfg["benchmark"]["trim"])
elif len(universe) >= cfg["benchmark"]["min_stocks"]:
    benchmark = MarketBenchmark(universe, cfg["benchmark"]["min_stocks"], cfg["benchmark"]["trim"])

exdiv, exdiv_errors = parse_ex_dividend(exdiv_text)
for e in exdiv_errors:
    st.warning(e)

with st.expander("Data loaded", expanded=False):
    for n in notes:
        st.write(n)
    st.write(
        "Benchmark: "
        + (
            benchmark.description
            if benchmark is not None and benchmark.available
            else "not available, so no window can reach Tier 1"
        )
    )

tickers_text = st.text_input(
    "Ticker symbol(s)",
    value="FCMB",
    help="One ticker, or several separated by commas, e.g. FCMB, VITAFOAM, ETI",
)
run = st.button("Run scan", type="primary")

if "last_run" not in st.session_state:
    st.session_state.last_run = None
if run:
    tickers = [t.strip().upper() for t in tickers_text.split(",") if t.strip()]
    if not tickers:
        st.warning("Enter at least one ticker.")
        st.stop()
    with st.spinner("Scanning..."):
        results, combined, perm, missing = scan_many(
            tickers,
            universe,
            benchmark,
            cfg,
            pd.Timestamp(as_of),
            import_gaps,
            exdiv,
        )
    st.session_state.last_run = (tickers, results, combined, perm, missing)

if st.session_state.last_run is None:
    st.info("Enter a ticker and press Run scan.")
    st.stop()

tickers, results, combined, perm, missing = st.session_state.last_run
for t in missing:
    st.error(no_data_message(t))
if not results:
    st.stop()

as_of_ts = pd.Timestamp(as_of)
title = "Seasonal scan: " + ", ".join(results)

# ---------------------------------------------------------------- summary
first = min(r.meta["first_date"] for r in results.values())
last = max(r.meta["last_date"] for r in results.values())
cols = st.columns(4)
cols[0].metric("Stocks scanned", len(results))
cols[1].metric("Data range", f"{first.date()} to {last.date()}")
cols[2].metric("Tier 1 / Tier 2", f"{(combined['class'] == 'Tier 1').sum()} / {(combined['class'] == 'Tier 2').sum()}")
cols[3].metric("Negative windows", int((combined["class"] == "Negative").sum()))

for r in results.values():
    for wmsg in r.quality.warnings():
        st.warning(f"**{r.ticker}:** {wmsg}")
for note in dict.fromkeys(r.meta["completeness"] for r in results.values()):
    st.info(note)
if perm:
    st.markdown("**Chance check.** " + describe_permutation(perm))

multi = len(results) > 1
tabs = st.tabs(["Patterns", "Exit or avoid", "Heatmap", "Calendar", "Year detail", "All windows", "Method"])

with tabs[0]:
    for klass in ["Tier 1", "Tier 2", "Watch", "Emerging"]:
        st.subheader(klass)
        tbl = pattern_table(combined, [klass], include_ticker=multi).drop(columns=["Class"])
        show_df(tbl)

with tabs[1]:
    st.caption(
        "Windows that fell in most years. Useful for timing exits; retail short selling is not generally "
        "available on the NGX."
    )
    show_df(pattern_table(combined, ["Negative"], include_ticker=multi).drop(columns=["Class"]))

with tabs[2]:
    pick = st.selectbox("Stock", list(results), key="hm_pick") if multi else next(iter(results))
    r = results[pick]
    st.plotly_chart(heatmap_figure(r.yearly, r.stats, f"{pick}: window returns by year"), width="stretch")
    st.caption("Colour saturates at +/-50%; the printed value is exact. Labels show the window's class.")

with tabs[3]:
    st.caption(
        f"Next or current occurrence of each qualifying window as of {as_of_ts.date()}. "
        "Dates are the last business day of the month; NGX holidays are not modelled."
    )
    show_df(calendar_table(combined, as_of_ts))
    strip = month_strip(combined)
    if not strip.empty:
        st.markdown("**Months covered** (+ rising window, - falling window)")
        st.dataframe(strip, width="stretch")

with tabs[4]:
    pick = st.selectbox("Stock", list(results), key="yd_pick") if multi else next(iter(results))
    r = results[pick]
    wnames = r.stats["window"].tolist()
    wsel = st.selectbox("Window", wnames)
    srow = r.stats[r.stats["window"] == wsel].iloc[0]
    st.write(
        f"**{pick} {wsel}**: {srow['class']}. Up in {srow['up']} of {srow['n']} years, "
        f"median {srow['median']:+.1%}, mean {srow['mean']:+.1%}, worst {srow['worst']:+.1%}, "
        f"best {srow['best']:+.1%}, standard deviation {srow['std']:.1%}."
    )
    show_df(year_detail(r.yearly, wsel))

with tabs[5]:
    show_df(pattern_table(combined, CLASS_ORDER, include_ticker=multi))

with tabs[6]:
    st.markdown(method_markdown(cfg))
    st.caption(
        f"Code version {code_version()}. Settings hash {settings_hash(cfg)}. Data hash per stock: "
        + ", ".join(f"{t} {r.meta['data_hash']}" for t, r in results.items())
        + "."
    )

# ---------------------------------------------------------------- exports
st.divider()
st.subheader("Export")
stamp = as_of_ts.strftime("%Y%m%d")
name = "_".join(results)[:60]
yearly_all = pd.concat([r.yearly for r in results.values()], ignore_index=True)
bench_text = benchmark.description if benchmark is not None and benchmark.available else "not available"
meta_lines = [
    f"Data range: {first.date()} to {last.date()}. Calendar date: {as_of_ts.date()}.",
    "Benchmark: " + bench_text,
    *notes,
]
c1, c2, c3, c4 = st.columns(4)
c1.download_button("Statistics (CSV)", stats_csv(combined), f"patterns_{name}_{stamp}.csv", "text/csv")
c2.download_button("Year by year (CSV)", yearly_csv(yearly_all), f"yearly_{name}_{stamp}.csv", "text/csv")
c3.download_button(
    "Report (PDF)",
    pdf_report(list(results.values()), perm, as_of_ts, title, meta_lines),
    f"report_{name}_{stamp}.pdf",
    "application/pdf",
)
c4.download_button(
    "Run details (JSON)",
    run_manifest(list(results.values()), perm, as_of_ts, notes, bench_text),
    f"run_{name}_{stamp}.json",
    "application/json",
)
