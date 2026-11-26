"""Price-series validation shared by all loaders."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class ImportReport:
    ticker: str
    rows_read: int = 0
    rows_used: int = 0
    rejected: list[str] = field(default_factory=list)
    duplicates_removed: int = 0
    first_date: pd.Timestamp | None = None
    last_date: pd.Timestamp | None = None
    gaps: list[tuple[pd.Timestamp, pd.Timestamp, int]] = field(default_factory=list)

    def summary(self) -> str:
        if self.rows_used == 0:
            return f"{self.ticker}: no usable rows"
        parts = [
            f"{self.ticker}: {self.rows_used} rows used",
            f"{self.first_date.date()} to {self.last_date.date()}",
        ]
        if self.rejected:
            parts.append(f"{len(self.rejected)} rows rejected")
        if self.duplicates_removed:
            parts.append(f"{self.duplicates_removed} duplicate dates removed")
        if self.gaps:
            parts.append(f"{len(self.gaps)} gaps longer than the threshold")
        return ", ".join(parts)


def clean_series(raw: pd.Series, ticker: str, gap_business_days: int = 10) -> tuple[pd.Series, ImportReport]:
    """Validate a date-indexed close series.

    Rules (docs/SCOPE.md 7.2): reject non-positive or missing prices, keep the last
    value for duplicate dates, sort ascending, report long gaps.
    """
    report = ImportReport(ticker=ticker, rows_read=len(raw))
    s = raw.copy()
    s.index = pd.to_datetime(s.index).tz_localize(None) if getattr(s.index, "tz", None) else pd.to_datetime(s.index)
    s = pd.to_numeric(s, errors="coerce")

    bad = s.isna() | (s <= 0)
    for idx, val in s[bad].items():
        report.rejected.append(f"{pd.Timestamp(idx).date()}: invalid close {raw.get(idx, val)!r}")
    s = s[~bad]

    s = s.sort_index(kind="mergesort")
    dup = s.index.duplicated(keep="last")
    report.duplicates_removed = int(dup.sum())
    s = s[~dup].astype(float)
    s.name = ticker

    report.rows_used = len(s)
    if len(s):
        report.first_date, report.last_date = s.index[0], s.index[-1]
        if len(s) > 1:
            bdays = np.busday_count(
                s.index[:-1].values.astype("datetime64[D]"), s.index[1:].values.astype("datetime64[D]")
            )
            for i in np.where(bdays > gap_business_days)[0]:
                report.gaps.append((s.index[i], s.index[i + 1], int(bdays[i])))
    return s, report
