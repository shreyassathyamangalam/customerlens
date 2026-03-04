"""
graph/loaders/schema_loader.py
================================
Applies uniqueness constraints and indexes from
graph/schema/constraints.cypher to a fresh Neo4j database.

Safe to re-run: uses IF NOT EXISTS throughout.
"""

from __future__ import annotations

from pathlib import Path

from graph.loaders.neo4j_client import Neo4jClient

CONSTRAINTS_FILE = Path(__file__).parents[1] / "schema" / "constraints.cypher"


def _parse_statements(path: Path) -> list[str]:
    """Split a .cypher file on semicolons, stripping comments and blanks."""
    raw = path.read_text(encoding="utf-8")
    statements = []
    for block in raw.split(";"):
        lines = [
            line for line in block.splitlines()
            if line.strip() and not line.strip().startswith("//")
        ]
        stmt = " ".join(lines).strip()
        if stmt:
            statements.append(stmt)
    return statements


def apply_constraints(verbose: bool = True) -> None:
    """Create all constraints and indexes defined in constraints.cypher."""
    statements = _parse_statements(CONSTRAINTS_FILE)
    if not statements:
        print("  ⚠️  No statements found in constraints.cypher")
        return

    with Neo4jClient() as client:
        if not client.verify_connectivity():
            raise RuntimeError("Cannot reach Neo4j — check .env credentials.")
        for stmt in statements:
            client.run(stmt)
            if verbose:
                label = stmt[:72].replace("\n", " ")
                print(f"  ✓  {label}…")

    print(f"  ✅ Applied {len(statements)} constraint/index statement(s).")


if __name__ == "__main__":
    apply_constraints()
