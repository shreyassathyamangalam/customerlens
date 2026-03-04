"""
graph/queries/report_queries.py
================================
Named Cypher queries used by the Report Builder.
Each entry is a dict with:
  - cypher : the query string (may contain $params)
  - params : default parameter dict
  - title  : short display title for the result table
"""

from __future__ import annotations

# ── Segment Health ────────────────────────────────────────────────────────────
SEGMENT_AOV = {
    "title": "Average Order Value by Segment",
    "cypher": """
        MATCH (c:Customer)-[:BELONGS_TO]->(s:Segment),
              (c)-[:PLACED]->(o:Order)
        WHERE o.status = 'completed'
        RETURN s.name AS Segment,
               count(DISTINCT c) AS Customers,
               count(o)          AS Orders,
               round(avg(o.total_value), 2) AS Avg_Order_Value,
               round(sum(o.total_value), 2) AS Total_Revenue
        ORDER BY Avg_Order_Value DESC
    """,
    "params": {},
}

SEGMENT_RECENCY = {
    "title": "Segment Recency & Frequency Overview",
    "cypher": """
        MATCH (c:Customer)-[:BELONGS_TO]->(s:Segment)
        RETURN s.name                       AS Segment,
               count(c)                     AS Customers,
               round(avg(c.recency_days),1) AS Avg_Recency_Days,
               round(avg(c.frequency),1)    AS Avg_Orders,
               round(avg(c.monetary),2)     AS Avg_Lifetime_Spend
        ORDER BY Avg_Recency_Days ASC
    """,
    "params": {},
}

SEGMENT_CHANNEL_MIX = {
    "title": "Preferred Channel by Segment",
    "cypher": """
        MATCH (c:Customer)-[:BELONGS_TO]->(s:Segment)
        RETURN s.name              AS Segment,
               c.preferred_channel AS Channel,
               count(c)            AS Customers
        ORDER BY Segment, Customers DESC
    """,
    "params": {},
}

# ── Churn Risk ────────────────────────────────────────────────────────────────
CHURN_AT_RISK_DETAIL = {
    "title": "At-Risk & Hibernating Customers",
    "cypher": """
        MATCH (c:Customer)-[:BELONGS_TO]->(s:Segment)
        WHERE s.name IN ['At-Risk', 'Hibernating']
        OPTIONAL MATCH (c)-[:PLACED]->(o:Order)
        WHERE o.status = 'completed'
        WITH c, s, max(o.date) AS last_order
        RETURN c.name          AS Customer,
               c.city          AS City,
               s.name          AS Segment,
               c.recency_days  AS Days_Since_Order,
               c.frequency     AS Total_Orders,
               round(c.monetary, 2) AS Lifetime_Spend,
               last_order      AS Last_Order_Date
        ORDER BY Days_Since_Order DESC
        LIMIT 30
    """,
    "params": {},
}

CHURN_BY_CITY = {
    "title": "Churn Risk Concentration by City",
    "cypher": """
        MATCH (c:Customer)-[:BELONGS_TO]->(s:Segment)
        WHERE s.name IN ['At-Risk', 'Hibernating', 'Lost']
        RETURN c.city   AS City,
               s.name   AS Segment,
               count(c) AS At_Risk_Customers
        ORDER BY At_Risk_Customers DESC
        LIMIT 20
    """,
    "params": {},
}

CHURN_REVENUE_AT_STAKE = {
    "title": "Revenue at Stake from Churning Segments",
    "cypher": """
        MATCH (c:Customer)-[:BELONGS_TO]->(s:Segment)
        WHERE s.name IN ['At-Risk', 'Hibernating', 'Lost']
        RETURN s.name                       AS Segment,
               count(c)                     AS Customers,
               round(sum(c.monetary), 2)    AS Total_Historical_Spend,
               round(avg(c.monetary), 2)    AS Avg_Spend_Per_Customer
        ORDER BY Total_Historical_Spend DESC
    """,
    "params": {},
}

# ── Campaign Effectiveness ────────────────────────────────────────────────────
CAMPAIGN_RESPONSE_SUMMARY = {
    "title": "Campaign Response Summary",
    "cypher": """
        MATCH (camp:Campaign)-[:TARGETS]->(s:Segment)
        OPTIONAL MATCH (c:Customer)-[r:RESPONDED_TO]->(camp)
        RETURN camp.name              AS Campaign,
               camp.type             AS Type,
               camp.start_date       AS Start_Date,
               s.name                AS Target_Segment,
               count(DISTINCT c)     AS Responders
        ORDER BY Responders DESC
    """,
    "params": {},
}

CAMPAIGN_RESPONSE_BY_SEGMENT = {
    "title": "Responders by Actual Segment (vs Target)",
    "cypher": """
        MATCH (c:Customer)-[:RESPONDED_TO]->(camp:Campaign),
              (c)-[:BELONGS_TO]->(s:Segment)
        RETURN camp.name  AS Campaign,
               s.name     AS Responder_Segment,
               count(c)   AS Responders
        ORDER BY Campaign, Responders DESC
    """,
    "params": {},
}

