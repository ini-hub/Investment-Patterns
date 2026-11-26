"""Visual building blocks for the app (design canvas: blue accent, Inter / Space Grotesk, white cards).

Every value that reaches HTML goes through esc(): tickers can be typed by the user.
"""

from __future__ import annotations

import html

import numpy as np
import pandas as pd
import streamlit as st

from scanner.engine.windows import MONTHS
from scanner.report.calendar import next_dates

INK, MUTED, LINE, BG = "#14171F", "#4B5160", "#E3E6EB", "#F6F7F9"
BLUE, BLUE_DARK, BLUE_SOFT, ORANGE = "#1D4ED8", "#1E3A8A", "#EEF2FF", "#C2410C"

BADGE = {
    "Tier 1": ("#1D4ED8", "#FFFFFF"),
    "Tier 2": ("#DBEAFE", "#1E3A8A"),
    "Watch": ("#E5E7EB", "#1F2937"),
    "Emerging": ("#F5F3FF", "#4C1D95"),
    "Negative": ("#FFEDD5", "#9A3412"),
    "Open now": ("#DCFCE7", "#14532D"),
    "Upcoming": ("#F1F3F6", "#374151"),
    "None": ("#FFFFFF", "#4B5160"),
    "Insufficient history": ("#FFFFFF", "#4B5160"),
}
LABEL = {"Negative": "Exit or avoid"}
MAP_FILL = {"Tier 1": "#1D4ED8", "Tier 2": "#93B4F5", "Watch": "#D1D5DB", "Negative": "#EA7A3D", "": "#F1F3F6"}
POSITIVE = ["Tier 1", "Tier 2", "Watch"]

