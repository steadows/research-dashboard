"""Tests for Cockpit graph context — page-level behavior in 2_Project_Cockpit.py.

Covers: missing-project graceful degradation, graph context rendering,
None return handling, direction indicators.
"""


class TestCockpitGraphContext:
    """Tests for graph context data in the Project Cockpit page."""

    def test_graph_context_handles_none_gracefully(self) -> None:
        """get_project_context returning None does not raise an exception."""
        from utils.graph_engine import (
            compute_centrality_metrics,
            detect_communities,
            get_project_context,
        )
        import networkx as nx

        G = nx.DiGraph()
        metrics = compute_centrality_metrics(G)
        communities = detect_communities(G)

        # Should return None, not raise
        result = get_project_context(G, metrics, communities, "NonExistent")
        assert result is None

    def test_direction_indicators(self) -> None:
        """Neighbors have correct direction field based on edge direction."""
        from utils.graph_engine import (
            compute_centrality_metrics,
            detect_communities,
            get_project_context,
        )
        import networkx as nx

        G = nx.DiGraph()
        G.add_edge("Project", "OutNeighbor")
        G.add_edge("InNeighbor", "Project")
        G.add_edge("Project", "BothNeighbor")
        G.add_edge("BothNeighbor", "Project")

        metrics = compute_centrality_metrics(G)
        communities = detect_communities(G)
        ctx = get_project_context(G, metrics, communities, "Project")

        assert ctx is not None
        neighbors_by_name = {n["name"]: n for n in ctx["neighbors"]}

        assert neighbors_by_name["OutNeighbor"]["direction"] == "out"
        assert neighbors_by_name["InNeighbor"]["direction"] == "in"
        assert neighbors_by_name["BothNeighbor"]["direction"] == "both"
