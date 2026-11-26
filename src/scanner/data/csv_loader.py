"""CSV import for daily prices (docs/SCOPE.md 7.2).

Accepts TradingView "Export chart data" files and most broker exports:
one file per ticker, a date column and a close column, optional volume.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

import pandas as pd

from .validation import ImportReport, clean_series

DATE_COLUMNS = ("date", "time", "timestamp")
CLOSE_COLUMNS = ("close", "price", "last")
VOLUME_COLUMNS = ("volume", "vol")


class CSVFormatError(ValueError):
    pass


def ticker_from_filename(name: str) -> str:
    """'NSENG_FCMB, 1D.csv' -> 'FCMB'; 'fcmb.csv' -> 'FCMB'."""
    stem = Path(name).stem
    stem = re.split(r"[,\s]", stem)[0]
    if "_" in stem:
        stem = stem.split("_")[-1]
    if ":" in stem:
        stem = stem.split(":")[-1]
    return stem.upper()


def _find(columns: list[str], options: tuple[str, ...]) -> str | None:
    lower = {c.strip().lower(): c for c in columns}
    for opt in options:
        if opt in lower:
            return lower[opt]
    return None


def _parse_dates(col: pd.Series) -> pd.DatetimeIndex:
    numeric = pd.to_numeric(col, errors="coerce")
    if numeric.notna().all():
        unit = "ms" if numeric.max() > 1e11 else "s"
        return pd.DatetimeIndex(pd.to_datetime(numeric, unit=unit, utc=True).dt.tz_localize(None).dt.normalize())
    text = col.astype(str).str.strip()
    iso = pd.to_datetime(text, format="ISO8601", errors="coerce", utc=True)
    if iso.notna().all():
        return pd.DatetimeIndex(iso.dt.tz_localize(None).dt.normalize())
    dmy = pd.to_datetime(text, format="%d/%m/%Y", errors="coerce")
    if dmy.notna().all():
        return pd.DatetimeIndex(dmy)
    raise CSVFormatError("Could not read the date column. Use YYYY-MM-DD, DD/MM/YYYY or Unix seconds.")


def load_csv(source, ticker: str | None = None, gap_business_days: int = 10):
    """Load one CSV (path, bytes or file-like).

    Returns (close_series, volume_series_or_None, ImportReport).
    """
    if isinstance(source, (str, Path)):
        name = str(source)
        df = pd.read_csv(source)
    else:
        name = getattr(source, "name", "upload.csv")
        data = source.read() if hasattr(source, "read") else source
        if isinstance(data, bytes):
            data = data.decode("utf-8-sig")
        df = pd.read_csv(io.StringIO(data))
    ticker = (ticker or ticker_from_filename(name)).upper()

    date_col = _find(list(df.columns), DATE_COLUMNS)
    close_col = _find(list(df.columns), CLOSE_COLUMNS)
    if date_col is None or close_col is None:
        raise CSVFormatError(
            f"{name}: needs a date column ({', '.join(DATE_COLUMNS)}) and a close column ({', '.join(CLOSE_COLUMNS)})."
        )
    dates = _parse_dates(df[date_col])
    close = pd.Series(df[close_col].values, index=dates)
    series, report = clean_series(close, ticker, gap_business_days)

    vol_col = _find(list(df.columns), VOLUME_COLUMNS)
    volume = None
    if vol_col is not None:
        volume = pd.Series(pd.to_numeric(df[vol_col], errors="coerce").values, index=dates)
        volume = volume[~volume.index.duplicated(keep="last")].reindex(series.index)
    return series, volume, report


__all__ = ["load_csv", "ticker_from_filename", "CSVFormatError", "ImportReport"]
