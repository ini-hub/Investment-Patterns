"""Loader for the open NairaDB dataset (github.com/kennybix/NairaDB).

The dataset has no licence file, so it is NOT stored in this repository.
It is downloaded at runtime into a local cache folder (ignored by git) and
pinned to a fixed commit so results are reproducible.

Contents: daily, unadjusted closing prices for about 147 NGX stocks,
late December 2015 to 19 December 2025.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pandas as pd

from .validation import clean_series

REPO_URL = "https://github.com/kennybix/NairaDB.git"
PINNED_COMMIT = "4de805bb7e88f82cc54cdb011e6b019af0ae539f"
DEFAULT_CACHE = Path(os.environ.get("NAIRADB_CACHE", Path.cwd() / "data" / "nairadb"))


class DatasetUnavailable(RuntimeError):
    pass


def _git(*args: str, cwd: Path | None = None) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, timeout=300)


def ensure_dataset(cache_dir: Path | None = None, commit: str = PINNED_COMMIT) -> Path:
    """Return the folder with the *_history.json files, downloading it if needed.

    Set NAIRADB_PATH to use an existing local copy of data/historical instead.
    """
    if os.environ.get("NAIRADB_PATH"):
        path = Path(os.environ["NAIRADB_PATH"])
        if not path.is_dir():
            raise DatasetUnavailable(f"NAIRADB_PATH does not exist: {path}")
        return path

    cache_dir = Path(cache_dir or DEFAULT_CACHE)
    hist = cache_dir / "data" / "historical"
    marker = cache_dir / ".pinned_commit"
    if hist.is_dir() and marker.exists() and marker.read_text().strip() == commit:
        return hist

    if shutil.which("git") is None:
        raise DatasetUnavailable("git is required to download the NairaDB dataset.")
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    cache_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        _git("clone", "--filter=blob:none", "--no-checkout", REPO_URL, str(cache_dir))
        _git("sparse-checkout", "set", "data/historical", cwd=cache_dir)
        _git("checkout", commit, cwd=cache_dir)
    except (subprocess.SubprocessError, OSError) as exc:
        raise DatasetUnavailable(f"Could not download NairaDB: {exc}") from exc
    marker.write_text(commit)
    return hist


def load_universe(path: Path | None = None, gap_business_days: int = 10) -> dict[str, pd.Series]:
    """Load every ticker in the dataset as {TICKER: close series}."""
    hist = Path(path) if path else ensure_dataset()
    universe: dict[str, pd.Series] = {}
    for f in sorted(hist.glob("*_history.json")):
        if f.name.endswith("_full_history.json"):
            continue
        ticker = f.name[: -len("_history.json")].upper()
        with open(f, encoding="utf-8") as fh:
            rows = json.load(fh)["data"]
        raw = pd.Series({pd.Timestamp(r["date"]): r["price"] for r in rows})
        series, _ = clean_series(raw, ticker, gap_business_days)
        if len(series):
            universe[ticker] = series
    if not universe:
        raise DatasetUnavailable(f"No *_history.json files found in {hist}")
    return universe
