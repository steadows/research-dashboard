"""Graph router — health, project context, communities, visualization."""

import logging
import threading
from typing import Any

from cachetools import TTLCache
from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_vault_path_str
from api.serializers import serialize_communities, serialize_project_context

from utils.graph_engine import (
    build_vault_graph,
    compute_centrality_metrics,
    detect_communities,
    get_graph_health,
    get_project_context,
)
from utils.smart_matcher import build_smart_project_index, get_graph_linked_items

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/graph", tags=["graph"])

# ---------------------------------------------------------------------------
# Cached graph data — expensive to rebuild on every request
# ---------------------------------------------------------------------------

_graph_cache: TTLCache[str, dict[str, Any]] = TTLCache(maxsize=4, ttl=3600)
_graph_lock = threading.Lock()


def invalidate_graph_cache(vault_path: str | None = None) -> None:
    """Invalidate the graph cache.

    If vault_path is provided, only that key is cleared.
    Otherwise, the entire cache is cleared.

    Args:
        vault_path: Optional vault path key to invalidate.
    """
    with _graph_lock:
        if vault_path and vault_path in _graph_cache:
            del _graph_cache[vault_path]
        elif vault_path is None:
            _graph_cache.clear()


def _get_graph_data(vault_path: str) -> dict[str, Any]:
    """Build and cache graph, metrics, and communities.

    Args:
        vault_path: String path to the vault root.

    Returns:
        Dict with 'graph', 'metrics', 'communities', 'health' keys.
    """
    with _graph_lock:
        if vault_path in _graph_cache:
            return _graph_cache[vault_path]

    G = build_vault_graph(vault_path)
    metrics = compute_centrality_metrics(G)
    communities = detect_communities(G)
    health = get_graph_health(G)

    data = {
        "graph": G,
        "metrics": metrics,
        "communities": communities,
        "health": health,
    }

    with _graph_lock:
        _graph_cache[vault_path] = data
    return data


@router.get("/health")
def graph_health(
    vault_path: str = Depends(get_vault_path_str),
) -> dict[str, Any]:
    """Get vault graph health statistics, transformed for frontend contract.

    Returns:
        Dict with total_nodes, total_edges, connected_components,
        orphan_nodes, avg_degree, density.
    """
    data = _get_graph_data(vault_path)
    raw = data["health"]

    node_count = raw.get("node_count", 0)
    edge_count = raw.get("edge_count", 0)

    avg_degree = (2.0 * edge_count / node_count) if node_count > 0 else 0.0
    max_edges = node_count * (node_count - 1)
    density = (edge_count / max_edges) if max_edges > 0 else 0.0

    return {
        "total_nodes": node_count,
        "total_edges": edge_count,
        "connected_components": raw.get("component_count", 0),
        "orphan_nodes": raw.get("orphan_count", 0),
        "avg_degree": round(avg_degree, 4),
        "density": round(density, 6),
    }


@router.get("/hub-notes")
def graph_hub_notes(
    vault_path: str = Depends(get_vault_path_str),
    limit: int = 15,
) -> list[dict[str, Any]]:
    """Get top hub notes ranked by PageRank.

    Args:
        vault_path: Path to the Obsidian vault.
        limit: Maximum number of hub notes to return.

    Returns:
        List of dicts with name, pagerank, in_degree, betweenness.
    """
    data = _get_graph_data(vault_path)
    metrics = data["metrics"]
    pagerank = metrics.get("pagerank", {})
    betweenness = metrics.get("betweenness", {})
    in_degree = metrics.get("in_degree", {})

    sorted_nodes = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)

    return [
        {
            "name": name,
            "pagerank": round(score, 6),
            "in_degree": in_degree.get(name, 0),
            "betweenness": round(betweenness.get(name, 0.0), 6),
        }
        for name, score in sorted_nodes[:limit]
    ]


@router.get("/communities")
def graph_communities(
    vault_path: str = Depends(get_vault_path_str),
) -> list[list[str]]:
    """Get detected vault communities as sorted lists."""
    data = _get_graph_data(vault_path)
    return serialize_communities(data["communities"])


@router.get("/{project}/viz")
def graph_viz(
    project: str,
    vault_path: str = Depends(get_vault_path_str),
) -> dict[str, list[dict[str, str]]]:
    """Build derived visualization graph for D3.js.

    Returns {nodes: [{id, type, label}], edges: [{source, target, relation}]}
    where items are represented as nodes connected to the project node.
    Empty graphs return {nodes: [], edges: []}.
    """
    index = build_smart_project_index(vault_path)
    linked_items = index.get(project, [])

    data = _get_graph_data(vault_path)
    G = data["graph"]
    graph_ctx = None
    if G.number_of_nodes() > 0:
        graph_ctx = get_project_context(
            G, data["metrics"], data["communities"], project
        )

    all_items = get_graph_linked_items(project, linked_items, index, graph_ctx)

    if not all_items:
        return {"nodes": [], "edges": []}

    return _build_viz_graph(project, all_items)


@router.get("/{project}")
def graph_project_context(
    project: str,
    vault_path: str = Depends(get_vault_path_str),
) -> dict[str, Any]:
    """Get graph context for a project."""
    data = _get_graph_data(vault_path)
    G = data["graph"]
    if G.number_of_nodes() == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project}' not found in graph",
        )

    context = get_project_context(G, data["metrics"], data["communities"], project)

    if context is None:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project}' not found in graph",
        )

    return serialize_project_context(context)


# ---------------------------------------------------------------------------
# Viz graph builder
# ---------------------------------------------------------------------------

_RELATION_PRIORITY = {"linked": 0, "community": 1, "suggested": 2}


def _build_viz_graph(
    project_name: str,
    items: list[dict[str, Any]],
) -> dict[str, list[dict[str, str]]]:
    """Build a derived visualization graph from project items.

    Creates nodes for the project and each item, plus edges based on
    discovery_source. Duplicate edges are collapsed keeping highest-signal.
    Node IDs are globally unique: ``{type}::{name}``.

    Args:
        project_name: The selected project name.
        items: List of graph-linked items with discovery_source.

    Returns:
        Dict with 'nodes' and 'edges' lists.
    """
    nodes: list[dict[str, str]] = []
    seen_node_ids: set[str] = set()
    edges: list[dict[str, str]] = []
    seen_edges: dict[tuple[str, str], str] = {}  # (source, target) → relation

    # Project node
    project_id = f"project::{project_name}"
    nodes.append({"id": project_id, "type": "project", "label": project_name})
    seen_node_ids.add(project_id)

    for item in items:
        source_type = item.get("source_type", "item")
        name = item.get("name", "")
        item_id = f"{source_type}::{name}"
        discovery = item.get("discovery_source", "linked")

        # Map discovery_source to relation
        relation = discovery if discovery in _RELATION_PRIORITY else "linked"

        # Add node if not seen
        if item_id not in seen_node_ids:
            nodes.append({"id": item_id, "type": source_type, "label": name})
            seen_node_ids.add(item_id)

        # Add/collapse edge
        edge_key = (project_id, item_id)
        existing = seen_edges.get(edge_key)
        if existing is None or _RELATION_PRIORITY.get(
            relation, 2
        ) < _RELATION_PRIORITY.get(existing, 2):
            seen_edges[edge_key] = relation

    # Build final edge list
    for (source, target), relation in seen_edges.items():
        edges.append({"source": source, "target": target, "relation": relation})

    return {"nodes": nodes, "edges": edges}
