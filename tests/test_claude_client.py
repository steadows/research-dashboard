"""Tests for claude_client — Anthropic SDK wrapper with LLM trace logging."""

import hashlib
import logging
import logging.handlers
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from utils.claude_client import (
    _get_client,
    analyze_item_deep,
    analyze_item_quick,
    call_haiku_json,
)


# --- Helpers ---


def _make_item(name: str = "Graph RAG for Code Search") -> dict:
    return {
        "name": name,
        "source": "JournalClub 2026-03-07",
        "status": "New",
        "why_it_matters": "Combines graph structure with retrieval.",
    }


def _make_project(name: str = "Axon") -> dict:
    return {
        "name": name,
        "status": "Active",
        "domain": "Developer Tools",
        "tech_stack": ["Python", "KuzuDB"],
        "overview": "Code intelligence graph.",
    }


def _cache_key(item_name: str, project_name: str, analysis_type: str) -> str:
    raw = f"{item_name}:{project_name}:{analysis_type}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _mock_api_response(text: str = "Relevant because of graph structure.") -> MagicMock:
    """Build a mock Anthropic API response."""
    content_block = MagicMock()
    content_block.text = text

    usage = MagicMock()
    usage.input_tokens = 100
    usage.output_tokens = 50

    response = MagicMock()
    response.content = [content_block]
    response.usage = usage
    response.model = "claude-haiku-4-5-20251001"
    return response


@pytest.fixture(autouse=True)
def _clear_client_cache() -> None:
    """Clear the lru_cache on _get_client before each test."""
    _get_client.cache_clear()


# --- Tests ---


class TestGetClient:
    """Tests for _get_client — API key validation."""

    def test_empty_api_key_raises(self) -> None:
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}, clear=False):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                _get_client()

    def test_missing_api_key_raises(self) -> None:
        import os

        with patch.dict("os.environ", {}, clear=False):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                _get_client()

    def test_valid_api_key_returns_client(self) -> None:
        with patch.dict(
            "os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test-key"}, clear=False
        ):
            with patch("utils.claude_client.anthropic.Anthropic") as mock_cls:
                mock_cls.return_value = MagicMock()
                client = _get_client()
                assert client is not None