CSS = f"""
<style>
[data-testid="stSidebarCollapsedControl"], [data-testid="stSidebar"] {{ display: none; }}
.block-container {{ max-width: 1200px; padding-top: 1.25rem; padding-bottom: 4rem; }}
h1, h2, h3 {{ letter-spacing: -0.01em; }}
.stButton button, .stDownloadButton button, [data-testid="stPageLink"] a {{ min-height: 44px; }}
[class*="st-key-card"] {{
  background: #FFFFFF; border: 1px solid {LINE}; border-radius: 14px; padding: 20px 24px;
}}
.st-key-topbar {{
  background: #FFFFFF; border: 1px solid {LINE}; border-radius: 14px; padding: 6px 16px; margin-bottom: 8px;
}}
.st-key-topbar [data-testid="stPageLink"] a {{ padding: 4px 12px; }}
.st-key-topbar [data-testid="stMarkdownContainer"] > div, .st-key-topbar .ip-status {{ margin: 0; }}
.st-key-topbar [data-testid="stElementContainer"] {{ margin-bottom: 0; }}
.st-key-w_source [role="radiogroup"] {{ gap: 12px; flex-wrap: wrap; }}
.st-key-w_source [role="radiogroup"] > div {{
  flex: 1 1 240px; align-items: flex-start; background: #FFFFFF; border: 1px solid #D5D9E0;
  border-radius: 12px; padding: 16px 18px; margin: 0; min-height: 96px;
}}
.st-key-w_source [role="radiogroup"] > div:has(input:checked) {{
  border: 2px solid {BLUE}; background: #F5F8FF; padding: 15px 17px;
}}
.st-key-quickpicks button {{
  min-height: 36px; padding: 6px 12px; border-radius: 18px; border: 1px solid #D5D9E0; background: #FFFFFF;
}}
.st-key-quickpicks button:hover {{ border-color: {BLUE}; }}
.ip-brand {{ font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 18px; color: {INK}; }}
.ip-status {{ font-size: 13px; color: {MUTED}; display: flex; align-items: center; gap: 8px;
  justify-content: flex-end; }}
.ip-dot {{ width: 8px; height: 8px; border-radius: 4px; background: #16A34A; display: inline-block; }}
.ip-soon {{ font-size: 14px; color: #8A909C; }}
.ip-h1 {{ font-family: 'Space Grotesk', sans-serif; font-size: 34px; line-height: 1.15; font-weight: 700;
  margin: 0; color: {INK}; }}
.ip-h1 small {{ font-weight: 500; color: {MUTED}; font-size: 20px; }}
.ip-lede {{ font-size: 16px; color: {MUTED}; max-width: 720px; margin: 6px 0 0; }}
.ip-muted {{ font-size: 13px; color: {MUTED}; margin: 0; }}
.ip-badge {{ display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 600;
  white-space: nowrap; }}
.ip-tiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }}
.ip-tile {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 12px; padding: 16px;
  display: flex; flex-direction: column; gap: 4px; }}
.ip-tile .k {{ font-size: 13px; color: {MUTED}; }}
.ip-tile .v {{ font-family: 'Space Grotesk', sans-serif; font-size: 30px; font-weight: 700; color: {INK}; }}
.ip-tile .s {{ font-size: 12px; color: {MUTED}; }}
.ip-callout {{ display: flex; gap: 12px; align-items: flex-start; padding: 14px 16px; border-radius: 12px;
  font-size: 14px; line-height: 1.5; margin-bottom: 8px; }}
.ip-callout.warn {{ background: #FFF7ED; border: 1px solid #FDBA74; color: #7C2D12; }}
.ip-callout.info {{ background: {BLUE_SOFT}; border: 1px solid #C7D2FE; color: {BLUE_DARK}; }}
.ip-callout.plain {{ background: #FFFFFF; border: 1px solid {LINE}; color: {INK}; }}
.ip-callout svg {{ flex: none; margin-top: 1px; }}
.ip-pcard {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 12px; padding: 18px 20px;
  display: flex; flex-wrap: wrap; gap: 20px; align-items: center; margin-bottom: 12px; }}
.ip-pcard .head {{ flex: 1 1 200px; display: flex; flex-direction: column; gap: 6px; align-items: flex-start; }}
.ip-pcard .win {{ font-family: 'Space Grotesk', sans-serif; font-size: 22px; font-weight: 700; color: {INK}; }}
.ip-pcard dl {{ flex: 3 1 420px; margin: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(96px, 1fr));
  gap: 12px; }}
.ip-pcard dt {{ font-size: 12px; color: {MUTED}; }}
.ip-pcard dd {{ margin: 2px 0 0; font-size: 16px; font-weight: 600; color: {INK}; font-variant-numeric: tabular-nums; }}
.ip-pcard .flags {{ flex: 1 1 100%; font-size: 12px; color: #9A3412; margin-top: -8px; }}
.ip-spark {{ flex: 0 1 180px; min-width: 120px; display: flex; gap: 3px; align-items: center; height: 56px; }}
.ip-spark span {{ max-width: 16px; }}
.ip-spark span {{ flex: 1; border-radius: 2px; }}
.ip-scroll {{ overflow-x: auto; background: #FFFFFF; border: 1px solid {LINE}; border-radius: 12px; padding: 12px; }}
.ip-heat {{ border-collapse: separate; border-spacing: 3px; font-size: 13px; min-width: 760px; width: 100%; }}
.ip-heat th {{ font-weight: 600; padding: 6px; color: {INK}; }}
.ip-heat th[scope=row] {{ text-align: left; white-space: nowrap; }}
.ip-heat td {{ padding: 8px 4px; text-align: center; border-radius: 4px; font-variant-numeric: tabular-nums; }}
.ip-list {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 12px; overflow: hidden; }}
.ip-list .row {{ display: flex; flex-wrap: wrap; gap: 16px; align-items: center; padding: 14px 20px;
  border-bottom: 1px solid #EEF0F3; font-size: 14px; color: {INK}; }}
.ip-list .row:last-child {{ border-bottom: 0; }}
.ip-map {{ min-width: 760px; display: grid; grid-template-columns: 120px repeat(12, minmax(0, 1fr)); gap: 4px;
  font-size: 12px; }}
.ip-map .m {{ text-align: center; font-weight: 600; padding: 4px 0; border-radius: 4px; color: {MUTED}; }}
.ip-map .m.now {{ background: {INK}; color: #FFFFFF; }}
.ip-map .t {{ font-weight: 600; font-size: 13px; align-self: center; color: {INK}; }}
.ip-map .c {{ height: 30px; border-radius: 4px; }}
.ip-legend {{ display: flex; flex-wrap: wrap; gap: 12px; font-size: 12px; color: {MUTED}; }}
.ip-legend span {{ display: inline-flex; gap: 6px; align-items: center; }}
.ip-legend i {{ width: 14px; height: 14px; border-radius: 3px; display: inline-block; }}
.ip-cmp {{ width: 100%; min-width: 760px; border-collapse: separate; border-spacing: 4px; font-size: 13px; }}
.ip-cmp th {{ text-align: left; padding: 6px; font-weight: 600; color: {INK}; }}
.ip-cmp td {{ padding: 8px 10px; border-radius: 6px; vertical-align: top; }}
.ip-cmp td b {{ display: block; }}
.ip-cmp td span {{ display: block; font-variant-numeric: tabular-nums; }}
[class*="st-key-card_s_"] {{ padding: 16px; }}
[class*="st-key-card_s_"] .ip-badge {{ padding: 2px 6px; }}
.ip-tk {{ font-family: 'Space Grotesk', sans-serif; font-size: 18px; font-weight: 700; color: {INK}; }}
</style>
"""

