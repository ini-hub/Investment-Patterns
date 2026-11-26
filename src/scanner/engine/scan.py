"""Scan orchestration: one ticker or many."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..config import load_config, settings_hash
from ..version import code_version
from . import classify as cl
from .benchmark import own_average
from .metrics import window_stats
from .quality import QualityReport, check_quality
from .significance import permutation_test
from .windows import Window, last_complete_month, window_returns, windows_from_config


@dataclass
class ScanResult:
    ticker: str
    stats: pd.DataFrame            # one row per window
    yearly: pd.DataFrame           # one row per window-year
    quality: QualityReport
    permutation: dict | None
    meta: dict = field(default_factory=dict)

    def by_class(self, name: str) -> pd.DataFrame:
        return self.stats[self.stats["class"] == name]


def data_hash(series: pd.Series) -> str:
    payload = pd.util.hash_pandas_object(series, index=True).values.tobytes()
    return hashlib.sha256(payload).hexdigest()[:16]


def no_data_message(ticker: str) -> str:
    return f"No price data found for {ticker}"


def completeness_note(last_date: pd.Timestamp, last_complete: pd.Period) -> str:
    """Plain statement of which month, if any, is cut off because the data ends part-way through it."""
    last_month = pd.Timestamp(last_date).to_period("M")
    if last_month <= last_complete:
        return f"Last complete month: {last_complete.strftime('%B %Y')}."
    return (
        f"{last_month.strftime('%B %Y')} is incomplete (data ends {pd.Timestamp(last_date).date()}), "
        f"so windows ending in {last_month.strftime('%B %Y')} or later are excluded. "
        f"Last complete month: {last_complete.strftime('%B %Y')}."
    )


def _covers_ex_dividend(w: Window, quality: QualityReport) -> bool:
    return any(m in quality.ex_dividend_months for m in w.months())


def scan_ticker(
    ticker: str,
    series: pd.Series,
    benchmark=None,
    config: dict | None = None,
    as_of: pd.Timestamp | None = None,
    run_permutation: bool = True,
    import_gaps: list | None = None,
    ex_dividend_dates: list | None = None,
) -> ScanResult:
    cfg = config or load_config()
    c, q = cfg["classification"], cfg["quality"]
    start_year, end_year = cfg["lookback"]["start_year"], cfg["lookback"]["end_year"]
    windows = windows_from_config(cfg)
    if series is None or len(series) < 2:
        raise ValueError(no_data_message(ticker))

    last_complete = last_complete_month(series.index[-1])
    own = own_average(series, windows, last_complete)
    quality = check_quality(series, ticker, q, as_of=as_of, gaps=import_gaps, ex_dividend_dates=ex_dividend_dates)
    market_ok = bool(benchmark is not None and benchmark.available)
    provenance = {"data_hash": data_hash(series), "code_version": code_version(), "settings_hash": settings_hash(cfg)}

    stat_rows, year_rows = [], []
    for w in windows:
        yr = window_returns(series, w, last_complete, start_year, end_year)
        mkt = benchmark.values(w) if market_ok else None
        own_w = {y: v for (L, y), v in own.items() if L == w.length} if w.length < 12 else None
        st = window_stats(yr, mkt, own_w)
        st.update({"ticker": ticker, "window": w.name, "kind": w.kind, "start_month": w.start_month,
                   "length": w.length, "is_quarter": w.is_quarter})
        klass, note = cl.classify(st, c, market_available=market_ok)
        flags = []
        if st["n"] < c["min_years"]:
            flags.append("Insufficient history")
        if quality.frozen and klass in (cl.TIER1, cl.TIER2, cl.WATCH, cl.EMERGING, cl.NEGATIVE):
            flags.append("Unreliable: frozen price")
        if _covers_ex_dividend(w, quality) and w.length < 12:
            flags.append("Covers an ex-dividend month: price-only return understates the holder's return")
        st["class"], st["note"], st["flags"] = klass, note, "; ".join(flags)
        st["score"] = cl.score(st, c) if st["n"] else np.nan
        stat_rows.append(st)
        for row in yr.itertuples(index=False):
            year_rows.append({
                "ticker": ticker, "window": w.name, "year": int(row.year),
                "entry_date": row.entry_date, "entry_price": row.entry_price,
                "exit_date": row.exit_date, "exit_price": row.exit_price,
                "return": row.ret, "dip": row.dip,
                "market": mkt.get(int(row.year), np.nan) if mkt else np.nan,
                "own_average": own_w.get(int(row.year), np.nan) if own_w else np.nan,
                **provenance,
            })

    stats = cl.sort_stats(pd.DataFrame(stat_rows).assign(**provenance))
    yearly = pd.DataFrame(year_rows)

    perm = None
    if run_permutation and cfg["significance"]["runs"] > 0:
        perm = permutation_test(
            {ticker: series}, {ticker: last_complete}, sorted({w.length for w in windows}), c,
            cfg["significance"]["runs"], cfg["significance"]["seed"], start_year, end_year,
        )

    meta = {
        "ticker": ticker,
        "first_date": series.index[0],
        "last_date": series.index[-1],
        "last_complete_month": str(last_complete),
        "completeness": completeness_note(series.index[-1], last_complete),
        "benchmark": benchmark.description if market_ok else "Not available",
        **provenance,
        "windows": len(windows),
        "config": cfg,
    }
    return ScanResult(ticker, stats, yearly, quality, perm, meta)


def scan_many(
    tickers: list[str],
    universe: dict[str, pd.Series],
    benchmark=None,
    config: dict | None = None,
    as_of: pd.Timestamp | None = None,
    import_gaps: dict | None = None,
    ex_dividend_dates: dict | None = None,
) -> tuple[dict[str, ScanResult], pd.DataFrame, dict | None, list[str]]:
    """Scan several tickers. Returns (results, combined stats, combined permutation, missing tickers)."""
    cfg = config or load_config()
    results, missing = {}, []
    for t in tickers:
        if t not in universe:
            missing.append(t)
            continue
        results[t] = scan_ticker(t, universe[t], benchmark, cfg, as_of, run_permutation=False,
                                 import_gaps=(import_gaps or {}).get(t),
                                 ex_dividend_dates=(ex_dividend_dates or {}).get(t))
    combined = pd.concat([r.stats for r in results.values()], ignore_index=True) if results else pd.DataFrame()
    if not combined.empty:
        combined = cl.sort_stats(combined)
    perm = None
    if results and cfg["significance"]["runs"] > 0:
        lengths = sorted({w.length for w in windows_from_config(cfg)})
        perm = permutation_test(
            {t: universe[t] for t in results},
            {t: last_complete_month(universe[t].index[-1]) for t in results},
            lengths, cfg["classification"], cfg["significance"]["runs"], cfg["significance"]["seed"],
            cfg["lookback"]["start_year"], cfg["lookback"]["end_year"],
        )
    return results, combined, perm, missing
