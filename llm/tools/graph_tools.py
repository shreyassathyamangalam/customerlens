"""
llm/tools/graph_tools.py
=========================
Pre-built, @tool-decorated functions that wrap every Cypher query from
report_queries.py.  Each tool:
  - Has a clear, business-facing docstring (the LLM reads this to decide
    which tool to call)
  - Returns a compact JSON string the agent can reason over
  - Uses Neo4jClient directly — no LangChain graph wrapper needed
  - Is safe to call repeatedly (all read-only MATCH queries)

Tools are grouped into four domains:
  1. Segment Analytics        (3 tools)
  2. Churn Risk               (3 tools)
  3. Campaign Effectiveness   (3 tools)
  4. Cross-Sell Intelligence  (4 tools)
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool

from graph.loaders.neo4j_client import Neo4jClient

# ── Shared DB helper ──────────────────────────────────────────────────────────


def _run(cypher: str, params: dict | None = None) -> str:
    """Execute a Cypher query and return compact JSON string."""
    with Neo4jClient() as client:
        client._database = None  # AuraDB fix
        rows: list[dict[str, Any]] = client.run(cypher, params or {})
    if not rows:
        return json.dumps({"result": "No data returned."})
    return json.dumps(rows, default=str, ensure_ascii=False)


# ═════════════════════════════════════════════════════════════════════════════
# 1. SEGMENT ANALYTICS
# ═════════════════════════════════════════════════════════════════════════════


@tool
def get_segment_aov() -> str:
    """
    Returns the average order value (AOV), total orders, customer count,
    and total revenue for every RFM segment, ranked by AOV descending.
    Use this when asked about spending patterns, revenue by segment,
    or which segment is most valuable.
    """
    return _run("""
        MATCH (c:Customer)-[:BELONGS_TO]->(s:Segment),
              (c)-[:PLACED]->(o:Order)
        WHERE o.status = 'completed'
        RETURN s.name AS Segment,
               count(DISTINCT c)            AS Customers,
               count(o)                     AS Orders,
               round(avg(o.total_value), 2) AS Avg_Order_Value,
               round(sum(o.total_value), 2) AS Total_Revenue
        ORDER BY Avg_Order_Value DESC
    """)


@tool
def get_segment_recency_frequency() -> str:
    """
    Returns recency, frequency and average lifetime spend for each segment.
    Avg_Recency_Days = average days since last order (lower = more active).
    Use this when asked about how recently or how often customers buy,
    or to compare engagement levels across segments.
    """
    return _run("""
        MATCH (c:Customer)-[:BELONGS_TO]->(s:Segment)
        RETURN s.name                       AS Segment,
               count(c)                     AS Customers,
               round(avg(c.recency_days),1) AS Avg_Recency_Days,
               round(avg(c.frequency),1)    AS Avg_Orders,
               round(avg(c.monetary),2)     AS Avg_Lifetime_Spend
        ORDER BY Avg_Recency_Days ASC
    """)


@tool
def get_segment_channel_mix() -> str:
    """
    Returns the preferred purchase channel (online / in-store / mobile)
    breakdown for each segment.
    Use this when asked about channel preferences, omnichannel behaviour,
    or where customers prefer to shop.
    """
    return _run("""
        MATCH (c:Customer)-[:BELONGS_TO]->(s:Segment)
        RETURN s.name               AS Segment,
               c.preferred_channel  AS Channel,
               count(c)             AS Customers
        ORDER BY Segment, Customers DESC
    """)


# ═════════════════════════════════════════════════════════════════════════════
# 2. CHURN RISK
# ═════════════════════════════════════════════════════════════════════════════


@tool
def get_churn_revenue_at_stake() -> str:
    """
    Returns the total and average historical spend for At-Risk, Hibernating
    and Lost segments — quantifying the revenue at stake if these customers
    churn permanently.
    Use this when asked about churn risk, revenue exposure, or the financial
    impact of losing inactive customers.
    """
    return _run("""
        MATCH (c:Customer)-[:BELONGS_TO]->(s:Segment)
        WHERE s.name IN ['At-Risk', 'Hibernating', 'Lost']
        RETURN s.name                    AS Segment,
               count(c)                  AS Customers,
               round(sum(c.monetary), 2) AS Total_Historical_Spend,
               round(avg(c.monetary), 2) AS Avg_Spend_Per_Customer
        ORDER BY Total_Historical_Spend DESC
    """)


@tool
def get_churn_risk_by_city() -> str:
    """
    Returns the concentration of At-Risk, Hibernating and Lost customers
    per city, ranked by count.
    Use this when asked where churning customers are located, or to
    prioritise geographic re-engagement campaigns.
    """
    return _run("""
        MATCH (c:Customer)-[:BELONGS_TO]->(s:Segment)
        WHERE s.name IN ['At-Risk', 'Hibernating', 'Lost']
        RETURN c.city    AS City,
               s.name    AS Segment,
               count(c)  AS At_Risk_Customers
        ORDER BY At_Risk_Customers DESC
        LIMIT 20
    """)


@tool
def get_at_risk_customer_detail() -> str:
    """
    Returns a detailed list of At-Risk and Hibernating customers including
    their city, days since last order, total orders, and lifetime spend.
    Limited to the 30 most inactive customers.
    Use this when asked to identify specific customers to re-engage,
    or for a customer-level churn risk view.
    """
    return _run("""
        MATCH (c:Customer)-[:BELONGS_TO]->(s:Segment)
        WHERE s.name IN ['At-Risk', 'Hibernating']
        OPTIONAL MATCH (c)-[:PLACED]->(o:Order)
        WHERE o.status = 'completed'
        WITH c, s, max(o.date) AS last_order
        RETURN c.name               AS Customer,
               c.city               AS City,
               s.name               AS Segment,
               c.recency_days       AS Days_Since_Order,
               c.frequency          AS Total_Orders,
               round(c.monetary, 2) AS Lifetime_Spend,
               last_order           AS Last_Order_Date
        ORDER BY Days_Since_Order DESC
        LIMIT 30
    """)


# ═════════════════════════════════════════════════════════════════════════════
# 3. CAMPAIGN EFFECTIVENESS
# ═════════════════════════════════════════════════════════════════════════════


@tool
def get_campaign_response_summary() -> str:
    """
    Returns a summary of all campaigns: type, start date, target segment,
    and total unique responders, ranked by response count.
    Use this when asked about campaign performance, which campaigns worked
    best, or overall marketing effectiveness.
    """
    return _run("""
        MATCH (camp:Campaign)-[:TARGETS]->(s:Segment)
        OPTIONAL MATCH (c:Customer)-[:RESPONDED_TO]->(camp)
        RETURN camp.name          AS Campaign,
               camp.type         AS Type,
               camp.start_date   AS Start_Date,
               s.name            AS Target_Segment,
               count(DISTINCT c) AS Responders
        ORDER BY Responders DESC
    """)


@tool
def get_campaign_response_by_segment() -> str:
    """
    Returns how many customers from each actual segment responded to each
    campaign — revealing whether campaigns reached beyond their target segment.
    Use this when asked about which segments engaged with a campaign,
    or to compare target vs actual audience.
    """
    return _run("""
        MATCH (c:Customer)-[:RESPONDED_TO]->(camp:Campaign),
              (c)-[:BELONGS_TO]->(s:Segment)
        RETURN camp.name AS Campaign,
               s.name    AS Responder_Segment,
               count(c)  AS Responders
        ORDER BY Campaign, Responders DESC
    """)


@tool
def get_multi_campaign_customers() -> str:
    """
    Returns customers who responded to more than one campaign, including
    their segment, city, number of campaigns responded to, and lifetime spend.
    Use this when asked about highly engaged customers, multi-touch
    attribution, or which customers are most responsive to marketing.
    """
    return _run("""
        MATCH (c:Customer)-[:RESPONDED_TO]->(camp:Campaign)
        WITH c, count(camp) AS campaign_count
        WHERE campaign_count > 1
        MATCH (c)-[:BELONGS_TO]->(s:Segment)
        RETURN c.name               AS Customer,
               c.city               AS City,
               s.name               AS Segment,
               campaign_count       AS Campaigns_Responded,
               round(c.monetary, 2) AS Lifetime_Spend
        ORDER BY Campaigns_Responded DESC, Lifetime_Spend DESC
        LIMIT 20
    """)


# ═════════════════════════════════════════════════════════════════════════════
# 4. CROSS-SELL INTELLIGENCE
# ═════════════════════════════════════════════════════════════════════════════


@tool
def get_cross_sell_pairs_global() -> str:
    """
    Returns the top 20 product pairs most frequently purchased together
    across all customers and orders.
    Use this when asked about product bundling, cross-sell opportunities,
    'customers also bought' style recommendations, or basket analysis.
    """
    return _run("""
        MATCH (o:Order)-[:CONTAINS]->(p1:Product),
              (o)-[:CONTAINS]->(p2:Product)
        WHERE p1.id < p2.id
          AND o.status = 'completed'
        RETURN p1.name            AS Product_A,
               p2.name            AS Product_B,
               count(DISTINCT o)  AS Co_Purchases
        ORDER BY Co_Purchases DESC
        LIMIT 20
    """)


@tool
def get_cross_sell_pairs_champions() -> str:
    """
    Returns the top 15 product pairs most frequently purchased together
    specifically by Champions segment customers.
    Use this when asked about premium or high-value customer purchasing
    patterns, or to build recommendations for your best customers.
    """
    return _run("""
        MATCH (c:Customer)-[:BELONGS_TO]->(s:Segment {name: 'Champions'}),
              (c)-[:PLACED]->(o:Order)-[:CONTAINS]->(p1:Product),
              (o)-[:CONTAINS]->(p2:Product)
        WHERE p1.id < p2.id
          AND o.status = 'completed'
        RETURN p1.name            AS Product_A,
               p2.name            AS Product_B,
               count(DISTINCT o)  AS Co_Purchases
        ORDER BY Co_Purchases DESC
        LIMIT 15
    """)


@tool
def get_category_affinity() -> str:
    """
    Returns the top 15 category pairs most frequently purchased together
    in the same order.
    Use this when asked about category-level cross-sell, department affinities,
    or how to structure promotions across product ranges.
    """
    return _run("""
        MATCH (o:Order)-[:CONTAINS]->(p1:Product)-[:BELONGS_TO]->(c1:Category),
              (o)-[:CONTAINS]->(p2:Product)-[:BELONGS_TO]->(c2:Category)
        WHERE c1.id < c2.id
          AND o.status = 'completed'
        RETURN c1.name            AS Category_A,
               c2.name            AS Category_B,
               count(DISTINCT o)  AS Orders_Together
        ORDER BY Orders_Together DESC
        LIMIT 15
    """)


@tool
def get_top_products_by_segment() -> str:
    """
    Returns the top 3 revenue-generating products for each RFM segment.
    Use this when asked about what products drive revenue in each segment,
    segment-specific product preferences, or personalisation strategies.
    """
    return _run("""
        MATCH (c:Customer)-[:BELONGS_TO]->(s:Segment),
              (c)-[:PLACED]->(o:Order)-[r:CONTAINS]->(p:Product)
        WHERE o.status = 'completed'
        WITH s.name AS Segment, p.name AS Product,
             sum(r.quantity * r.unit_price) AS Revenue
        ORDER BY Segment, Revenue DESC
        WITH Segment, collect({product: Product, revenue: Revenue})[..3] AS top
        UNWIND top AS t
        RETURN Segment,
               t.product           AS Product,
               round(t.revenue, 2) AS Revenue
        ORDER BY Segment
    """)


# ── Exported tool list ────────────────────────────────────────────────────────

ALL_TOOLS = [
    # Segment Analytics
    get_segment_aov,
    get_segment_recency_frequency,
    get_segment_channel_mix,
    # Churn Risk
    get_churn_revenue_at_stake,
    get_churn_risk_by_city,
    get_at_risk_customer_detail,
    # Campaign Effectiveness
    get_campaign_response_summary,
    get_campaign_response_by_segment,
    get_multi_campaign_customers,
    # Cross-Sell Intelligence
    get_cross_sell_pairs_global,
    get_cross_sell_pairs_champions,
    get_category_affinity,
    get_top_products_by_segment,
]
