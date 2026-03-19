"""Tests for graph_engine — vault network analysis via obsidiantools + NetworkX.

Covers: build_vault_graph, compute_centrality_metrics, detect_communities,
suggest_links, get_graph_health, get_project_context, plus integration test
with a real tmp vault.
"""

from pathlib import Path

import networkx as nx


# ---------------------------------------------------------------------------
# build_vault_graph
# ---------------------------------------------------------------------------


class TestBuildVaultGraph:
    """Tests for build_vault_graph — vault markdown → nx.DiGraph."""

    def test_returns_digraph(self, tmp_path: Path) -> None:
        """build_vault_graph returns an nx.DiGraph, not MultiDiGraph."""
        # Create minimal vault with two linked notes
        (tmp_path / "Alpha.md").write_text("Link to [[Beta]]")
        (tmp_path / "Beta.md").write_text("# Beta\nContent here.")

        from utils.graph_engine import build_vault_graph

        G = build_vault_graph(str(tmp_path))
        assert isinstance(G, nx.DiGraph)
        assert not isinstance(G, nx.MultiDiGraph)

    def test_no_self_loops(self, tmp_path: Path) -> None:
        """Returned graph has no self-loops (e.g. [[note#section]])."""
        (tmp_path / "Alpha.md").write_text("Link to [[Alpha#section]] and [[Beta]]")
        (tmp_path / "Beta.md").write_text("# Beta")

        from utils.graph_engine import build_vault_graph

        G = build_vault_graph(str(tmp_path))
        assert len(list(nx.selfloop_edges(G))) == 0

    def test_nonexistent_notes_filtered(self, tmp_path: Path) -> None:
        """Notes linked but never created are filtered out."""
        (tmp_path / "Alpha.md").write_text("Link to [[Ghost]] and [[Beta]]")
        (tmp_path / "Beta.md").write_text("# Beta")

        from utils.graph_engine import build_vault_graph

        G = build_vault_graph(str(tmp_path))
        assert "Ghost" not in G.nodes()

    def test_empty_vault_returns_empty_graph(self, tmp_path: Path) -> None:
        """Empty vault returns graph with 0 nodes."""
        from utils.graph_engine import build_vault_graph

        G = build_vault_graph(str(tmp_path))
        assert G.number_of_nodes() == 0


# ---------------------------------------------------------------------------
# compute_centrality_metrics
# ---------------------------------------------------------------------------


class TestComputeCentralityMetrics:
    """Tests for compute_centrality_metrics — pagerank, betweenness, degree."""

    def test_returns_expected_keys(self, graph_fixture: nx.DiGraph) -> None:
        """Result dict has keys: pagerank, betweenness, degree, in_degree, out_degree."""
        from utils.graph_engine import compute_centrality_metrics

        metrics = compute_centrality_metrics(graph_fixture)
        assert set(metrics.keys()) == {
            "pagerank",
            "betweenness",
            "degree",
            "in_degree",
            "out_degree",
        }

    def test_values_are_dicts_keyed_by_node(self, graph_fixture: nx.DiGraph) -> None:
        """Each metric value is a dict[str, float|int] keyed by note name."""
        from utils.graph_engine import compute_centrality_metrics

        metrics = compute_centrality_metrics(graph_fixture)
        for key in ("pagerank", "betweenness", "degree", "in_degree", "out_degree"):
            val = metrics[key]
            assert isinstance(val, dict)
            for node_name, score in val.items():
                assert isinstance(node_name, str)
                assert isinstance(score, (int, float))

    def test_pagerank_sums_to_one(self, graph_fixture: nx.DiGraph) -> None:
        """PageRank values sum to approximately 1.0."""
        from utils.graph_engine import compute_centrality_metrics

        metrics = compute_centrality_metrics(graph_fixture)
        total = sum(metrics["pagerank"].values())
        assert abs(total - 1.0) < 0.01

    def test_hub_has_highest_in_degree(self, graph_fixture: nx.DiGraph) -> None:
        """Hub node (T1) has highest in-degree (3 incoming edges)."""
        from utils.graph_engine import compute_centrality_metrics

        metrics = compute_centrality_metrics(graph_fixture)
        in_degrees = metrics["in_degree"]
        max_node = max(in_degrees, key=in_degrees.get)
        assert max_node == "T1"
        assert in_degrees["T1"] == 3

    def test_empty_graph_returns_empty_dicts(self) -> None:
        """Empty graph returns empty dicts for all metrics."""
        from utils.graph_engine import compute_centrality_metrics

        G = nx.DiGraph()
        metrics = compute_centrality_metrics(G)
        for key in ("pagerank", "betweenness", "degree", "in_degree", "out_degree"):
            assert metrics[key] == {}


