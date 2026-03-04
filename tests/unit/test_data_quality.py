"""
tests/unit/test_data_quality.py
=================================
Validates that generated CSVs in data/raw/ meet the structural
and statistical expectations of the knowledge graph schema.

Run:
  uv run pytest tests/unit/test_data_quality.py -v
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

RAW = Path(__file__).parents[2] / "data" / "raw"

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def categories():    return pd.read_csv(RAW / "categories.csv")

@pytest.fixture(scope="module")
def products():      return pd.read_csv(RAW / "products.csv")

@pytest.fixture(scope="module")
def customers():     return pd.read_csv(RAW / "customers.csv")

@pytest.fixture(scope="module")
def orders():        return pd.read_csv(RAW / "orders.csv")

@pytest.fixture(scope="module")
def order_items():   return pd.read_csv(RAW / "order_items.csv")

@pytest.fixture(scope="module")
def segments():      return pd.read_csv(RAW / "segments.csv")

@pytest.fixture(scope="module")
def cust_segments(): return pd.read_csv(RAW / "customer_segments.csv")

@pytest.fixture(scope="module")
def campaigns():     return pd.read_csv(RAW / "campaigns.csv")

@pytest.fixture(scope="module")
def responses():     return pd.read_csv(RAW / "campaign_responses.csv")


# ── Categories ────────────────────────────────────────────────────────────────

def test_categories_row_count(categories):
    assert len(categories) == 8

def test_categories_no_nulls(categories):
    assert categories.isnull().sum().sum() == 0

def test_categories_unique_ids(categories):
    assert categories["category_id"].is_unique


# ── Products ──────────────────────────────────────────────────────────────────

def test_products_row_count(products):
    assert len(products) == 200

def test_products_unique_ids(products):
    assert products["product_id"].is_unique

def test_products_price_positive(products):
    assert (products["price"] > 0).all()

def test_products_valid_category_refs(products, categories):
    valid_cats = set(categories["category_id"])
    assert set(products["category_id"]).issubset(valid_cats)

def test_products_no_missing_names(products):
    assert products["product_name"].notna().all()
    assert (products["product_name"].str.strip() != "").all()


# ── Customers ─────────────────────────────────────────────────────────────────

def test_customers_row_count(customers):
    assert len(customers) == 500

def test_customers_unique_ids(customers):
    assert customers["customer_id"].is_unique

def test_customers_unique_emails(customers):
    assert customers["email"].is_unique

def test_customers_age_range(customers):
    assert customers["age"].between(18, 80).all()

def test_customers_valid_genders(customers):
    valid = {"M", "F", "Non-binary", "Prefer not to say"}
    assert set(customers["gender"]).issubset(valid)

def test_customers_valid_channels(customers):
    valid = {"online", "in-store", "mobile"}
    assert set(customers["preferred_channel"]).issubset(valid)

def test_customers_have_segment(customers):
    assert customers["segment_name"].notna().all()

def test_customers_rfm_score_positive(customers):
    assert (customers["rfm_score"] > 0).all()


# ── Orders ────────────────────────────────────────────────────────────────────

def test_orders_row_count(orders):
    assert len(orders) == 2000

def test_orders_unique_ids(orders):
    assert orders["order_id"].is_unique

def test_orders_valid_customer_refs(orders, customers):
    valid = set(customers["customer_id"])
    assert set(orders["customer_id"]).issubset(valid)

def test_orders_positive_total(orders):
    assert (orders["total_value"] > 0).all()

def test_orders_valid_status(orders):
    valid = {"completed", "returned", "cancelled"}
    assert set(orders["status"]).issubset(valid)

def test_orders_completed_majority(orders):
    pct = (orders["status"] == "completed").mean()
    assert pct > 0.80, f"Expected >80% completed, got {pct:.1%}"

def test_orders_date_range(orders):
    dates = pd.to_datetime(orders["order_date"])
    assert dates.min() >= pd.Timestamp("2022-01-01")
    assert dates.max() <= pd.Timestamp("2024-12-31")


# ── Order Items ───────────────────────────────────────────────────────────────

def test_order_items_valid_order_refs(order_items, orders):
    valid = set(orders["order_id"])
    assert set(order_items["order_id"]).issubset(valid)

def test_order_items_valid_product_refs(order_items, products):
    valid = set(products["product_id"])
    assert set(order_items["product_id"]).issubset(valid)

def test_order_items_quantity_positive(order_items):
    assert (order_items["quantity"] >= 1).all()

def test_order_items_price_positive(order_items):
    assert (order_items["unit_price"] > 0).all()

def test_every_order_has_items(orders, order_items):
    orders_with_items = set(order_items["order_id"])
    all_orders = set(orders["order_id"])
    missing = all_orders - orders_with_items
    assert len(missing) == 0, f"{len(missing)} orders have no line items"


# ── Segments ──────────────────────────────────────────────────────────────────

def test_segments_count(segments):
    assert len(segments) >= 5, "Expected at least 5 distinct segments"

def test_segments_unique_ids(segments):
    assert segments["segment_id"].is_unique

def test_all_customers_segmented(customers, cust_segments):
    assert len(cust_segments) == len(customers)

def test_cust_segments_rfm_scores_valid(cust_segments):
    for col in ["R", "F", "M"]:
        assert cust_segments[col].between(1, 5).all(), f"{col} score out of 1–5 range"


# ── Campaigns & Responses ─────────────────────────────────────────────────────

def test_campaigns_count(campaigns):
    assert len(campaigns) == 8

def test_campaigns_unique_ids(campaigns):
    assert campaigns["campaign_id"].is_unique

def test_responses_valid_campaign_refs(responses, campaigns):
    valid = set(campaigns["campaign_id"])
    assert set(responses["campaign_id"]).issubset(valid)

def test_responses_valid_customer_refs(responses, customers):
    valid = set(customers["customer_id"])
    assert set(responses["customer_id"]).issubset(valid)

def test_response_rate_reasonable(responses, customers):
    # Total unique responding customers shouldn't exceed all customers
    assert responses["customer_id"].nunique() <= len(customers)

def test_responses_after_campaign_start(responses, campaigns):
    camp_dates = campaigns.set_index("campaign_id")["start_date"].to_dict()
    df = responses.copy()
    df["campaign_start"] = pd.to_datetime(df["campaign_id"].map(camp_dates))
    df["response_date"]  = pd.to_datetime(df["response_date"])
    assert (df["response_date"] >= df["campaign_start"]).all(), \
        "Some response dates precede campaign start dates"
