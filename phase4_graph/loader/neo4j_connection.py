"""Neo4j connection management."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from contextlib import contextmanager
from neo4j import GraphDatabase
from rich.console import Console

from config.settings import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

console = Console()


class Neo4jConnection:
    """Manages Neo4j driver lifecycle and provides session helpers."""

    def __init__(self, uri: str = NEO4J_URI, user: str = NEO4J_USER, password: str = NEO4J_PASSWORD):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def verify(self) -> bool:
        """Test connectivity and return True if successful."""
        try:
            self.driver.verify_connectivity()
            console.print("[green]Neo4j connection verified.[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Neo4j connection failed: {e}[/red]")
            return False

    @contextmanager
    def session(self):
        """Yield a Neo4j session."""
        session = self.driver.session()
        try:
            yield session
        finally:
            session.close()

    def run(self, cypher: str, **params):
        """Execute a single Cypher statement and return the result."""
        with self.session() as session:
            result = session.run(cypher, **params)
            return [record.data() for record in result]

    def run_batch(self, cypher: str, batch: list[dict], batch_size: int = 1000) -> int:
        """Execute a parameterized Cypher statement in batches using UNWIND.

        Args:
            cypher: Cypher query using UNWIND $batch AS row
            batch: List of parameter dicts
            batch_size: Number of rows per transaction

        Returns:
            Total number of rows processed
        """
        total = 0
        for i in range(0, len(batch), batch_size):
            chunk = batch[i:i + batch_size]
            with self.session() as session:
                session.run(cypher, batch=chunk)
            total += len(chunk)
        return total

    def clear_database(self):
        """Delete all nodes and relationships. Use with caution."""
        with self.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        console.print("[yellow]Database cleared.[/yellow]")

    def count_nodes(self, label: str = None) -> int:
        """Count nodes, optionally filtered by label."""
        if label:
            result = self.run(f"MATCH (n:{label}) RETURN COUNT(n) AS count")
        else:
            result = self.run("MATCH (n) RETURN COUNT(n) AS count")
        return result[0]["count"] if result else 0

    def count_relationships(self, rel_type: str = None) -> int:
        """Count relationships, optionally filtered by type."""
        if rel_type:
            result = self.run(f"MATCH ()-[r:{rel_type}]->() RETURN COUNT(r) AS count")
        else:
            result = self.run("MATCH ()-[r]->() RETURN COUNT(r) AS count")
        return result[0]["count"] if result else 0
