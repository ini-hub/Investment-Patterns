"""Screen 2: one stock's results."""

from __future__ import annotations

import pandas as pd
import state
import streamlit as st
import ui

from scanner import code_version, settings_hash
from scanner.data import company_name
from scanner.engine import CLASS_ORDER, describe_permutation
from scanner.report import (
    calendar_table,
    method_markdown,
    pattern_table,
    pdf_report,
    run_manifest,
    stats_csv,
    year_detail,
    yearly_csv,
)

PCT_COLS = {"Median", "Worst year", "Best year", "Std dev", "Median dip", "Worst dip", "Return", "Dip inside window",
            "Market", "Own average"}  # fmt: skip
POSITIVE = ["Tier 1", "Tier 2", "Watch", "Emerging"]

scan = state.current()
if scan is None or not scan.results:
    ui.page_title("No results yet")
    st.page_link(st.session_state.pages["scan"], label="Start a scan", icon=":material/arrow_back:")
    st.stop()

tickers = list(scan.results)
if st.session_state.get("focus") not in scan.results:
    st.session_state.focus = tickers[0]

if scan.multi:
    with st.container(horizontal=True, vertical_alignment="center"):
        st.page_link(st.session_state.pages["compare"], label="Back to comparison", icon=":material/arrow_back:")
        st.space("stretch")
        st.segmented_control("Stock", tickers, key="focus", label_visibility="collapsed", required=True)
else:
    st.page_link(st.session_state.pages["scan"], label="New scan", icon=":material/arrow_back:")

t = st.session_state.focus
r = scan.results[t]
cfg = r.meta["config"]
stats, yearly, as_of = r.stats, r.yearly, scan.as_of
meta = r.meta

# ---------------------------------------------------------------- header
with st.container(horizontal=True, vertical_alignment="center"):
    ui.page_title(t, small=company_name(t))
    with st.container(horizontal=True, horizontal_alignment="right", width="content"):
        if st.button("Add to comparison", icon=":material/add:"):
            current = list(st.session_state.get("w_tickers") or [])
            st.session_state.w_tickers = list(dict.fromkeys([*current, t]))[: state.MAX_COMPARE]
            st.session_state.w_mode = "Compare"
            st.switch_page(st.session_state.pages["scan"])
        stamp = as_of.strftime("%Y%m%d")
        st.download_button("CSV", stats_csv(stats), f"patterns_{t}_{stamp}.csv", "text/csv")
        st.download_button("Run details", run_manifest([r], r.permutation, as_of, scan.sources, scan.benchmark),
                           f"run_{t}_{stamp}.json", "application/json")  # fmt: skip
        st.download_button(
            "Download PDF",
            pdf_report([r], r.permutation, as_of, f"Seasonal scan: {t}",
                       [f"Calendar date: {as_of.date()}.", "Benchmark: " + scan.benchmark, *scan.sources]),
            f"report_{t}_{stamp}.pdf", "application/pdf", type="primary",
        )  # fmt: skip

ui.md(
    f'<p class="ip-muted">Daily closes {ui.day(meta["first_date"])} to {ui.day(meta["last_date"])} · '
    f"{ui.esc(meta['completeness'])} Benchmark: {ui.esc(scan.benchmark)}.</p>"
)

# ---------------------------------------------------------------- warnings
for w in r.quality.warnings():
    head, _, rest = w.partition(":")
    kind = "warn" if head in ("Frozen price", "Stale data") else "plain"
    ui.callout(kind, f"<strong>{ui.esc(head)}:</strong>{ui.esc(rest)}" if rest else ui.esc(w))


# ---------------------------------------------------------------- tiles
def _names(klass: str) -> tuple[str, str]:
    w = stats[stats["class"] == klass]["window"].tolist()
    return str(len(w)), ", ".join(w[:4]) + (" …" if len(w) > 4 else "") or "none"


perm = r.permutation
chance = (
    (f"{perm['share_at_or_above']:.0%}", f"{perm['actual']} found vs {perm['null_mean']:.1f} by chance")
    if perm
    else ("n/a", "chance check skipped")
)
ui.tiles(
    [
        ("Tier 1", *_names("Tier 1")),
        ("Tier 2", *_names("Tier 2")),
        ("Watch", *_names("Watch")),
        ("Exit or avoid", *_names("Negative")),
        ("Chance check", *chance),
    ]
)

