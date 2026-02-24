"""Describe the HR ontology schema: node types, relationship types, properties."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
from phase3_ontology.schema import ALL_NODE_SCHEMAS
from phase3_ontology.relations import ALL_EDGE_SCHEMAS


def describe_ontology(entity_type: str = "all") -> str:
    """Describe the HR ontology schema.

    Args:
        entity_type: What to describe. Options:
            - "all": Full schema overview
            - "nodes": All node types with properties
            - "edges": All relationship types
            - A specific node label (e.g., "Employee", "SalaryBand")
            - A specific relationship type (e.g., "REPORTS_TO", "EARNS_BASE")

    Returns:
        JSON string with schema information.
    """
    if entity_type == "all":
        nodes = {}
        for name, schema in ALL_NODE_SCHEMAS.items():
            nodes[name] = {
                "id_property": schema.id_property,
                "properties": schema.required + schema.optional,
            }
        edges = {}
        for name, schema in ALL_EDGE_SCHEMAS.items():
            edges[name] = {
                "source": schema.source_label,
                "target": schema.target_label,
                "properties": schema.properties,
            }
        return json.dumps({"node_types": nodes, "relationship_types": edges}, indent=2)

    elif entity_type == "nodes":
        nodes = {}
        for name, schema in ALL_NODE_SCHEMAS.items():
            nodes[name] = {
                "labels": schema.labels,
                "id_property": schema.id_property,
                "required": schema.required,
                "optional": schema.optional,
                "indexes": schema.indexes,
            }
        return json.dumps({"node_types": nodes}, indent=2)

    elif entity_type == "edges":
        edges = {}
        for name, schema in ALL_EDGE_SCHEMAS.items():
            edges[name] = {
                "source": schema.source_label,
                "target": schema.target_label,
                "properties": schema.properties,
            }
        return json.dumps({"relationship_types": edges}, indent=2)

    elif entity_type in ALL_NODE_SCHEMAS:
        schema = ALL_NODE_SCHEMAS[entity_type]
        return json.dumps({
            "type": "node",
            "name": entity_type,
            "labels": schema.labels,
            "id_property": schema.id_property,
            "required_properties": schema.required,
            "optional_properties": schema.optional,
            "indexes": schema.indexes,
        }, indent=2)

    elif entity_type in ALL_EDGE_SCHEMAS:
        schema = ALL_EDGE_SCHEMAS[entity_type]
        return json.dumps({
            "type": "relationship",
            "name": entity_type,
            "source_label": schema.source_label,
            "target_label": schema.target_label,
            "properties": schema.properties,
        }, indent=2)

    else:
        return json.dumps({
            "error": f"Unknown entity type: {entity_type}",
            "available_nodes": list(ALL_NODE_SCHEMAS.keys()),
            "available_edges": list(ALL_EDGE_SCHEMAS.keys()),
        })
