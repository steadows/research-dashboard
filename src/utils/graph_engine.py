"""Graph analysis engine — vault network intelligence via obsidiantools + NetworkX.

Pure analysis module with no Streamlit imports. Page files own all caching
via @st.cache_data / @st.cache_resource wrappers.

Functions:
    build_vault_graph: Parse vault wiki-links into a directed graph.
    compute_centrality_metrics: PageRank, betweenness, degree metrics.
    detect_communities: Louvain community detection.
    suggest_links: Adamic-Adar link prediction.
    get_graph_health: Structural health statistics.
    get_project_context: Per-project graph summary.
"""

import logging
from typing import Any

import networkx as nx

logger = logging.getLogger(__name__)


def build_vault_graph(vault_path_str: str) -> nx.DiGraph:
    """Parse Obsidian vault wiki-link structure into a directed graph.

    Uses obsidiantools to build the graph, then cleans it:
    1. Convert MultiDiGraph → simple DiGraph
    2. Remove self-loops (e.g. [[note#section]])
    3. Filter non-existent notes (linked but never created)

    Args:
        vault_path_str: Absolute path to the Obsidian vault root.

    Returns:
        Cleaned nx.DiGraph with existing notes as nodes.
    """
    try:
        from obsidiantools.api import Vault
    except ImportError:
        logger.warning("obsidiantools not installed — returning empty graph")
        return nx.DiGraph()

    from pathlib import Path

    vault = Vault(Path(vault_path_str)).connect()

    # Get the raw graph (MultiDiGraph) and collapse to simple DiGraph
    raw_graph = vault.graph
    G = nx.DiGraph()

    for u, v in raw_graph.edges():
        if u != v:  # Skip self-loops inline
            G.add_edge(u, v)

    # Also add isolated nodes that exist as files
    for node in raw_graph.nodes():
        if node not in G:
            G.add_node(node)

    # Remove self-loops (safety net)
    G.remove_edges_from(list(nx.selfloop_edges(G)))

    # Filter non-existent notes — remove notes that are linked but never created
    if hasattr(vault, "nonexistent_notes"):
        nonexistent = set(vault.nonexistent_notes)
        G.remove_nodes_from(list(nonexistent & set(G.nodes())))
    elif hasattr(vault, "file_index"):
        existing = set(vault.file_index.keys())
        nodes_to_remove = [n for n in G.nodes() if n not in existing]
        G.remove_nodes_from(nodes_to_remove)
    else:
        logger.warning(
            "obsidiantools vault has no nonexistent_notes or file_index — "
            "skipping non-existent note filtering"
        )

    return G


def compute_centrality_metrics(
    G: nx.DiGraph,
) -> dict[str, dict[str, float | int]]:
    """Compute centrality metrics for all nodes in the graph.

    Args:
        G: Directed graph of vault notes.

    Returns:
        Dict with keys: pagerank, betweenness, degree, in_degree, out_degree.
        Each value is a dict mapping node name to score.
        Empty graph returns empty dicts for all keys.
    """
    if G.number_of_nodes() == 0:
        return {
            "pagerank": {},
            "betweenness": {},
            "degree": {},
            "in_degree": {},
            "out_degree": {},
        }

    pagerank = dict(nx.pagerank(G))

    # Performance guard: skip betweenness for large graphs
    if G.number_of_nodes() > 1000:
        logger.warning(
            "Vault has %d nodes — skipping betweenness_centrality (O(VE))",
            G.number_of_nodes(),
        )
        betweenness: dict[str, float] = {}
    else:
        betweenness = dict(nx.betweenness_centrality(G))

    degree = dict(G.degree())
    in_degree = dict(G.in_degree())
    out_degree = dict(G.out_degree())

    return {
        "pagerank": pagerank,
        "betweenness": betweenness,
        "degree": degree,
        "in_degree": in_degree,
        "out_degree": out_degree,
    }


def detect_communities(G: nx.DiGraph) -> list[frozenset[str]]:
    """Detect communities using Louvain algorithm on undirected projection.

    Args:
        G: Directed graph of vault notes.

    Returns:
        List of frozenset[str] — each frozenset is a community of note names.
        Returns empty list for graphs with < 2 nodes (no meaningful communities).
    """
    if G.number_of_nodes() < 2:
        return []

    G_undirected = G.to_undirected()
    communities = nx.community.louvain_communities(G_undirected, seed=42)
    return [frozenset(c) for c in communities]


