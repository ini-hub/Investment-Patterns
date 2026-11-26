"""Heatmap of window returns: windows as rows, years as columns.

Diverging scale (orange for losses, neutral grey at 0%, blue for gains). Blue and orange
also differ in lightness, so it reads for common colour-vision deficiencies; every cell also prints its value.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

NEG, MID, POS = "#C2410C", "#F1F3F6", "#1D4ED8"
TEXT = "#191919"


def heatmap_figure(yearly: pd.DataFrame, stats: pd.DataFrame, title: str = "", cap: float = 0.5) -> go.Figure:
    """cap: colour saturates at +/- this return so one extreme year does not wash out the rest."""
    order = stats.sort_values(["length", "start_month"])["window"].tolist()
    pivot = yearly.pivot_table(index="window", columns="year", values="return", aggfunc="first")
    pivot = pivot.reindex([w for w in order if w in pivot.index])
    z = pivot.to_numpy(dtype=float)
    text = np.where(np.isnan(z), "", np.vectorize(lambda v: f"{v:+.0%}")(np.nan_to_num(z)))
    klass = stats.set_index("window")["class"].reindex(pivot.index)
    ylabels = [f"{w}  ({k})" if k not in ("None", "Insufficient history") else w for w, k in klass.items()]

    fig = go.Figure(
        go.Heatmap(
            z=np.clip(z, -cap, cap),
            x=[str(c) for c in pivot.columns],
            y=ylabels,
            text=text,
            texttemplate="%{text}",
            textfont={"size": 10, "color": TEXT},
            customdata=z,
            hovertemplate="%{y}<br>%{x}: %{customdata:+.1%}<extra></extra>",
            colorscale=[[0, NEG], [0.5, MID], [1, POS]],
            zmin=-cap,
            zmax=cap,
            zmid=0,
            xgap=2,
            ygap=2,
            colorbar={"title": "Return", "tickformat": "+.0%"},
        )
    )
    fig.update_layout(
        title=title,
        height=max(420, 22 * len(ylabels) + 120),
        margin={"l": 10, "r": 10, "t": 50 if title else 20, "b": 30},
        yaxis={"autorange": "reversed", "tickfont": {"size": 11}},
        xaxis={"side": "top", "type": "category"},
        plot_bgcolor="#ffffff",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig
