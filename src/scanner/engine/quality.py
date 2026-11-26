"""Data-quality checks (docs/SCOPE.md 8.7)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .windows import MONTHS, month_end_prices


@dataclass
class QualityReport:
    ticker: str
    first_date: pd.Timestamp
    last_date: pd.Timestamp
    frozen: bool
    zero_change_share: float
    corporate_actions: list[tuple[pd.Timestamp, float]] = field(default_factory=list)
    ex_dividend_months: dict[int, list[int]] = field(default_factory=dict)  # month -> years (user supplied)
    gaps: list[tuple[pd.Timestamp, pd.Timestamp, int]] = field(default_factory=list)
    missing_years: list[int] = field(default_factory=list)
    stale: bool = False
    stale_business_days: int = 0

    def warnings(self) -> list[str]:
        out = []
        if self.frozen:
            out.append(
                f"Frozen price: {self.zero_change_share:.0%} of month-to-month changes are exactly 0%. "
                "Patterns for this stock are unreliable."
            )
        if self.stale:
            out.append(f"Stale data: the last price is {self.stale_business_days} business days old.")
        if self.missing_years:
            out.append("No prices at all in: " + ", ".join(map(str, self.missing_years)) + ".")
        if self.gaps:
            out.append(f"{len(self.gaps)} gap(s) longer than the threshold between consecutive prices.")
        if self.corporate_actions:
            moves = ", ".join(f"{d.date()} ({m:+.1%})" for d, m in self.corporate_actions[:8])
            more = "" if len(self.corporate_actions) <= 8 else f" and {len(self.corporate_actions) - 8} more"
            out.append(f"Large single-day moves (possible dividend, bonus or data error): {moves}{more}.")
        for m, years in sorted(self.ex_dividend_months.items()):
            out.append(
                f"Ex-dividend dates fall in {MONTHS[m - 1]} ({len(years)} of the years supplied). "
                "Windows covering this month understate the holder's return because prices are unadjusted."
            )
        return out


def check_quality(
    series: pd.Series,
    ticker: str,
    q: dict,
    as_of: pd.Timestamp | None = None,
    gaps: list | None = None,
    ex_dividend_dates: list | None = None,
) -> QualityReport:
    me = month_end_prices(series)
    changes = me.pct_change().dropna()
    zero_share = float((changes == 0).mean()) if len(changes) else 1.0

    daily = series.pct_change().dropna()
    big = daily[daily.abs() > q["corporate_action_move"]]

    exdiv: dict[int, list[int]] = {}
    for d in pd.to_datetime(ex_dividend_dates or []):
        exdiv.setdefault(d.month, []).append(d.year)
    exdiv = {m: sorted(set(y)) for m, y in exdiv.items()}

    all_years = range(series.index[0].year, series.index[-1].year + 1)
    present = set(series.index.year)
    missing = [y for y in all_years if y not in present]

    if gaps is None:
        gaps = []
        if len(series) > 1:
            bd = np.busday_count(
                series.index[:-1].values.astype("datetime64[D]"), series.index[1:].values.astype("datetime64[D]")
            )
            gaps = [
                (series.index[i], series.index[i + 1], int(bd[i])) for i in np.where(bd > q["gap_business_days"])[0]
            ]

    stale, stale_days = False, 0
    if as_of is not None:
        stale_days = int(np.busday_count(series.index[-1].date(), pd.Timestamp(as_of).date()))
        stale = stale_days > q["stale_business_days"]

    return QualityReport(
        ticker=ticker,
        first_date=series.index[0],
        last_date=series.index[-1],
        frozen=zero_share > q["frozen_zero_share"],
        zero_change_share=zero_share,
        corporate_actions=[(d, float(v)) for d, v in big.items()],
        ex_dividend_months=exdiv,
        gaps=gaps,
        missing_years=missing,
        stale=stale,
        stale_business_days=stale_days,
    )