MULTI_CAMPAIGN_CUSTOMERS = {
    "title": "Customers Who Responded to Multiple Campaigns",
    "cypher": """
        MATCH (c:Customer)-[:RESPONDED_TO]->(camp:Campaign)
        WITH c, count(camp) AS campaign_count
        WHERE campaign_count > 1
        MATCH (c)-[:BELONGS_TO]->(s:Segment)
        RETURN c.name          AS Customer,
               c.city          AS City,
               s.name          AS Segment,
               campaign_count  AS Campaigns_Responded,
               round(c.monetary, 2) AS Lifetime_Spend
        ORDER BY Campaigns_Responded DESC, Lifetime_Spend DESC
        LIMIT 20
    """,
    "params": {},
}

# ── Cross-Sell Opportunities ──────────────────────────────────────────────────
CROSS_SELL_GLOBAL = {
    "title": "Top Product Co-Purchase Pairs (All Customers)",
    "cypher": """
        MATCH (o:Order)-[:CONTAINS]->(p1:Product),
              (o)-[:CONTAINS]->(p2:Product)
        WHERE p1.id < p2.id
          AND o.status = 'completed'
        RETURN p1.name AS Product_A,
               p2.name AS Product_B,
               count(DISTINCT o) AS Co_Purchases
        ORDER BY Co_Purchases DESC
        LIMIT 20
    """,
    "params": {},
}

CROSS_SELL_BY_SEGMENT = {
    "title": "Cross-Sell Pairs — Champions Segment",
    "cypher": """
        MATCH (c:Customer)-[:BELONGS_TO]->(s:Segment {name: 'Champions'}),
              (c)-[:PLACED]->(o:Order)-[:CONTAINS]->(p1:Product),
              (o)-[:CONTAINS]->(p2:Product)
        WHERE p1.id < p2.id
          AND o.status = 'completed'
        RETURN p1.name AS Product_A,
               p2.name AS Product_B,
               count(DISTINCT o) AS Co_Purchases
        ORDER BY Co_Purchases DESC
        LIMIT 15
    """,
    "params": {},
}

CATEGORY_AFFINITY = {
    "title": "Category Co-Purchase Affinity",
    "cypher": """
        MATCH (o:Order)-[:CONTAINS]->(p1:Product)-[:BELONGS_TO]->(c1:Category),
              (o)-[:CONTAINS]->(p2:Product)-[:BELONGS_TO]->(c2:Category)
        WHERE c1.id < c2.id
          AND o.status = 'completed'
        RETURN c1.name AS Category_A,
               c2.name AS Category_B,
               count(DISTINCT o) AS Orders_Together
        ORDER BY Orders_Together DESC
        LIMIT 15
    """,
    "params": {},
}

TOP_PRODUCTS_BY_SEGMENT = {
    "title": "Top Products by Revenue — per Segment",
    "cypher": """
        MATCH (c:Customer)-[:BELONGS_TO]->(s:Segment),
              (c)-[:PLACED]->(o:Order)-[r:CONTAINS]->(p:Product)
        WHERE o.status = 'completed'
        WITH s.name AS Segment, p.name AS Product,
             sum(r.quantity * r.unit_price) AS Revenue
        ORDER BY Segment, Revenue DESC
        WITH Segment, collect({product: Product, revenue: Revenue})[..3] AS top
        UNWIND top AS t
        RETURN Segment,
               t.product            AS Product,
               round(t.revenue, 2)  AS Revenue
        ORDER BY Segment
    """,
    "params": {},
}

# ── Report definitions — maps report name → list of queries to run ────────────
REPORTS: dict[str, dict] = {
    "Segment Health Overview": {
        "description": "RFM segment breakdown with AOV, recency, channel preferences and revenue contribution.",
        "icon": "📊",
        "queries": [SEGMENT_AOV, SEGMENT_RECENCY, SEGMENT_CHANNEL_MIX],
    },
    "Churn Risk Report": {
        "description": "Identifies At-Risk, Hibernating and Lost customers with revenue exposure by city.",
        "icon": "⚠️",
        "queries": [CHURN_REVENUE_AT_STAKE, CHURN_BY_CITY, CHURN_AT_RISK_DETAIL],
    },
    "Campaign Effectiveness": {
        "description": "Response rates per campaign, segment-level breakdown and multi-touch customers.",
        "icon": "📣",
        "queries": [
            CAMPAIGN_RESPONSE_SUMMARY,
            CAMPAIGN_RESPONSE_BY_SEGMENT,
            MULTI_CAMPAIGN_CUSTOMERS,
        ],
    },
    "Cross-Sell Opportunities": {
        "description": "Frequently co-purchased product and category pairs to inform bundling and recommendations.",
        "icon": "🔗",
        "queries": [
            CROSS_SELL_GLOBAL,
            CROSS_SELL_BY_SEGMENT,
            CATEGORY_AFFINITY,
            TOP_PRODUCTS_BY_SEGMENT,
        ],
    },
}
