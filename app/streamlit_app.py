"""Investment Patterns: NGX seasonal pattern scanner (Phase 1 web app).

Run from the repository root:  streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Investment Patterns", layout="wide", initial_sidebar_state="collapsed")

import state  # noqa: E402  (set_page_config must come first)
import ui  # noqa: E402

# Streamlit forgets a widget's value when its page is not shown. Settings widgets use keys
# starting with "w_"; re-assigning them on every run keeps them across page changes.
for _k in [k for k in st.session_state if str(k).startswith("w_")]:
    st.session_state[_k] = st.session_state[_k]

PAGES = {
    "scan": st.Page("views/scan.py", title="Scan", url_path="scan", default=True),
    "results": st.Page("views/results.py", title="Results", url_path="results"),
    "compare": st.Page("views/compare.py", title="Compare", url_path="compare"),
}
st.session_state.pages = PAGES
page = st.navigation(list(PAGES.values()), position="hidden")

ui.inject_css()
with st.container(key="topbar", horizontal=True, vertical_alignment="center", gap="medium"):
    ui.md('<span class="ip-brand">Investment Patterns</span>')
    st.page_link(PAGES["scan"], label="Scan")
    st.page_link(PAGES["compare"], label="Compare")
    ui.md('<span class="ip-soon" title="Arrives in Phase 3">Watchlist (Phase 3)</span>')
    st.space("stretch")
    status = state.dataset_status()
    ui.md(
        f'<div class="ip-status"><span class="ip-dot" aria-hidden="true"></span>{ui.esc(status)}</div>'
        if status
        else '<div class="ip-status">Dataset loads on first scan</div>'
    )

page.run()

ui.md(
    '<p class="ip-muted" style="margin-top:32px">Research tool, not investment advice. '
    "Past seasonal behaviour does not guarantee future results.</p>"
)
