"""Shared app state: cached data, the current scan and recent scans.

Phase 1 keeps everything in the browser session; nothing is saved after the app closes.
"""

from __future__ import annotations

import copy
import datetime as dt
from dataclasses import dataclass, field

import pandas as pd
import streamlit as st

from scanner.config import load_config
from scanner.data import CSVFormatError, DatasetUnavailable, load_csv, load_universe
from scanner.data.nairadb_loader import PINNED_COMMIT
from scanner.engine import IndexBenchmark, MarketBenchmark, scan_many

SOURCES = {
    "dataset": (
        "Open NGX dataset",
        "About 147 stocks, Dec 2015 to 19 Dec 2025. Downloaded on first run.",
    ),
    "csv": ("My CSV files", "Upload TradingView or broker exports, for example to include 2026."),
    "both": ("Both", "Dataset for history and the market benchmark; your files take priority."),
}
CARD_LIMIT = 6  # Compare shows cards and side-by-side columns up to this many stocks, tables above it
LARGE_SCAN = 20  # above this many stocks the Scan screen shows a time estimate
# Measured on a laptop (Nov 2026): seconds per stock to scan, and per stock per 300 chance-check runs.
SCAN_SECONDS, CHANCE_SECONDS = 0.22, 0.33


def estimate_seconds(n: int, runs: int) -> float:
    """Rough scan time: scanning, plus the chance check per stock and for the group."""
    chance = CHANCE_SECONDS * runs / 300 * n * (2 if n > 1 else 1)
    return n * SCAN_SECONDS + chance


MAX_RECENT = 5
# Research session (docs/SCOPE.md Appendix A.2): stocks with at least one Tier 1 window.
RESEARCH_TIER1 = ["FCMB", "VITAFOAM", "ETI", "IKEJAHOTEL", "LEARNAFRCA"]


@dataclass
class Scan:
    tickers: list[str]
    results: dict
    combined: pd.DataFrame
    permutation: dict | None
    missing: list[str]
    as_of: pd.Timestamp
    sources: list[str]
    benchmark: str
    created: dt.datetime = field(default_factory=dt.datetime.now)

    @property
    def multi(self) -> bool:
        return len(self.results) > 1

    def counts(self) -> dict[str, int]:
        c = self.combined["class"].value_counts() if not self.combined.empty else {}
        return {k: int(c.get(k, 0)) for k in ("Tier 1", "Tier 2", "Watch", "Emerging", "Negative")}

    def summary(self) -> str:
        c = self.counts()
        return f"{c['Tier 1']} Tier 1 · {c['Tier 2']} Tier 2 · {c['Negative']} falling windows"


@st.cache_data(show_spinner="Loading the open NGX dataset (the first run downloads it)...")
def cached_universe() -> dict[str, pd.Series]:
    return load_universe()


@st.cache_resource(show_spinner="Building the market benchmark...")
def cached_market_benchmark(min_stocks: int, trim: float) -> MarketBenchmark:
    return MarketBenchmark(cached_universe(), min_stocks, trim)


def dataset_status() -> str | None:
    """One-line status for the top bar, or None if the dataset has not been loaded yet."""
    if not st.session_state.get("dataset_loaded") and st.session_state.get("w_source", "dataset") == "csv":
        return None
    try:
        uni = cached_universe()
    except DatasetUnavailable:
        return None
    st.session_state.dataset_loaded = True
    last = max(s.index[-1] for s in uni.values())
    return f"NGX dataset · {len(uni)} stocks · to {last.day} {last:%b %Y}"


def config() -> dict:
    if "cfg" not in st.session_state:
        st.session_state.cfg = load_config()
    return st.session_state.cfg


def current() -> Scan | None:
    return st.session_state.get("scan")


def recent() -> list[Scan]:
    return st.session_state.setdefault("recent", [])


def open_scan(scan: Scan, focus: str | None = None) -> None:
    st.session_state.scan = scan
    st.session_state.focus = focus or next(iter(scan.results), None)


def parse_ex_dividend(text: str) -> tuple[dict[str, list], list[str]]:
    out, errors = {}, []
    for i, line in enumerate((text or "").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            ticker, date = (x.strip() for x in line.split(",")[:2])
            out.setdefault(ticker.upper(), []).append(pd.Timestamp(date))
        except Exception:  # noqa: BLE001
            errors.append(f"Line {i}: expected 'TICKER, YYYY-MM-DD', got '{line}'")
    return out, errors


def run_scan(
    tickers: list[str],
    source: str,
    uploads: list,
    index_file,
    exdiv_text: str,
    as_of: dt.date,
    progress=None,
) -> tuple[Scan | None, list[str], list[str]]:
    """Load data, scan and store the result. Returns (scan or None, errors, warnings)."""
    cfg = copy.deepcopy(config())
    errors, warnings, sources = [], [], []
    universe: dict[str, pd.Series] = {}
    import_gaps: dict[str, list] = {}
    dataset_loaded = False

    if source != "csv":
        try:
            universe.update(cached_universe())
            dataset_loaded = True
            st.session_state.dataset_loaded = True
            sources.append(f"Open NGX dataset (NairaDB, commit {PINNED_COMMIT[:7]}): {len(universe)} stocks.")
        except DatasetUnavailable as exc:
            errors.append(f"Could not load the open dataset: {exc}")
    for f in uploads or []:
        try:
            series, _vol, rep = load_csv(f, gap_business_days=cfg["quality"]["gap_business_days"])
        except CSVFormatError as exc:
            errors.append(str(exc))
            continue
        if len(series) < 2:
            warnings.append(f"{f.name}: no usable rows.")
            continue
        universe[rep.ticker] = series
        import_gaps[rep.ticker] = rep.gaps
        sources.append("Upload " + rep.summary() + ".")
        warnings += [f"{f.name}: {r}" for r in rep.rejected[:5]]

    benchmark = None
    if index_file is not None:
        try:
            idx, _v, _r = load_csv(index_file, ticker="INDEX")
            benchmark = IndexBenchmark(idx, name=index_file.name)
        except CSVFormatError as exc:
            errors.append(f"Index file: {exc}")
    elif dataset_loaded:
        benchmark = cached_market_benchmark(cfg["benchmark"]["min_stocks"], cfg["benchmark"]["trim"])
    elif len(universe) >= cfg["benchmark"]["min_stocks"]:
        benchmark = MarketBenchmark(universe, cfg["benchmark"]["min_stocks"], cfg["benchmark"]["trim"])
    bench_text = (
        benchmark.description
        if benchmark is not None and benchmark.available
        else "not available, so no window can reach Tier 1"
    )

    exdiv, exdiv_errors = parse_ex_dividend(exdiv_text)
    warnings += exdiv_errors
    if errors and not universe:
        return None, errors, warnings

    as_of_ts = pd.Timestamp(as_of)
    results, combined, perm, missing = scan_many(
        tickers, universe, benchmark, cfg, as_of_ts, import_gaps, exdiv, progress=progress
    )
    scan = Scan(tickers, results, combined, perm, missing, as_of_ts, sources, bench_text)
    if results:
        rec = [s for s in recent() if s.tickers != tickers]
        st.session_state.recent = [scan, *rec][:MAX_RECENT]
        open_scan(scan)
    return scan, errors, warnings
