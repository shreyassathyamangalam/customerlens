"""
pipeline/ingestion/run_ingestion.py
=====================================
Orchestrates the full CSV → Neo4j pipeline in dependency order:

  1. Apply schema constraints & indexes
  2. Load Categories
  3. Load Segments (master nodes)
  4. Load Products  (→ Category edges)
  5. Load Customers (→ Segment edges)
  6. Load Orders    (→ Customer edges)
  7. Load Order Items (→ Product edges)
  8. Load Campaigns  (→ Segment edges)
  9. Load Campaign Responses (→ Customer + Campaign edges)

Run:
  uv run python -m pipeline.ingestion.run_ingestion

Options:
  --skip-schema   Skip constraint creation (re-runs only)
  --dry-run       Parse CSVs but don't write to Neo4j
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).parents[2] / "data" / "raw"


def _load(filename: str) -> pd.DataFrame:
    path = RAW_DIR / filename
    if not path.exists():
        print(f"  ❌ Missing: {path}")
        print("     Run `uv run python -m pipeline.generation.generate_data` first.")
        sys.exit(1)
    df = pd.read_csv(path)
    print(f"  📂 {filename:<30} {len(df):>6} rows")
    return df


def run(skip_schema: bool = False, dry_run: bool = False) -> None:
    t0 = time.perf_counter()
    print("\n" + "═" * 50)
    print("  CustomerLens — Neo4j Ingestion Pipeline")
    print("═" * 50)

    # ── 1. Load all CSVs ───────────────────────────────────
    print("\n📂  Reading CSVs from data/raw/ …")
    categories_df        = _load("categories.csv")
    segments_df          = _load("segments.csv")
    products_df          = _load("products.csv")
    customers_df         = _load("customers.csv")
    customer_segments_df = _load("customer_segments.csv")
    orders_df            = _load("orders.csv")
    order_items_df       = _load("order_items.csv")
    campaigns_df         = _load("campaigns.csv")
    responses_df         = _load("campaign_responses.csv")

    if dry_run:
        print("\n⚠️   --dry-run: CSVs parsed OK. No data written to Neo4j.")
        return

    # ── 2. Apply schema ────────────────────────────────────
    from graph.loaders import schema_loader, graph_loader

    if not skip_schema:
        print("\n🔧  Applying schema constraints & indexes …")
        schema_loader.apply_constraints()
    else:
        print("\n⏭️   Skipping schema (--skip-schema)")

    # ── 3–9. Load nodes & edges in dependency order ────────
    print("\n📥  Loading nodes & relationships …\n")

    graph_loader.load_categories(categories_df)
    graph_loader.load_segment_nodes(segments_df)
    graph_loader.load_products(products_df)
    graph_loader.load_customers(customers_df, customer_segments_df)
    graph_loader.load_orders(orders_df)
    graph_loader.load_order_items(order_items_df)
    graph_loader.load_campaigns(campaigns_df, segments_df)
    graph_loader.load_campaign_responses(responses_df)

    elapsed = time.perf_counter() - t0
    print(f"\n{'═' * 50}")
    print(f"  🎉  Ingestion complete in {elapsed:.1f}s")
    print(f"{'═' * 50}\n")

    # ── Quick graph stats ──────────────────────────────────
    _print_graph_stats()


def _print_graph_stats() -> None:
    from graph.loaders.neo4j_client import Neo4jClient

    node_q = """
    CALL apoc.meta.stats() YIELD labels
    RETURN labels
    """
    count_q = """
    MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count
    ORDER BY count DESC
    """
    rel_q = """
    MATCH ()-[r]->() RETURN type(r) AS rel_type, count(r) AS count
    ORDER BY count DESC
    """
    print("📊  Graph summary:")
    with Neo4jClient() as client:
        for row in client.run(count_q):
            print(f"    {row['label']:<20} {row['count']:>6} nodes")
        print()
        for row in client.run(rel_q):
            print(f"    :{row['rel_type']:<25} {row['count']:>6} relationships")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CustomerLens Neo4j ingestion")
    parser.add_argument("--skip-schema", action="store_true")
    parser.add_argument("--dry-run",     action="store_true")
    args = parser.parse_args()
    run(skip_schema=args.skip_schema, dry_run=args.dry_run)