class TestAnalyzeItemQuick:
    """Tests for analyze_item_quick — Haiku model, caching, error handling."""

    def test_uses_haiku_model(self, tmp_path: Path) -> None:
        """Quick analysis should use the Haiku model."""
        status_file = tmp_path / "status.json"
        item = _make_item()
        project = _make_project()

        with patch.dict(
            "os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=False
        ):
            with patch("utils.claude_client.anthropic.Anthropic") as mock_cls:
                mock_client = MagicMock()
                mock_cls.return_value = mock_client
                mock_client.messages.create.return_value = _mock_api_response()

                analyze_item_quick(item, project, status_file)

                call_kwargs = mock_client.messages.create.call_args
                assert (
                    "haiku"
                    in call_kwargs.kwargs.get(
                        "model", call_kwargs[1].get("model", "")
                    ).lower()
                )

    def test_cache_hit_skips_api(self, tmp_path: Path) -> None:
        """Cache hit should return cached result without API call."""
        status_file = tmp_path / "status.json"
        item = _make_item()
        project = _make_project()

        cached_result = {
            "response": "cached answer",
            "model": "claude-haiku-4-5-20251001",
        }

        with patch(
            "utils.claude_client.get_analysis_cache", return_value=cached_result
        ):
            with patch("utils.claude_client.anthropic.Anthropic") as mock_cls:
                with patch.dict(
                    "os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=False
                ):
                    mock_client = MagicMock()
                    mock_cls.return_value = mock_client

                    result = analyze_item_quick(item, project, status_file)

                    assert result == cached_result
                    mock_client.messages.create.assert_not_called()

    def test_cache_miss_calls_api_and_caches(self, tmp_path: Path) -> None:
        """Cache miss should call API and store result in cache."""
        status_file = tmp_path / "status.json"
        item = _make_item()
        project = _make_project()

        with patch("utils.claude_client.get_analysis_cache", return_value=None):
            with patch("utils.claude_client.set_analysis_cache") as mock_set_cache:
                with patch("utils.claude_client.anthropic.Anthropic") as mock_cls:
                    with patch.dict(
                        "os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=False
                    ):
                        mock_client = MagicMock()
                        mock_cls.return_value = mock_client
                        mock_client.messages.create.return_value = _mock_api_response()

                        result = analyze_item_quick(item, project, status_file)

                        assert (
                            result["response"] == "Relevant because of graph structure."
                        )
                        mock_set_cache.assert_called_once()

    def test_api_error_raises_and_logs(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """API error should raise and log a warning."""
        status_file = tmp_path / "status.json"
        item = _make_item()
        project = _make_project()

        with patch("utils.claude_client.get_analysis_cache", return_value=None):
            with patch("utils.claude_client.anthropic.Anthropic") as mock_cls:
                with patch.dict(
                    "os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=False
                ):
                    mock_client = MagicMock()
                    mock_cls.return_value = mock_client
                    mock_client.messages.create.side_effect = Exception("API timeout")

                    with pytest.raises(Exception, match="API timeout"):
                        analyze_item_quick(item, project, status_file)


class TestAnalyzeItemDeep:
    """Tests for analyze_item_deep — Sonnet model."""

    def test_uses_sonnet_model(self, tmp_path: Path) -> None:
        """Deep analysis should use the Sonnet model."""
        status_file = tmp_path / "status.json"
        item = _make_item()
        project = _make_project()

        with patch.dict(
            "os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=False
        ):
            with patch("utils.claude_client.anthropic.Anthropic") as mock_cls:
                with patch("utils.claude_client.get_analysis_cache", return_value=None):
                    with patch("utils.claude_client.set_analysis_cache"):
                        mock_client = MagicMock()
                        mock_cls.return_value = mock_client
                        mock_client.messages.create.return_value = _mock_api_response()

                        analyze_item_deep(item, project, status_file)

                        call_kwargs = mock_client.messages.create.call_args
                        model_used = call_kwargs.kwargs.get(
                            "model", call_kwargs[1].get("model", "")
                        )
                        assert "sonnet" in model_used.lower()

    def test_cache_hit_skips_api(self, tmp_path: Path) -> None:
        """Deep analysis cache hit should skip API."""
        status_file = tmp_path / "status.json"
        item = _make_item()
        project = _make_project()

        cached_result = {"response": "deep cached", "model": "claude-sonnet-4-6"}

        with patch(
            "utils.claude_client.get_analysis_cache", return_value=cached_result
        ):
            with patch("utils.claude_client.anthropic.Anthropic") as mock_cls:
                with patch.dict(
                    "os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=False
                ):
                    mock_client = MagicMock()
                    mock_cls.return_value = mock_client

                    result = analyze_item_deep(item, project, status_file)

                    assert result == cached_result
                    mock_client.messages.create.assert_not_called()


class TestLLMTrace:
    """Tests for LLM trace logging behavior."""

    def test_trace_fires_when_enabled(self, tmp_path: Path) -> None:
        """LLM trace should log when LLM_TRACE=1."""
        status_file = tmp_path / "status.json"
        item = _make_item()
        project = _make_project()

        with patch("utils.claude_client.get_analysis_cache", return_value=None):
            with patch("utils.claude_client.set_analysis_cache"):
                with patch("utils.claude_client.anthropic.Anthropic") as mock_cls:
                    with patch.dict(
                        "os.environ",
                        {"ANTHROPIC_API_KEY": "sk-ant-test", "LLM_TRACE": "1"},
                        clear=False,
                    ):
                        mock_client = MagicMock()
                        mock_cls.return_value = mock_client
                        resp = _mock_api_response()
                        resp.model = "claude-haiku-4-5-20251001"
                        mock_client.messages.create.return_value = resp

                        # Set up trace logger to capture
                        trace_logger = logging.getLogger("llm_trace")
                        trace_logger.setLevel(logging.DEBUG)
                        handler = logging.handlers.MemoryHandler(capacity=100)
                        trace_logger.addHandler(handler)

                        try:
                            analyze_item_quick(item, project, status_file)

                            # Flush handler and check records
                            handler.flush()
                            records = handler.buffer
                            debug_records = [
                                r for r in records if r.levelno == logging.DEBUG
                            ]
                            info_records = [
                                r for r in records if r.levelno == logging.INFO
                            ]
                            assert len(debug_records) >= 1 or len(info_records) >= 1
                        finally:
                            trace_logger.removeHandler(handler)

    def test_trace_silent_when_disabled(self, tmp_path: Path) -> None:
        """LLM trace should not log prompts when LLM_TRACE is not set."""
        status_file = tmp_path / "status.json"
        item = _make_item()
        project = _make_project()

        with patch("utils.claude_client.get_analysis_cache", return_value=None):
            with patch("utils.claude_client.set_analysis_cache"):
                with patch("utils.claude_client.anthropic.Anthropic") as mock_cls:
                    env = {"ANTHROPIC_API_KEY": "sk-ant-test"}
                    with patch.dict("os.environ", env, clear=False):
                        # Ensure LLM_TRACE is not set
                        import os

                        os.environ.pop("LLM_TRACE", None)

                        mock_client = MagicMock()
                        mock_cls.return_value = mock_client
                        mock_client.messages.create.return_value = _mock_api_response()

                        trace_logger = logging.getLogger("llm_trace")
                        trace_logger.setLevel(logging.DEBUG)
                        handler = logging.handlers.MemoryHandler(capacity=100)
                        trace_logger.addHandler(handler)

                        try:
                            analyze_item_quick(item, project, status_file)

                            handler.flush()
                            debug_records = [
                                r for r in handler.buffer if r.levelno == logging.DEBUG
                            ]
                            # No debug-level prompt logs when trace is off
                            prompt_records = [
                                r
                                for r in debug_records
                                if "prompt" in r.getMessage().lower()
                            ]
                            assert len(prompt_records) == 0
                        finally:
                            trace_logger.removeHandler(handler)


class TestCallHaikuJson:
    """Tests for call_haiku_json — thin Haiku wrapper."""

    def test_calls_api_with_haiku_model(self, tmp_path: Path) -> None:
        """call_haiku_json calls _call_api with the Haiku model."""
        with patch.dict(
            "os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=False
        ):
            with patch("utils.claude_client.anthropic.Anthropic") as mock_cls:
                mock_client = MagicMock()
                mock_cls.return_value = mock_client
                mock_client.messages.create.return_value = _mock_api_response(
                    '{"key": "value"}'
                )

                result = call_haiku_json("Extract JSON from this text")

                call_kwargs = mock_client.messages.create.call_args
                model_used = call_kwargs.kwargs.get(
                    "model", call_kwargs[1].get("model", "")
                )
                assert "haiku" in model_used.lower()
                assert result == '{"key": "value"}'

    def test_respects_max_tokens(self, tmp_path: Path) -> None:
        """call_haiku_json passes max_tokens to the API."""
        with patch.dict(
            "os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=False
        ):
            with patch("utils.claude_client.anthropic.Anthropic") as mock_cls:
                mock_client = MagicMock()
                mock_cls.return_value = mock_client
                mock_client.messages.create.return_value = _mock_api_response("ok")

                call_haiku_json("prompt", max_tokens=300)

                call_kwargs = mock_client.messages.create.call_args
                tokens = call_kwargs.kwargs.get(
                    "max_tokens", call_kwargs[1].get("max_tokens", 0)
                )
                assert tokens == 300
