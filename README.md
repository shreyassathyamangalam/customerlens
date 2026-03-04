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
Ask plain-English questions, generate executive reports, and explore your customer data as an interactive graph — all without writing a line of SQL or Cypher.

[Features](#-features) · [Architecture](#-architecture) · [Quickstart](#-quickstart) · [Project Structure](#-project-structure) · [Screenshots](#-screenshots) · [Configuration](#-configuration)

</div>

---

## ✨ Features

| | Feature | Details |
|---|---|---|
| 💬 | **Natural Language Q&A** | Ask business questions in plain English — LangChain + Claude Sonnet generates Cypher, queries Neo4j, and explains the results |
| 📄 | **Report Builder** | Choose from 4 templates (Segment Health, Churn Risk, Campaign Effectiveness, Cross-Sell) — Claude writes an executive narrative from live graph data |
| 🕸️ | **Graph Explorer** | Interactive pyvis visualisations — Customer Neighbourhood, Segment Overview, and Schema Diagram |
| 🏭 | **Synthetic Data Pipeline** | Realistic retail data generated with SDV + Faker: 500 customers, 200 products, 2,000 orders, RFM-scored segments |
| 🔒 | **Read-only by design** | All LangChain chains use `MATCH`-only Cypher — no writes can be issued through the UI |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit UI                             │
│   ┌──────────────┐  ┌─────────────────┐  ┌──────────────────┐  │
│   │  Q&A Chat    │  │ Report Builder  │  │ Graph Explorer   │  │
│   └──────┬───────┘  └────────┬────────┘  └────────┬─────────┘  │
└──────────┼───────────────────┼─────────────────────┼────────────┘
           │                   │                     │
           ▼                   ▼                     │
┌─────────────────────┐ ┌─────────────────┐          │
│  LangChain          │ │ Report Builder  │          │
│  GraphCypherQAChain │ │ (direct SDK)    │          │
│  ┌───────────────┐  │ │                 │          │
│  │ Claude Sonnet │  │ │ Claude Sonnet   │          │
│  │ (Cypher gen)  │  │ │ (narrative)     │          │
│  └───────┬───────┘  │ └────────┬────────┘          │
└──────────┼──────────┘          │                   │
           │                     │                   │
           ▼                     ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Neo4j AuraDB Free                           │
│                                                                 │
│  (Customer)──PLACED──▶(Order)──CONTAINS──▶(Product)            │
│       │                                       │                 │
│  BELONGS_TO                             BELONGS_TO             │
│       ▼                                       ▼                 │
│  (Segment)◀──TARGETS──(Campaign)         (Category)            │
│       ▲                                                         │
│  RESPONDED_TO from (Customer)                                   │
└─────────────────────────────────────────────────────────────────┘
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

| Relationship | From | To | Properties |
|---|---|---|---|
| `PLACED` | Customer | Order | — |
| `CONTAINS` | Order | Product | quantity, unit_price |
| `BELONGS_TO` | Product | Category | — |
| `BELONGS_TO` | Customer | Segment | since_date |
| `RESPONDED_TO` | Customer | Campaign | response_date |
| `TARGETS` | Campaign | Segment | — |

---

## 🚀 Quickstart

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed
- [Neo4j AuraDB Free](https://neo4j.com/cloud/platform/aura-graph-database/) instance
- [Anthropic API key](https://console.anthropic.com/)

### 1. Clone & install

```bash
git clone https://github.com/your-username/customerlens.git
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

Generates 9 CSVs in `data/raw/` including RFM-scored customer segments.

### 4. Validate data quality

```bash
uv run pytest tests/unit/test_data_quality.py -v
# 38 tests, ~2s
```

### 5. Ingest into Neo4j

```bash
uv run python -m pipeline.ingestion.run_ingestion
```

Applies schema constraints, loads all nodes and relationships in dependency order. Safe to re-run (all `MERGE` — no duplicates).

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
├── app/                          # Streamlit application
│   ├── main.py                   # Entry point, global CSS design system
│   ├── _pages/                   # Page modules (underscore = not MPA-discovered)
│   │   ├── qa_page.py            # Q&A chat interface
│   │   ├── report_page.py        # Report Builder with template selector
│   │   └── graph_page.py         # Interactive graph visualisations
│   ├── components/
│   │   └── graph_viz.py          # pyvis graph builders (no Streamlit dependency)
│   └── reports/
│       └── report_builder.py     # Cypher → DataFrames → Claude narrative
│
├── config/
│   └── settings.py               # Pydantic Settings — reads from .env
│
├── data/
│   ├── raw/                      # Generated CSVs (git-ignored)
│   └── processed/                # Transformed CSVs (git-ignored)
│
├── graph/
│   ├── schema/
│   │   ├── constraints.cypher    # Uniqueness constraints + indexes
│   │   └── node_labels.md        # Schema data dictionary
│   ├── loaders/
│   │   ├── neo4j_client.py       # Driver wrapper (context-manager safe)
│   │   ├── schema_loader.py      # Applies constraints.cypher
│   │   └── graph_loader.py       # Idempotent bulk loaders (MERGE-based)
│   └── queries/
│       └── report_queries.py     # Named Cypher query library for reports
│
├── llm/
│   ├── chains/
│   │   └── qa_chain.py           # GraphCypherQAChain wiring + AuraDB fix
│   └── prompts/
│       └── cypher_prompt.py      # Custom Cypher generation + QA prompt templates
│
├── pipeline/
│   ├── generation/
│   │   └── generate_data.py      # SDV + Faker synthetic data generation
│   ├── transformation/
│   │   └── rfm_segmentation.py   # RFM scoring (run inside generate_data.py)
│   └── ingestion/
│       └── run_ingestion.py      # Orchestrator: CSV → Neo4j
│
├── scripts/
│   └── ask.py                    # Interactive CLI REPL for testing Q&A
│
├── tests/
│   ├── unit/
│   │   └── test_data_quality.py  # 38 data quality assertions
│   └── integration/
│       └── test_qa_chain.py      # 16 end-to-end Q&A tests (skipped without creds)
│
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   └── 02_graph_exploration.ipynb
│
├── .env.example
├── pyproject.toml
└── README.md
```

---

## 🖥️ Screenshots

### Q&A Chat
Ask natural-language questions — see the generated Cypher, raw graph results, and a plain-English answer from Claude.

> _"Which customer segment has the highest average order value?"_
> _"Show me Champions customers from Chicago who haven't ordered in 90 days."_
> _"Which products are most frequently bought together by At-Risk customers?"_

### Report Builder
Pick a template and click **Generate Report** — the app runs a bundle of Cypher queries and Claude writes a ≤350-word executive narrative alongside interactive data tables and charts.

| Template | Queries | Focus |
|---|---|---|
| 📊 Segment Health Overview | 3 | AOV, recency, channel mix by RFM segment |
| ⚠️ Churn Risk Report | 3 | At-Risk / Hibernating customers, revenue at stake |
| 📣 Campaign Effectiveness | 3 | Response rates, segment breakdown, multi-touch |
| 🔗 Cross-Sell Opportunities | 4 | Co-purchase pairs, category affinity, top products per segment |

### Graph Explorer
Three interactive pyvis views rendered in-browser via vis.js:
- **Customer Neighbourhood** — pick any customer, explore their orders → products → categories → segment
- **Segment Overview** — hub-and-spoke view of top-RFM customers per segment
- **Schema Diagram** — static reference of all node types and relationship types

---

## ⚙️ Configuration

All settings are read from `.env` via Pydantic Settings. Every value has a sensible default.

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

> **Neo4j AuraDB note:** `langchain-neo4j` defaults the database name to `"neo4j"`, which AuraDB Free rejects. This project patches `graph._database = None` before calling `refresh_schema()` so the driver uses the server's default database automatically. No extra configuration needed.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.11+ |
| **Package manager** | [uv](https://docs.astral.sh/uv/) |
| **Graph database** | [Neo4j AuraDB Free](https://neo4j.com/cloud/platform/aura-graph-database/) |
| **LLM** | [Claude Sonnet](https://anthropic.com) via `langchain-anthropic` + `anthropic` SDK |
| **NL → Cypher** | [LangChain `GraphCypherQAChain`](https://python.langchain.com/docs/integrations/graphs/neo4j_cypher/) + `langchain-neo4j` |
| **Synthetic data** | [SDV](https://sdv.dev/) (HMASynthesizer) + [Faker](https://faker.readthedocs.io/) |
| **UI framework** | [Streamlit](https://streamlit.io/) |
| **Graph visualisation** | [pyvis](https://pyvis.readthedocs.io/) (vis.js under the hood) |
| **Charts** | [Altair](https://altair-viz.github.io/) |
| **Config** | [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) |
| **Testing** | [pytest](https://pytest.org/) |

---

## 🧪 Testing

```bash
# Unit tests — data quality (no credentials needed)
uv run pytest tests/unit/ -v

# Integration tests — live Q&A chain (requires .env with credentials)
uv run pytest tests/integration/ -v -s

# Interactive CLI for manual Q&A testing
uv run python scripts/ask.py
uv run python scripts/ask.py --question "Which segment has the highest AOV?"
```

The integration test suite covers 16 questions across 4 domains (Segment Analytics, Product Intelligence, Campaign Effectiveness, Customer Look-ups) and automatically skips when `NEO4J_URI` or `ANTHROPIC_API_KEY` are absent, making them safe to run in CI without secrets.

---

## 🗺️ Roadmap

- [ ] Streamlit `st.chat_message` redesign for Q&A page
- [ ] Export reports to PDF
- [ ] LangChain agent with pre-built Cypher tools for multi-hop reasoning
- [ ] Neo4j GDS (Graph Data Science) integration — PageRank, community detection
- [ ] Docker Compose for one-command local setup
- [ ] GitHub Actions CI — unit tests on every push

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.

---

<div align="center">
<sub>Built with Neo4j · LangChain · Claude · Streamlit · pyvis</sub>
</div>
