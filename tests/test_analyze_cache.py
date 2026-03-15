"""Tests for analyze cache — cache miss calls API, cache hit skips, deep cached separately."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch


def _make_item(**overrides: Any) -> dict[str, Any]:
    """Factory for item dicts."""
    defaults: dict[str, Any] = {
        "name": "Graph RAG for Code Search",
        "source_type": "method",
        "source": "JournalClub 2026-03-07",
        "status": "New",
        "projects": ["Axon"],
    }
    return {**defaults, **overrides}


def _make_project(**overrides: Any) -> dict[str, Any]:
    """Factory for project dicts."""
    defaults: dict[str, Any] = {
        "name": "Axon",
        "status": "Active",
        "domain": "Developer Tool",
        "tech": ["Python", "KuzuDB"],
    }
    return {**defaults, **overrides}


def _make_api_response(**overrides: Any) -> MagicMock:
    """Factory for mock Anthropic API response."""
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text=overrides.get("text", "Relevance: 4/5"))]
    mock_resp.model = overrides.get("model", "claude-haiku-4-5-20251001")
    mock_resp.usage.input_tokens = overrides.get("input_tokens", 100)
    mock_resp.usage.output_tokens = overrides.get("output_tokens", 50)
    return mock_resp


class TestAnalyzeCacheMiss:
    """Cache miss should call API and cache the result."""

    @patch("utils.claude_client._get_client")
    def test_cache_miss_calls_haiku(
        self, mock_get_client: MagicMock, tmp_path: Path
    ) -> None:
        """On cache miss, analyze_item_quick should call Haiku and cache."""
        from utils.claude_client import analyze_item_quick

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_api_response()
        mock_get_client.return_value = mock_client

        status_file = tmp_path / "status.json"
        item = _make_item()
        project = _make_project()

        result = analyze_item_quick(item, project, status_file)

        assert "response" in result
        assert result["response"] == "Relevance: 4/5"
        mock_client.messages.create.assert_called_once()

        # Verify the model used was Haiku
        call_kwargs = mock_client.messages.create.call_args
        assert "haiku" in call_kwargs.kwargs.get(
            "model", call_kwargs[1].get("model", "")
        )


class TestAnalyzeCacheHit:
    """Cache hit should skip API call and return cached result."""

    @patch("utils.claude_client._get_client")
    def test_cache_hit_skips_api(
        self, mock_get_client: MagicMock, tmp_path: Path
    ) -> None:
        """Second call with same params should return cached, no API call."""
        from utils.claude_client import analyze_item_quick

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_api_response()
        mock_get_client.return_value = mock_client

        status_file = tmp_path / "status.json"
        item = _make_item()
        project = _make_project()

        # First call — cache miss, calls API
        result1 = analyze_item_quick(item, project, status_file)

        # Second call — cache hit, skips API
        result2 = analyze_item_quick(item, project, status_file)

        assert result1["response"] == result2["response"]
        # API should have been called exactly once (first call only)
        assert mock_client.messages.create.call_count == 1


class TestDeepCachedSeparately:
    """Deep analysis should be cached separately from quick analysis."""

    @patch("utils.claude_client._get_client")
    def test_deep_and_quick_cached_independently(
        self, mock_get_client: MagicMock, tmp_path: Path
    ) -> None:
        """Quick and deep analysis for same item+project should each call API."""
        from utils.claude_client import analyze_item_deep, analyze_item_quick

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_api_response(
            text="Quick result"
        )
        mock_get_client.return_value = mock_client

        status_file = tmp_path / "status.json"
        item = _make_item()
        project = _make_project()

        # Quick analysis
        result_quick = analyze_item_quick(item, project, status_file)

        # Deep analysis — should NOT use quick's cache
        mock_client.messages.create.return_value = _make_api_response(
            text="Deep result", model="claude-sonnet-4-6"
        )
        result_deep = analyze_item_deep(item, project, status_file)

        # Both should have called the API
        assert mock_client.messages.create.call_count == 2
        assert result_quick["response"] == "Quick result"
        assert result_deep["response"] == "Deep result"

    @patch("utils.claude_client._get_client")
    def test_deep_cache_hit(self, mock_get_client: MagicMock, tmp_path: Path) -> None:
        """Second deep call should return cached result."""
        from utils.claude_client import analyze_item_deep

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_api_response(
            text="Deep result", model="claude-sonnet-4-6"
        )
        mock_get_client.return_value = mock_client

        status_file = tmp_path / "status.json"
        item = _make_item()
        project = _make_project()

        result1 = analyze_item_deep(item, project, status_file)
        result2 = analyze_item_deep(item, project, status_file)

        assert result1["response"] == result2["response"]
        assert mock_client.messages.create.call_count == 1
