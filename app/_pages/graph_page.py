"""
app/_pages/graph_page.py
=========================
Graph Explorer page — interactive pyvis visualisations of the
Neo4j knowledge graph.

Three views:
  1. Customer Neighbourhood  — pick a customer, see their orders, products, segment
  2. Segment Overview        — see customers clustered by segment
  3. Schema Diagram          — static overview of all node types + relationships
"""

from __future__ import annotations

import streamlit as st
from streamlit import components


@st.cache_resource(show_spinner=False)
def _get_client():
    from graph.loaders.neo4j_client import Neo4jClient

    client = Neo4jClient()
    client._database = None
    return client


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_customer_list() -> list[dict]:
    client = _get_client()
    return client.run("""
        MATCH (c:Customer)-[:BELONGS_TO]->(s:Segment)
        RETURN c.id AS id, c.name AS name, s.name AS segment,
               c.city AS city, c.rfm_score AS rfm
        ORDER BY c.rfm_score DESC
        LIMIT 200
    """)


@st.cache_data(ttl=120, show_spinner=False)
def _fetch_neighbourhood(customer_id: str, limit: int) -> str:
    from app.components.graph_viz import (
        CUSTOMER_NEIGHBOURHOOD_CYPHER,
        build_customer_neighbourhood,
    )

    client = _get_client()
    rows = client.run(
        CUSTOMER_NEIGHBOURHOOD_CYPHER,
        {"customer_id": customer_id, "limit": limit},
    )
    if not rows:
        return ""
    # Attach segment info (repeated on each row from the OPTIONAL MATCH)
    first = rows[0]
    for r in rows:
        r["c_segment"] = first.get("seg_name", "")
    return build_customer_neighbourhood(rows, customer_id)


@st.cache_data(ttl=120, show_spinner=False)
def _fetch_segment_graph(segments: tuple[str, ...], per_segment: int) -> str:
    from app.components.graph_viz import (
        SEGMENT_SAMPLE_CYPHER,
        build_segment_overview,
    )

    client = _get_client()
    rows = client.run(
        SEGMENT_SAMPLE_CYPHER,
        {"segments": list(segments), "per_segment": per_segment},
    )
    if not rows:
        return ""
    return build_segment_overview(rows)


def _embed(html: str, height: int = 540) -> None:
    """Embed pyvis HTML in a styled container."""
    wrapped = f"""
    <div style="border:1px solid #30363d;border-radius:10px;overflow:hidden;">
      {html}
    </div>
    """
    components.v1.html(wrapped, height=height, scrolling=False)


def _legend() -> None:
    """Render a colour legend matching NODE_COLORS."""
    from app.components.graph_viz import NODE_COLORS

    items = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:5px;'
        f'margin-right:16px;font-size:0.78rem;color:#8b949e;">'
        f'<span style="width:10px;height:10px;border-radius:50%;'
        f'background:{color};display:inline-block;"></span>{label}</span>'
        for label, color in NODE_COLORS.items()
    )
    st.markdown(
        f'<div style="margin:8px 0 16px 0;">{items}</div>',
        unsafe_allow_html=True,
    )


ALL_SEGMENTS = [
    "Champions",
    "Loyal Customers",
    "Potential Loyalists",
    "At-Risk",
    "Hibernating",
    "Lost",
    "Others",
]


