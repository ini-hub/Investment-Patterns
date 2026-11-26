"""Build the data files for the public static site (invest.bolujo.com).

    python -m scanner.publish --out site/data

Scans every stock in the pinned dataset with the default settings and writes:

- index.json            summary of every stock, every classified window, and the market-wide chance check
- stocks/<TICKER>.json  one stock's statistics, year-by-year returns and data-quality notes

Only returns and statistics are published, never closing prices (docs/SCOPE.md 7.3: the dataset has no
licence and NGX may require a redistribution licence for price data).
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .config import load_config, settings_hash
from .data import company_name, load_securities, load_universe
from .data.nairadb_loader import PINNED_COMMIT
from .engine import MarketBenchmark, scan_many
from .report.method import CAVEATS, CLASSES, METHOD
from .version import code_version

RISING = ["Tier 1", "Tier 2", "Watch", "Emerging"]
UNCLASSIFIED = ["None", "Insufficient history"]
# Every field written for a window. Nothing here is a price.
WINDOW_FIELDS = [
    "window", "kind", "start_month", "length", "class", "note", "flags", "n", "up", "hit_rate", "streak",
    "longest_streak", "median", "mean", "worst", "best", "std", "beat_market", "market_n", "median_ex_market",
    "beat_own", "own_n", "median_ex_own", "median_dip", "worst_dip", "p_up", "p_own", "score",
]  # fmt: skip
COMPACT_FIELDS = ["window", "start_month", "length", "class", "n", "up", "streak", "median", "worst",
                  "beat_market", "market_n", "median_dip", "flags", "score"]  # fmt: skip
YEAR_FIELDS = ["year", "return", "dip", "market", "own_average"]
FORBIDDEN = {"entry_price", "exit_price", "close", "price", "entry_date", "exit_date"}


def _clean(v):
    """JSON-safe value: NaN -> None, numpy -> Python, floats rounded to 6 places."""
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return None if math.isnan(v) else round(float(v), 6)
    if isinstance(v, (pd.Timestamp,)):
        return str(v.date())
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v


def _rows(df: pd.DataFrame, fields: list[str]) -> list[dict]:
    cols = [f for f in fields if f in df.columns]
    return [{k: _clean(v) for k, v in rec.items()} for rec in df[cols].to_dict("records")]


def _perm(p: dict | None) -> dict | None:
    if not p:
        return None
    return {k: _clean(p[k]) for k in ("actual", "null_mean", "null_p95", "share_at_or_above", "runs", "seed")}


def stock_document(r) -> dict:
    s, y, q = r.stats, r.yearly, r.quality
    years: dict[str, list] = {}
    for w, g in y.sort_values("year").groupby("window", sort=False):
        years[w] = [[_clean(v) for v in row] for row in g[YEAR_FIELDS].itertuples(index=False)]
    return {
        "ticker": r.ticker,
        "name": company_name(r.ticker),
        "first_date": str(pd.Timestamp(r.meta["first_date"]).date()),
        "last_date": str(pd.Timestamp(r.meta["last_date"]).date()),
        "last_complete_month": r.meta["last_complete_month"],
        "completeness": r.meta["completeness"],
        "data_hash": r.meta["data_hash"],
        "quality": {
            "frozen": bool(q.frozen),
            "zero_change_share": _clean(q.zero_change_share),
            "large_moves": [[str(d.date()), _clean(m)] for d, m in q.corporate_actions],
            "gaps": len(q.gaps),
            "missing_years": list(q.missing_years),
        },
        "permutation": _perm(r.permutation),
        "windows": _rows(s, WINDOW_FIELDS),
        "years": years,
        "year_fields": YEAR_FIELDS,
    }


def stock_summary(r) -> dict:
    s = r.stats
    counts = s["class"].value_counts()
    ranked = s[s["class"].isin(RISING)]
    best = ranked.iloc[0] if not ranked.empty else None
    sec = load_securities()
    return {
        "ticker": r.ticker,
        "name": company_name(r.ticker),
        "sector": sec.at[r.ticker, "sector"] if r.ticker in sec.index else "",
        "years": int(s["n"].max()) if len(s) else 0,
        "frozen": bool(r.quality.frozen),
        "counts": {k: int(counts.get(k, 0)) for k in [*RISING, "Negative"]},
        "best": None if best is None else {k: _clean(best[k]) for k in ("window", "class", "up", "n", "median")},
        "chance": _clean(r.permutation["share_at_or_above"]) if r.permutation else None,
        "classified": _rows(s[~s["class"].isin(UNCLASSIFIED)], COMPACT_FIELDS),
    }


def publish(out: Path, universe: dict[str, pd.Series] | None = None, config: dict | None = None,
            log=print) -> dict:  # fmt: skip
    """Scan every stock and write the site's data files. Returns the index document."""
    t0 = time.time()
    universe = universe if universe is not None else load_universe()
    cfg = config or load_config()
    bench = MarketBenchmark(universe, cfg["benchmark"]["min_stocks"], cfg["benchmark"]["trim"])
    tickers = sorted(universe)

    def progress(i, n, label):
        if i % 25 == 0 or i == n:
            log(f"[{time.time() - t0:5.0f}s] {label} ({min(i + 1, n)} of {n})")

    results, _combined, perm, _missing = scan_many(tickers, universe, bench, cfg, progress=progress)
    out = Path(out)
    (out / "stocks").mkdir(parents=True, exist_ok=True)
    for t, r in results.items():
        _write(out / "stocks" / f"{t}.json", stock_document(r))
    last = max(s.index[-1] for s in universe.values())
    index = {
        "snapshot_date": str(pd.Timestamp(last).date()),
        "last_complete_month": next(iter(results.values())).meta["last_complete_month"] if results else None,
        "source": f"NairaDB open dataset (github.com/kennybix/NairaDB), commit {PINNED_COMMIT[:7]}, unadjusted closes",
        "benchmark": bench.description if bench.available else "not available",
        "code_version": code_version(),
        "settings_hash": settings_hash(cfg),
        "settings": cfg,
        "permutation": _perm(perm),
        "method": METHOD,
        "classes": CLASSES,
        "caveats": CAVEATS,
        "stocks": [stock_summary(results[t]) for t in tickers if t in results],
    }
    _write(out / "index.json", index)
    log(f"[{time.time() - t0:5.0f}s] wrote {len(results)} stocks to {out}")
    return index


def _write(path: Path, doc: dict) -> None:
    text = json.dumps(doc, separators=(",", ":"), ensure_ascii=False, default=_clean)
    leaked = [k for k in FORBIDDEN if f'"{k}"' in text]
    if leaked:  # guard: prices must never be published
        raise RuntimeError(f"refusing to write {path}: contains {leaked}")
    path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="site/data", help="output folder (default: site/data)")
    args = ap.parse_args(argv)
    publish(Path(args.out))


if __name__ == "__main__":
    main()