ICON_WARN = (
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 9v4M12 17h.01M10.3 3.9'
    'L1.8 18a2 2 0 001.7 3h17a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z"/></svg>'
)
ICON_INFO = (
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 8h.01M11 12h1v5h1"/></svg>'
)


def esc(x) -> str:
    return html.escape("" if x is None else str(x))


def md(fragment: str) -> None:
    st.markdown(fragment, unsafe_allow_html=True)


def inject_css() -> None:
    st.html(CSS)


def pct(v, digits: int = 1, sign: bool = True) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "n/a"
    return f"{v:+.{digits}%}" if sign else f"{v:.{digits}%}"


def ratio(a, b) -> str:
    if a is None or b is None or pd.isna(a) or pd.isna(b) or not b:
        return "n/a"
    return f"{int(a)} / {int(b)}"


def day(ts) -> str:
    ts = pd.Timestamp(ts)
    return f"{ts.day} {ts:%b %Y}"


def badge(klass: str, text: str | None = None) -> str:
    bg, fg = BADGE.get(klass, BADGE["None"])
    border = f"; outline: 1px solid {LINE}" if bg == "#FFFFFF" else ""
    label = esc(text or LABEL.get(klass, klass))
    return f'<span class="ip-badge" style="background:{bg};color:{fg}{border}">{label}</span>'


def callout(kind: str, body_html: str) -> None:
    icon = ICON_WARN if kind == "warn" else ICON_INFO
    md(f'<div class="ip-callout {kind}" role="status">{icon}<div>{body_html}</div></div>')


def page_title(title: str, small: str = "", lede: str = "") -> None:
    sub = f" <small>{esc(small)}</small>" if small else ""
    para = f'<p class="ip-lede">{esc(lede)}</p>' if lede else ""
    md(f'<h1 class="ip-h1">{esc(title)}{sub}</h1>{para}')


def tiles(items: list[tuple[str, str, str]]) -> None:
    cells = "".join(
        f'<div class="ip-tile"><span class="k">{esc(k)}</span><span class="v">{esc(v)}</span>'
        f'<span class="s">{esc(s)}</span></div>'
        for k, v, s in items
    )
    md(f'<div class="ip-tiles">{cells}</div>')


def when_text(row, as_of) -> str:
    if row["length"] >= 12:
        return "Full calendar year"
    entry, exit_, status = next_dates(int(row["start_month"]), int(row["length"]), as_of)
    if status == "Open now":
        return f"Open now · exit close {day(exit_)}"
    return f"Entry close {day(entry)} · exit close {day(exit_)}"


def _spark(yearly: pd.DataFrame, ticker: str, window: str) -> str:
    d = yearly[(yearly["ticker"] == ticker) & (yearly["window"] == window)].sort_values("year")
    if d.empty:
        return ""
    rets = d["return"].to_numpy(dtype=float)
    scale = max(np.nanmax(np.abs(rets)), 0.05)
    bars = "".join(
        f'<span title="{int(y)}: {pct(r)}" style="height:{max(3, min(56, abs(r) / scale * 56)):.0f}px;'
        f'background:{BLUE if r > 0 else ORANGE};align-self:{"flex-end" if r > 0 else "flex-start"}"></span>'
        for y, r in zip(d["year"], rets, strict=True)
    )
    label = f"{window} returns by year, {int(d['year'].iloc[0])} to {int(d['year'].iloc[-1])}"
    return f'<div class="ip-spark" role="img" aria-label="{esc(label)}">{bars}</div>'


