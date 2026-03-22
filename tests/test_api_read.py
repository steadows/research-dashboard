"""Tests for FastAPI read-only endpoints — Session 18.

TDD RED phase: all tests written before implementation.
Mocks all parsers at the boundary to test endpoint shapes only.
"""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import networkx as nx
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_VAULT = "/tmp/test-vault"

_MOCK_PROJECTS: list[dict[str, Any]] = [
    {
        "name": "Axon",
        "status": "Active",
        "domain": "Developer Tool",
        "tech": ["Python", "KuzuDB"],
        "file_path": f"{_VAULT}/Projects/Axon.md",
        "content": "Code intelligence graph.\n",
        "wiki_links": [],
    },
    {
        "name": "Wealth Manager",
        "status": "active",
        "domain": "Native Apps",
        "tech": ["SwiftUI", "FastAPI", "Plaid"],
        "file_path": f"{_VAULT}/Projects/Wealth Manager.md",
        "content": "AI personal CFO.\n",
        "wiki_links": ["SwiftUI", "FastAPI", "Plaid"],
    },
]

_MOCK_METHODS: list[dict[str, Any]] = [
    {
        "name": "Graph RAG for Code Search",
        "source_type": "method",
        "source": "JournalClub 2026-03-07",
        "status": "New",
        "why it matters": "Combines graph structure with retrieval.",
        "projects": ["Axon"],
    },
]

_MOCK_TOOLS: list[dict[str, Any]] = [
    {
        "name": "Cursor Tab",
        "source_type": "tool",
        "category": "IDE",
        "source": "TLDR 2026-03-07",
        "status": "New",
        "what it does": "AI-powered tab completion.",
        "projects": ["Axon"],
    },
]

_MOCK_BLOG: list[dict[str, Any]] = [
    {
        "name": "Building a Code Knowledge Graph",
        "source_type": "blog",
        "status": "Draft",
        "hook": "Technical deep-dive on Axon architecture.",
        "tags": "research, graph, ml",
        "projects": ["Axon"],
    },
]

_MOCK_JC_REPORTS: list[dict[str, Any]] = [
    {
        "date": "2026-03-07",
        "filename": "JournalClub 2026-03-07.md",
        "sections": {"Top Picks": "1. Graph RAG paper"},
        "content": "# JournalClub\n\n## Top Picks\n1. Graph RAG paper",
    },
]

_MOCK_TLDR_REPORTS: list[dict[str, Any]] = [
    {
        "date": "2026-03-07",
        "filename": "TLDR 2026-03-07.md",
        "sections": {"Headlines": "- Claude 4 released"},
        "ai_signal": "The industry is shifting.",
        "content": "# TLDR\n\n## Headlines\n- Claude 4",
    },
]

_MOCK_INSTAGRAM: list[dict[str, Any]] = [
    {
        "name": "AI CFO demo",
        "account": "stevedev",
        "date": "2026-03-10",
        "source_url": "https://instagram.com/p/abc123",
        "shortcode": "abc123",
        "key_points": ["point 1"],
        "keywords": ["AI", "finance"],
        "caption": "Demo caption",
        "transcript": "",
        "source_type": "instagram",
    },
]

_MOCK_SMART_INDEX: dict[str, list[dict[str, Any]]] = {
    "Axon": [
        {
            "name": "Graph RAG for Code Search",
            "source_type": "method",
            "match_type": "explicit",
            "confidence": 1.0,
            "projects": ["Axon"],
        },
        {
            "name": "Cursor Tab",
            "source_type": "tool",
            "match_type": "explicit",
            "confidence": 1.0,
            "projects": ["Axon"],
        },
    ],
}

_MOCK_WORKBENCH: dict[str, dict[str, Any]] = {
    "tool::Cursor Tab": {
        "item": {"name": "Cursor Tab", "source_type": "tool"},
        "source_type": "tool",
        "status": "queued",
        "added": "2026-03-10",
    },
}