def suggest_links(G: nx.DiGraph, note: str, top_n: int = 10) -> list[tuple[str, float]]:
    """Suggest missing links using Adamic-Adar index within 3-hop neighborhood.

    Args:
        G: Directed graph of vault notes.
        note: Name of the note to suggest links for.
        top_n: Maximum number of suggestions to return.

    Returns:
        List of (note_name, score) tuples sorted by score descending.
        Returns empty list if note is not in the graph.
    """
    if note not in G:
        return []

    G_undirected = G.to_undirected()

    # Limit candidates to 3-hop neighborhood
    reachable = nx.single_source_shortest_path_length(G_undirected, note, cutoff=3)

    # Exclude self and existing neighbors
    neighbors = set(G_undirected.neighbors(note))
    candidates = {n for n in reachable if n != note and n not in neighbors}

    if not candidates:
        return []

    # Build pairs for Adamic-Adar
    pairs = [(note, c) for c in candidates]
    aa_scores = nx.adamic_adar_index(G_undirected, pairs)

    # Collect non-zero scores
    results = []
    for u, v, score in aa_scores:
        if score > 0:
            target = v if u == note else u
            results.append((target, float(score)))

    # Sort descending by score
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_n]


def get_graph_health(G: nx.DiGraph) -> dict[str, int]:
    """Compute structural health statistics for the vault graph.

    Args:
        G: Directed graph of vault notes.

    Returns:
        Dict with: node_count, edge_count, orphan_count, component_count, bridge_count.
        All values are non-negative ints. Empty graph returns all zeros.
    """
    if G.number_of_nodes() == 0:
        return {
            "node_count": 0,
            "edge_count": 0,
            "orphan_count": 0,
            "component_count": 0,
            "bridge_count": 0,
        }

    node_count = G.number_of_nodes()
    edge_count = G.number_of_edges()
    orphan_count = sum(1 for n in G.nodes() if G.degree(n) == 0)
    component_count = nx.number_weakly_connected_components(G)
    bridge_count = len(list(nx.bridges(G.to_undirected())))

    return {
        "node_count": node_count,
        "edge_count": edge_count,
        "orphan_count": orphan_count,
        "component_count": component_count,
        "bridge_count": bridge_count,
    }


def get_project_context(
    G: nx.DiGraph,
    metrics: dict[str, dict[str, float | int]],
    communities: list[frozenset[str]],
    project_name: str,
) -> dict[str, Any] | None:
    """Build per-project graph context summary.

    Args:
        G: Directed graph of vault notes.
        metrics: Output of compute_centrality_metrics().
        communities: Output of detect_communities().
        project_name: Name of the project note.

    Returns:
        Dict with centrality_rank, pagerank_score, neighbors,
        community_members, suggested_connections. Returns None if
        project_name is not in the graph.
    """
    if project_name not in G:
        return None

    pagerank = metrics.get("pagerank", {})

    # Centrality rank — 1-indexed, among ALL vault notes by PageRank descending
    sorted_by_pr = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)
    rank = 1
    for name, _ in sorted_by_pr:
        if name == project_name:
            break
        rank += 1

    # Neighbors with direction
    predecessors = set(G.predecessors(project_name))
    successors = set(G.successors(project_name))
    all_neighbors = predecessors | successors

    neighbors = []
    for n in all_neighbors:
        if n in predecessors and n in successors:
            direction = "both"
        elif n in predecessors:
            direction = "in"
        else:
            direction = "out"

        neighbors.append(
            {
                "name": n,
                "direction": direction,
                "pagerank": float(pagerank.get(n, 0.0)),
            }
        )

    # Sort by PageRank descending
    neighbors.sort(key=lambda x: x["pagerank"], reverse=True)

    # Community membership
    community_members: frozenset[str] | None = None
    for c in communities:
        if project_name in c:
            community_members = c
            break

    # Suggested connections
    suggested = suggest_links(G, project_name)

    return {
        "centrality_rank": rank,
        "pagerank_score": float(pagerank.get(project_name, 0.0)),
        "neighbors": neighbors,
        "community_members": community_members,
        "suggested_connections": suggested,
    }
