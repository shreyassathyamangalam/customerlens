"""
app/pages/report_page.py
=========================
Report Builder page — users choose a template, the app runs a bundle
of Cypher queries and Claude synthesises the results into a narrative.

Features:
  - 4 report templates with live graph data
  - Expandable data tables per query section
  - Claude-generated executive narrative
  - Markdown export (copy-to-clipboard)
  - Altair bar charts for key metrics
"""

from __future__ import annotations

import time
from datetime import date

import pandas as pd
import streamlit as st

from graph.queries.report_queries import REPORTS

try:
    import altair as alt

    HAS_ALTAIR = True
except ImportError:
    HAS_ALTAIR = False


def _render_chart(df: pd.DataFrame, report_name: str, section_title: str):
    """Render an Altair bar chart when the data has exactly the right shape."""
    if not HAS_ALTAIR or df.empty:
        return

    cols = df.columns.tolist()

    # Need at least one string col (category axis) and one numeric col (value axis)
    str_cols = [c for c in cols if df[c].dtype == object]
    num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]

    if not str_cols or not num_cols:
        return

    x_col = str_cols[0]
    y_col = num_cols[0]

    # Only chart when we have 2–20 rows — enough to be meaningful, not overwhelming
    if not (2 <= len(df) <= 20):
        return

    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X(
                f"{x_col}:N", sort="-y", axis=alt.Axis(labelAngle=-30, labelLimit=160)
            ),
            y=alt.Y(f"{y_col}:Q", title=y_col.replace("_", " ")),
            color=alt.value("#58a6ff"),
            tooltip=cols,
        )
        .properties(height=260)
        .configure_axis(labelFontSize=11, titleFontSize=12, grid=False)
        .configure_view(strokeWidth=0)
        .configure_mark(opacity=0.9)
    )
    st.altair_chart(chart, width="content")


def _render_section(section: dict, report_name: str):
    """Render one query result section — table + optional chart."""
    title = section["title"]
    df = section["df"]

    st.markdown(
        f'<div style="font-size:0.85rem;font-weight:600;color:#0d1117;'
        f"margin:20px 0 10px 0;padding-bottom:6px;"
        f'border-bottom:1px solid #d0d7de;">{title}</div>',
        unsafe_allow_html=True,
    )

    if df.empty:
        st.info("No data returned for this query.")
        return

    tab_table, tab_chart = st.tabs(["📋 Table", "📊 Chart"])
    with tab_table:
        st.dataframe(df, width="stretch", hide_index=True)
    with tab_chart:
        _render_chart(df, report_name, title)


def _summary_metrics(sections: list[dict]) -> dict:
    """Extract a few top-line numbers to show in the metric strip."""
    metrics = {}
    for s in sections:
        df = s["df"]
        if df.empty:
            continue
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if num_cols and len(df) <= 12:
            # First numeric col, first row — e.g. AOV of top segment
            metrics[s["title"]] = (
                df.columns[0],
                df.iloc[0, 0],
                num_cols[0],
                df.iloc[0][num_cols[0]],
            )
    return metrics


