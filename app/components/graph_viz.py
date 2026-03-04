"""
app/components/graph_viz.py
============================
Builds interactive pyvis network graphs from Neo4j subgraph data
and renders them inside Streamlit via components.v1.html.

Public API:
    render_customer_neighbourhood(customer_id, depth, neo4j_client)
    render_segment_graph(segment_name, limit, neo4j_client)
    render_schema_graph()
"""

from __future__ import annotations

from typing import Any

from pyvis.network import Network

# ── Design tokens (match app colour scheme) ──────────────────────────────────
BG = "#0d1117"
FONT_COLOR = "#e6edf3"
EDGE_COLOR = "#30363d"
HOVER_BG = "#161b22"

NODE_COLORS = {
    "Customer": "#58a6ff",  # blue
    "Order": "#3fb950",  # green
    "Product": "#f78166",  # coral
    "Category": "#d2a8ff",  # purple
    "Segment": "#ffa657",  # orange
    "Campaign": "#79c0ff",  # light blue
}

NODE_SIZES = {
    "Customer": 22,
    "Order": 16,
    "Product": 18,
    "Category": 24,
    "Segment": 28,
    "Campaign": 22,
}

VIS_OPTIONS = """
{
  "nodes": {
    "font": { "size": 13, "color": "#e6edf3", "face": "DM Sans, sans-serif" },
    "borderWidth": 2,
    "borderWidthSelected": 3,
    "shadow": { "enabled": true, "color": "rgba(0,0,0,0.4)", "size": 8 }
  },
  "edges": {
    "font": {
      "size": 10, "color": "#8b949e", "face": "DM Mono, monospace",
      "align": "middle", "strokeWidth": 0
    },
    "smooth": { "type": "curvedCW", "roundness": 0.2 },
    "arrows": { "to": { "enabled": true, "scaleFactor": 0.6 } },
    "shadow": false
  },
  "physics": {
    "enabled": true,
    "stabilization": { "iterations": 120, "fit": true },
    "barnesHut": {
      "gravitationalConstant": -8000,
      "centralGravity": 0.3,
      "springLength": 140,
      "springConstant": 0.04,
      "damping": 0.09
    }
  },
  "interaction": {
    "hover": true,
    "tooltipDelay": 150,
    "hideEdgesOnDrag": true,
    "navigationButtons": false,
    "keyboard": false
  }
}
"""


# ── Network factory ───────────────────────────────────────────────────────────


def _make_network(height: int = 520) -> Network:
    net = Network(
        height=f"{height}px",
        width="100%",
        directed=True,
        bgcolor=BG,
        font_color=FONT_COLOR,
        cdn_resources="in_line",
    )
    net.set_options(VIS_OPTIONS)
    return net


def _node_id(label: str, node_id: str) -> str:
    return f"{label}::{node_id}"


def _add_node(
    net: Network,
    label: str,
    node_id: str,
    display: str,
    tooltip: str = "",
    node_size: int | None = None,
    **kwargs,
) -> str:
    uid = _node_id(label, node_id)
    if uid not in net.get_nodes():
        size = node_size if node_size is not None else NODE_SIZES.get(label, 18)
        net.add_node(
            uid,
            label=display,
            title=tooltip or display,
            color=NODE_COLORS.get(label, "#8b949e"),
            size=size,
            group=label,
            **kwargs,
        )
    return uid


def _net_to_html(net: Network) -> str:
    """Generate self-contained HTML string."""
    return net.generate_html()


# ── Graph builders ────────────────────────────────────────────────────────────


def build_customer_neighbourhood(
    rows: list[dict[str, Any]],
    customer_id: str,
) -> str:
    """
    Build a customer-centric subgraph from flat Neo4j result rows.

    Expected row keys: c_id, c_name, c_segment,
                       o_id, o_total, o_date, o_channel,
                       p_id, p_name, p_brand,
                       cat_id, cat_name,
                       seg_id, seg_name
    """
    net = _make_network(height=520)

    for row in rows:
        # Customer
        c_uid = _add_node(
            net,
            "Customer",
            row["c_id"],
            display=row.get("c_name", row["c_id"])[:18],
            tooltip=(
                f"<b>{row.get('c_name', '')}</b><br>"
                f"Segment: {row.get('c_segment', '')}<br>"
                f"ID: {row['c_id']}"
            ),
            borderColor="#79c0ff",
        )

        # Segment node
        if row.get("seg_id"):
            s_uid = _add_node(
                net,
                "Segment",
                row["seg_id"],
                display=row.get("seg_name", row["seg_id"]),
                tooltip=f"Segment: {row.get('seg_name', '')}",
            )
            net.add_edge(c_uid, s_uid, label="BELONGS_TO", color="#ffa657", width=1.5)

        # Order
        if row.get("o_id"):
            o_uid = _add_node(
                net,
                "Order",
                row["o_id"],
                display=f"${row.get('o_total', 0):.0f}",
                tooltip=(
                    f"<b>Order {row['o_id']}</b><br>"
                    f"Date: {row.get('o_date', '')}<br>"
                    f"Channel: {row.get('o_channel', '')}<br>"
                    f"Total: ${row.get('o_total', 0):.2f}"
                ),
            )
            net.add_edge(c_uid, o_uid, label="PLACED", color="#3fb950", width=1.5)

            # Product
            if row.get("p_id"):
                p_uid = _add_node(
                    net,
                    "Product",
                    row["p_id"],
                    display=row.get("p_name", row["p_id"])[:20],
                    tooltip=(
                        f"<b>{row.get('p_name', '')}</b><br>"
                        f"Brand: {row.get('p_brand', '')}<br>"
                        f"ID: {row['p_id']}"
                    ),
                )
                net.add_edge(o_uid, p_uid, label="CONTAINS", color="#f78166", width=1)

                # Category
                if row.get("cat_id"):
                    cat_uid = _add_node(
                        net,
                        "Category",
                        row["cat_id"],
                        display=row.get("cat_name", row["cat_id"]),
                        tooltip=f"Category: {row.get('cat_name', '')}",
                    )
                    net.add_edge(
                        p_uid, cat_uid, label="BELONGS_TO", color="#d2a8ff", width=1
                    )

    return _net_to_html(net)


