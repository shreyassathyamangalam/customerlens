"""
tests/integration/test_qa_chain.py
====================================
Integration test suite for the GraphCypherQAChain.

Tests are grouped into four business domains:
  1. Segment analytics
  2. Product & basket intelligence
  3. Campaign effectiveness
  4. Customer look-ups

Each test:
  - Sends a natural-language question to the chain
  - Asserts the chain returns a non-empty answer string
  - Prints the generated Cypher and answer for human review

Requirements:
  - A live Neo4j AuraDB instance populated by run_ingestion.py
  - ANTHROPIC_API_KEY set in .env

Run:
  uv run pytest tests/integration/test_qa_chain.py -v -s

Skip a single test:
  uv run pytest tests/integration/test_qa_chain.py -v -s -k "not cross_sell"
"""

from __future__ import annotations

import os
import textwrap

import pytest

# Skip entire module if credentials are absent (CI without secrets)
NEO4J_URI = os.getenv("NEO4J_URI", "")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")

pytestmark = pytest.mark.skipif(
    not NEO4J_URI or not ANTHROPIC_KEY,
    reason="NEO4J_URI or ANTHROPIC_API_KEY not set — skipping integration tests",
)


# ── Fixture ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def chain():
    """Build the QA chain once and reuse across all tests in this module."""
    from llm.chains.qa_chain import build_qa_chain

    return build_qa_chain(verbose=True, return_intermediate_steps=True)


# ── Helper ───────────────────────────────────────────────────────────────────


def ask(chain, question: str) -> dict:
    """Invoke the chain and pretty-print results."""
    print(f"\n{'─' * 60}")
    print(f"Q: {question}")
    result = chain.invoke({"query": question})
    steps = result.get("intermediate_steps", [])

    if steps:
        cypher = steps[0].get("query", "n/a")
        raw = steps[1].get("context", []) if len(steps) > 1 else []
        print(f"\nCypher:\n{textwrap.indent(cypher, '  ')}")
        print(f"\nRaw rows ({len(raw)}):")
        for row in raw[:5]:
            print(f"  {row}")
        if len(raw) > 5:
            print(f"  … {len(raw) - 5} more rows")

    answer = result.get("result", "")
    print(f"\nAnswer:\n{textwrap.indent(answer, '  ')}")
    return result


# ═════════════════════════════════════════════════════════════════════════════
# 1. SEGMENT ANALYTICS
# ═════════════════════════════════════════════════════════════════════════════


class TestSegmentAnalytics:
    def test_segment_aov(self, chain):
        """Which customer segment has the highest average order value?"""
        result = ask(
            chain, "Which customer segment has the highest average order value?"
        )
        assert result["result"].strip(), "Expected a non-empty answer"

    def test_inactive_champions(self, chain):
        """Champions who haven't ordered in 90 days."""
        result = ask(
            chain,
            "Show me customers in the Champions segment who haven't placed "
            "an order in the last 90 days.",
        )
        assert result["result"].strip()

    def test_segment_distribution(self, chain):
        """How many customers are in each segment?"""
        result = ask(chain, "How many customers are in each RFM segment?")
        assert result["result"].strip()

    def test_high_value_cities(self, chain):
        """Which cities have the most Champions customers?"""
        result = ask(
            chain,
            "Which cities have the highest concentration of Champions customers?",
        )
        assert result["result"].strip()

    def test_at_risk_monetary(self, chain):
        """Total revenue from At-Risk customers."""
        result = ask(
            chain,
            "What is the total lifetime spend of customers in the At-Risk segment?",
        )
        assert result["result"].strip()


# ═════════════════════════════════════════════════════════════════════════════
# 2. PRODUCT & BASKET INTELLIGENCE
# ═════════════════════════════════════════════════════════════════════════════


class TestProductIntelligence:
    def test_top_products_by_revenue(self, chain):
        """Top 10 revenue-generating products."""
        result = ask(chain, "What are the top 10 products by total revenue?")
        assert result["result"].strip()

    def test_top_categories_by_orders(self, chain):
        """Which category appears most frequently in orders?"""
        result = ask(
            chain,
            "Which product category has the highest number of order line items?",
        )
        assert result["result"].strip()

    def test_cross_sell_champions(self, chain):
        """Cross-sell pairs for Champions segment."""
        result = ask(
            chain,
            "Which pairs of products are most frequently bought together "
            "by Champions segment customers?",
        )
        assert result["result"].strip()

    def test_avg_basket_size_by_channel(self, chain):
        """Average basket size per channel."""
        result = ask(
            chain,
            "What is the average number of products per order for each "
            "sales channel (online, in-store, mobile)?",
        )
        assert result["result"].strip()


# ═════════════════════════════════════════════════════════════════════════════
# 3. CAMPAIGN EFFECTIVENESS
# ═════════════════════════════════════════════════════════════════════════════


class TestCampaignEffectiveness:
    def test_campaign_response_rates(self, chain):
        """How many customers responded to each campaign?"""
        result = ask(
            chain,
            "How many unique customers responded to each campaign? "
            "Rank campaigns by response count.",
        )
        assert result["result"].strip()

    def test_email_vs_sms_response(self, chain):
        """Email vs SMS campaign response volume."""
        result = ask(
            chain,
            "Compare the total number of customer responses for email "
            "campaigns versus SMS campaigns.",
        )
        assert result["result"].strip()

    def test_campaign_segment_overlap(self, chain):
        """Which segment responded most to the Black Friday campaign?"""
        result = ask(
            chain,
            "For the Black Friday Blast campaign, how many customers "
            "responded and what segment were they in?",
        )
        assert result["result"].strip()

    def test_multi_campaign_responders(self, chain):
        """Customers who responded to more than one campaign."""
        result = ask(
            chain,
            "How many customers have responded to more than one campaign?",
        )
        assert result["result"].strip()


# ═════════════════════════════════════════════════════════════════════════════
# 4. CUSTOMER LOOK-UPS
# ═════════════════════════════════════════════════════════════════════════════


class TestCustomerLookups:
    def test_top_customers_by_spend(self, chain):
        """Top 5 customers by lifetime spend."""
        result = ask(
            chain,
            "Who are the top 5 customers by total lifetime spend? "
            "Show their name, city, segment, and total spend.",
        )
        assert result["result"].strip()

    def test_mobile_first_customers(self, chain):
        """Customers who prefer mobile channel."""
        result = ask(
            chain,
            "How many customers prefer the mobile channel, and which "
            "segment do most of them belong to?",
        )
        assert result["result"].strip()

    def test_new_customer_orders(self, chain):
        """Customers who joined in 2023 and have placed at least 3 orders."""
        result = ask(
            chain,
            "Which customers joined in 2023 and have placed at least "
            "3 completed orders?",
        )
        assert result["result"].strip()
