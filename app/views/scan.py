"""Screen 1: enter tickers, choose data, run a scan."""

from __future__ import annotations

import datetime as dt

import state
import streamlit as st
import ui

from scanner.data import DatasetUnavailable, company_name, load_securities, sector_groups, ticker_from_filename
from scanner.engine.windows import windows_from_config

cfg = state.config()
c, sig = cfg["classification"], cfg["significance"]


def ensure(key: str, value) -> None:
    if key not in st.session_state:
        st.session_state[key] = value


ensure("w_mode", "Compare")
ensure("w_tickers", ["FCMB"])
ensure("w_source", "dataset")
ensure("w_as_of", dt.date.today())
ensure("w_exdiv", "")
for name, val in [*c.items(), *sig.items()]:
    if not isinstance(val, dict):
        ensure(f"w_c_{name}" if name in c else f"w_s_{name}", val)
for name, val in cfg["windows"].items():
    ensure(f"w_win_{name}", val)
ensure("w_start_year", 0)
ensure("w_end_year", 0)


def _duration(seconds: float) -> str:
    if seconds < 60:
        return f"{max(5, round(seconds / 5) * 5):.0f} seconds"
    minutes = round(seconds / 60)
    return f"{minutes} minute{'s' if minutes != 1 else ''}"


def _single() -> bool:
    return st.session_state.w_mode == "Single report"


def _on_mode() -> None:
    if _single():
        st.session_state.w_tickers = st.session_state.w_tickers[:1]


def _pick(tickers: list[str]) -> None:
    st.session_state.w_tickers = list(tickers)
    st.session_state.w_mode = "Compare" if len(tickers) > 1 else st.session_state.w_mode


# ---------------------------------------------------------------- ticker options
universe_tickers: list[str] = []
if st.session_state.w_source != "csv":
    try:
        universe_tickers = sorted(state.cached_universe())
        st.session_state.dataset_loaded = True
    except DatasetUnavailable as exc:
        st.error(f"Could not load the open dataset: {exc}")
uploads = st.session_state.get("uploads") or []
upload_tickers = [ticker_from_filename(f.name) for f in uploads]
options = sorted(
    {*universe_tickers, *load_securities().index, *upload_tickers, *st.session_state.w_tickers},
)


def _label(t: str) -> str:
    name = company_name(t)
    return f"{t} · {name}" if name else t


# ---------------------------------------------------------------- page
ui.page_title(
    "Scan stocks for seasonal patterns",
    lede="Enter one ticker for a full report, or several (up to every stock) to compare them. Every month, "
    "rolling 2 and 3-month window and the full year is tested.",
)

with st.container(key="card_scan", gap="small"):
    with st.container(horizontal=True, vertical_alignment="center"):
        ui.md('<label for="tickers" style="font-size:14px;font-weight:600">Ticker symbols</label>')
        st.space("stretch")
        st.segmented_control(
            "Scan mode",
            ["Single report", "Compare"],
            key="w_mode",
            on_change=_on_mode,
            label_visibility="collapsed",
            required=True,
        )
    single = _single()
    with st.container(horizontal=True, vertical_alignment="bottom"):
        tickers = st.multiselect(
            "Ticker symbols",
            options,
            key="w_tickers",
            format_func=_label,
            max_selections=1 if single else None,
            accept_new_options=True,
            placeholder="Type a ticker, e.g. ETI",
            label_visibility="collapsed",
            width="stretch",
        )
        tickers = [t.strip().upper() for t in tickers if t.strip()]
        n = len(tickers)
        run_label = "Run scan" if single or n <= 1 else f"Compare {n} stocks"
        run = st.button(run_label, type="primary", icon=":material/arrow_forward:", width=200, disabled=n == 0)
    ui.md(
        '<p class="ip-muted">'
        + (
            "Single report: one stock, every window, heatmap, calendar and year-by-year detail."
            if single
            else f"{n} selected. Up to {state.CARD_LIMIT} line up side by side; more are shown as sortable tables "
            "you can filter."
            + (
                f" Scanning {n} stocks takes about {_duration(state.estimate_seconds(n, sig['runs']))}."
                if n > state.LARGE_SCAN
                else ""
            )
        )
        + "</p>"
    )
    with st.container(key="quickpicks", horizontal=True, vertical_alignment="center", gap="small", wrap=True):
        ui.md('<span class="ip-muted">Quick picks:</span>')
        avail = set(options)
        if universe_tickers and not single:
            all_label = f"All stocks ({len(universe_tickers)})"
            st.button(all_label, on_click=_pick, args=(universe_tickers,), type="tertiary")
        t1 = [t for t in state.RESEARCH_TIER1 if t in avail]
        if t1:
            st.button(f"Research Tier 1 stocks ({len(t1)})", on_click=_pick, args=(t1,), type="tertiary")
        for sector, group in sector_groups([*avail]).items():
            if len(group) >= 2:
                st.button(f"{sector} ({len(group)})", on_click=_pick, args=(group,), type="tertiary")
        if len(st.session_state.w_tickers) > 1:
            st.button("Clear", on_click=_pick, args=([],), type="tertiary", icon=":material/close:")

# ---------------------------------------------------------------- price data
st.subheader("Price data", anchor=False)
source = st.radio(
    "Price source",
    list(state.SOURCES),
    key="w_source",
    format_func=lambda k: state.SOURCES[k][0],
    captions=[v[1] for v in state.SOURCES.values()],
    horizontal=True,
    label_visibility="collapsed",
)
if source != "dataset":
    st.file_uploader(
        "Drop TradingView or broker CSV files here (one file per stock; the ticker is read from the file name, "
        "e.g. NSENG_FCMB, 1D.csv)",
        type=["csv"],
        accept_multiple_files=True,
        key="uploads",
    )

