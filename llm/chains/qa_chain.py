"""
llm/chains/qa_chain.py
========================
Wires together:
  Neo4jGraph  ──schema──▶  ChatAnthropic (Cypher generation)
                                │
                           Cypher query
                                │
                          Neo4j execution
                                │
                           raw results
                                │
                    ChatAnthropic (QA answer)
                                │
                         human answer

Public API:
    chain = build_qa_chain()
    result = chain.invoke({"query": "Which segment has the highest AOV?"})
    print(result["result"])               # human answer
    print(result["intermediate_steps"])   # cypher + raw data (when verbose)
"""

from __future__ import annotations

from functools import lru_cache

from langchain_anthropic import ChatAnthropic
from langchain_neo4j import GraphCypherQAChain, Neo4jGraph

from config.settings import settings
from llm.prompts.cypher_prompt import CYPHER_GENERATION_PROMPT, QA_PROMPT


def _build_graph() -> Neo4jGraph:
    """
    Connect to Neo4j AuraDB and load the graph schema.

    Root cause of the GqlError:
      langchain-neo4j delegates schema fetching to neo4j-graphrag, which
      calls driver.execute_query(database_=database). When no NEO4J_DATABASE
      env var is set the default resolves to the string "neo4j". AuraDB Free
      rejects that name because your instance database has a different
      internal identifier — it only accepts connections routed to the server's
      default database (i.e. database_=None).

    Fix:
      1. Connect with refresh_schema=False so no query fires during __init__.
      2. Patch graph._database to None — the Neo4j driver treats None as
         "use the server's default database", which is exactly what AuraDB
         expects.
      3. Call refresh_schema() manually now that routing is correct.
    """
    graph = Neo4jGraph(
        url=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
        enhanced_schema=False,
        refresh_schema=False,  # hold off — we patch _database first
    )
    # Override the hardcoded "neo4j" default so AuraDB routes correctly.
    # None tells the driver to use whatever the server's default DB is.
    graph._database = None  # type: ignore[assignment]
    graph.refresh_schema()
    return graph


def _build_llm(temperature: float = 0.0) -> ChatAnthropic:
    """Instantiate Claude Sonnet via LangChain."""
    return ChatAnthropic(
        model=settings.llm_model,
        anthropic_api_key=settings.anthropic_api_key,
        temperature=temperature,
        max_tokens=2048,
    )


def build_qa_chain(
    *,
    verbose: bool = True,
    return_intermediate_steps: bool = True,
    validate_cypher: bool = True,
    top_k: int = 25,
) -> GraphCypherQAChain:
    """
    Build and return a GraphCypherQAChain.

    Parameters
    ----------
    verbose                  : print Cypher queries to stdout
    return_intermediate_steps: include generated Cypher + raw results in output
    validate_cypher          : use LangChain's built-in Cypher corrector
    top_k                    : max rows returned from Neo4j per query

    """
    graph = _build_graph()

    # Separate LLM instances allow independent tuning:
    # - Cypher generation: temperature=0 for deterministic queries
    # - QA answering:      temperature=0.2 for slightly more natural prose
    cypher_llm = _build_llm(temperature=0.0)
    qa_llm = _build_llm(temperature=0.2)

    chain = GraphCypherQAChain.from_llm(
        cypher_llm=cypher_llm,
        qa_llm=qa_llm,
        graph=graph,
        cypher_prompt=CYPHER_GENERATION_PROMPT,
        qa_prompt=QA_PROMPT,
        verbose=verbose,
        return_intermediate_steps=return_intermediate_steps,
        validate_cypher=validate_cypher,
        top_k=top_k,
        allow_dangerous_requests=True,  # required by LangChain ≥0.3
    )
    return chain


# ── Cached singleton for Streamlit (avoids reconnecting on every rerun) ──────
@lru_cache(maxsize=1)
def get_qa_chain() -> GraphCypherQAChain:
    """Return a module-level cached chain instance (safe for Streamlit)."""
    return build_qa_chain()
