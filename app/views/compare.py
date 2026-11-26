"""Screen 3: compare several stocks.

Up to state.CARD_LIMIT stocks: cards and side-by-side columns (design canvas). Above that: a sortable stock
table and a ranked pattern list. Filters and sorting apply to what is shown; exports and the chance check
always cover the whole scan.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
import state
import streamlit as st
import ui

from scanner.data import company_name
from scanner.engine import describe_permutation
from scanner.report import calendar_table, pdf_report, run_manifest, stats_csv
from scanner.report.calendar import next_dates

RISING = ["Tier 1", "Tier 2", "Watch", "Emerging"]
FILTERS = ["Exclude frozen price", "Exclude no rising pattern"]
SORTS = {
    "Most Tier 1": (["t1", "t2", "best_median"], [False, False, False]),
    "Best median": (["best_median"], [False]),
    "Least likely chance": (["chance"], [True]),
    "Most exit windows": (["exits"], [False]),
    "Ticker A to Z": (["ticker"], [True]),
}

scan = state.current()
if scan is None or not scan.multi:
    ui.page_title("Compare stocks")
    st.write("Pick two or more tickers on the Scan screen and choose **Compare** to see them side by side.")
    if scan is not None and scan.results:
        st.page_link(st.session_state.pages["results"], label="Open the current single-stock results")
    st.page_link(st.session_state.pages["scan"], label="Go to Scan", icon=":material/arrow_back:")
    st.stop()

tickers = list(scan.results)
stats, as_of = scan.combined, scan.as_of
stamp = as_of.strftime("%Y%m%d")
name = "_".join(tickers)[:60] if len(tickers) <= state.CARD_LIMIT else f"{len(tickers)}_stocks"


def open_stock(t: str) -> None:
    st.session_state.focus = t
    st.switch_page(st.session_state.pages["results"])


def _key(t: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", t)


# ---------------------------------------------------------------- one summary row per stock
def _summary() -> pd.DataFrame:
    rows = []
    for t, r in scan.results.items():
        s = r.stats
        counts = s["class"].value_counts()
        ranked = s[s["class"].isin(RISING)]
        best = ranked.iloc[0] if not ranked.empty else None
        rows.append(
            {
                "ticker": t,
                "name": company_name(t),
                "years": int(s["n"].max()) if len(s) else 0,
                "frozen": bool(r.quality.frozen),
                "t1": int(counts.get("Tier 1", 0)),
                "t2": int(counts.get("Tier 2", 0)),
                "watch": int(counts.get("Watch", 0)),
                "emerging": int(counts.get("Emerging", 0)),
                "exits": int(counts.get("Negative", 0)),
                "rising": best is not None,
                "best_window": best["window"] if best is not None else "",
                "best_class": best["class"] if best is not None else "",
                "best_up": ui.ratio(best["up"], best["n"]) if best is not None else "",
                "best_median": float(best["median"]) if best is not None else np.nan,
                "chance": r.permutation["share_at_or_above"] if r.permutation else np.nan,
            }
        )
    return pd.DataFrame(rows)


summary = _summary()

# ---------------------------------------------------------------- header
with st.container(horizontal=True, vertical_alignment="bottom"):
    with st.container(gap="small"):
        ui.page_title(f"Comparing {len(tickers)} stocks")
        with st.container(horizontal=True, gap="small", vertical_alignment="center"):
            if len(tickers) <= state.CARD_LIMIT:
                for t in tickers:
                    if st.button(t, key=f"chip_{_key(t)}", help=f"Open {t} results"):
                        open_stock(t)
            st.page_link(st.session_state.pages["scan"], label="Edit list")
    with st.container(horizontal=True, horizontal_alignment="right", width="content"):
        st.download_button("CSV", stats_csv(stats), f"patterns_{name}_{stamp}.csv", "text/csv",
                           help="Every scanned stock, whatever the filters")  # fmt: skip
        st.download_button(
            "Run details",
            run_manifest(list(scan.results.values()), scan.permutation, as_of, scan.sources, scan.benchmark),
            f"run_{name}_{stamp}.json",
            "application/json",
        )
        st.download_button(
            "Download PDF",
            pdf_report(list(scan.results.values()), scan.permutation, as_of,
                       "Seasonal scan: " + (", ".join(tickers) if len(tickers) <= state.CARD_LIMIT
                                            else f"{len(tickers)} stocks"),
                       [f"Calendar date: {as_of.date()}.", "Benchmark: " + scan.benchmark, *scan.sources]),
            f"report_{name}_{stamp}.pdf", "application/pdf", type="primary",
        )  # fmt: skip

for t in scan.missing:
    st.error(f"No price data found for {t}")

# ---------------------------------------------------------------- filter and sort
with st.container(key="card_filters", horizontal=True, vertical_alignment="center", wrap=True):
    chosen = st.pills("Filters", FILTERS, selection_mode="multi", key="w_cmp_filters", label_visibility="collapsed")
    st.space("stretch")
    sort = st.selectbox("Sort by", list(SORTS), key="w_cmp_sort", width=220)

view = summary
if "Exclude frozen price" in (chosen or []):
    view = view[~view["frozen"]]
if "Exclude no rising pattern" in (chosen or []):
    view = view[view["rising"]]
cols, asc = SORTS[sort or "Most Tier 1"]
view = view.sort_values(cols, ascending=asc, na_position="last", kind="mergesort")
shown = view["ticker"].tolist()

n_frozen = int(summary["frozen"].sum())
note = f"Showing {len(shown)} of {len(tickers)} stocks."
if n_frozen and "Exclude frozen price" not in (chosen or []):
    note += f" {n_frozen} have frozen prices; their patterns are marked unreliable."
ui.md(f'<p class="ip-muted">{ui.esc(note)} Exports and the chance check cover all {len(tickers)} scanned.</p>')

if not shown:
    st.info("No stocks match the filters. Turn a filter off to see them.")

# ---------------------------------------------------------------- stocks
elif len(shown) <= state.CARD_LIMIT:
    with st.container(horizontal=True, wrap=True, gap="small"):
        for _, row in view.iterrows():
            t = row["ticker"]
            pills = "".join(
                ui.badge(k, f"{short} {int(row[col])}")
                for k, short, col in [("Tier 1", "T1", "t1"), ("Tier 2", "T2", "t2"), ("Watch", "W", "watch"),
                                      ("Negative", "Exit", "exits")]
            )  # fmt: skip
            best = (
                f"{row['best_window']} {row['best_up']}, median {ui.pct(row['best_median'])}"
                if row["rising"]
                else "no rising pattern"
            )
            frozen = '<p class="ip-muted" style="color:#9A3412">Frozen price: unreliable</p>' if row["frozen"] else ""
            with st.container(key=f"card_s_{_key(t)}", width=190, gap="small"):
                ui.md(
                    '<div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px">'
                    f'<span class="ip-tk">{ui.esc(t)}</span><span class="ip-muted">{row["years"]} yrs</span></div>'
                    f'<div style="display:flex;gap:4px;flex-wrap:wrap;margin:8px 0">{pills}</div>'
                    f'<p class="ip-muted">Best: <strong style="color:#14171F">{ui.esc(best)}</strong></p>{frozen}'
                )
                if st.button("Open report", key=f"open_{_key(t)}", type="tertiary", icon=":material/arrow_forward:"):
                    open_stock(t)
else:
    with st.container(key="card_stocks"):
        st.subheader("Stocks", anchor=False)
        st.caption("Click a row to open that stock's report. Click a column header to re-sort.")
        table = pd.DataFrame(
            {
                "Stock": view["ticker"],
                "Name": view["name"],
                "Years": view["years"],
                "Tier 1": view["t1"],
                "Tier 2": view["t2"],
                "Watch": view["watch"],
                "Emerging": view["emerging"],
                "Exit": view["exits"],
                "Best window": view["best_window"] + np.where(view["rising"], " (" + view["best_class"] + ")", ""),
                "Years up": view["best_up"],
                "Median": view["best_median"] * 100,
                "Chance": view["chance"] * 100,
                "Frozen": np.where(view["frozen"], "Frozen", ""),
            }
        )
        if (table["Name"] != "").mean() < 0.5:  # names are hand-kept; hide the column while most are missing
            table = table.drop(columns="Name")
        picked = st.dataframe(
            table,
            hide_index=True,
            width="stretch",
            on_select="rerun",
            selection_mode="single-row",
            key="cmp_stock_table",
            column_config={
                "Median": st.column_config.NumberColumn("Best median", format="%+.1f%%"),
                "Chance": st.column_config.NumberColumn(
                    "Chance check",
                    format="%.0f%%",
                    help="Share of shuffled runs with as many patterns (lower is better)",
                ),
            },
        )
        rows = picked.selection.rows if picked and picked.selection else []
        if rows:
            open_stock(table.iloc[rows[0]]["Stock"])

# ---------------------------------------------------------------- seasonal map
if shown:
    with st.container(key="card_map"):
        st.subheader("Seasonal map", anchor=False)
        ui.md(
            '<p class="ip-muted">Strongest class covering each month. Read down a column to see which stocks move '
            f"together. The dark month is the calendar date ({ui.day(as_of)}).</p>"
        )
        ui.seasonal_map(stats, shown, as_of)
        cal = calendar_table(stats[stats["ticker"].isin(shown)], as_of, classes=("Tier 1", "Negative"))
        if not cal.empty:
            soon = cal[(cal["Class"] == "Tier 1") & ((cal["Status"] == "Open now") | (cal["Days to entry"] <= 31))]
            exits = cal[(cal["Class"] == "Negative") & (cal["Days to entry"] <= 120)]
            parts = []

            def _cap(items: list[str], limit: int = 12) -> str:
                more = f"; and {len(items) - limit} more" if len(items) > limit else ""
                return "; ".join(items[:limit]) + more

            if not soon.empty:

                def _when(r) -> str:
                    return "open now" if r["Status"] == "Open now" else "opens " + ui.day(r["Entry (close of)"])

                items = [f"{r['Stock']} {r['Window']} ({_when(r)})" for _, r in soon.iterrows()]
                parts.append("Tier 1 windows open now or opening within a month: " + _cap(items) + ".")
            if not exits.empty:
                by_window = exits.groupby("Window", sort=False)["Stock"].apply(lambda s: ", ".join(dict.fromkeys(s)))
                items = [f"{w} for {s}" for w, s in by_window.items()]
                parts.append("Exit or avoid windows in the next four months: " + _cap(items, 6) + ".")
            if parts:
                ui.callout("info", ui.esc(f"As of {ui.day(as_of)}: " + " ".join(parts)))

# ---------------------------------------------------------------- windows
if shown and len(shown) <= state.CARD_LIMIT:
    with st.container(key="card_table"):
        with st.container(horizontal=True, vertical_alignment="center"):
            st.subheader("Window by window", anchor=False)
            st.space("stretch")
            rows = st.segmented_control(
                "Rows to show", ["Patterns only", "All windows"], default="Patterns only", key="cmp_rows",
                label_visibility="collapsed",
            )  # fmt: skip
        ui.compare_table(stats, shown, patterns_only=rows != "All windows")
elif shown:
    with st.container(key="card_ranked"):
        with st.container(horizontal=True, vertical_alignment="center"):
            st.subheader("Ranked patterns", anchor=False)
            st.space("stretch")
            kind = st.segmented_control(
                "Patterns to show", ["Rising", "Exit or avoid"], default="Rising", key="cmp_ranked",
                label_visibility="collapsed",
            )  # fmt: skip
        classes = ["Negative"] if kind == "Exit or avoid" else RISING
        p = stats[stats["ticker"].isin(shown) & stats["class"].isin(classes)]
        if p.empty:
            st.caption("None among the stocks shown.")
        else:
            entry = [
                next_dates(int(r.start_month), int(r.length), as_of) if r.length < 12 else (pd.NaT, pd.NaT, "")
                for r in p.itertuples()
            ]
            ranked = pd.DataFrame(
                {
                    "Stock": p["ticker"],
                    "Window": p["window"],
                    "Class": p["class"].replace({"Negative": "Exit or avoid"}),
                    "Years up": [ui.ratio(u, n) for u, n in zip(p["up"], p["n"], strict=True)],
                    "Streak": p["streak"],
                    "Median": p["median"] * 100,
                    "Worst year": p["worst"] * 100,
                    "Beat market": [ui.ratio(b, n) for b, n in zip(p["beat_market"], p["market_n"], strict=True)],
                    "Median dip": p["median_dip"] * 100,
                    "Status": [e[2] for e in entry],
                    "Entry close": [e[0].date() if pd.notna(e[0]) else None for e in entry],
                    "Flags": p["flags"],
                }
            )
            pct = st.column_config.NumberColumn
            picked = st.dataframe(
                ranked,
                hide_index=True,
                width="stretch",
                height=min(38 + 35 * len(ranked), 600),
                on_select="rerun",
                selection_mode="single-row",
                key="cmp_ranked_table",
                column_config={
                    "Median": pct(format="%+.1f%%"),
                    "Worst year": pct(format="%+.1f%%"),
                    "Median dip": pct(format="%+.1f%%"),
                },
            )
            st.caption(f"{len(ranked)} windows, strongest first. Click a row to open that stock's report.")
            rows = picked.selection.rows if picked and picked.selection else []
            if rows:
                open_stock(ranked.iloc[rows[0]]["Stock"])

# ---------------------------------------------------------------- chance check
perm = scan.permutation
if perm:
    per = [
        f"{t} {r.permutation['actual']} vs {r.permutation['null_mean']:.1f} ({r.permutation['share_at_or_above']:.0%})"
        for t, r in scan.results.items()
        if r.permutation
    ]
    each = (
        f"<br><strong>Each stock</strong> (found vs expected, share of shuffles as high): {ui.esc('; '.join(per))}."
        if per and len(tickers) <= state.CARD_LIMIT
        else "<br>Each stock's own figure is in the Chance check column above and on its report."
        if per
        else ""
    )
    ui.callout(
        "plain",
        f"<strong>Chance check (all {len(tickers)} scanned stocks together, whatever the filters):</strong> "
        + ui.esc(describe_permutation(perm))
        + each
        + "<br>If these stocks were picked because they already showed patterns, this flatters them; "
        "the fair test is a scan of stocks chosen in advance, or of the whole market.",
    )
else:
    st.caption("Chance check skipped (shuffle runs set to 0 in Settings).")
