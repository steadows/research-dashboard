"""Tests for the knowledge linker router — [24.6g].

Covers POST /api/linker/run and GET /api/linker/status with:
- Happy path (202 + run_id)
- Concurrent-run rejection (409)
- Idle status before any run
- Complete status with results after job finishes
- Error terminal state when linker raises
- Graph cache invalidation on success
- Graph cache invalidation even on crash-after-mutation

Follows the ExitStack + double-patch pattern from test_api_mutations.py.
"""

from __future__ import annotations

import time
from contextlib import ExitStack
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.utils.knowledge_linker import LinkResult

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

_VAULT = "/tmp/test-vault"

_MOCK_RESULT = LinkResult(
    results={"Instagram": 2, "Dev Journal": 1, "Satellites": 0},
    warnings=[],
    total_modified=3,
    mutated=True,
)


def _apply_patches(stack: ExitStack) -> dict[str, Any]:
    """Apply all mocks needed for linker router testing.

    Double-patches at both the source module and the router import level so
    that the router always sees the mock regardless of import order.

    Returns a dict of named mock objects for assertion.
    """
    p = stack.enter_context
    mocks: dict[str, Any] = {}

    # Environment / dependency injection
    p(patch.dict("os.environ", {"OBSIDIAN_VAULT_PATH": _VAULT}))
    p(patch("api.deps.get_vault_path", return_value=Path(_VAULT)))

    # link_vault_all_with_progress — double-patched
    mocks["link_fn"] = MagicMock(return_value=_MOCK_RESULT)
    p(
        patch(
            "utils.knowledge_linker.link_vault_all_with_progress",
            mocks["link_fn"],
        )
    )
    p(
        patch(
            "api.routers.linker.link_vault_all_with_progress",
            mocks["link_fn"],
        )
    )

    # invalidate_graph_cache — patched at the source (linker imports it lazily
    # via `from api.routers.graph import invalidate_graph_cache` inside the
    # finally block, so only the source-module patch is effective).
    mocks["invalidate"] = MagicMock()
    p(patch("api.routers.graph.invalidate_graph_cache", mocks["invalidate"]))

    # Parser / engine stubs needed for app startup
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

    return mocks


def _make_client(stack: ExitStack, mocks: dict[str, Any] | None = None) -> TestClient:
    """Build a TestClient with patches already applied to stack."""
    from api.main import create_app

    app = create_app()
    return TestClient(app, raise_server_exceptions=False)


