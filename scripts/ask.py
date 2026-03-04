"""
scripts/ask.py
===============
Interactive CLI for testing the GraphCypherQAChain.

Usage:
    uv run python scripts/ask.py
    uv run python scripts/ask.py --question "Which segment has the highest AOV?"
    uv run python scripts/ask.py --no-steps    # hide intermediate Cypher

Keyboard shortcuts in interactive mode:
    'q' or 'quit'  → exit
    'schema'       → print the current graph schema
    'history'      → show questions asked this session
"""

from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path

# Allow running from project root without installing the package
sys.path.insert(0, str(Path(__file__).parents[1]))


BANNER = """
╔══════════════════════════════════════════════════════════╗
║       CustomerLens  ·  Graph Q&A  ·  Powered by Claude  ║
║  Type your question, 'schema', 'history', or 'quit'     ║
╚══════════════════════════════════════════════════════════╝
"""

SAMPLE_QUESTIONS = [
    "Which customer segment has the highest average order value?",
    "What are the top 5 products by total revenue?",
    "How many customers are in each RFM segment?",
    "Which campaigns had the most responses?",
    "Show customers in the At-Risk segment from New York.",
    "Which product categories are most popular among Champions?",
    "How many customers responded to more than one campaign?",
    "Who are the top 5 customers by lifetime spend?",
]


def _divider(char: str = "─", width: int = 62) -> str:
    return char * width


def _print_result(result: dict, show_steps: bool) -> None:
    steps = result.get("intermediate_steps", [])

    if show_steps and steps:
        cypher = steps[0].get("query", "").strip()
        raw = steps[1].get("context", []) if len(steps) > 1 else []

        print(f"\n{_divider()}")
        print("Generated Cypher:")
        print(textwrap.indent(cypher, "  "))

        print(f"\nRaw results ({len(raw)} row{'s' if len(raw) != 1 else ''}):")
        for row in raw[:8]:
            print(f"  {row}")
        if len(raw) > 8:
            print(f"  … and {len(raw) - 8} more row(s)")

    answer = result.get("result", "").strip()
    print(f"\n{_divider()}")
    print("Answer:")
    print(textwrap.indent(answer, "  "))
    print(_divider())


def run_single(question: str, show_steps: bool) -> None:
    from llm.chains.qa_chain import build_qa_chain

    chain = build_qa_chain(verbose=show_steps)
    print(f"\nQ: {question}")
    result = chain.invoke({"query": question})
    _print_result(result, show_steps)


def run_interactive(show_steps: bool) -> None:
    print(BANNER)
    print("Sample questions to get you started:")
    for i, q in enumerate(SAMPLE_QUESTIONS, 1):
        print(f"  {i:2d}. {q}")
    print()

    print("Connecting to Neo4j and loading schema…", end=" ", flush=True)
    from llm.chains.qa_chain import build_qa_chain

    chain = build_qa_chain(verbose=show_steps)
    print("ready.\n")

    history: list[str] = []

    while True:
        try:
            raw = input("You › ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not raw:
            continue

        if raw.lower() in {"q", "quit", "exit"}:
            print("Goodbye!")
            break

        if raw.lower() == "schema":
            print("\nGraph Schema:")
            print(textwrap.indent(chain.graph_schema, "  "))
            print()
            continue

        if raw.lower() == "history":
            if not history:
                print("  (no questions yet)\n")
            else:
                for i, q in enumerate(history, 1):
                    print(f"  {i}. {q}")
                print()
            continue

        # Shortcut: type a number to ask a sample question
        if raw.isdigit() and 1 <= int(raw) <= len(SAMPLE_QUESTIONS):
            raw = SAMPLE_QUESTIONS[int(raw) - 1]
            print(f"  → {raw}")

        history.append(raw)
        print("\nThinking…", end=" ", flush=True)
        try:
            result = chain.invoke({"query": raw})
            print()
            _print_result(result, show_steps)
        except Exception as exc:
            print(f"\n⚠️  Error: {exc}\n")

        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="CustomerLens interactive Q&A CLI")
    parser.add_argument(
        "--question",
        "-q",
        type=str,
        default=None,
        help="Ask a single question and exit",
    )
    parser.add_argument(
        "--no-steps", action="store_true", help="Hide intermediate Cypher and raw data"
    )
    args = parser.parse_args()

    show_steps = not args.no_steps

    if args.question:
        run_single(args.question, show_steps)
    else:
        run_interactive(show_steps)


if __name__ == "__main__":
    main()
