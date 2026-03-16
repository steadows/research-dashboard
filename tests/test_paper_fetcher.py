"""Tests for paper_fetcher — Semantic Scholar abstract fetching."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from utils.paper_fetcher import fetch_paper_abstract, _abstract_cache_key


class TestAbstractCacheKey:
    """Cache key is deterministic and normalised."""

    def test_same_title_same_key(self) -> None:
        assert _abstract_cache_key("Foo Bar") == _abstract_cache_key("Foo Bar")

    def test_case_insensitive(self) -> None:
        assert _abstract_cache_key("Foo Bar") == _abstract_cache_key("foo bar")

    def test_strips_whitespace(self) -> None:
        assert _abstract_cache_key("  Foo  ") == _abstract_cache_key("Foo")

    def test_different_titles_differ(self) -> None:
        assert _abstract_cache_key("Paper A") != _abstract_cache_key("Paper B")


class TestFetchPaperAbstract:
    """fetch_paper_abstract() caching, API call, and error paths."""

    def test_returns_empty_for_blank_title(self, tmp_path: Path) -> None:
        sf = tmp_path / "status.json"
        assert fetch_paper_abstract("", status_file=sf) == ""
        assert fetch_paper_abstract("   ", status_file=sf) == ""

    def test_returns_cached_abstract_without_http(self, tmp_path: Path) -> None:
        sf = tmp_path / "status.json"
        # Prime the cache manually
        from utils.status_tracker import set_analysis_cache
        from utils.paper_fetcher import _abstract_cache_key

        key = _abstract_cache_key("Some Paper Title")
        set_analysis_cache(key, {"abstract": "Cached abstract text."}, sf)

        with patch("utils.paper_fetcher._query_semantic_scholar") as mock_q:
            result = fetch_paper_abstract("Some Paper Title", status_file=sf)

        mock_q.assert_not_called()
        assert result == "Cached abstract text."

    def test_calls_api_on_cache_miss(self, tmp_path: Path) -> None:
        sf = tmp_path / "status.json"
        with patch(
            "utils.paper_fetcher._query_semantic_scholar", return_value="Fresh abstract."
        ) as mock_q:
            result = fetch_paper_abstract("New Paper", status_file=sf)

        mock_q.assert_called_once_with("New Paper")
        assert result == "Fresh abstract."

    def test_caches_result_after_api_call(self, tmp_path: Path) -> None:
        sf = tmp_path / "status.json"
        with patch(
            "utils.paper_fetcher._query_semantic_scholar", return_value="Abstract body."
        ):
            fetch_paper_abstract("Cacheable Paper", status_file=sf)

        # Second call must not hit the API
        with patch("utils.paper_fetcher._query_semantic_scholar") as mock_q:
            result = fetch_paper_abstract("Cacheable Paper", status_file=sf)

        mock_q.assert_not_called()
        assert result == "Abstract body."

    def test_returns_empty_on_network_error(self, tmp_path: Path) -> None:
        sf = tmp_path / "status.json"
        with patch(
            "utils.paper_fetcher._query_semantic_scholar",
            side_effect=Exception("timeout"),
        ):
            result = fetch_paper_abstract("Broken Paper", status_file=sf)

        assert result == ""

    def test_caches_empty_string_on_no_abstract(self, tmp_path: Path) -> None:
        """An empty-abstract result is cached so we don't hammer the API."""
        sf = tmp_path / "status.json"
        with patch(
            "utils.paper_fetcher._query_semantic_scholar", return_value=""
        ):
            fetch_paper_abstract("Abstract-less Paper", status_file=sf)

        with patch("utils.paper_fetcher._query_semantic_scholar") as mock_q:
            result = fetch_paper_abstract("Abstract-less Paper", status_file=sf)

        mock_q.assert_not_called()
        assert result == ""


class TestQuerySemanticScholar:
    """_query_semantic_scholar() parses API responses correctly."""

    def test_returns_abstract_from_top_result(self) -> None:
        from utils.paper_fetcher import _query_semantic_scholar

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"abstract": "This paper proposes...", "year": 2024, "venue": "NeurIPS"}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response

            result = _query_semantic_scholar("Some Title")

        assert result == "This paper proposes..."

    def test_returns_empty_when_no_results(self) -> None:
        from utils.paper_fetcher import _query_semantic_scholar

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response

            result = _query_semantic_scholar("Unknown Paper")

        assert result == ""

    def test_returns_empty_when_abstract_is_none(self) -> None:
        from utils.paper_fetcher import _query_semantic_scholar

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"abstract": None, "year": 2023, "venue": "ICML"}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response

            result = _query_semantic_scholar("No Abstract Paper")

        assert result == ""
