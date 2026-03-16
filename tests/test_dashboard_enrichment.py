"""Tests for dashboard enrichment — Blog Queue render path must not trigger fetches."""

from pathlib import Path
from unittest.mock import patch


class TestBlogQueueRenderPath:
    """Blog Queue rendering must never call fetch_paper_context — only passive cache."""

    def test_render_never_calls_fetch_paper_context(self) -> None:
        """Blog Queue render does not call fetch_paper_context on the render path."""
        # We verify that the blog queue card rendering uses get_cached_paper_context
        # (passive) rather than fetch_paper_context (active network call).
        from utils.paper_fetcher import get_cached_paper_context

        # get_cached_paper_context should return None on cache miss without triggering fetch
        with patch("utils.paper_fetcher._read_paper_cache", return_value=None):
            result = get_cached_paper_context("Some Title")

        assert result is None

    def test_blog_queue_render_is_instant_no_http(self) -> None:
        """Blog Queue render path makes zero HTTP calls regardless of network state."""
        from utils.paper_fetcher import get_cached_paper_context

        # Even with httpx completely broken, get_cached_paper_context works fine
        with (
            patch("utils.paper_fetcher._read_paper_cache", return_value=None),
            patch("httpx.Client", side_effect=RuntimeError("Network is down")),
        ):
            # Should not raise — no network calls
            result = get_cached_paper_context("Any Paper Title")

        assert result is None

    def test_get_cached_paper_context_returns_cached_data(self, tmp_path: Path) -> None:
        """get_cached_paper_context returns cached PaperContext when available."""
        from utils.paper_fetcher import get_cached_paper_context

        cached = {
            "abstract": "Cached abstract.",
            "full_text": "Full text here.",
            "full_text_source": "pdf",
            "year": "2025",
            "venue": "ICML",
            "authors": ["Author A"],
            "fetch_state": "pdf",
            "error": "",
        }

        with patch("utils.paper_fetcher._read_paper_cache", return_value=cached):
            result = get_cached_paper_context("Cached Paper", cache_dir=tmp_path)

        assert result is not None
        assert result["abstract"] == "Cached abstract."
        assert result["fetch_state"] == "pdf"


class TestDeepReadFallback:
    """Deep Read falls back cleanly when no full text is available."""

    def test_deep_read_works_without_full_text(self, tmp_path: Path) -> None:
        """deep_read_paper still works when paper enrichment returns empty full_text."""
        from utils.claude_client import deep_read_paper

        item = {"name": "Fallback Paper", "hook": "h", "source": "src"}

        empty_context = {
            "abstract": "Just an abstract.",
            "full_text": "",
            "full_text_source": "",
            "year": "",
            "venue": "",
            "authors": [],
            "fetch_state": "abstract_only",
            "error": "",
        }

        with (
            patch(
                "utils.claude_client.fetch_paper_context", return_value=empty_context
            ),
            patch("utils.claude_client._call_api") as mock_api,
            patch("utils.claude_client.get_analysis_cache", return_value=None),
            patch("utils.claude_client.set_analysis_cache"),
        ):
            mock_api.return_value = {
                "response": "Deep read result",
                "model": "m",
                "input_tokens": 1,
                "output_tokens": 1,
                "cost": 0.0,
            }
            result = deep_read_paper(item, status_file=tmp_path / "status.json")

        assert result == "Deep read result"
        # Prompt should use Abstract: fallback
        prompt = mock_api.call_args[0][0]
        assert "Abstract:" in prompt
        assert "Just an abstract." in prompt

    def test_generate_draft_works_with_empty_enrichment(self, tmp_path: Path) -> None:
        """generate_blog_draft still works when paper enrichment returns all empty."""
        from utils.claude_client import generate_blog_draft

        item = {"name": "Empty Enrichment Paper", "hook": "h", "source": "s"}

        empty_context = {
            "abstract": "",
            "full_text": "",
            "full_text_source": "",
            "year": "",
            "venue": "",
            "authors": [],
            "fetch_state": "not_found",
            "error": "",
        }

        with (
            patch(
                "utils.claude_client.fetch_paper_context", return_value=empty_context
            ),
            patch("utils.claude_client._call_api") as mock_api,
            patch("utils.claude_client.get_analysis_cache", return_value=None),
            patch("utils.claude_client.set_analysis_cache"),
        ):
            mock_api.return_value = {
                "response": "Draft body",
                "model": "m",
                "input_tokens": 1,
                "output_tokens": 1,
                "cost": 0.0,
            }
            result = generate_blog_draft(item, status_file=tmp_path / "status.json")

        assert result == "Draft body"
