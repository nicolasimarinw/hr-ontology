"""Execute Cypher queries against Neo4j."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
from phase4_graph.loader.neo4j_connection import Neo4jConnection

_conn = None


def _get_conn() -> Neo4jConnection:
    global _conn
    if _conn is None:
        _conn = Neo4jConnection()
        _conn.verify()
    return _conn


def query_graph(cypher: str, params: dict | None = None) -> str:
    """Execute a Cypher query against Neo4j and return results as JSON.

    Args:
        cypher: A valid Cypher query string.
        params: Optional parameter dict for parameterized queries.

    Returns:
        JSON string with query results or error message.
    """
    try:
        conn = _get_conn()
        results = conn.run(cypher, **(params or {}))

        if not results:
            return json.dumps({"rows": [], "count": 0})

        # Convert results to serializable format
        rows = []
        for record in results:
            row = {}
            for key, val in record.items():
                if hasattr(val, 'isoformat'):
                    row[key] = val.isoformat()
                elif val is None or isinstance(val, (str, int, float, bool)):
                    row[key] = val
                else:
                    row[key] = str(val)
            rows.append(row)

        return json.dumps({"rows": rows, "count": len(rows)}, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


def get_node_counts() -> str:
    """Get counts of all node types in the graph."""
    return query_graph("""
        CALL db.labels() YIELD label
        CALL {
            WITH label
            MATCH (n)
            WHERE label IN labels(n)
            RETURN count(n) AS count
        }
        RETURN label, count
        ORDER BY count DESC
    """)


def get_relationship_counts() -> str:
    """Get counts of all relationship types in the graph."""
    return query_graph("""
        CALL db.relationshipTypes() YIELD relationshipType AS type
        CALL {
            WITH type
            MATCH ()-[r]->()
            WHERE type(r) = type
            RETURN count(r) AS count
        }
        RETURN type, count
        ORDER BY count DESC
    """)