# ---------------------------------------------------------------- settings
n_windows = len(windows_from_config(cfg))
left, right = st.columns(2)
with left.expander(
    f"Settings · {n_windows} windows · {c['min_years']}+ years · {c['candidate_hit_rate']:.0%} hit rate · "
    f"{sig['runs']} chance runs"
):
    st.caption("Windows and years")
    st.checkbox("Single months", key="w_win_single_month")
    st.checkbox("Rolling 2-month", key="w_win_rolling_2_month")
    st.checkbox("Rolling 3-month (includes quarters)", key="w_win_rolling_3_month")
    st.checkbox("Full year", key="w_win_full_year")
    y1, y2 = st.columns(2)
    y1.number_input("First year (0 = all)", 0, 2100, step=1, key="w_start_year")
    y2.number_input("Last year (0 = latest complete)", 0, 2100, step=1, key="w_end_year")
    st.caption("Tier 1 and Tier 2")
    st.number_input("Minimum complete years", 3, 30, key="w_c_min_years")
    st.slider("Hit rate (share of years up)", 0.5, 1.0, step=0.05, key="w_c_candidate_hit_rate")
    st.slider("Beat own average (share of years)", 0.5, 1.0, step=0.05, key="w_c_candidate_own_rate")
    st.slider("Minimum median return", 0.0, 0.3, step=0.01, key="w_c_candidate_min_median")
    st.number_input("Tier 1 minimum current streak", 1, 20, key="w_c_tier1_min_streak")
    st.slider("Tier 1 beat market (share of years)", 0.5, 1.0, step=0.001, format="%.3f", key="w_c_tier1_market_rate")
    st.caption("Watch")
    st.slider("Watch: hit rate", 0.5, 1.0, step=0.05, key="w_c_watch_hit_rate")
    st.slider("Watch: beat own average (share of years)", 0.5, 1.0, step=0.05, key="w_c_watch_own_rate")
    st.slider("Watch: minimum median return", 0.0, 0.3, step=0.01, key="w_c_watch_min_median")
    st.number_input("Watch: minimum current streak", 0, 20, key="w_c_watch_min_streak")
    st.caption("Exit or avoid (Negative)")
    st.slider("Negative: maximum hit rate", 0.0, 0.5, step=0.05, key="w_c_negative_max_hit_rate")
    st.slider("Negative: maximum median return", -0.3, 0.0, step=0.01, key="w_c_negative_max_median")
    st.caption("Emerging")
    st.number_input("Emerging: minimum current streak", 1, 20, key="w_c_emerging_min_streak")
    st.slider("Emerging: minimum median return", 0.0, 0.3, step=0.01, key="w_c_emerging_min_median")
    st.caption("Chance check")
    st.number_input("Shuffle runs (0 to skip)", 0, 5000, step=50, key="w_s_runs")
    st.number_input("Random seed", 0, 10_000, key="w_s_seed")
    st.date_input("Calendar date (for upcoming windows and stale-data checks)", key="w_as_of")
with right.expander("Optional: benchmark index and ex-dividend dates"):
    index_file = st.file_uploader(
        "Index CSV to use as the benchmark (e.g. NGX All-Share Index)", type=["csv"], key="index_file"
    )
    st.text_area(
        "Ex-dividend dates, one per line: TICKER, YYYY-MM-DD",
        key="w_exdiv",
        placeholder="VITAFOAM, 2025-02-10\nLEARNAFRCA, 2025-09-15",
        help="Windows covering these months get a note, because prices are unadjusted.",
    )

# Settings widgets -> config used by the next scan
for name in c:
    if f"w_c_{name}" in st.session_state:
        c[name] = st.session_state[f"w_c_{name}"]
for name in sig:
    if f"w_s_{name}" in st.session_state:
        sig[name] = int(st.session_state[f"w_s_{name}"])
for name in cfg["windows"]:
    cfg["windows"][name] = bool(st.session_state[f"w_win_{name}"])
cfg["lookback"]["start_year"] = int(st.session_state.w_start_year) or None
cfg["lookback"]["end_year"] = int(st.session_state.w_end_year) or None

# ---------------------------------------------------------------- run
if run:
    if not windows_from_config(cfg):
        st.error("Turn on at least one window type in Settings.")
        st.stop()
    bar = st.progress(0.0, text="Loading data...")

    def _progress(i: int, total: int, label: str) -> None:
        bar.progress(min(i / max(total, 1), 1.0), text=f"{label} ({min(i + 1, total)} of {total})"
                     if i < total else label)  # fmt: skip

    scan, errors, warnings = state.run_scan(
        tickers,
        source,
        st.session_state.get("uploads") or [],
        index_file,
        st.session_state.w_exdiv,
        st.session_state.w_as_of,
        progress=_progress,
    )
    bar.empty()
    for e in errors:
        st.error(e)
    for w in warnings:
        st.warning(w)
    if scan is not None:
        for t in scan.missing:
            st.error(f"No price data found for {t}")
        if scan.results and not warnings:
            st.switch_page(st.session_state.pages["compare" if scan.multi else "results"])
        elif scan.results:
            st.page_link(
                st.session_state.pages["compare" if scan.multi else "results"],
                label="Open results",
                icon=":material/arrow_forward:",
            )

# ---------------------------------------------------------------- recent
history = state.recent()
if history:
    st.subheader("Recent scans", anchor=False)
    with st.container(key="card_recent", gap="small"):
        for i, s in enumerate(history):
            label = f"**{', '.join(s.results)}**  ·  {s.summary()}  ·  {s.created:%H:%M}"
            if st.button(label, key=f"recent_{i}", type="tertiary"):
                state.open_scan(s)
                st.switch_page(st.session_state.pages["compare" if s.multi else "results"])
