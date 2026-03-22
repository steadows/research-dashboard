"""Tests for FastAPI mutation endpoints — Session 19.

TDD RED phase: all tests written before implementation.
Mocks all side-effect-producing functions at the boundary.
"""

from contextlib import ExitStack
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_VAULT = "/tmp/test-vault"

_MOCK_WORKBENCH: dict[str, dict[str, Any]] = {
    "tool::Cursor Tab": {
        "item": {"name": "Cursor Tab", "source_type": "tool"},
        "source_type": "tool",
        "status": "queued",
        "added": "2026-03-10",
    },
}


def _apply_patches(stack: ExitStack) -> None:
    """Apply all mocks needed for mutation endpoint testing."""
    p = stack.enter_context
    p(patch.dict("os.environ", {"OBSIDIAN_VAULT_PATH": _VAULT}))
    p(patch("api.deps.get_vault_path", return_value=Path(_VAULT)))

    # status_tracker — patch at both source and usage sites
    p(patch("utils.status_tracker.get_item_status", return_value="new"))
    p(patch("utils.status_tracker.set_item_status"))
    p(patch("api.routers.status.get_item_status", return_value="new"))
    p(patch("api.routers.status.set_item_status"))

    # claude_client — patch at both source and usage sites
    _quick_result = {
        "response": "Quick analysis result",
        "model": "claude-haiku-4-5-20251001",
        "input_tokens": 100,
        "output_tokens": 50,
        "cost": 0.001,
    }
    _deep_result = {
        "response": "Deep analysis result",
        "model": "claude-sonnet-4-6",
        "input_tokens": 200,
        "output_tokens": 100,
        "cost": 0.005,
    }
    p(patch("utils.claude_client.analyze_item_quick", return_value=_quick_result))
    p(patch("utils.claude_client.analyze_item_deep", return_value=_deep_result))
    p(patch("api.routers.analysis.analyze_item_quick", return_value=_quick_result))
    p(patch("api.routers.analysis.analyze_item_deep", return_value=_deep_result))
    p(
        patch(
            "utils.claude_client.summarize_instagram_post",
            return_value="Instagram summary text",
        )
    )
    p(
        patch(
            "utils.claude_client.generate_blog_draft",
            return_value="# Blog draft body\n\nContent here.",
        )
    )
    p(
        patch(
            "api.routers.content.summarize_instagram_post",
            return_value="Instagram summary text",
        )
    )
    p(
        patch(
            "api.routers.content.generate_blog_draft",
            return_value="# Blog draft body\n\nContent here.",
        )
    )
    p(
        patch(
            "api.routers.content.write_draft_mdx",
            return_value=Path("/tmp/blog-draft.mdx"),
        )
    )

    # workbench_tracker — patch at both source and usage sites
    def _wb_get(key: str, **kw: object) -> dict[str, Any] | None:
        return _MOCK_WORKBENCH.get(key)

    p(
        patch(
            "utils.workbench_tracker.get_workbench_items", return_value=_MOCK_WORKBENCH
        )
    )
    p(patch("utils.workbench_tracker.get_workbench_item", side_effect=_wb_get))
    p(patch("utils.workbench_tracker.add_to_workbench"))
    p(patch("utils.workbench_tracker.update_workbench_item"))
    p(patch("utils.workbench_tracker.remove_from_workbench"))
    p(patch("api.routers.workbench.get_workbench_items", return_value=_MOCK_WORKBENCH))
    p(patch("api.routers.workbench.get_workbench_item", side_effect=_wb_get))
    p(patch("api.routers.workbench.add_to_workbench"))
    p(patch("api.routers.workbench.update_workbench_item"))
    p(patch("api.routers.workbench.remove_from_workbench"))
    p(patch("api.routers.research.get_workbench_item", side_effect=_wb_get))
    p(patch("api.routers.research.update_workbench_item"))

    # research_agent — patch at both source and usage sites
    _proc_mock = MagicMock(pid=12345)
    p(
        patch(
            "utils.research_agent.launch_research_agent",
            return_value=(_proc_mock, "claude-opus-4-6"),
        )
    )
    p(patch("utils.research_agent.is_agent_running", return_value=True))
    p(patch("utils.research_agent.tail_log", return_value="Researching..."))
    p(
        patch(
            "api.routers.research.launch_research_agent",
            return_value=(_proc_mock, "claude-opus-4-6"),
        )
    )
    p(patch("api.routers.research.is_agent_running", return_value=True))
    p(patch("api.routers.research.tail_log", return_value="Researching..."))

    # instagram_ingester — patch at both source and usage sites
    p(
        patch(
            "utils.instagram_ingester.run_ingestion",
            return_value=[Path("/tmp/note1.md")],
        )
    )
    p(
        patch(
            "api.routers.ingestion.run_ingestion", return_value=[Path("/tmp/note1.md")]
        )
    )

    # blog_publisher
    p(
        patch(
            "utils.blog_publisher.write_draft_mdx",
            return_value=Path("/tmp/blog-draft.mdx"),
        )
    )

    # parser stubs (needed for app startup)
    p(patch("utils.vault_parser.parse_projects", return_value=[]))
    p(patch("utils.methods_parser.parse_methods", return_value=[]))
    p(patch("utils.tools_parser.parse_tools", return_value=[]))
    p(patch("utils.blog_queue_parser.parse_blog_queue", return_value=[]))
    p(patch("utils.reports_parser.parse_journalclub_reports", return_value=[]))
    p(patch("utils.reports_parser.parse_tldr_reports", return_value=[]))
    p(patch("utils.instagram_parser.parse_instagram_posts", return_value=[]))
    p(patch("utils.smart_matcher.build_smart_project_index", return_value={}))
    p(patch("utils.graph_engine.build_vault_graph", return_value=MagicMock()))
    p(
        patch(
            "utils.graph_engine.get_graph_health",
            return_value={"node_count": 0, "edge_count": 0},
        )
    )
    p(patch("utils.graph_engine.detect_communities", return_value=[]))
    p(
        patch(
            "utils.graph_engine.compute_centrality_metrics",
            return_value={"pagerank": {}, "betweenness": {}, "degree": {}},
        )
    )
    p(patch("utils.graph_engine.get_project_context", return_value=None))
    p(patch("utils.smart_matcher.get_graph_linked_items", return_value=[]))


@pytest.fixture
def client() -> TestClient:
    """Create a test client with all side-effect functions mocked."""
    with ExitStack() as stack:
        _apply_patches(stack)
        from api.main import create_app

        app = create_app()
        yield TestClient(app)


# ===================================================================
# Status Router
# ===================================================================


class TestStatusRouter:
    """POST/PATCH /api/status/{key} endpoints."""

    def test_set_status(self, client: TestClient) -> None:
        """POST /api/status/{key} sets item status."""
        resp = client.post(
            "/api/status/tool::Cursor Tab",
            json={"status": "reviewed"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["key"] == "tool::Cursor Tab"
        assert data["status"] == "reviewed"

    def test_set_status_missing_body(self, client: TestClient) -> None:
        """POST /api/status/{key} returns 422 without body."""
        resp = client.post("/api/status/tool::Cursor Tab")
        assert resp.status_code == 422

    def test_set_status_empty_status(self, client: TestClient) -> None:
        """POST /api/status/{key} rejects empty status string."""
        resp = client.post(
            "/api/status/tool::Cursor Tab",
            json={"status": ""},
        )
        assert resp.status_code == 422

    def test_patch_status(self, client: TestClient) -> None:
        """PATCH /api/status/{key} updates item status."""
        resp = client.patch(
            "/api/status/tool::Cursor Tab",
            json={"status": "skipped"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "skipped"

    def test_get_status(self, client: TestClient) -> None:
        """GET /api/status/{key} returns current status."""
        resp = client.get("/api/status/tool::Cursor Tab")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data


# ===================================================================
# Analysis Router
# ===================================================================


class TestAnalysisRouter:
    """POST /api/analyze and POST /api/analyze/deep endpoints."""

    def test_analyze_quick(self, client: TestClient) -> None:
        """POST /api/analyze runs quick Haiku analysis."""
        resp = client.post(
            "/api/analyze",
            json={
                "item": {"name": "Test Tool", "source_type": "tool"},
                "project": {"name": "Axon"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert data["model"] == "claude-haiku-4-5-20251001"

    def test_analyze_deep(self, client: TestClient) -> None:
        """POST /api/analyze/deep runs deep Sonnet analysis."""
        resp = client.post(
            "/api/analyze/deep",
            json={
                "item": {"name": "Test Tool", "source_type": "tool"},
                "project": {"name": "Axon"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert data["model"] == "claude-sonnet-4-6"

    def test_analyze_with_graph_context(self, client: TestClient) -> None:
        """POST /api/analyze accepts optional graph_context."""
        resp = client.post(
            "/api/analyze",
            json={
                "item": {"name": "Test Tool"},
                "project": {"name": "Axon"},
                "graph_context": {"centrality_rank": 1},
            },
        )
        assert resp.status_code == 200

    def test_analyze_missing_item(self, client: TestClient) -> None:
        """POST /api/analyze returns 422 without item."""
        resp = client.post(
            "/api/analyze",
            json={"project": {"name": "Axon"}},
        )
        assert resp.status_code == 422

    def test_analyze_missing_project(self, client: TestClient) -> None:
        """POST /api/analyze returns 422 without project."""
        resp = client.post(
            "/api/analyze",
            json={"item": {"name": "Test Tool"}},
        )
        assert resp.status_code == 422


# ===================================================================
# Workbench Mutations
# ===================================================================


class TestWorkbenchMutations:
    """POST, PATCH, DELETE on /api/workbench."""

    def test_add_to_workbench(self, client: TestClient) -> None:
        """POST /api/workbench adds an item."""
        resp = client.post(
            "/api/workbench",
            json={
                "item": {"name": "New Tool", "source_type": "tool"},
                "previous_status": "new",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["key"] == "tool::New Tool"

    def test_add_to_workbench_default_status(self, client: TestClient) -> None:
        """POST /api/workbench defaults previous_status to 'new'."""
        resp = client.post(
            "/api/workbench",
            json={"item": {"name": "Another Tool", "source_type": "tool"}},
        )
        assert resp.status_code == 201

    def test_update_workbench_item(self, client: TestClient) -> None:
        """PATCH /api/workbench/{key} updates fields."""
        resp = client.patch(
            "/api/workbench/tool::Cursor Tab",
            json={"updates": {"status": "researching"}},
        )
        assert resp.status_code == 200

    def test_update_workbench_invalid_fields(self, client: TestClient) -> None:
        """PATCH /api/workbench/{key} rejects disallowed fields."""
        with patch(
            "api.routers.workbench.update_workbench_item",
            side_effect=ValueError("Disallowed workbench update fields: {'item'}"),
        ):
            resp = client.patch(
                "/api/workbench/tool::Cursor Tab",
                json={"updates": {"item": {"hacked": True}}},
            )
            assert resp.status_code == 400

    def test_delete_workbench_item(self, client: TestClient) -> None:
        """DELETE /api/workbench/{key} removes an item."""
        resp = client.delete("/api/workbench/tool::Cursor Tab")
        assert resp.status_code == 200
        data = resp.json()
        assert data["removed"] == "tool::Cursor Tab"


# ===================================================================
# Research Router
# ===================================================================


class TestResearchRouter:
    """POST /api/research/{key} and GET /api/research/{key}/status."""

    def test_launch_research(self, client: TestClient) -> None:
        """POST /api/research/{key} launches research agent."""
        resp = client.post("/api/research/tool::Cursor Tab")
        assert resp.status_code == 202
        data = resp.json()
        assert data["pid"] == 12345
        assert "model" in data

    def test_launch_research_not_found(self, client: TestClient) -> None:
        """POST /api/research/{key} returns 404 for unknown key."""
        resp = client.post("/api/research/tool::NonExistent")
        assert resp.status_code == 404

    def test_research_status(self, client: TestClient) -> None:
        """GET /api/research/{key}/status returns agent status."""
        resp = client.get("/api/research/tool::Cursor Tab/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "running" in data

    def test_research_status_not_found(self, client: TestClient) -> None:
        """GET /api/research/{key}/status returns 404 for unknown key."""
        resp = client.get("/api/research/tool::NonExistent/status")
        assert resp.status_code == 404


# ===================================================================
# Ingestion Router
# ===================================================================


class TestIngestionRouter:
    """POST /api/instagram/refresh endpoint."""

    def test_refresh_instagram(self, client: TestClient) -> None:
        """POST /api/instagram/refresh triggers ingestion."""
        resp = client.post(
            "/api/instagram/refresh",
            json={"username": "stevedev", "days": 7},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["notes_written"] == 1
        assert isinstance(data["note_paths"], list)

    def test_refresh_instagram_invalid_username(self, client: TestClient) -> None:
        """POST /api/instagram/refresh rejects invalid usernames."""
        resp = client.post(
            "/api/instagram/refresh",
            json={"username": "../../../etc/passwd", "days": 7},
        )
        assert resp.status_code == 422

    def test_refresh_instagram_default_days(self, client: TestClient) -> None:
        """POST /api/instagram/refresh defaults to 14 days."""
        resp = client.post(
            "/api/instagram/refresh",
            json={"username": "stevedev"},
        )
        assert resp.status_code == 200


# ===================================================================
# Content Mutations (extend content.py)
# ===================================================================


class TestContentMutations:
    """POST /api/summarize/instagram and POST /api/blog-queue/draft."""

    def test_summarize_instagram(self, client: TestClient) -> None:
        """POST /api/summarize/instagram returns a summary."""
        resp = client.post(
            "/api/summarize/instagram",
            json={
                "post": {
                    "name": "AI demo",
                    "account": "stevedev",
                    "transcript": "Some text",
                    "key_points": ["point1"],
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data

    def test_blog_queue_draft(self, client: TestClient) -> None:
        """POST /api/blog-queue/draft generates a blog draft."""
        resp = client.post(
            "/api/blog-queue/draft",
            json={
                "item": {
                    "name": "Building a Code Knowledge Graph",
                    "hook": "Deep dive on Axon",
                    "tags": "research, graph",
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "draft" in data
        assert "draft_path" in data
