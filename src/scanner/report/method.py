"""Plain-language method and caveats, included in every report (docs/SCOPE.md 8.8)."""
from __future__ import annotations

METHOD = [
    "Month-end price: the last available daily close in each calendar month.",
    "Window return: the month-end close of the window's last month divided by the month-end close of "
    "the month before the window starts, minus 1. A window is labelled by the year it starts in, so "
    "Nov 2024 to Jan 2025 counts as 2024.",
    "Only complete windows are used. A month is complete when the data reaches its last business day.",
    "Dip inside window: the lowest daily close inside the window compared with the entry close.",
    "Beat market: the window return was higher than the market benchmark for the same window and year.",
    "Beat own average: the window return was higher than the average of the stock's 12 rolling windows "
    "of the same length in that year. This removes the stock's general trend.",
    "Permutation test: monthly returns are shuffled within each year many times to see how many "
    "patterns appear by chance alone.",
]

CLASSES = [
    "Tier 1: at least 8 years, up in 80% or more, beat its own average in 70% or more, median gain 5% "
    "or more, current streak of 4 or more years, and beat the market in two thirds of years or more.",
    "Tier 2: meets the Tier 1 consistency tests but not the streak or market test.",
    "Watch: up in 70% or more of years, median 5% or more, beat its own average in 60% or more, "
    "streak of 3 or more years.",
    "Emerging: does not qualify above, but up in each of the last 5 or more years with a median of 5% or more. "
    "This can apply to a stock with fewer than 8 years of history; such windows keep the Insufficient history flag.",
    "Negative: up in 20% or fewer of years with a median of -5% or worse. Useful as exit or avoid windows.",
    "Insufficient history: fewer than 8 complete years and no Emerging streak.",
    "Unreliable: any classified window on a stock with frozen prices (more than 30% of month-to-month "
    "changes exactly 0%).",
]

CAVEATS = [
    "Past seasonal behaviour does not guarantee future results. This report is research, not investment advice.",
    "Prices are not adjusted for dividends or bonus issues. Windows that include an ex-dividend date "
    "look weaker than the return a holder actually received.",
    "Results exclude brokerage, fees, slippage and the exchange's daily price limits.",
    "An unchanged price does not always mean no trading; check volume before acting on illiquid stocks.",
]


def method_markdown(config: dict) -> str:
    c = config["classification"]
    lines = ["**Method**", *[f"- {m}" for m in METHOD], "", "**Classes (current thresholds)**"]
    lines += [f"- {x}" for x in CLASSES]
    lines += [
        "",
        f"Thresholds in use: minimum years {c['min_years']}, candidate hit rate {c['candidate_hit_rate']:.0%}, "
        f"own-average rate {c['candidate_own_rate']:.0%}, minimum median {c['candidate_min_median']:.0%}, "
        f"Tier 1 streak {c['tier1_min_streak']}, Tier 1 market rate {c['tier1_market_rate']:.1%}; "
        f"Watch hit rate {c['watch_hit_rate']:.0%}, own-average rate {c['watch_own_rate']:.0%}, "
        f"median {c['watch_min_median']:.0%}, streak {c['watch_min_streak']}; "
        f"Negative hit rate at most {c['negative_max_hit_rate']:.0%}, median at most {c['negative_max_median']:.0%}; "
        f"Emerging streak {c['emerging_min_streak']}, median {c['emerging_min_median']:.0%}.",
        "",
        "**Caveats**",
        *[f"- {x}" for x in CAVEATS],
    ]
    return "\n".join(lines)
