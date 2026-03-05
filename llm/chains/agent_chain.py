"""
llm/chains/agent_chain.py
==========================
A tool-calling agent built on LCEL (LangChain Expression Language).

Architecture:
  1. Claude receives the question + tool schemas
  2. Claude decides which tool(s) to call and with what arguments
  3. Each tool executes a pre-vetted Cypher query against Neo4j
  4. Results are fed back to Claude as ToolMessages
  5. Claude loops until it has enough data, then writes the final answer

This differs from GraphCypherQAChain (which generates arbitrary Cypher)
in two important ways:
  - Queries are pre-tested and locked — no hallucinated property names
  - Multi-hop: Claude can call several tools and synthesise across them

Public API:
    agent = build_agent()
    result = agent.invoke("Which At-Risk customers spent the most historically?")
    # result is an AgentResult(answer, steps) dataclass
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from config.settings import settings
from llm.tools.graph_tools import ALL_TOOLS

# ── Tool lookup map ───────────────────────────────────────────────────────────
_TOOL_MAP = {t.name: t for t in ALL_TOOLS}

# ── System prompt ─────────────────────────────────────────────────────────────
AGENT_SYSTEM_PROMPT = """You are a senior retail customer analytics expert with access \
to a set of tools that query a live Neo4j customer knowledge graph.

## Your approach
1. Think carefully about which tool(s) you need to answer the question.
2. Call tools one at a time, read the results, then decide if more calls are needed.
3. For multi-part questions, chain multiple tool calls before writing your final answer.
4. Always base your answer strictly on the tool results — never invent data.
5. Lead with the direct answer, then provide supporting numbers and insight.
6. Keep answers concise and business-focused — no jargon, no Cypher references.

## Available data domains
- Segment Analytics: AOV, recency/frequency, channel mix per RFM segment
- Churn Risk: At-Risk / Hibernating / Lost customers, revenue at stake, city breakdown
- Campaign Effectiveness: response rates, segment breakdown, multi-touch customers
- Cross-Sell Intelligence: product co-purchase pairs, category affinity, top products by segment

## RFM Segments
Champions · Loyal Customers · Potential Loyalists · At-Risk · Hibernating · Lost · Others

## Response format
Write your final answer in clear, concise business language.
Use bold for key figures. Use bullet points only for lists of 4+ items."""


# ── Result dataclass ──────────────────────────────────────────────────────────


@dataclass
class AgentStep:
    tool_name: str
    tool_input: dict
    tool_output: str

    @property
    def output_preview(self) -> str:
        """First 300 chars of output for UI display."""
        return self.tool_output[:300] + ("…" if len(self.tool_output) > 300 else "")


@dataclass
class AgentResult:
    answer: str
    steps: list[AgentStep] = field(default_factory=list)
    error: str | None = None


# ── Agent executor ────────────────────────────────────────────────────────────


class CustomerLensAgent:
    """
    Thin wrapper around a Claude model with tools bound.
    Implements a manual ReAct loop so we have full control over
    intermediate step capture for the UI.
    """

    MAX_ITERATIONS = 8  # safety ceiling — prevents runaway loops

    def __init__(self) -> None:
        self._llm = ChatAnthropic(
            model=settings.llm_model,
            anthropic_api_key=settings.anthropic_api_key,
            temperature=0.0,
            max_tokens=2048,
        ).bind_tools(ALL_TOOLS)

    def invoke(self, question: str) -> AgentResult:
        """Run the agent to completion and return an AgentResult."""
        messages = [
            SystemMessage(content=AGENT_SYSTEM_PROMPT),
            HumanMessage(content=question),
        ]
        steps: list[AgentStep] = []

        for _ in range(self.MAX_ITERATIONS):
            response: AIMessage = self._llm.invoke(messages)
            messages.append(response)

            # ── No tool calls → Claude is done ───────────────────────────────
            if not response.tool_calls:
                return AgentResult(answer=response.content, steps=steps)

            # ── Execute each requested tool call ─────────────────────────────
            for tc in response.tool_calls:
                tool_name = tc["name"]
                tool_input = tc["args"]  # dict (may be empty for no-arg tools)
                tool_id = tc["id"]

                tool_fn = _TOOL_MAP.get(tool_name)
                if tool_fn is None:
                    tool_output = json.dumps({"error": f"Unknown tool: {tool_name}"})
                else:
                    try:
                        tool_output = tool_fn.invoke(tool_input)
                    except Exception as exc:
                        tool_output = json.dumps({"error": str(exc)})

                steps.append(
                    AgentStep(
                        tool_name=tool_name,
                        tool_input=tool_input,
                        tool_output=tool_output,
                    )
                )

                messages.append(
                    ToolMessage(
                        content=tool_output,
                        tool_call_id=tool_id,
                    )
                )

        # Exceeded max iterations — return whatever we have
        return AgentResult(
            answer="I reached the maximum number of tool calls without a complete answer. "
            "Please try rephrasing your question more specifically.",
            steps=steps,
            error="max_iterations_exceeded",
        )


# ── Cached singleton for Streamlit ────────────────────────────────────────────


@lru_cache(maxsize=1)
def get_agent() -> CustomerLensAgent:
    """Return a module-level cached agent instance (safe for Streamlit)."""
    return CustomerLensAgent()


def build_agent() -> CustomerLensAgent:
    """Build a fresh agent instance (use get_agent() in Streamlit)."""
    return CustomerLensAgent()