def _mock_graph() -> nx.DiGraph:
    """Small graph for testing."""
    G = nx.DiGraph()
    G.add_edges_from([("Axon", "Wealth Manager"), ("Axon", "Methods")])
    return G


def _mock_health() -> dict[str, int]:
    return {
        "node_count": 3,
        "edge_count": 2,
        "orphan_count": 0,
        "component_count": 1,
        "bridge_count": 1,
    }


def _mock_communities() -> list[frozenset[str]]:
    return [frozenset({"Axon", "Wealth Manager", "Methods"})]


def _mock_project_context() -> dict[str, Any]:
    return {
        "centrality_rank": 1,
        "pagerank_score": 0.45,
        "neighbors": [
            {"name": "Wealth Manager", "direction": "out", "pagerank": 0.3},
        ],
        "community_members": frozenset({"Axon", "Wealth Manager"}),
        "suggested_connections": [("DinnerBot", 0.42)],
    }


@pytest.fixture
def client() -> TestClient:
    """Create a test client with all parsers mocked."""
    with (
        patch.dict("os.environ", {"OBSIDIAN_VAULT_PATH": _VAULT}),
        patch("api.deps.get_vault_path", return_value=Path(_VAULT)),
        patch("utils.vault_parser.parse_projects", return_value=_MOCK_PROJECTS),
        patch("utils.methods_parser.parse_methods", return_value=_MOCK_METHODS),
        patch("utils.tools_parser.parse_tools", return_value=_MOCK_TOOLS),
        patch("utils.blog_queue_parser.parse_blog_queue", return_value=_MOCK_BLOG),
        patch(
            "utils.reports_parser.parse_journalclub_reports",
            return_value=_MOCK_JC_REPORTS,
        ),
        patch(
            "utils.reports_parser.parse_tldr_reports",
            return_value=_MOCK_TLDR_REPORTS,
        ),
        patch(
            "utils.instagram_parser.parse_instagram_posts",
            return_value=_MOCK_INSTAGRAM,
        ),
        patch(
            "utils.smart_matcher.build_smart_project_index",
            return_value=_MOCK_SMART_INDEX,
        ),
        patch(
            "utils.workbench_tracker.get_workbench_items",
            return_value=_MOCK_WORKBENCH,
        ),
        patch(
            "utils.workbench_tracker.get_workbench_item",
            side_effect=lambda key, **kw: _MOCK_WORKBENCH.get(key),
        ),
        patch("utils.graph_engine.build_vault_graph", return_value=_mock_graph()),
        patch("utils.graph_engine.get_graph_health", return_value=_mock_health()),
        patch(
            "utils.graph_engine.detect_communities",
            return_value=_mock_communities(),
        ),
        patch(
            "utils.graph_engine.compute_centrality_metrics",
            return_value={
                "pagerank": {"Axon": 0.45, "Wealth Manager": 0.3, "Methods": 0.25},
                "betweenness": {"Axon": 0.5, "Wealth Manager": 0.0, "Methods": 0.0},
                "degree": {"Axon": 2, "Wealth Manager": 1, "Methods": 1},
                "in_degree": {"Axon": 0, "Wealth Manager": 1, "Methods": 1},
                "out_degree": {"Axon": 2, "Wealth Manager": 0, "Methods": 0},
            },
        ),
        patch(
            "utils.graph_engine.get_project_context",
            return_value=_mock_project_context(),
        ),
        patch(
            "utils.smart_matcher.get_graph_linked_items",
            return_value=[
                {
                    "name": "Graph RAG for Code Search",
                    "source_type": "method",
                    "match_type": "explicit",
                    "confidence": 1.0,
                    "discovery_source": "linked",
                    "via_project": None,
                },
            ],
        ),
    ):
        from api.main import create_app

        app = create_app()
        yield TestClient(app)


# ===================================================================
# Projects Router
# ===================================================================