# ---------------------------------------------------------------------------
# detect_communities
# ---------------------------------------------------------------------------


class TestDetectCommunities:
    """Tests for detect_communities — Louvain community detection."""

    def test_returns_list_of_frozensets(self, graph_fixture: nx.DiGraph) -> None:
        """Result is a list of frozenset[str]."""
        from utils.graph_engine import detect_communities

        communities = detect_communities(graph_fixture)
        assert isinstance(communities, list)
        for c in communities:
            assert isinstance(c, frozenset)
            for member in c:
                assert isinstance(member, str)

    def test_every_node_in_exactly_one_community(
        self, graph_fixture: nx.DiGraph
    ) -> None:
        """For 2+ node graphs: every node in exactly one community, union = all nodes."""
        from utils.graph_engine import detect_communities

        communities = detect_communities(graph_fixture)
        all_members = set()
        for c in communities:
            # No overlap
            assert len(all_members & c) == 0
            all_members.update(c)
        assert all_members == set(graph_fixture.nodes())

    def test_empty_graph_returns_empty_list(self) -> None:
        """Graph with 0 nodes returns empty list."""
        from utils.graph_engine import detect_communities

        communities = detect_communities(nx.DiGraph())
        assert communities == []

    def test_single_node_returns_empty_list(self) -> None:
        """Graph with 1 node returns empty list (no meaningful communities)."""
        from utils.graph_engine import detect_communities

        G = nx.DiGraph()
        G.add_node("solo")
        communities = detect_communities(G)
        assert communities == []


# ---------------------------------------------------------------------------
# suggest_links
# ---------------------------------------------------------------------------


class TestSuggestLinks:
    """Tests for suggest_links — Adamic-Adar link prediction."""

    def test_returns_sorted_tuples(self, graph_fixture: nx.DiGraph) -> None:
        """Returns list[tuple[str, float]] sorted by score descending."""
        from utils.graph_engine import suggest_links

        suggestions = suggest_links(graph_fixture, "A")
        assert isinstance(suggestions, list)
        for name, score in suggestions:
            assert isinstance(name, str)
            assert isinstance(score, float)
        scores = [s for _, s in suggestions]
        assert scores == sorted(scores, reverse=True)

    def test_excludes_existing_neighbors(self, graph_fixture: nx.DiGraph) -> None:
        """Existing neighbors are not suggested."""
        from utils.graph_engine import suggest_links

        neighbors = set(graph_fixture.successors("A")) | set(
            graph_fixture.predecessors("A")
        )
        suggestions = suggest_links(graph_fixture, "A")
        suggested_names = {name for name, _ in suggestions}
        assert len(suggested_names & neighbors) == 0

    def test_excludes_self(self, graph_fixture: nx.DiGraph) -> None:
        """Self is not included in suggestions."""
        from utils.graph_engine import suggest_links

        suggestions = suggest_links(graph_fixture, "A")
        suggested_names = {name for name, _ in suggestions}
        assert "A" not in suggested_names

    def test_note_not_in_graph_returns_empty(self, graph_fixture: nx.DiGraph) -> None:
        """Returns empty list for a note not in the graph."""
        from utils.graph_engine import suggest_links

        suggestions = suggest_links(graph_fixture, "NonExistent")
        assert suggestions == []

    def test_top_n_limits_results(self, graph_fixture: nx.DiGraph) -> None:
        """top_n parameter limits result count."""
        from utils.graph_engine import suggest_links

        suggestions = suggest_links(graph_fixture, "B", top_n=1)
        assert len(suggestions) <= 1

    def test_scores_are_non_negative(self, graph_fixture: nx.DiGraph) -> None:
        """All scores are non-negative floats."""
        from utils.graph_engine import suggest_links

        suggestions = suggest_links(graph_fixture, "B")
        for _, score in suggestions:
            assert score >= 0.0


