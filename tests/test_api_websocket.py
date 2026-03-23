"""Tests for FastAPI WebSocket endpoint — Session 19.

TDD RED phase: tests written before implementation.
Tests the /ws/research/{key} WebSocket for research log streaming.
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
        "status": "researching",
        "added": "2026-03-10",
        "pid": 12345,
        "log_file": "/tmp/research-workbench/tool-cursor-tab/agent.log",
    },
}

_LOG_LINES = [
    "Searching: cursor tab documentation",
    "Fetching github.com/cursor-tab",
    "Writing research.md",
]


def _apply_patches(stack: ExitStack) -> None:
    """Apply all mocks needed for WebSocket testing."""
    p = stack.enter_context
    p(patch.dict("os.environ", {"OBSIDIAN_VAULT_PATH": _VAULT}))
    p(patch("api.deps.get_vault_path", return_value=Path(_VAULT)))

    # workbench — patch both the module-level import and the utils source
    def wb_side_effect(key: str, **kw: object) -> dict[str, Any] | None:
        return _MOCK_WORKBENCH.get(key)

    p(
        patch(
            "utils.workbench_tracker.get_workbench_items", return_value=_MOCK_WORKBENCH
        )
    )
    p(patch("utils.workbench_tracker.get_workbench_item", side_effect=wb_side_effect))
    p(patch("api.ws.get_workbench_item", side_effect=wb_side_effect))

    # research agent — running first call, then exits
    p(patch("utils.research_agent.is_agent_running", side_effect=[True, False]))
    _tail_return = ("\n".join(_LOG_LINES), 100)
    p(patch("utils.research_agent.tail_log", return_value=_tail_return))
    p(patch("api.ws.is_agent_running", side_effect=[True, False]))
    p(patch("api.ws.tail_log", return_value=_tail_return))

    # parser stubs
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

    # mutation stubs
    p(patch("utils.status_tracker.get_item_status", return_value="new"))
    p(patch("utils.status_tracker.set_item_status"))
    p(patch("utils.workbench_tracker.add_to_workbench"))
    p(patch("utils.workbench_tracker.update_workbench_item"))
    p(patch("utils.workbench_tracker.remove_from_workbench"))
    p(
        patch(
            "utils.claude_client.analyze_item_quick",
            return_value={
                "response": "",
                "model": "",
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0,
            },
        )
    )
    p(
        patch(
            "utils.claude_client.analyze_item_deep",
            return_value={
                "response": "",
                "model": "",
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0,
            },
        )
    )
    p(patch("utils.claude_client.summarize_instagram_post", return_value=""))
    p(patch("utils.claude_client.generate_blog_draft", return_value=""))
    p(
        patch(
            "utils.research_agent.launch_research_agent",
            return_value=(MagicMock(pid=12345), "claude-opus-4-6"),
        )
    )
    p(patch("utils.instagram_ingester.run_ingestion", return_value=[]))
    p(patch("utils.blog_publisher.write_draft_mdx", return_value=Path("/tmp/x.mdx")))


@pytest.fixture
def client() -> TestClient:
    """Create a test client with workbench and research mocks."""
    with ExitStack() as stack:
        _apply_patches(stack)
        from api.main import create_app

        app = create_app()
        yield TestClient(app)


# ===================================================================
# WebSocket Tests
# ===================================================================


class TestResearchWebSocket:
    """WebSocket /ws/research/{key} for research log streaming."""

    def test_websocket_connects(self, client: TestClient) -> None:
        """WebSocket connects successfully for a known workbench item."""
        with client.websocket_connect("/ws/research/tool::Cursor Tab") as ws:
            data = ws.receive_json()
            assert data["type"] in ("log", "done")

    def test_websocket_receives_log_frames(self, client: TestClient) -> None:
        """WebSocket sends JSON frames with log tail."""
        with client.websocket_connect("/ws/research/tool::Cursor Tab") as ws:
            data = ws.receive_json()
            assert data["type"] == "log"
            assert "lines" in data

    def test_websocket_sends_done_when_agent_exits(self, client: TestClient) -> None:
        """WebSocket sends a 'done' frame when the agent process exits."""
        frames = []
        with client.websocket_connect("/ws/research/tool::Cursor Tab") as ws:
            for _ in range(5):
                data = ws.receive_json()
                frames.append(data)
                if data["type"] == "done":
                    break

        types = [f["type"] for f in frames]
        assert "done" in types

    def test_websocket_unknown_key_closes(self, client: TestClient) -> None:
        """WebSocket for unknown workbench key receives error and closes."""
        with client.websocket_connect("/ws/research/tool::NonExistent") as ws:
            data = ws.receive_json()
            assert data["type"] == "error"