def render():
    # ── Page header ───────────────────────────────────────────────────────────
    st.markdown(
        """
    <div class="cl-header">
      <div class="cl-badge">Report Builder</div>
      <div class="cl-header-title">Generate Analytics Reports</div>
      <div class="cl-header-sub">
        Choose a template — the app queries the graph and Claude writes the narrative
      </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ── Template picker ───────────────────────────────────────────────────────
    report_names = list(REPORTS.keys())

    st.markdown(
        '<div style="font-size:0.8rem;font-weight:600;color:#57606a;'
        'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:14px;">'
        "Select a report template</div>",
        unsafe_allow_html=True,
    )

    cols = st.columns(len(report_names))
    selected = st.session_state.get("selected_report", report_names[0])

    for i, name in enumerate(report_names):
        info = REPORTS[name]
        is_selected = name == selected
        border = "#58a6ff" if is_selected else "#d0d7de"
        bg = "#f0f6ff" if is_selected else "#ffffff"
        with cols[i]:
            if st.button(
                f"{info['icon']}  {name}",
                key=f"rpt_{i}",
                width="content",
                type="primary" if is_selected else "secondary",
            ):
                st.session_state.selected_report = name
                # Clear cached results when template changes
                for k in ["report_sections", "report_narrative", "report_name_cached"]:
                    st.session_state.pop(k, None)
                st.rerun()

    selected = st.session_state.get("selected_report", report_names[0])
    report_info = REPORTS[selected]

    # Description
    st.markdown(
        f'<div style="background:#f6f8fa;border:1px solid #d0d7de;border-radius:8px;'
        f'padding:14px 18px;margin:16px 0;font-size:0.88rem;color:#57606a;">'
        f"{report_info['icon']}  {report_info['description']}"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Generate button ───────────────────────────────────────────────────────
    col_btn, col_info = st.columns([2, 6])
    with col_btn:
        generate = st.button("⚡ Generate Report", width="content")
    with col_info:
        n_queries = len(report_info["queries"])
        st.markdown(
            f'<div style="padding-top:10px;font-size:0.82rem;color:#8b949e;">'
            f"Runs {n_queries} graph queries · Claude writes the narrative</div>",
            unsafe_allow_html=True,
        )

    # ── Run queries + generate narrative ─────────────────────────────────────
    cached_name = st.session_state.get("report_name_cached")

    if generate or (cached_name and cached_name != selected):
        for k in ["report_sections", "report_narrative", "report_name_cached"]:
            st.session_state.pop(k, None)

    if generate and not st.session_state.get("report_sections"):
        progress = st.progress(0, text="Connecting to graph…")
        try:
            from app.reports.report_builder import build_report

            progress.progress(20, text=f"Running {n_queries} Cypher queries…")
            sections, narrative = build_report(selected)
            progress.progress(80, text="Claude is writing the narrative…")
            time.sleep(0.3)
            progress.progress(100, text="Done!")
            time.sleep(0.4)
            progress.empty()

            st.session_state.report_sections = sections
            st.session_state.report_narrative = narrative
            st.session_state.report_name_cached = selected

        except Exception as exc:
            progress.empty()
            st.error(f"Report generation failed: {exc}")
            return

    # ── Render cached report ──────────────────────────────────────────────────
    sections = st.session_state.get("report_sections")
    narrative = st.session_state.get("report_narrative")

    if not sections:
        st.markdown(
            '<div style="text-align:center;padding:60px 0;color:#8b949e;font-size:0.9rem;">'
            "Select a template and click <strong>Generate Report</strong> to begin."
            "</div>",
            unsafe_allow_html=True,
        )
        return

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    st.markdown("---")

    # ── Two-column layout: narrative left, data right ─────────────────────────
    col_narrative, col_data = st.columns([5, 6], gap="large")

    with col_narrative:
        st.markdown(
            '<div style="font-size:0.8rem;font-weight:600;color:#57606a;'
            'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:14px;">'
            "🤖 Claude's Analysis</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="cl-narrative">{narrative}</div>',
            unsafe_allow_html=True,
        )

        # Export button
        today = date.today().isoformat()
        export_md = f"# {selected}\n_Generated {today}_\n\n{narrative}\n"
        st.download_button(
            label="⬇️ Download as Markdown",
            data=export_md,
            file_name=f"{selected.lower().replace(' ', '_')}_{today}.md",
            mime="text/markdown",
            width="content",
        )

    with col_data:
        st.markdown(
            '<div style="font-size:0.8rem;font-weight:600;color:#57606a;'
            'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:14px;">'
            "📊 Graph Data</div>",
            unsafe_allow_html=True,
        )
        for section in sections:
            _render_section(section, selected)