# ---------------------------------------------------------------------------
# get_graph_health
# ---------------------------------------------------------------------------


class TestGetGraphHealth:
    """Tests for get_graph_health — structural health metrics."""

    def test_returns_expected_keys(self, graph_fixture: nx.DiGraph) -> None:
        """Result has node_count, edge_count, orphan_count, component_count, bridge_count."""
        from utils.graph_engine import get_graph_health

        health = get_graph_health(graph_fixture)
        assert set(health.keys()) == {
            "node_count",
            "edge_count",
            "orphan_count",
            "component_count",
            "bridge_count",
        }

    def test_all_values_non_negative_ints(self, graph_fixture: nx.DiGraph) -> None:
        """All health values are non-negative integers."""
        from utils.graph_engine import get_graph_health

        health = get_graph_health(graph_fixture)
        for key, val in health.items():
            assert isinstance(val, int), f"{key} is not int"
            assert val >= 0, f"{key} is negative"

    def test_empty_graph_returns_all_zeros(self) -> None:
        """Empty graph returns all zeros."""
        from utils.graph_engine import get_graph_health

        health = get_graph_health(nx.DiGraph())
        assert all(v == 0 for v in health.values())

    def test_disconnected_graph_has_multiple_components(self) -> None:
        """Disconnected graph has component_count > 1."""
        from utils.graph_engine import get_graph_health

        G = nx.DiGraph()
        G.add_edge("A", "B")
        G.add_edge("C", "D")
        health = get_graph_health(G)
        assert health["component_count"] > 1


# ---------------------------------------------------------------------------
# get_project_context
# ---------------------------------------------------------------------------


class TestGetProjectContext:
    """Tests for get_project_context — per-project graph summary."""

    def _build_context_args(self, G: nx.DiGraph) -> tuple:
        """Helper to build metrics + communities for get_project_context."""
        from utils.graph_engine import compute_centrality_metrics, detect_communities

        metrics = compute_centrality_metrics(G)
        communities = detect_communities(G)
        return metrics, communities

    def test_returns_expected_keys(self, graph_fixture: nx.DiGraph) -> None:
        """Result dict has centrality_rank, pagerank_score, neighbors, etc."""
        from utils.graph_engine import get_project_context

        metrics, communities = self._build_context_args(graph_fixture)
        ctx = get_project_context(graph_fixture, metrics, communities, "A")
        assert ctx is not None
        assert set(ctx.keys()) == {
            "centrality_rank",
            "pagerank_score",
            "neighbors",
            "community_members",
            "suggested_connections",
        }

    def test_centrality_rank_is_1_indexed(self, graph_fixture: nx.DiGraph) -> None:
        """centrality_rank is a 1-indexed integer."""
        from utils.graph_engine import get_project_context

        metrics, communities = self._build_context_args(graph_fixture)
        ctx = get_project_context(graph_fixture, metrics, communities, "A")
        assert ctx is not None
        assert isinstance(ctx["centrality_rank"], int)
        assert ctx["centrality_rank"] >= 1

    def test_neighbors_have_correct_shape(self, graph_fixture: nx.DiGraph) -> None:
        """Each neighbor is {name, direction, pagerank}."""
        from utils.graph_engine import get_project_context

        metrics, communities = self._build_context_args(graph_fixture)
        ctx = get_project_context(graph_fixture, metrics, communities, "A")
        assert ctx is not None
        for neighbor in ctx["neighbors"]:
            assert "name" in neighbor
            assert "direction" in neighbor
            assert "pagerank" in neighbor
            assert neighbor["direction"] in ("in", "out", "both")
            assert isinstance(neighbor["pagerank"], float)

    def test_neighbors_sorted_by_pagerank_desc(self, graph_fixture: nx.DiGraph) -> None:
        """Neighbors are sorted by PageRank descending."""
        from utils.graph_engine import get_project_context

        metrics, communities = self._build_context_args(graph_fixture)
        ctx = get_project_context(graph_fixture, metrics, communities, "B")
        assert ctx is not None
        pageranks = [n["pagerank"] for n in ctx["neighbors"]]
        assert pageranks == sorted(pageranks, reverse=True)

    def test_community_members_present(self, graph_fixture: nx.DiGraph) -> None:
        """community_members is a frozenset for graphs with 2+ nodes."""
        from utils.graph_engine import get_project_context

        metrics, communities = self._build_context_args(graph_fixture)
        ctx = get_project_context(graph_fixture, metrics, communities, "A")
        assert ctx is not None
        assert isinstance(ctx["community_members"], frozenset)
        assert "A" in ctx["community_members"]

    def test_community_members_none_for_tiny_graph(self) -> None:
        """community_members is None when graph has < 2 nodes."""
        from utils.graph_engine import (
            compute_centrality_metrics,
            detect_communities,
            get_project_context,
        )

        G = nx.DiGraph()
        G.add_node("solo")
        metrics = compute_centrality_metrics(G)
        communities = detect_communities(G)
        ctx = get_project_context(G, metrics, communities, "solo")
        assert ctx is not None
        assert ctx["community_members"] is None

    def test_returns_none_for_missing_note(self, graph_fixture: nx.DiGraph) -> None:
        """Returns None for a note not in the graph."""
        from utils.graph_engine import get_project_context

        metrics, communities = self._build_context_args(graph_fixture)
        ctx = get_project_context(graph_fixture, metrics, communities, "NonExistent")
        assert ctx is None


