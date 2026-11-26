"""Screen 3: compare several stocks."""

from __future__ import annotations

import re

import state
import streamlit as st
import ui

from scanner.engine import describe_permutation
from scanner.report import calendar_table, pdf_report, run_manifest, stats_csv

scan = state.current()
if scan is None or not scan.multi:
    ui.page_title("Compare stocks")
    st.write("Pick two to six tickers on the Scan screen and choose **Compare** to see them side by side.")
    if scan is not None and scan.results:
        st.page_link(st.session_state.pages["results"], label="Open the current single-stock results")
    st.page_link(st.session_state.pages["scan"], label="Go to Scan", icon=":material/arrow_back:")
    st.stop()

tickers = list(scan.results)
stats, as_of = scan.combined, scan.as_of
stamp = as_of.strftime("%Y%m%d")
name = "_".join(tickers)[:60]


def open_stock(t: str) -> None:
    st.session_state.focus = t
    st.switch_page(st.session_state.pages["results"])


def _key(t: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", t)


# ---------------------------------------------------------------- header
with st.container(horizontal=True, vertical_alignment="bottom"):
    with st.container(gap="small"):
        ui.page_title(f"Comparing {len(tickers)} stocks")
        with st.container(horizontal=True, gap="small", vertical_alignment="center"):
            for t in tickers:
                if st.button(t, key=f"chip_{_key(t)}", help=f"Open {t} results"):
                    open_stock(t)
            st.page_link(st.session_state.pages["scan"], label="Edit list")
    with st.container(horizontal=True, horizontal_alignment="right", width="content"):
        st.download_button("CSV", stats_csv(stats), f"patterns_{name}_{stamp}.csv", "text/csv")
        st.download_button(
            "Run details",
            run_manifest(list(scan.results.values()), scan.permutation, as_of, scan.sources, scan.benchmark),
            f"run_{name}_{stamp}.json",
            "application/json",
        )
        st.download_button(
            "Download PDF",
            pdf_report(list(scan.results.values()), scan.permutation, as_of, "Seasonal scan: " + ", ".join(tickers),
                       [f"Calendar date: {as_of.date()}.", "Benchmark: " + scan.benchmark, *scan.sources]),
            f"report_{name}_{stamp}.pdf", "application/pdf", type="primary",
        )  # fmt: skip

for t in scan.missing:
    st.error(f"No price data found for {t}")
for t, r in scan.results.items():
    if r.quality.frozen:
        ui.callout("warn", f"<strong>{ui.esc(t)}: frozen price.</strong> Its patterns are marked unreliable.")

# ---------------------------------------------------------------- stock cards
with st.container(horizontal=True, wrap=True, gap="small"):
    for t, r in scan.results.items():
        s = r.stats
        counts = s["class"].value_counts()
        ranked = s[s["class"].isin(["Tier 1", "Tier 2", "Watch", "Emerging"])]
        best = (
            f"{ranked.iloc[0]['window']} {ui.ratio(ranked.iloc[0]['up'], ranked.iloc[0]['n'])}, "
            f"median {ui.pct(ranked.iloc[0]['median'])}"
            if not ranked.empty
            else "no rising pattern"
        )
        years = int(s["n"].max()) if len(s) else 0
        pills = "".join(
            ui.badge(k, f"{short} {int(counts.get(k, 0))}")
            for k, short in [("Tier 1", "T1"), ("Tier 2", "T2"), ("Watch", "W"), ("Negative", "Exit")]
        )
        with st.container(key=f"card_s_{_key(t)}", width=190, gap="small"):
            ui.md(
                '<div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px">'
                f'<span class="ip-tk">{ui.esc(t)}</span><span class="ip-muted">{years} yrs</span></div>'
                f'<div style="display:flex;gap:4px;flex-wrap:wrap;margin:8px 0">{pills}</div>'
                f'<p class="ip-muted">Best: <strong style="color:#14171F">{ui.esc(best)}</strong></p>'
            )
            if st.button("Open report", key=f"open_{_key(t)}", type="tertiary", icon=":material/arrow_forward:"):
                open_stock(t)

# ---------------------------------------------------------------- seasonal map
with st.container(key="card_map"):
    st.subheader("Seasonal map", anchor=False)
    ui.md(
        '<p class="ip-muted">Strongest class covering each month. Read down a column to see which stocks move '
        f"together. The dark month is the calendar date ({ui.day(as_of)}).</p>"
    )
    ui.seasonal_map(stats, tickers, as_of)
    cal = calendar_table(stats, as_of, classes=("Tier 1", "Negative"))
    if not cal.empty:
        soon = cal[(cal["Class"] == "Tier 1") & ((cal["Status"] == "Open now") | (cal["Days to entry"] <= 31))]
        exits = cal[(cal["Class"] == "Negative") & (cal["Days to entry"] <= 120)]
        parts = []
        if not soon.empty:

            def _when(r) -> str:
                return "open now" if r["Status"] == "Open now" else "opens " + ui.day(r["Entry (close of)"])

            items = [f"{r['Stock']} {r['Window']} ({_when(r)})" for _, r in soon.iterrows()]
            parts.append("Tier 1 windows open now or opening within a month: " + "; ".join(items) + ".")
        if not exits.empty:
            by_window = exits.groupby("Window", sort=False)["Stock"].apply(lambda s: ", ".join(dict.fromkeys(s)))
            parts.append(
                "Exit or avoid windows in the next four months: "
                + "; ".join(f"{w} for {st_}" for w, st_ in by_window.items())
                + "."
            )
        if parts:
            ui.callout("info", ui.esc(f"As of {ui.day(as_of)}: " + " ".join(parts)))

# ---------------------------------------------------------------- window by window
with st.container(key="card_table"):
    with st.container(horizontal=True, vertical_alignment="center"):
        st.subheader("Window by window", anchor=False)
        st.space("stretch")
        rows = st.segmented_control(
            "Rows to show", ["Patterns only", "All windows"], default="Patterns only", key="cmp_rows",
            label_visibility="collapsed",
        )  # fmt: skip
    ui.compare_table(stats, tickers, patterns_only=rows != "All windows")

# ---------------------------------------------------------------- chance check
perm = scan.permutation
if perm:
    per = [
        f"{t} {r.permutation['actual']} vs {r.permutation['null_mean']:.1f} ({r.permutation['share_at_or_above']:.0%})"
        for t, r in scan.results.items()
        if r.permutation
    ]
    ui.callout(
        "plain",
        "<strong>Chance check (all stocks together):</strong> "
        + ui.esc(describe_permutation(perm))
        + (f"<br><strong>Each stock</strong> (found vs expected, share of shuffles as high): {ui.esc('; '.join(per))}."
           if per else "")
        + "<br>If these stocks were picked because they already showed patterns, this flatters them; "
        "the fair test is a scan of stocks chosen in advance.",
    )  # fmt: skip
else:
    st.caption("Chance check skipped (shuffle runs set to 0 in Settings).")