def pattern_cards(stats: pd.DataFrame, yearly: pd.DataFrame, as_of) -> None:
    if stats.empty:
        md('<p class="ip-muted">None found with the current settings.</p>')
        return
    out = []
    for _, r in stats.iterrows():
        cells = [
            ("Years up", ratio(r["up"], r["n"])),
            ("Streak", str(int(r["streak"]))),
            ("Median", pct(r["median"])),
            ("Mean", pct(r["mean"])),
            ("Min / max", f"{pct(r['worst'])} / {pct(r['best'])}"),
            ("Std dev", pct(r["std"], sign=False)),
            ("Beat market", ratio(r.get("beat_market"), r.get("market_n"))),
            ("Beat own avg", ratio(r.get("beat_own"), r.get("own_n"))),
            ("Median dip", pct(r["median_dip"])),
        ]
        dl = "".join(f"<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in cells)
        notes = "; ".join(x for x in (r.get("flags") or "", r.get("note") or "") if x)
        flags = f'<div class="flags">{esc(notes)}</div>' if notes else ""
        out.append(
            f'<article class="ip-pcard"><div class="head">{badge(r["class"])}'
            f'<span class="win">{esc(r["window"])}</span><span class="ip-muted">{esc(when_text(r, as_of))}</span></div>'
            f"<dl>{dl}</dl>{_spark(yearly, r['ticker'], r['window'])}{flags}</article>"
        )
    md("".join(out))


def _heat_style(v: float, cap: float = 0.5) -> str:
    if v is None or np.isnan(v):
        return f"background:{BG};color:#8A909C"
    a = min(abs(v) / cap, 1) * 0.85 + 0.08
    rgb = "29,78,216" if v >= 0 else "194,65,12"
    return f"background:rgba({rgb},{a:.2f});color:{'#FFFFFF' if a > 0.5 else INK}"


def _cell_pct(v) -> str:
    if pd.isna(v):
        return "n/a"
    return "0%" if abs(v) < 0.005 else f"{v:+.0%}"


def heatmap_table(yearly: pd.DataFrame, stats: pd.DataFrame, classified_only: bool) -> None:
    rows = stats.sort_values(["length", "start_month"])
    if classified_only:
        rows = rows[~rows["class"].isin(["None", "Insufficient history"])]
    if rows.empty:
        md('<p class="ip-muted">No classified windows. Switch to all windows to see every return.</p>')
        return
    pivot = yearly.pivot_table(index="window", columns="year", values="return", aggfunc="first")
    years = list(pivot.columns)
    head = "".join(f'<th scope="col">{int(y)}</th>' for y in years)
    body = []
    for _, s in rows.iterrows():
        vals = pivot.loc[s["window"]] if s["window"] in pivot.index else pd.Series(dtype=float)
        tds = "".join(
            f'<td style="{_heat_style(vals.get(y, np.nan))}">{_cell_pct(vals.get(y, np.nan))}</td>' for y in years
        )
        klass = "" if s["class"] in ("None", "Insufficient history") else f" {badge(s['class'])}"
        body.append(f'<tr><th scope="row">{esc(s["window"])}{klass}</th>{tds}</tr>')
    md(
        f'<div class="ip-scroll"><table class="ip-heat"><thead><tr><th scope="col" style="text-align:left">Window</th>'
        f"{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"
    )
    md(
        '<p class="ip-muted">Blue: gain, orange: loss; colour saturates at ±50%. '
        "Each cell prints its value. Years are labelled by the year the window starts.</p>"
    )


def calendar_rows(cal: pd.DataFrame, show_stock: bool) -> None:
    if cal.empty:
        md('<p class="ip-muted">No qualifying windows.</p>')
        return
    rows = []
    for _, c in cal.iterrows():
        stock = f'<span style="font-weight:600;width:110px">{esc(c["Stock"])}</span>' if show_stock else ""
        rows.append(
            f'<div class="row">{badge(c["Status"])}{stock}<span style="font-weight:600;width:90px">'
            f'{esc(c["Window"])}</span>{badge(c["Class"])}<span style="flex:1 1 260px">Entry close '
            f"{esc(day(c['Entry (close of)']))} · exit close {esc(day(c['Exit (close of)']))}</span>"
            f'<span class="ip-muted">Up {esc(c["Years up"])} · median {esc(pct(c["Median"]))}</span></div>'
        )
    md(f'<div class="ip-list">{"".join(rows)}</div>')


def month_classes(stats: pd.DataFrame, ticker: str) -> list[str]:
    """Strongest class covering each calendar month: Tier 1 > Tier 2 > Watch, else Negative, else ''."""
    s = stats[(stats["ticker"] == ticker) & (stats["length"] < 12)]
    out = []
    for m in range(1, 13):
        covering = s[[m in _months(r.start_month, r.length) for r in s.itertuples()]]["class"].tolist()
        best = next((k for k in POSITIVE if k in covering), "Negative" if "Negative" in covering else "")
        out.append(best)
    return out


def _months(start: int, length: int) -> list[int]:
    return [((int(start) - 1 + i) % 12) + 1 for i in range(int(length))]


def seasonal_map(stats: pd.DataFrame, tickers: list[str], as_of) -> None:
    now = pd.Timestamp(as_of).month
    head = "<span></span>" + "".join(
        f'<span class="m{" now" if i + 1 == now else ""}">{m}</span>' for i, m in enumerate(MONTHS)
    )
    rows = []
    names = {"": "No pattern", "Negative": "Exit or avoid"}
    for t in tickers:
        cells = "".join(
            f'<span class="c" title="{esc(t)} {m}: {esc(names.get(k, k))}" style="background:{MAP_FILL[k]}"></span>'
            for m, k in zip(MONTHS, month_classes(stats, t), strict=True)
        )
        rows.append(f'<span class="t">{esc(t)}</span>{cells}')
    legend = "".join(
        f'<span><i style="background:{MAP_FILL[k]}"></i>{esc(LABEL.get(k, k))}</span>'
        for k in ["Tier 1", "Tier 2", "Watch", "Negative"]
    )
    md(f'<div class="ip-legend">{legend}</div>')
    md(f'<div style="overflow-x:auto;margin-top:8px"><div class="ip-map">{head}{"".join(rows)}</div></div>')


def compare_table(stats: pd.DataFrame, tickers: list[str], patterns_only: bool) -> None:
    order = stats.drop_duplicates("window").sort_values(["length", "start_month"])["window"].tolist()
    idx = stats.set_index(["window", "ticker"])
    rows = []
    for w in order:
        cells, any_class = [], False
        for t in tickers:
            if (w, t) not in idx.index:
                cells.append("<td></td>")
                continue
            r = idx.loc[(w, t)]
            k = r["class"]
            shown = k not in ("None", "Insufficient history")
            any_class |= shown
            bg, fg = BADGE.get(k, BADGE["None"])
            style = f"background:{bg};color:{fg}" + ("" if shown else f";outline:1px solid #EEF0F3;color:{MUTED}")
            label = esc(LABEL.get(k, k)) if shown else ("Short history" if k == "Insufficient history" else "")
            cells.append(
                f'<td style="{style}"><b>{label}</b><span>{esc(ratio(r["up"], r["n"]))} · {esc(pct(r["median"]))}'
                "</span></td>"
            )
        if patterns_only and not any_class:
            continue
        rows.append(f'<tr><th scope="row" style="white-space:nowrap">{esc(w)}</th>{"".join(cells)}</tr>')
    head = "".join(f'<th scope="col">{esc(t)}</th>' for t in tickers)
    if not rows:
        md('<p class="ip-muted">No window is classified for these stocks.</p>')
        return
    md(
        f'<div style="overflow-x:auto"><table class="ip-cmp"><thead><tr><th scope="col">Window</th>{head}</tr>'
        f"</thead><tbody>{''.join(rows)}</tbody></table></div>"
    )
    md('<p class="ip-muted">Each cell: class, years up, median return.</p>')