# ---------------------------------------------------------------- next window
cal = calendar_table(stats, as_of, classes=("Tier 1", "Tier 2", "Watch", "Negative"))
pos = cal[cal["Class"].isin(["Tier 1", "Tier 2", "Watch"])] if not cal.empty else cal
if not pos.empty:
    up = pos[pos["Status"] == "Upcoming"].sort_values("Days to entry")
    open_now = pos[pos["Status"] == "Open now"]
    parts = []
    if not up.empty:
        n = up.iloc[0]
        parts.append(
            f"<strong>Next window:</strong> {ui.esc(n['Window'])} ({ui.esc(n['Class'])}) opens at the close of "
            f"{ui.day(n['Entry (close of)'])} and closes {ui.day(n['Exit (close of)'])}. "
            f"Up {ui.esc(n['Years up'])} years, median {ui.pct(n['Median'])}."
        )
    if not open_now.empty:
        parts.append(
            "<strong>Open now:</strong> "
            + ", ".join(f"{ui.esc(x['Window'])} ({ui.esc(x['Class'])})" for _, x in open_now.iterrows())
        )
    ui.callout("info", " &nbsp;·&nbsp; ".join(parts))

# ---------------------------------------------------------------- tabs
pos_stats = stats[stats["class"].isin(POSITIVE)]
neg_stats = stats[stats["class"] == "Negative"]
tabs = st.tabs(
    [
        f"Patterns ({len(pos_stats)})",
        f"Exit or avoid ({len(neg_stats)})",
        "Heatmap",
        "Calendar",
        "Year detail",
        "Chance check",
        "All windows",
        "Method",
    ]
)

with tabs[0]:
    ui.pattern_cards(pos_stats, yearly, as_of)
with tabs[1]:
    st.caption("Windows that fell in most years. Useful for timing exits; retail short selling is not generally "
               "available on the NGX.")  # fmt: skip
    ui.pattern_cards(neg_stats, yearly, as_of)
with tabs[2]:
    mode = st.segmented_control(
        "Rows", ["Classified windows", "All windows"], default="Classified windows", key="heat_rows",
        label_visibility="collapsed",
    )  # fmt: skip
    ui.heatmap_table(yearly, stats, classified_only=mode != "All windows")
with tabs[3]:
    st.caption(f"Next or current occurrence of each classified window as of {ui.day(as_of)}. Dates are the last "
               "business day of the month; NGX holidays are not modelled.")  # fmt: skip
    ui.calendar_rows(cal, show_stock=False)
with tabs[4]:
    wsel = st.selectbox("Window", stats.sort_values(["length", "start_month"])["window"].tolist(), key="yd_window")
    row = stats[stats["window"] == wsel].iloc[0]
    ui.md(
        f"<p><strong>{ui.esc(t)} {ui.esc(wsel)}</strong>: {ui.badge(row['class'])} Up in {int(row['up'])} of "
        f"{int(row['n'])} years, median {ui.pct(row['median'])}, mean {ui.pct(row['mean'])}, worst "
        f"{ui.pct(row['worst'])}, best {ui.pct(row['best'])}.</p>"
    )
    detail = year_detail(yearly, wsel)
    for col in detail.columns:
        if col in PCT_COLS:
            detail[col] = detail[col].map(ui.pct)
    st.dataframe(detail, hide_index=True, width="stretch")
with tabs[5]:
    if perm:
        st.markdown(describe_permutation(perm))
        ui.tiles(
            [
                ("Patterns found", str(perm["actual"]), "windows passing the Tier 1 / Tier 2 filter"),
                ("Average by chance", f"{perm['null_mean']:.1f}", f"{perm['runs']} shuffles, seed {perm['seed']}"),
                ("95th percentile", str(perm["null_p95"]), "count reached by the luckiest 5% of shuffles"),
                ("Runs at or above", f"{perm['share_at_or_above']:.0%}", "lower means less likely to be chance"),
            ]
        )
    else:
        st.info("The chance check was skipped (shuffle runs set to 0).")
with tabs[6]:
    table = pattern_table(stats, CLASS_ORDER)
    for col in table.columns:
        if col in PCT_COLS:
            table[col] = table[col].map(lambda v: "" if pd.isna(v) else ui.pct(v))
    st.dataframe(table, hide_index=True, width="stretch")
    st.download_button("Year by year (CSV)", yearly_csv(yearly), f"yearly_{t}_{stamp}.csv", "text/csv")
with tabs[7]:
    st.markdown(method_markdown(cfg))
    st.caption(
        f"Code version {code_version()}. Settings hash {settings_hash(cfg)}. Data hash {meta['data_hash']}. "
        "Sources: " + " ".join(scan.sources)
    )
