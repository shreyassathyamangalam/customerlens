# 🧠 CustomerLens

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.55%2B-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Neo4j](https://img.shields.io/badge/Neo4j-AuraDB-008CC1?style=flat-square&logo=neo4j&logoColor=white)](https://neo4j.com/cloud/platform/aura-graph-database)
[![LangChain](https://img.shields.io/badge/LangChain-1.2%2B-1C3C3C?style=flat-square&logo=chainlink&logoColor=white)](https://langchain.com)
[![Claude](https://img.shields.io/badge/Claude-Sonnet-D4A574?style=flat-square&logo=anthropic&logoColor=white)](https://anthropic.com)
[![uv](https://img.shields.io/badge/uv-package%20manager-DE5FE9?style=flat-square)](https://docs.astral.sh/uv)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

**Retail customer intelligence via a Neo4j knowledge graph + Claude Sonnet.**  
Ask plain-English questions, generate executive reports, explore your data as an interactive graph,  
and run multi-step reasoning with a tool-calling agent — all without writing a line of SQL or Cypher.

[Features](#-features) · [Architecture](#-architecture) · [Quickstart](#-quickstart) · [Project Structure](#-project-structure) · [Query Modes](#-query-modes-chain-vs-agent) · [Configuration](#-configuration) · [Roadmap](#-roadmap)

</div>

---

## ✨ Features

| | Feature | Details |
|---|---|---|
| 💬 | **Q&A — Chain Mode** | Free-form natural language → Cypher generation → graph query → Claude explanation. Best for ad-hoc exploration. Exposes generated Cypher and raw result rows. |
| 🤖 | **Q&A — Agent Mode** | Multi-step ReAct agent with 13 pre-built tools. Claude reasons across multiple graph queries to answer complex questions. Shows full reasoning chain. |
| 📄 | **Report Builder** | 4 templates (Segment Health, Churn Risk, Campaign Effectiveness, Cross-Sell) — runs bundled Cypher queries and Claude writes an executive narrative |
| 🕸️ | **Graph Explorer** | Interactive pyvis visualisations — Customer Neighbourhood, Segment Overview, Schema Diagram |
| 🏭 | **Synthetic Data Pipeline** | Realistic retail data via SDV + Faker: 500 customers, 200 products, 2,000 orders, RFM-scored segments, 8 campaigns |
| 🔒 | **Read-only by design** | All queries use `MATCH`-only Cypher — no writes can be issued through the UI |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                           Streamlit UI                               │
│  ┌─────────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │     Q&A Chat        │  │  Report Builder  │  │ Graph Explorer │  │
│  │  ⛓ Chain │ 🤖 Agent │  │                  │  │                │  │
│  └──────┬──────────┬───┘  └────────┬─────────┘  └───────┬────────┘  │
└─────────┼──────────┼───────────────┼────────────────────┼───────────┘
          │          │               │                    │
          ▼          ▼               ▼                    │
┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  LangChain   │ │ CustomerLens │ │    Report    │       │
│  Cypher      │ │    Agent     │ │   Builder    │       │
│  QAChain     │ │  (LCEL +     │ │ (direct SDK) │       │
│              │ │ bind_tools)  │ │              │       │
│ Claude Sonnet│ │ Claude Sonnet│ │ Claude Sonnet│       │
│ (Cypher gen) │ │ (reasoning)  │ │ (narrative)  │       │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘       │
       │                │                │               │
       │         ┌──────┴──────┐         │               │
       │         │ 13 @tool    │         │               │
       │         │ functions   │         │               │
       │         │ (graph_tools│         │               │
       │         │ .py)        │         │               │
       │         └──────┬──────┘         │               │
       └────────────────┼────────────────┘               │
                        ▼                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        Neo4j AuraDB Free                             │
│                                                                      │
│  (Customer)──PLACED──▶(Order)──CONTAINS──▶(Product)                 │
│       │                                       │                      │
│  BELONGS_TO                             BELONGS_TO                  │
│       ▼                                       ▼                      │
│  (Segment)◀──TARGETS──(Campaign)         (Category)                 │
│       ▲                                                              │
│  RESPONDED_TO from (Customer)                                        │
└──────────────────────────────────────────────────────────────────────┘
```

### Knowledge Graph Schema

| Node | Key Properties |
|---|---|
| `Customer` | id, name, email, age, gender, city, join_date, preferred_channel, rfm_score, rfm_r/f/m, recency_days, frequency, monetary |
| `Order` | id, date, total_value, channel, status |
| `Product` | id, name, brand, price, is_active |
| `Category` | id, name |
| `Segment` | id, name _(Champions / Loyal Customers / Potential Loyalists / At-Risk / Hibernating / Lost)_ |
| `Campaign` | id, name, type _(email / sms / discount)_, start_date |

| Relationship | From → To | Properties |
|---|---|---|
| `PLACED` | Customer → Order | — |
| `CONTAINS` | Order → Product | quantity, unit_price |
| `BELONGS_TO` | Product → Category | — |
| `BELONGS_TO` | Customer → Segment | since_date |
| `RESPONDED_TO` | Customer → Campaign | response_date |
| `TARGETS` | Campaign → Segment | — |

---

## 🚀 Quickstart

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed
- [Neo4j AuraDB Free](https://neo4j.com/cloud/platform/aura-graph-database/) instance
- [Anthropic API key](https://console.anthropic.com/)

### 1. Clone & install

```bash
git clone https://github.com/shreyassathyamangalam/customerlens.git
cd customerlens
uv sync
```

### 2. Configure credentials

```bash
cp .env.example .env
```

Edit `.env`:

```env
NEO4J_URI=neo4j+s://<your-instance>.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password

ANTHROPIC_API_KEY=sk-ant-...

# Optional — tune data generation
NUM_CUSTOMERS=500
NUM_PRODUCTS=200
NUM_ORDERS=2000
RANDOM_SEED=42
```

### 3. Generate synthetic data

```bash
uv run python -m pipeline.generation.generate_data
```

Generates 9 CSVs in `data/raw/` — customers, orders, products, categories, segments, campaigns, and RFM scores.

### 4. Validate data quality

```bash
uv run pytest tests/unit/test_data_quality.py -v
# 38 tests, ~2s, no credentials needed
```

### 5. Ingest into Neo4j

```bash
uv run python -m pipeline.ingestion.run_ingestion
```

Applies schema constraints and loads all nodes and relationships in dependency order. Safe to re-run (all `MERGE` — no duplicates).

### 6. Launch the app

```bash
uv run streamlit run app/main.py
```

Open [http://localhost:8501](http://localhost:8501).

---

## 📁 Project Structure

```
customerlens/
│
├── app/                            # Streamlit application
│   ├── main.py                     # Entry point, global CSS design system, sidebar nav
│   ├── _pages/                     # Page modules (underscore prefix = not MPA-discovered)
│   │   ├── qa_page.py              # Q&A chat — Chain Mode + Agent Mode toggle
│   │   ├── report_page.py          # Report Builder with template selector
│   │   └── graph_page.py           # Interactive graph visualisations
│   ├── components/
│   │   └── graph_viz.py            # pyvis graph builders (no Streamlit dependency)
│   └── reports/
│       └── report_builder.py       # Cypher → DataFrames → Claude narrative
│
├── config/
│   └── settings.py                 # Pydantic Settings — reads from .env
│
├── data/
│   ├── raw/                        # Generated CSVs (git-ignored)
│   └── processed/                  # Transformed CSVs (git-ignored)
│
├── graph/
│   ├── schema/
│   │   ├── constraints.cypher      # Uniqueness constraints + lookup indexes
│   │   └── node_labels.md          # Schema data dictionary
│   ├── loaders/
│   │   ├── neo4j_client.py         # Driver wrapper (context-manager safe, AuraDB fix)
│   │   ├── schema_loader.py        # Applies constraints.cypher
│   │   └── graph_loader.py         # Idempotent bulk loaders (MERGE-based, batched)
│   └── queries/
│       └── report_queries.py       # Named Cypher query library for Report Builder
│
├── llm/
│   ├── chains/
│   │   ├── qa_chain.py             # GraphCypherQAChain wiring + AuraDB database fix
│   │   └── agent_chain.py          # CustomerLensAgent — LCEL ReAct loop, 13 tools
│   ├── prompts/
│   │   └── cypher_prompt.py        # Custom Cypher generation + QA prompt templates
│   └── tools/
│       └── graph_tools.py          # 13 @tool-decorated Cypher query functions
│
├── pipeline/
│   ├── generation/
│   │   └── generate_data.py        # SDV + Faker synthetic data generation
│   ├── transformation/
│   │   └── rfm_segmentation.py     # RFM quintile scoring
│   └── ingestion/
│       └── run_ingestion.py        # Orchestrator: CSV → Neo4j
│
├── scripts/
│   └── ask.py                      # Interactive CLI REPL for testing Q&A
│
├── tests/
│   ├── unit/
│   │   └── test_data_quality.py    # 38 data quality assertions
│   └── integration/
│       └── test_qa_chain.py        # 16 end-to-end Q&A tests (auto-skip without creds)
│
├── .env.example
├── pyproject.toml
└── README.md
```

---

## 🔄 Query Modes: Chain vs Agent

The Q&A page offers two modes, toggled from the top-right of the interface.

### ⛓ Chain Mode
Uses `GraphCypherQAChain` — Claude generates a single Cypher query, runs it against Neo4j, and explains the result.

**Best for:** Ad-hoc exploration, one-shot factual questions.  
**Inspector shows:** Generated Cypher query · raw result rows.

```
Question → Claude generates Cypher → Neo4j → Claude explains result
```

Example questions:
- _"Which customer segment has the highest average order value?"_
- _"What are the top 10 products by total revenue?"_
- _"Show customers in the At-Risk segment from New York."_

### 🤖 Agent Mode
Uses `CustomerLensAgent` — a custom LCEL ReAct loop with 13 pre-built `@tool` functions. Claude decides which tools to call, in what order, loops until it has enough data, then synthesises a final answer.

**Best for:** Multi-hop questions, cross-domain analysis, production reliability.  
**Inspector shows:** Full reasoning chain — each tool call, its input, and the data returned.

```
Question → Claude reasons → Tool call → Result → Claude reasons → ... → Final answer
```

Example questions:
- _"Compare AOV and recency across all segments, then tell me which needs the most urgent attention."_
- _"Give me a complete churn risk summary: revenue at stake, worst cities, top customers to re-engage."_
- _"What are the top cross-sell opportunities for Champions vs At-Risk customers?"_

### Why two modes?

| | Chain Mode | Agent Mode |
|---|---|---|
| Query reliability | Variable — LLM generates Cypher on the fly | High — queries are pre-tested and locked |
| Multi-step reasoning | ❌ Single query only | ✅ Chains multiple tool calls |
| Debugging | Inspect generated Cypher | Inspect full reasoning chain |
| Auditability | Low | High — every tool call is named and logged |
| Best use | Exploration | Production analytics |

---

## 🤖 Agent Tools

The agent has access to 13 pre-built tools across four domains:

| Domain | Tool | Description |
|---|---|---|
| **Segment Analytics** | `get_segment_aov` | AOV, revenue, order count per segment |
| | `get_segment_recency_frequency` | Recency, frequency, lifetime spend per segment |
| | `get_segment_channel_mix` | Preferred channel breakdown per segment |
| **Churn Risk** | `get_churn_revenue_at_stake` | Historical spend of At-Risk / Hibernating / Lost segments |
| | `get_churn_risk_by_city` | Geographic concentration of churning customers |
| | `get_at_risk_customer_detail` | Individual customer-level churn detail, top 30 |
| **Campaign Effectiveness** | `get_campaign_response_summary` | Responder counts per campaign, ranked |
| | `get_campaign_response_by_segment` | Actual vs target segment response breakdown |
| | `get_multi_campaign_customers` | Customers who responded to 2+ campaigns |
| **Cross-Sell Intelligence** | `get_cross_sell_pairs_global` | Top 20 product co-purchase pairs, all customers |
| | `get_cross_sell_pairs_champions` | Top 15 co-purchase pairs for Champions only |
| | `get_category_affinity` | Category-level co-purchase affinity |
| | `get_top_products_by_segment` | Top 3 revenue products per segment |

---

## 📊 Report Builder

Four report templates, each running a bundle of Cypher queries and generating a Claude-written executive narrative (≤350 words):

| Template | Queries | Focus |
|---|---|---|
| 📊 Segment Health Overview | 3 | AOV, recency, channel mix by RFM segment |
| ⚠️ Churn Risk Report | 3 | At-Risk / Hibernating customers, revenue at stake, city breakdown |
| 📣 Campaign Effectiveness | 3 | Response rates, segment breakdown, multi-touch customers |
| 🔗 Cross-Sell Opportunities | 4 | Co-purchase pairs, category affinity, top products per segment |

Reports include interactive data tables with Altair bar charts and a markdown download button.

---

## 🕸️ Graph Explorer

Three interactive pyvis views rendered via vis.js:

- **Customer Neighbourhood** — pick any customer from the top-200 by RFM score, see their orders → products → categories → segment as a force-directed graph
- **Segment Overview** — hub-and-spoke view of top-RFM customers clustered around their segments; multi-select which segments to include
- **Schema Diagram** — static reference of all 6 node types and 6 relationship types

All graphs are dark-themed, colour-coded by node type, with hover tooltips and drag-to-explore interaction.

---

## ⚙️ Configuration

All settings read from `.env` via Pydantic Settings. Every value has a sensible default.

| Variable | Default | Description |
|---|---|---|
| `NEO4J_URI` | `neo4j+s://localhost:7687` | AuraDB connection URI |
| `NEO4J_USERNAME` | `neo4j` | Database username |
| `NEO4J_PASSWORD` | _(required)_ | Database password |
| `ANTHROPIC_API_KEY` | _(required)_ | Anthropic API key |
| `LLM_MODEL` | `claude-sonnet-4-5` | Claude model identifier |
| `NUM_CUSTOMERS` | `500` | Customers to generate |
| `NUM_PRODUCTS` | `200` | Products to generate |
| `NUM_ORDERS` | `2000` | Orders to generate |
| `RANDOM_SEED` | `42` | Reproducibility seed |

> **Neo4j AuraDB note:** `langchain-neo4j` defaults the database name to `"neo4j"`, which AuraDB Free rejects. This project patches `graph._database = None` before calling `refresh_schema()` so the driver routes to the server's default database automatically. No extra configuration needed.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.11+ |
| **Package manager** | [uv](https://docs.astral.sh/uv/) |
| **Graph database** | [Neo4j AuraDB Free](https://neo4j.com/cloud/platform/aura-graph-database/) |
| **LLM** | [Claude Sonnet](https://anthropic.com) via `langchain-anthropic` + `anthropic` SDK |
| **Chain mode** | [LangChain `GraphCypherQAChain`](https://python.langchain.com/docs/integrations/graphs/neo4j_cypher/) + `langchain-neo4j` |
| **Agent mode** | Custom LCEL ReAct loop — `ChatAnthropic.bind_tools()` + 13 `@tool` functions |
| **Synthetic data** | [SDV](https://sdv.dev/) + [Faker](https://faker.readthedocs.io/) |
| **UI framework** | [Streamlit](https://streamlit.io/) 1.55+ |
| **Graph visualisation** | [pyvis](https://pyvis.readthedocs.io/) (vis.js) |
| **Charts** | [Altair](https://altair-viz.github.io/) |
| **Config** | [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) |
| **Testing** | [pytest](https://pytest.org/) |

---

## 🧪 Testing

```bash
# Unit tests — data quality (no credentials needed)
uv run pytest tests/unit/ -v
# 38 tests, ~2s

# Integration tests — live Q&A chain (requires .env credentials)
uv run pytest tests/integration/ -v -s
# 16 tests across 4 domains — auto-skipped in CI without secrets

# Interactive CLI REPL for manual Q&A testing
uv run python scripts/ask.py
uv run python scripts/ask.py --question "Which segment has the highest AOV?"
uv run python scripts/ask.py --no-steps   # hide Cypher / raw data
```

---

## 🗺️ Roadmap

- [x] Chain Mode — free-form Cypher Q&A
- [x] Agent Mode — multi-step ReAct agent with 13 pre-built tools
- [x] Report Builder — 4 templates with Claude narrative
- [x] Graph Explorer — pyvis visualisations
- [x] Synthetic data pipeline — SDV + Faker + RFM scoring
- [ ] Export reports to PDF
- [ ] Neo4j GDS integration — PageRank, community detection, link prediction
- [ ] Docker Compose for one-command local setup
- [ ] GitHub Actions CI — unit tests on every push
- [ ] `st.chat_message` redesign for Q&A page

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.

---

<div align="center">
<sub>Built with Neo4j · LangChain · Claude · Streamlit · pyvis</sub>
</div>