def build_segment_overview(rows: list[dict[str, Any]]) -> str:
    """
    Segment → Customer sample graph.

    Expected row keys: seg_id, seg_name, c_id, c_name, c_city, c_rfm_score
    """
    net = _make_network(height=500)

    for row in rows:
        # Segment hub
        s_uid = _add_node(
            net,
            "Segment",
            row["seg_id"],
            display=row["seg_name"],
            tooltip=f"<b>{row['seg_name']}</b>",
            node_size=32,
        )
        # Customer spoke
        c_uid = _add_node(
            net,
            "Customer",
            row["c_id"],
            display=row.get("c_name", row["c_id"])[:16],
            tooltip=(
                f"<b>{row.get('c_name', '')}</b><br>"
                f"City: {row.get('c_city', '')}<br>"
                f"RFM: {row.get('c_rfm_score', '')}"
            ),
            node_size=16,
        )
        net.add_edge(c_uid, s_uid, color="#ffa657", width=1)

    return _net_to_html(net)


def build_schema_graph() -> str:
    """Static schema diagram showing all node types and relationships."""
    net = _make_network(height=420)

    nodes = [
        ("Customer", "Customer"),
        ("Order", "Order"),
        ("Product", "Product"),
        ("Category", "Category"),
        ("Segment", "Segment"),
        ("Campaign", "Campaign"),
    ]
    for label, display in nodes:
        _add_node(
            net,
            label,
            label,
            display=display,
            tooltip=label,
            node_size=NODE_SIZES[label] + 6,
        )

    edges = [
        ("Customer", "Order", "PLACED"),
        ("Order", "Product", "CONTAINS"),
        ("Product", "Category", "BELONGS_TO"),
        ("Customer", "Segment", "BELONGS_TO"),
        ("Customer", "Campaign", "RESPONDED_TO"),
        ("Campaign", "Segment", "TARGETS"),
    ]
    for src, dst, lbl in edges:
        net.add_edge(
            _node_id(src, src),
            _node_id(dst, dst),
            label=lbl,
            color=EDGE_COLOR,
            width=2,
        )

    return _net_to_html(net)


# ── Cypher queries for fetching subgraph data ─────────────────────────────────

CUSTOMER_NEIGHBOURHOOD_CYPHER = """
MATCH (c:Customer {id: $customer_id})
OPTIONAL MATCH (c)-[:BELONGS_TO]->(s:Segment)
OPTIONAL MATCH (c)-[:PLACED]->(o:Order)
OPTIONAL MATCH (o)-[:CONTAINS]->(p:Product)-[:BELONGS_TO]->(cat:Category)
RETURN
  c.id          AS c_id,
  c.name        AS c_name,
  c.rfm_score   AS c_rfm,
  s.id          AS seg_id,
  s.name        AS seg_name,
  o.id          AS o_id,
  o.total_value AS o_total,
  o.date        AS o_date,
  o.channel     AS o_channel,
  p.id          AS p_id,
  p.name        AS p_name,
  p.brand       AS p_brand,
  cat.id        AS cat_id,
  cat.name      AS cat_name
ORDER BY o.date DESC
LIMIT $limit
"""

SEGMENT_SAMPLE_CYPHER = """
MATCH (c:Customer)-[:BELONGS_TO]->(s:Segment)
WHERE s.name IN $segments
WITH s, c ORDER BY c.rfm_score DESC
WITH s, collect(c)[..$per_segment] AS top_customers
UNWIND top_customers AS c
RETURN
  s.id        AS seg_id,
  s.name      AS seg_name,
  c.id        AS c_id,
  c.name      AS c_name,
  c.city      AS c_city,
  c.rfm_score AS c_rfm_score
"""
