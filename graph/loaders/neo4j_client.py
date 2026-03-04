"""
graph/loaders/neo4j_client.py
==============================
Thin, reusable wrapper around the official Neo4j Python driver.
All loaders and query modules import from here — never instantiate
the driver directly elsewhere.
"""

from __future__ import annotations

from neo4j import GraphDatabase, ManagedTransaction

try:
    from config import settings
    _URI      = settings.neo4j_uri
    _USER     = settings.neo4j_username
    _PASSWORD = settings.neo4j_password
except Exception:
    import os
    _URI      = os.getenv("NEO4J_URI",      "neo4j+s://localhost:7687")
    _USER     = os.getenv("NEO4J_USERNAME", "neo4j")
    _PASSWORD = os.getenv("NEO4J_PASSWORD", "")


class Neo4jClient:
    """Context-manager-compatible Neo4j session wrapper."""

    def __init__(
        self,
        uri: str = _URI,
        user: str = _USER,
        password: str = _PASSWORD,
    ) -> None:
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    # ── public API ────────────────────────────────────────────────────────────

    def run(self, query: str, parameters: dict | None = None) -> list[dict]:
        """Execute a Cypher query and return results as a list of dicts."""
        with self._driver.session() as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]

    def run_write(self, query: str, parameters: dict | None = None) -> list[dict]:
        """Execute a write transaction explicitly."""
        def _tx(tx: ManagedTransaction) -> list[dict]:
            result = tx.run(query, parameters or {})
            return [dict(record) for record in result]

        with self._driver.session() as session:
            return session.execute_write(_tx)

    def verify_connectivity(self) -> bool:
        """Return True if the driver can reach the database."""
        try:
            self._driver.verify_connectivity()
            return True
        except Exception as exc:
            print(f"  ⚠️  Neo4j connectivity check failed: {exc}")
            return False

    def close(self) -> None:
        self._driver.close()

    # ── context manager ───────────────────────────────────────────────────────

    def __enter__(self) -> "Neo4jClient":
        return self

    def __exit__(self, *_) -> None:
        self.close()