# ---------------------------------------------------------------------------
# Integration test — real tmp vault with .md files
# ---------------------------------------------------------------------------


class TestIntegration:
    """Integration test using a real tmp vault with markdown files and wiki-links."""

    def test_full_pipeline_with_tmp_vault(self, tmp_path: Path) -> None:
        """End-to-end: create vault files → build graph → compute metrics → project context."""
        from utils.graph_engine import (
            build_vault_graph,
            compute_centrality_metrics,
            detect_communities,
            get_project_context,
        )

        # Create vault structure with wiki-links
        projects_dir = tmp_path / "Projects"
        projects_dir.mkdir()

        (projects_dir / "Alpha.md").write_text(
            "---\ntags:\n  - project\nstatus: active\n---\n\n"
            "# Alpha\n\nA project about [[Beta]] and [[Methods]].\n"
        )
        (projects_dir / "Beta.md").write_text(
            "---\ntags:\n  - project\nstatus: active\n---\n\n"
            "# Beta\n\nRelated to [[Alpha]] and [[Tools]].\n"
        )
        (tmp_path / "Methods.md").write_text(
            "# Methods\n\nMethodology for [[Alpha]] and [[Gamma]].\n"
        )
        (tmp_path / "Tools.md").write_text("# Tools\n\nTools used by [[Beta]].\n")
        (tmp_path / "Gamma.md").write_text(
            "# Gamma\n\nStandalone note with link to [[Methods]].\n"
        )

        # Build graph
        G = build_vault_graph(str(tmp_path))
        assert isinstance(G, nx.DiGraph)
        assert G.number_of_nodes() > 0
        assert G.number_of_edges() > 0

        # Compute metrics
        metrics = compute_centrality_metrics(G)
        assert len(metrics["pagerank"]) > 0

        # Detect communities
        communities = detect_communities(G)
        assert len(communities) > 0

        # Project-name alignment: verify vault_parser project names match graph nodes
        from utils.vault_parser import parse_projects

        projects = parse_projects(tmp_path)
        project_names = {p["name"] for p in projects}

        # At least one project name appears as a graph node
        graph_nodes = set(G.nodes())
        overlap = project_names & graph_nodes
        assert len(overlap) > 0, (
            f"No overlap between parse_projects names {project_names} "
            f"and graph nodes {graph_nodes}"
        )

        # Get project context for a known project
        project_name = next(iter(overlap))
        ctx = get_project_context(G, metrics, communities, project_name)
        assert ctx is not None
        assert isinstance(ctx["centrality_rank"], int)
        assert ctx["centrality_rank"] >= 1
