"""
llm/prompts/cypher_prompt.py
==============================
Custom prompt templates for:
  1. Cypher generation  — NL question → valid Cypher query
  2. QA answering       — Cypher results → human-readable answer

Keeping prompts in their own module makes them easy to iterate on
without touching chain logic.
"""

from langchain_core.prompts import PromptTemplate

# ─────────────────────────────────────────────────────────────────────────────
# 1. Cypher Generation Prompt
# ─────────────────────────────────────────────────────────────────────────────

CYPHER_GENERATION_TEMPLATE = """You are an expert Neo4j Cypher query writer for a retail
customer analytics knowledge graph.

## Graph Schema
{schema}

## Node Labels & Key Properties
- Customer  : id, name, email, age, gender, city, join_date, preferred_channel,
              rfm_score, rfm_r, rfm_f, rfm_m, recency_days, frequency, monetary
- Order     : id, date, total_value, channel, status
- Product   : id, name, brand, price, is_active
- Category  : id, name
- Segment   : id, name
- Campaign  : id, name, type, start_date

## Relationship Types
(:Customer)-[:PLACED]->(:Order)
(:Order)-[:CONTAINS {{quantity, unit_price}}]->(:Product)
(:Product)-[:BELONGS_TO]->(:Category)
(:Customer)-[:BELONGS_TO {{since_date}}]->(:Segment)
(:Customer)-[:RESPONDED_TO {{response_date}}]->(:Campaign)
(:Campaign)-[:TARGETS]->(:Segment)

## Cypher Writing Rules
1. Use MATCH and RETURN — never CREATE, MERGE, DELETE, or SET.
2. Always alias return columns with descriptive names (e.g. `count(o) AS total_orders`).
3. Default LIMIT 25 unless the user specifies a different number.
4. For date comparisons use: date(o.date) >= date('2024-01-01')
5. For aggregations always include a GROUP BY equivalent (WITH clause or implicit).
6. When the question involves "cross-sell" or "also bought", traverse:
   (:Customer)-[:PLACED]->(:Order)-[:CONTAINS]->(:Product)
7. Segment names are: 'Champions', 'Loyal Customers', 'Potential Loyalists',
   'At-Risk', 'Hibernating', 'Lost', 'Others'
8. Campaign types are: 'email', 'sms', 'discount'
9. Order statuses: 'completed', 'returned', 'cancelled'
10. Do NOT wrap the query in markdown fences or add any explanation — return
    only the raw Cypher statement.

## Question
{question}

## Cypher Query
"""

CYPHER_GENERATION_PROMPT = PromptTemplate(
    input_variables=["schema", "question"],
    template=CYPHER_GENERATION_TEMPLATE,
)


# ─────────────────────────────────────────────────────────────────────────────
# 2. QA Answer Prompt
# ─────────────────────────────────────────────────────────────────────────────

QA_TEMPLATE = """You are a senior retail customer analytics advisor.
A colleague has asked a business question and you have retrieved relevant data
from the customer knowledge graph to answer it.

## Original Question
{question}

## Data Retrieved from Graph
{context}

## Instructions
- Answer in clear, concise business language — no technical jargon.
- Lead with the direct answer, then provide supporting detail.
- If the data contains numbers, include them precisely.
- If the data is empty or insufficient, say so honestly and suggest what
  additional data might help.
- Format lists or tables only when they genuinely aid readability.
- Keep the response under 200 words unless the question explicitly asks for
  a full report.

## Answer
"""

QA_PROMPT = PromptTemplate(
    input_variables=["question", "context"],
    template=QA_TEMPLATE,
)