def render() -> None:
    # ── Page header ───────────────────────────────────────────────────────────
    st.markdown(
        """
    <div class="cl-header">
      <div class="cl-badge">Graph Explorer</div>
      <div class="cl-header-title">Explore the Knowledge Graph</div>
      <div class="cl-header-sub">
        Interactive visualisations of customers, orders, products and segments
      </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    _legend()

    # ── View tabs ─────────────────────────────────────────────────────────────
    tab_customer, tab_segment, tab_schema = st.tabs(
        [
            "👤  Customer Neighbourhood",
            "🎯  Segment Overview",
            "🗺️  Schema Diagram",
        ]
    )

    # ════════════════════════════════════════════════════════════════════════
    # TAB 1 — Customer Neighbourhood
    # ════════════════════════════════════════════════════════════════════════
    with tab_customer:
        st.markdown(
            '<div style="font-size:0.85rem;color:#57606a;margin-bottom:16px;">'
            "Select a customer to explore their orders, products purchased, "
            "and segment membership as an interactive graph."
            "</div>",
            unsafe_allow_html=True,
        )

        col_select, col_depth = st.columns([4, 2])

        with col_select:
            with st.spinner("Loading customers…"):
                customers = _fetch_customer_list()

            if not customers:
                st.warning("No customers found — is Neo4j connected?")
                return

            # Build display options: "Name (Segment) — City"
            options = {
                f"{r['name']}  ·  {r['segment']}  ·  {r['city']}": r["id"]
                for r in customers
            }
            selected_label = st.selectbox(
                "Customer",
                list(options.keys()),
                label_visibility="collapsed",
            )
            customer_id = options[selected_label]

        with col_depth:
            order_limit = st.slider(
                "Max orders to show",
                min_value=3,
                max_value=20,
                value=8,
                step=1,
            )

        # Customer info strip
        cust_info = next((r for r in customers if r["id"] == customer_id), {})
        if cust_info:
            c1, c2, c3, c4 = st.columns(4)
            for col, (label, val) in zip(
                [c1, c2, c3, c4],
                [
                    ("Segment", cust_info.get("segment", "—")),
                    ("City", cust_info.get("city", "—")),
                    ("RFM Score", cust_info.get("rfm", "—")),
                    ("Customer ID", cust_info.get("id", "—")),
                ],
            ):
                col.markdown(
                    f'<div class="cl-metric">'
                    f'<div class="cl-metric-value" style="font-size:1rem;">{val}</div>'
                    f'<div class="cl-metric-label">{label}</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )

        st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

        with st.spinner("Building graph…"):
            html = _fetch_neighbourhood(customer_id, order_limit)

        if html:
            _embed(html, height=560)
            st.markdown(
                '<div style="font-size:0.75rem;color:#8b949e;text-align:center;'
                'margin-top:6px;">Drag nodes · Scroll to zoom · Hover for details</div>',
                unsafe_allow_html=True,
            )
        else:
            st.info("No graph data found for this customer.")

    # ════════════════════════════════════════════════════════════════════════
    # TAB 2 — Segment Overview
    # ════════════════════════════════════════════════════════════════════════
    with tab_segment:
        st.markdown(
            '<div style="font-size:0.85rem;color:#57606a;margin-bottom:16px;">'
            "See the highest-RFM customers clustered around their segments. "
            "Hover any node for details."
            "</div>",
            unsafe_allow_html=True,
        )

        col_segs, col_n = st.columns([5, 2])
        with col_segs:
            selected_segs = st.multiselect(
                "Segments to include",
                ALL_SEGMENTS,
                default=["Champions", "At-Risk", "Hibernating"],
                label_visibility="collapsed",
            )
        with col_n:
            per_seg = st.slider(
                "Customers per segment",
                min_value=3,
                max_value=15,
                value=6,
                step=1,
            )

        if not selected_segs:
            st.info("Select at least one segment above.")
        else:
            with st.spinner("Building segment graph…"):
                html = _fetch_segment_graph(tuple(selected_segs), per_seg)

            if html:
                _embed(html, height=540)
                st.markdown(
                    '<div style="font-size:0.75rem;color:#8b949e;text-align:center;'
                    'margin-top:6px;">Drag nodes · Scroll to zoom · Hover for details</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.info("No data returned — check your segment selection.")

    # ════════════════════════════════════════════════════════════════════════
    # TAB 3 — Schema Diagram
    # ════════════════════════════════════════════════════════════════════════
    with tab_schema:
        st.markdown(
            '<div style="font-size:0.85rem;color:#57606a;margin-bottom:16px;">'
            "Static overview of all node labels and relationship types "
            "in the CustomerLens knowledge graph."
            "</div>",
            unsafe_allow_html=True,
        )

        from app.components.graph_viz import build_schema_graph

        html = build_schema_graph()
        _embed(html, height=460)

        # Schema table
        st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
        col_nodes, col_rels = st.columns(2)

        with col_nodes:
            st.markdown(
                '<div style="font-size:0.8rem;font-weight:600;color:#57606a;'
                'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px;">'
                "Node Labels</div>",
                unsafe_allow_html=True,
            )
            from app.components.graph_viz import NODE_COLORS

            for label, color in NODE_COLORS.items():
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:10px;'
                    f'padding:6px 0;border-bottom:1px solid #f0f0f0;">'
                    f'<span style="width:12px;height:12px;border-radius:50%;'
                    f'background:{color};flex-shrink:0;"></span>'
                    f'<span style="font-size:0.85rem;font-weight:500;">{label}</span>'
                    f"</div>",
                    unsafe_allow_html=True,
                )

        with col_rels:
            st.markdown(
                '<div style="font-size:0.8rem;font-weight:600;color:#57606a;'
                'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px;">'
                "Relationships</div>",
                unsafe_allow_html=True,
            )
            rels = [
                ("Customer", "PLACED", "Order"),
                ("Order", "CONTAINS", "Product"),
                ("Product", "BELONGS_TO", "Category"),
                ("Customer", "BELONGS_TO", "Segment"),
                ("Customer", "RESPONDED_TO", "Campaign"),
                ("Campaign", "TARGETS", "Segment"),
            ]
            for src, rel, dst in rels:
                src_color = NODE_COLORS.get(src, "#8b949e")
                dst_color = NODE_COLORS.get(dst, "#8b949e")
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:6px;'
                    f'padding:6px 0;border-bottom:1px solid #f0f0f0;font-size:0.82rem;">'
                    f'<span style="color:{src_color};font-weight:500;">{src}</span>'
                    f"<span style=\"color:#8b949e;font-family:'DM Mono',monospace;"
                    f'font-size:0.75rem;">─[{rel}]→</span>'
                    f'<span style="color:{dst_color};font-weight:500;">{dst}</span>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
