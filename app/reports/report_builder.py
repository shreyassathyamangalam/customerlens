"""
app/reports/report_builder.py
==============================
Runs a bundle of pre-built Cypher queries for a given report template,
then calls Claude Sonnet to synthesise the raw results into a polished
markdown narrative report.

Public API:
    sections, narrative = build_report("Segment Health Overview", neo4j_client)
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from anthropic import Anthropic
from graph.queries.report_queries import REPORTS

from config.settings import settings
from graph.loaders.neo4j_client import Neo4jClient

_anthropic = Anthropic(api_key=settings.anthropic_api_key)

REPORT_SYSTEM_PROMPT = """You are a senior retail customer analytics consultant writing an
executive-ready report section. You will be given structured data tables from a customer
knowledge graph and must synthesise them into a concise, insight-driven narrative.

Guidelines:
- Lead with the single most important finding.
- Quantify every claim with the exact numbers from the data.
- Use clear business language — no jargon, no SQL/Cypher references.
- Structure with short paragraphs; use bullet points only for lists of 4+ items.
- Flag any anomalies or actionable recommendations.
- Keep the entire narrative under 150 words.
- Format in clean markdown (bold key figures, use ## for section headers)."""


def _run_query(client: Neo4jClient, query_def: dict) -> pd.DataFrame:
    """Execute one Cypher query and return results as a DataFrame."""
    rows = client.run(query_def["cypher"], query_def.get("params", {}))
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _df_to_text(title: str, df: pd.DataFrame) -> str:
    """Convert a DataFrame to a compact markdown table string for the LLM."""
    if df.empty:
        return f"**{title}**: No data returned.\n"
    return f"**{title}**\n{df.to_markdown(index=False)}\n"


def build_report(
    report_name: str,
) -> tuple[list[dict[str, Any]], str]:
    """
    Run all queries for a report template and generate a narrative.

    Returns
    -------
    sections : list of {title, dataframe} dicts — for rendering tables in UI
    narrative: Claude-generated markdown summary

    """
    if report_name not in REPORTS:
        raise ValueError(
            f"Unknown report: {report_name!r}. Choose from {list(REPORTS)}",
        )

    report_def = REPORTS[report_name]
    sections: list[dict[str, Any]] = []
    table_blocks: list[str] = []

    with Neo4jClient() as client:
        # Override database to None for AuraDB compatibility (same fix as qa_chain)
        client._driver  # ensure connected
        for q in report_def["queries"]:
            df = _run_query(client, q)
            sections.append({"title": q["title"], "df": df})
            table_blocks.append(_df_to_text(q["title"], df))

    # Ask Claude to synthesise all tables into a narrative
    data_dump = "\n\n".join(table_blocks)
    user_message = (
        f"Report: **{report_name}**\n\n"
        f"{report_def['description']}\n\n"
        f"---\n\n"
        f"## Data Tables\n\n"
        f"{data_dump}\n\n"
        f"---\n\n"
        f"Write the executive narrative for this report."
    )

    response = _anthropic.messages.create(
        model=settings.llm_model,
        max_tokens=1024,
        system=REPORT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    narrative = response.content[0].text
    return sections, narrative