class TestProjectsRouter:
    """GET /api/projects and related endpoints."""

    def test_list_projects(self, client: TestClient) -> None:
        """GET /api/projects returns list of project dicts."""
        resp = client.get("/api/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2
        names = {p["name"] for p in data}
        assert names == {"Axon", "Wealth Manager"}

    def test_get_project_by_name(self, client: TestClient) -> None:
        """GET /api/projects/{name} returns single project."""
        resp = client.get("/api/projects/Axon")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Axon"
        assert data["status"] == "Active"

    def test_get_project_not_found(self, client: TestClient) -> None:
        """GET /api/projects/{name} returns 404 for unknown project."""
        resp = client.get("/api/projects/NonExistent")
        assert resp.status_code == 404

    def test_project_index(self, client: TestClient) -> None:
        """GET /api/project-index/{project} returns smart index items."""
        resp = client.get("/api/project-index/Axon")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["match_type"] == "explicit"

    def test_project_index_empty(self, client: TestClient) -> None:
        """GET /api/project-index/{project} returns empty list for unknown project."""
        resp = client.get("/api/project-index/NonExistent")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_project_graph_linked_items(self, client: TestClient) -> None:
        """GET /api/project-index/{project}/graph returns graph-linked items."""
        resp = client.get("/api/project-index/Axon/graph")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        item = data[0]
        assert "discovery_source" in item
        assert "via_project" in item

    def test_project_graph_linked_stable_keys(self, client: TestClient) -> None:
        """Graph-linked items have stable composite keys."""
        resp = client.get("/api/project-index/Axon/graph")
        data = resp.json()
        for item in data:
            assert "name" in item
            assert "source_type" in item


# ===================================================================
# Content Router
# ===================================================================


class TestContentRouter:
    """GET /api/methods, /api/tools, /api/blog-queue, /api/reports, /api/instagram."""

    def test_get_methods(self, client: TestClient) -> None:
        """GET /api/methods returns list of method items."""
        resp = client.get("/api/methods")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "Graph RAG for Code Search"

    def test_get_tools(self, client: TestClient) -> None:
        """GET /api/tools returns list of tool items."""
        resp = client.get("/api/tools")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert data[0]["name"] == "Cursor Tab"

    def test_get_blog_queue(self, client: TestClient) -> None:
        """GET /api/blog-queue returns list of blog items."""
        resp = client.get("/api/blog-queue")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert data[0]["source_type"] == "blog"

    def test_get_reports_journalclub(self, client: TestClient) -> None:
        """GET /api/reports/journalclub returns JournalClub reports."""
        resp = client.get("/api/reports/journalclub")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert data[0]["date"] == "2026-03-07"

    def test_get_reports_tldr(self, client: TestClient) -> None:
        """GET /api/reports/tldr returns TLDR reports."""
        resp = client.get("/api/reports/tldr")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert "ai_signal" in data[0]

    def test_get_reports_invalid_type(self, client: TestClient) -> None:
        """GET /api/reports/{invalid} returns 400."""
        resp = client.get("/api/reports/invalid")
        assert resp.status_code == 400

    def test_get_instagram(self, client: TestClient) -> None:
        """GET /api/instagram returns list of instagram posts."""
        resp = client.get("/api/instagram")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert data[0]["source_type"] == "instagram"


# ===================================================================
# Graph Router
# ===================================================================


class TestGraphRouter:
    """GET /api/graph/health, /api/graph/{project}, /api/graph/communities, viz."""

    def test_graph_health(self, client: TestClient) -> None:
        """GET /api/graph/health returns health metrics."""
        resp = client.get("/api/graph/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "node_count" in data
        assert "edge_count" in data
        assert data["node_count"] == 3

    def test_graph_project_context(self, client: TestClient) -> None:
        """GET /api/graph/{project} returns project context."""
        resp = client.get("/api/graph/Axon")
        assert resp.status_code == 200
        data = resp.json()
        assert "centrality_rank" in data
        assert "pagerank_score" in data
        assert "neighbors" in data
        # community_members should be serialized as list (not frozenset)
        assert isinstance(data.get("community_members"), list)

    def test_graph_project_not_found(self, client: TestClient) -> None:
        """GET /api/graph/{project} returns 404 for unknown project."""
        with patch(
            "api.routers.graph.get_project_context",
            return_value=None,
        ):
            resp = client.get("/api/graph/NonExistent")
            assert resp.status_code == 404

    def test_graph_communities(self, client: TestClient) -> None:
        """GET /api/graph/communities returns list of communities."""
        resp = client.get("/api/graph/communities")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Each community should be a list (serialized from frozenset)
        assert isinstance(data[0], list)

    def test_graph_viz(self, client: TestClient) -> None:
        """GET /api/graph/{project}/viz returns {nodes, edges} for D3."""
        resp = client.get("/api/graph/Axon/viz")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)

    def test_graph_viz_node_ids_unique(self, client: TestClient) -> None:
        """Viz node IDs are globally unique."""
        resp = client.get("/api/graph/Axon/viz")
        data = resp.json()
        ids = [n["id"] for n in data["nodes"]]
        assert len(ids) == len(set(ids)), f"Duplicate node IDs: {ids}"

    def test_graph_viz_node_shape(self, client: TestClient) -> None:
        """Each viz node has id, type, label."""
        resp = client.get("/api/graph/Axon/viz")
        data = resp.json()
        for node in data["nodes"]:
            assert "id" in node
            assert "type" in node
            assert "label" in node
            assert node["type"] in {"project", "method", "tool", "blog"}

    def test_graph_viz_edge_shape(self, client: TestClient) -> None:
        """Each viz edge has source, target, relation."""
        resp = client.get("/api/graph/Axon/viz")
        data = resp.json()
        for edge in data["edges"]:
            assert "source" in edge
            assert "target" in edge
            assert "relation" in edge
            assert edge["relation"] in {"linked", "community", "suggested"}

    def test_graph_viz_empty_for_unknown(self, client: TestClient) -> None:
        """Viz returns empty nodes/edges for unknown project, never errors."""
        with (
            patch(
                "api.routers.graph.build_smart_project_index",
                return_value={},
            ),
            patch(
                "api.routers.graph.get_graph_linked_items",
                return_value=[],
            ),
        ):
            resp = client.get("/api/graph/NonExistent/viz")
            assert resp.status_code == 200
            data = resp.json()
            assert data == {"nodes": [], "edges": []}


# ===================================================================
# Workbench Router
# ===================================================================


class TestWorkbenchRouter:
    """GET /api/workbench and GET /api/workbench/{key}."""

    def test_list_workbench(self, client: TestClient) -> None:
        """GET /api/workbench returns workbench items."""
        resp = client.get("/api/workbench")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "tool::Cursor Tab" in data

    def test_get_workbench_item(self, client: TestClient) -> None:
        """GET /api/workbench/{key} returns single item."""
        resp = client.get("/api/workbench/tool::Cursor Tab")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"

    def test_get_workbench_item_not_found(self, client: TestClient) -> None:
        """GET /api/workbench/{key} returns 404 for missing key."""
        resp = client.get("/api/workbench/tool::NonExistent")
        assert resp.status_code == 404


# ===================================================================
# CORS
# ===================================================================


class TestCORS:
    """CORS is configured for localhost:3000."""

    def test_cors_allowed_origin(self, client: TestClient) -> None:
        """localhost:3000 is an allowed CORS origin."""
        resp = client.options(
            "/api/projects",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert (
            resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
        )

    def test_cors_disallowed_origin(self, client: TestClient) -> None:
        """Random origins are not allowed."""
        resp = client.options(
            "/api/projects",
            headers={
                "Origin": "http://evil.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") != "http://evil.com"