def _wait_for_status(
    client: TestClient, terminal: set[str], timeout: float = 3.0
) -> dict[str, Any]:
    """Poll GET /api/linker/status until a terminal state is reached."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        resp = client.get("/api/linker/status")
        data = resp.json()
        if data.get("status") in terminal:
            return data
        time.sleep(0.05)
    return client.get("/api/linker/status").json()


# ---------------------------------------------------------------------------
# Fixture — isolated client with reset_job() before each test
# ---------------------------------------------------------------------------


@pytest.fixture()
def client_and_mocks() -> Any:
    """Yield (TestClient, mocks) with job state reset for isolation."""
    from api.routers.linker import reset_job

    reset_job()
    with ExitStack() as stack:
        mocks = _apply_patches(stack)
        client = _make_client(stack, mocks)
        yield client, mocks
        # Ensure background threads don't bleed into the next test
        reset_job()


# ---------------------------------------------------------------------------
# TestLinkerRun
# ---------------------------------------------------------------------------


class TestLinkerRun:
    """POST /api/linker/run endpoint."""

    def test_run_returns_202_with_run_id(self, client_and_mocks: Any) -> None:
        """POST /api/linker/run returns 202 with status=accepted and a run_id UUID."""
        client, mocks = client_and_mocks

        resp = client.post("/api/linker/run")

        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "accepted"
        assert "run_id" in data
        # run_id must be a non-empty UUID-shaped string
        assert len(data["run_id"]) == 36

    def test_concurrent_run_returns_409(self, client_and_mocks: Any) -> None:
        """POST /api/linker/run while running returns 409 Conflict.

        TestClient executes BackgroundTasks synchronously after returning the
        response, so we cannot use a blocking background task to hold the
        "running" state between two HTTP calls in the same thread.  Instead we
        set the in-memory _job state directly to "running" before the second
        POST, which is exactly what the router checks.  This is deterministic
        and tests the correct branching logic without relying on thread timing.
        """
        client, mocks = client_and_mocks

        import api.routers.linker as linker_mod

        # Force the job into "running" state between the two POST calls
        with linker_mod._job_lock:
            linker_mod._job.clear()
            linker_mod._job["status"] = "running"

        second = client.post("/api/linker/run")

        assert second.status_code == 409
        assert "already running" in second.json()["detail"].lower()


# ---------------------------------------------------------------------------
# TestLinkerStatus
# ---------------------------------------------------------------------------


class TestLinkerStatus:
    """GET /api/linker/status endpoint."""

    def test_status_idle_before_any_run(self, client_and_mocks: Any) -> None:
        """GET /api/linker/status returns status=idle when no job has been started."""
        client, mocks = client_and_mocks

        resp = client.get("/api/linker/status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "idle"
        assert data.get("run_id") is None

    def test_status_complete_with_results_after_job(
        self, client_and_mocks: Any
    ) -> None:
        """GET /api/linker/status returns complete with results and run_id after job finishes."""
        client, mocks = client_and_mocks

        post_resp = client.post("/api/linker/run")
        assert post_resp.status_code == 202
        run_id = post_resp.json()["run_id"]

        # Poll until the background task completes
        data = _wait_for_status(client, {"complete", "partial", "error"})

        assert data["status"] == "complete"
        assert data["run_id"] == run_id
        assert data["results"] == {"Instagram": 2, "Dev Journal": 1, "Satellites": 0}
        assert data["total_modified"] == 3
        assert data["warnings"] == []
        assert data["completed_at"] is not None

    def test_status_error_on_linker_exception(self, client_and_mocks: Any) -> None:
        """GET /api/linker/status returns status=error with detail when linker raises."""
        client, mocks = client_and_mocks

        boom = RuntimeError("disk full")
        mocks["link_fn"].side_effect = boom

        client.post("/api/linker/run")
        data = _wait_for_status(client, {"error", "complete", "partial"})

        assert data["status"] == "error"
        assert "disk full" in data.get("error", "")
        assert data["completed_at"] is not None


# ---------------------------------------------------------------------------
# TestGraphCacheInvalidation
# ---------------------------------------------------------------------------


class TestGraphCacheInvalidation:
    """Verify graph cache is invalidated after successful or crashing linker runs."""

    def test_cache_invalidated_on_success(self, client_and_mocks: Any) -> None:
        """invalidate_graph_cache is called after a successful linker run with mutations."""
        client, mocks = client_and_mocks

        # _MOCK_RESULT has mutated=True; the on_step callback fires with modified_count>0
        # We simulate this by making the mock call on_step before returning.
        real_result = _MOCK_RESULT

        def _linker_with_step(vault_path: Path, on_step: Any = None) -> LinkResult:
            if on_step is not None:
                on_step("Instagram", 2, [])
            return real_result

        with patch(
            "api.routers.linker.link_vault_all_with_progress", _linker_with_step
        ):
            client.post("/api/linker/run")
            _wait_for_status(client, {"complete", "partial", "error"})

        mocks["invalidate"].assert_called_once()

    def test_cache_invalidated_after_crash_with_prior_mutations(
        self, client_and_mocks: Any
    ) -> None:
        """invalidate_graph_cache is called even when linker crashes after some files modified."""
        client, mocks = client_and_mocks

        def _crash_after_mutation(vault_path: Path, on_step: Any = None) -> LinkResult:
            # Signal that one directory was modified before the crash
            if on_step is not None:
                on_step("Projects", 1, [])
            raise RuntimeError("crash mid-run")

        with patch(
            "api.routers.linker.link_vault_all_with_progress", _crash_after_mutation
        ):
            client.post("/api/linker/run")
            data = _wait_for_status(client, {"error", "complete", "partial"})

        assert data["status"] == "error"
        # Cache must still be invalidated because a mutation occurred before the crash
        mocks["invalidate"].assert_called_once()

    def test_cache_not_invalidated_when_no_mutations(
        self, client_and_mocks: Any
    ) -> None:
        """invalidate_graph_cache is NOT called when linker runs but modifies zero files."""
        client, mocks = client_and_mocks

        no_op_result = LinkResult(
            results={"Instagram": 0, "Dev Journal": 0},
            warnings=[],
            total_modified=0,
            mutated=False,
        )

        def _no_op_linker(vault_path: Path, on_step: Any = None) -> LinkResult:
            # on_step never called with modified_count > 0
            if on_step is not None:
                on_step("Instagram", 0, [])
            return no_op_result

        with patch("api.routers.linker.link_vault_all_with_progress", _no_op_linker):
            client.post("/api/linker/run")
            _wait_for_status(client, {"complete", "partial", "error"})

        mocks["invalidate"].assert_not_called()
