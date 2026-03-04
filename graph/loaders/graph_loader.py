"""
graph/loaders/graph_loader.py
==============================
Bulk-loads processed CSVs into Neo4j using idempotent MERGE statements.
Each loader function is independent and safe to re-run.

Batching is used throughout to avoid single massive transactions.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from graph.loaders.neo4j_client import Neo4jClient

BATCH_SIZE = 250  # rows per transaction


def _batched(records: list[dict], batch_size: int = BATCH_SIZE):
    """Yield successive batches of records."""
    for i in range(0, len(records), batch_size):
        yield records[i : i + batch_size]


def _run_batched(client: Neo4jClient, query: str, records: list[dict], label: str) -> int:
    total = 0
    n_batches = math.ceil(len(records) / BATCH_SIZE)
    for i, batch in enumerate(_batched(records), 1):
        client.run(query, {"rows": batch})
        total += len(batch)
        print(f"    {label}: batch {i}/{n_batches}  ({total}/{len(records)})", end="\r")
    print()
    return total


# ─────────────────────────────────────────────────────────────────────────────
# Categories
# ─────────────────────────────────────────────────────────────────────────────
def load_categories(df: pd.DataFrame) -> None:
    query = """
    UNWIND $rows AS row
    MERGE (c:Category {id: row.category_id})
    SET   c.name = row.category_name
    """
    with Neo4jClient() as client:
        n = _run_batched(client, query, df.to_dict("records"), "Category")
    print(f"  ✅ Loaded {n} categories.")


# ─────────────────────────────────────────────────────────────────────────────
# Products  (also creates :BELONGS_TO → Category)
# ─────────────────────────────────────────────────────────────────────────────
def load_products(df: pd.DataFrame) -> None:
    query = """
    UNWIND $rows AS row
    MERGE (p:Product {id: row.product_id})
    SET   p.name      = row.product_name,
          p.brand     = row.brand,
          p.price     = toFloat(row.price),
          p.is_active = row.is_active
    WITH  p, row
    MATCH (c:Category {id: row.category_id})
    MERGE (p)-[:BELONGS_TO]->(c)
    """
    with Neo4jClient() as client:
        n = _run_batched(client, query, df.to_dict("records"), "Product")
    print(f"  ✅ Loaded {n} products with category edges.")


# ─────────────────────────────────────────────────────────────────────────────
# Segments master nodes
# ─────────────────────────────────────────────────────────────────────────────
def load_segment_nodes(df: pd.DataFrame) -> None:
    query = """
    UNWIND $rows AS row
    MERGE (s:Segment {id: row.segment_id})
    SET   s.name = row.segment_name
    """
    with Neo4jClient() as client:
        n = _run_batched(client, query, df.to_dict("records"), "Segment")
    print(f"  ✅ Loaded {n} segment nodes.")


# ─────────────────────────────────────────────────────────────────────────────
# Customers  (also creates :BELONGS_TO → Segment)
# ─────────────────────────────────────────────────────────────────────────────
def load_customers(customers_df: pd.DataFrame, customer_segments_df: pd.DataFrame) -> None:
    # Build a lookup: customer_id → {segment_id, since_date, rfm_score, R, F, M}
    seg_lookup: dict[str, dict[str, Any]] = (
        customer_segments_df.set_index("customer_id")[
            ["segment_id", "since_date", "rfm_score", "R", "F", "M",
             "recency", "frequency", "monetary"]
        ]
        .to_dict("index")
    )

    records = []
    for row in customers_df.to_dict("records"):
        cid  = row["customer_id"]
        seg  = seg_lookup.get(cid, {})
        records.append({**row, **seg})

    customer_query = """
    UNWIND $rows AS row
    MERGE (c:Customer {id: row.customer_id})
    SET   c.name               = row.name,
          c.email              = row.email,
          c.age                = toInteger(row.age),
          c.gender             = row.gender,
          c.city               = row.city,
          c.join_date          = row.join_date,
          c.preferred_channel  = row.preferred_channel,
          c.rfm_score          = toInteger(row.rfm_score),
          c.rfm_r              = toInteger(row.R),
          c.rfm_f              = toInteger(row.F),
          c.rfm_m              = toInteger(row.M),
          c.recency_days       = toInteger(row.recency),
          c.frequency          = toInteger(row.frequency),
          c.monetary           = toFloat(row.monetary)
    WITH  c, row
    WHERE row.segment_id IS NOT NULL
    MATCH (s:Segment {id: row.segment_id})
    MERGE (c)-[r:BELONGS_TO]->(s)
    SET   r.since_date = row.since_date
    """
    with Neo4jClient() as client:
        n = _run_batched(client, customer_query, records, "Customer")
    print(f"  ✅ Loaded {n} customers with segment edges.")


# ─────────────────────────────────────────────────────────────────────────────
# Orders  (creates Order nodes + :PLACED edges)
# ─────────────────────────────────────────────────────────────────────────────
def load_orders(orders_df: pd.DataFrame) -> None:
    query = """
    UNWIND $rows AS row
    MERGE (o:Order {id: row.order_id})
    SET   o.date        = row.order_date,
          o.total_value = toFloat(row.total_value),
          o.channel     = row.channel,
          o.status      = row.status
    WITH  o, row
    MATCH (c:Customer {id: row.customer_id})
    MERGE (c)-[:PLACED]->(o)
    """
    with Neo4jClient() as client:
        n = _run_batched(client, query, orders_df.to_dict("records"), "Order")
    print(f"  ✅ Loaded {n} orders with PLACED edges.")


# ─────────────────────────────────────────────────────────────────────────────
# Order Items  (creates :CONTAINS edges between Order and Product)
# ─────────────────────────────────────────────────────────────────────────────
def load_order_items(items_df: pd.DataFrame) -> None:
    query = """
    UNWIND $rows AS row
    MATCH (o:Order   {id: row.order_id})
    MATCH (p:Product {id: row.product_id})
    MERGE (o)-[r:CONTAINS]->(p)
    SET   r.quantity   = toInteger(row.quantity),
          r.unit_price = toFloat(row.unit_price)
    """
    with Neo4jClient() as client:
        n = _run_batched(client, query, items_df.to_dict("records"), "OrderItem")
    print(f"  ✅ Loaded {n} order-item edges.")


# ─────────────────────────────────────────────────────────────────────────────
# Campaigns  (creates Campaign nodes + :TARGETS → Segment)
# ─────────────────────────────────────────────────────────────────────────────
def load_campaigns(campaigns_df: pd.DataFrame, segments_df: pd.DataFrame) -> None:
    # Resolve target_segment name → segment_id
    seg_name_to_id = segments_df.set_index("segment_name")["segment_id"].to_dict()

    records = []
    for row in campaigns_df.to_dict("records"):
        records.append({
            **row,
            "segment_id": seg_name_to_id.get(row["target_segment"]),
        })

    query = """
    UNWIND $rows AS row
    MERGE (camp:Campaign {id: row.campaign_id})
    SET   camp.name       = row.campaign_name,
          camp.type       = row.campaign_type,
          camp.start_date = row.start_date
    WITH  camp, row
    WHERE row.segment_id IS NOT NULL
    MATCH (s:Segment {id: row.segment_id})
    MERGE (camp)-[:TARGETS]->(s)
    """
    with Neo4jClient() as client:
        n = _run_batched(client, query, records, "Campaign")
    print(f"  ✅ Loaded {n} campaigns with TARGETS edges.")


# ─────────────────────────────────────────────────────────────────────────────
# Campaign Responses  (:RESPONDED_TO edges)
# ─────────────────────────────────────────────────────────────────────────────
def load_campaign_responses(responses_df: pd.DataFrame) -> None:
    query = """
    UNWIND $rows AS row
    MATCH (c:Customer  {id: row.customer_id})
    MATCH (camp:Campaign {id: row.campaign_id})
    MERGE (c)-[r:RESPONDED_TO]->(camp)
    SET   r.response_date = row.response_date
    """
    with Neo4jClient() as client:
        n = _run_batched(client, query, responses_df.to_dict("records"), "CampResponse")
    print(f"  ✅ Loaded {n} campaign-response edges.")
