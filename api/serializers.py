"""Serializers — convert non-JSON-serializable types to JSON-safe structures.

Handles DiGraph → adjacency dict, frozenset → list, and other conversions
needed for FastAPI response serialization.
"""

from typing import Any

import networkx as nx


def serialize_graph(G: nx.DiGraph) -> dict[str, Any]:
    """Convert a NetworkX DiGraph to a JSON-serializable adjacency dict.

    Args:
        G: Directed graph to serialize.

    Returns:
        Dict with 'nodes' (list of node names) and 'adjacency' (dict of
        node → list of neighbor names).
    """
    return {
        "nodes": list(G.nodes()),
        "adjacency": {str(n): list(G.successors(n)) for n in G.nodes()},
    }


def serialize_communities(communities: list[frozenset[str]]) -> list[list[str]]:
    """Convert list of frozensets to list of sorted lists.

    Args:
        communities: List of community frozensets.

    Returns:
        List of sorted string lists.
    """
    return [sorted(c) for c in communities]


def serialize_project_context(context: dict[str, Any]) -> dict[str, Any]:
    """Serialize a project context dict, converting frozensets to lists.

    Args:
        context: Output from graph_engine.get_project_context().

    Returns:
        New dict with frozensets replaced by sorted lists and tuples by lists.
    """
    result = dict(context)

    # community_members: frozenset → sorted list
    members = result.get("community_members")
    if isinstance(members, frozenset):
        result["community_members"] = sorted(members)
    elif members is None:
        result["community_members"] = []

    # suggested_connections: list of tuples → list of lists
    suggestions = result.get("suggested_connections")
    if suggestions is not None:
        result["suggested_connections"] = [list(s) for s in suggestions]

    return result
