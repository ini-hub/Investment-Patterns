"""CSV and PDF export."""

from __future__ import annotations

import io
import json

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..config import settings_hash
from ..engine.significance import describe as describe_permutation
from ..version import code_version
from .calendar import calendar_table
from .method import CAVEATS, CLASSES, METHOD
from .tables import PCT, pattern_table

STATS_EXPORT_COLUMNS = [
    "ticker",
    "window",
    "kind",
    "class",
    "note",
    "flags",
    "n",
    "up",
    "hit_rate",
    "streak",
    "longest_streak",
    "median",
    "mean",
    "worst",
    "best",
    "std",
    "variance",
    "beat_market",
    "market_n",
    "market_rate",
    "median_ex_market",
    "beat_own",
    "own_n",
    "own_rate",
    "median_ex_own",
    "median_dip",
    "worst_dip",
    "p_up",
    "p_own",
    "score",
    "first_year",
    "last_year",
    "years",
    "data_hash",
    "code_version",
    "settings_hash",
]


def stats_csv(stats: pd.DataFrame) -> bytes:
    cols = [c for c in STATS_EXPORT_COLUMNS if c in stats.columns]
    return stats[cols].to_csv(index=False, float_format="%.6f").encode("utf-8")


def yearly_csv(yearly: pd.DataFrame) -> bytes:
    return yearly.to_csv(index=False, float_format="%.6f").encode("utf-8")


def run_manifest(
    results: list, permutation: dict | None, as_of: pd.Timestamp, sources: list[str], benchmark: str
) -> bytes:
    """Run details as JSON: everything needed to reproduce the report (docs/SCOPE.md NF-2, NF-3)."""
    cfg = results[0].meta["config"] if results else {}
    doc = {
        "code_version": code_version(),
        "settings_hash": settings_hash(cfg),
        "settings": cfg,
        "calendar_date": str(pd.Timestamp(as_of).date()),
        "sources": sources,
        "benchmark": benchmark,
        "tickers": {
            r.ticker: {
                "first_date": str(pd.Timestamp(r.meta["first_date"]).date()),
                "last_date": str(pd.Timestamp(r.meta["last_date"]).date()),
                "last_complete_month": r.meta["last_complete_month"],
                "data_hash": r.meta["data_hash"],
            }
            for r in results
        },
        "permutation": permutation,
    }
    return json.dumps(doc, indent=2, default=str).encode("utf-8")


def _flatten(d: dict, prefix: str = "") -> list[tuple[str, str]]:
    out = []
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out += _flatten(v, key + ".")
        else:
            out.append((key, str(v)))
    return out


def _fmt(df: pd.DataFrame) -> list[list[str]]:
    out = [list(df.columns)]
    pct_labels = {"Median", "Worst year", "Best year", "Std dev", "Median dip", "Worst dip"}
    for _, row in df.iterrows():
        cells = []
        for col, v in row.items():
            if col in pct_labels and isinstance(v, (int, float)) and pd.notna(v):
                cells.append(f"{v:+.1%}")
            elif isinstance(v, float) and pd.isna(v):
                cells.append("")
            else:
                cells.append(str(v))
        out.append(cells)
    return out


def _table(data: list[list[str]], styles, col_widths=None) -> Table:
    body = styles["BodyText"].clone("cell", fontSize=7, leading=8.5)
    wrapped = [[Paragraph(c, body) for c in r] for r in data]
    t = Table(wrapped, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#efefef")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return t


def pdf_report(
    results: list, permutation: dict | None, as_of: pd.Timestamp, title: str, meta_lines: list[str]
) -> bytes:
    """results: list of ScanResult. Returns PDF bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=title,
    )
    st = getSampleStyleSheet()
    story = [Paragraph(title, st["Title"])]
    cfg = results[0].meta["config"] if results else {}
    provenance = [
        f"Code version: {code_version()}. Settings hash: {settings_hash(cfg)}.",
        "Data hash: " + ", ".join(f"{r.ticker} {r.meta['data_hash']}" for r in results) + ".",
        *dict.fromkeys(r.meta["completeness"] for r in results),
    ]
    for line in [*meta_lines, *provenance]:
        story.append(Paragraph(line, st["BodyText"]))
    if permutation:
        story += [Spacer(1, 4), Paragraph("<b>Chance check.</b> " + describe_permutation(permutation), st["BodyText"])]

    stats = pd.concat([r.stats for r in results], ignore_index=True)
    multi = len(results) > 1
    for heading, classes in [
        ("Tier 1 patterns", ["Tier 1"]),
        ("Tier 2 patterns", ["Tier 2"]),
        ("Watch", ["Watch"]),
        ("Emerging", ["Emerging"]),
        ("Negative windows (exit or avoid)", ["Negative"]),
    ]:
        tbl = pattern_table(stats, classes, include_ticker=True).drop(columns=["Class"])
        if not multi:
            tbl = tbl.drop(columns=["Stock"])
        story += [Spacer(1, 8), Paragraph(heading, st["Heading3"])]
        story.append(_table(_fmt(tbl), st) if len(tbl) else Paragraph("None found.", st["BodyText"]))

    cal = calendar_table(stats, as_of)
    story += [Spacer(1, 8), Paragraph(f"Calendar (as of {pd.Timestamp(as_of).date()})", st["Heading3"])]
    if len(cal):
        cal = cal.copy()
        cal["Median"] = cal["Median"].map(lambda v: f"{v:+.1%}")
        story.append(_table(_fmt(cal), st))
    else:
        story.append(Paragraph("No qualifying windows.", st["BodyText"]))

    story += [Spacer(1, 8), Paragraph("Data quality", st["Heading3"])]
    any_warn = False
    for r in results:
        for w in r.quality.warnings():
            any_warn = True
            story.append(Paragraph(f"<b>{r.ticker}:</b> {w}", st["BodyText"]))
    if not any_warn:
        story.append(Paragraph("No data-quality warnings.", st["BodyText"]))

    story += [PageBreak(), Paragraph("Method", st["Heading3"])]
    story += [Paragraph("&bull; " + m, st["BodyText"]) for m in METHOD]
    story += [Spacer(1, 6), Paragraph("Classes", st["Heading3"])]
    story += [Paragraph("&bull; " + m, st["BodyText"]) for m in CLASSES]
    story += [Spacer(1, 6), Paragraph("Caveats", st["Heading3"])]
    story += [Paragraph("&bull; " + m, st["BodyText"]) for m in CAVEATS]
    story += [Spacer(1, 6), Paragraph(f"Settings used (hash {settings_hash(cfg)})", st["Heading3"])]
    story.append(_table([["Setting", "Value"], *[[k, v] for k, v in _flatten(cfg)]], st, col_widths=[90 * mm, 60 * mm]))
    doc.build(story)
    return buf.getvalue()


__all__ = ["stats_csv", "yearly_csv", "pdf_report", "run_manifest", "PCT"]
