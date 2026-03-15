"""Tests for Dashboard page — data flow, filter logic, status persistence, tab loading."""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from utils.blog_queue_parser import parse_blog_queue
from utils.methods_parser import parse_methods
from utils.page_helpers import get_vault_path, safe_html
from utils.reports_parser import parse_journalclub_reports, parse_tldr_reports
from utils.status_tracker import get_item_status, set_item_status
from utils.tools_parser import parse_tools


# ---------------------------------------------------------------------------
# Data flow: parsers return expected structures
# ---------------------------------------------------------------------------


class TestDataFlow:
    """Parser calls return expected structures for dashboard tabs."""

    def test_blog_queue_returns_list_of_dicts(self, tmp_vault: Path) -> None:
        """parse_blog_queue returns a list of dicts with required keys."""
        items = parse_blog_queue(tmp_vault)
        assert isinstance(items, list)
        assert len(items) > 0
        for item in items:
            assert "name" in item
            assert "status" in item
            assert "source_type" in item
            assert item["source_type"] == "blog"

    def test_tools_returns_list_of_dicts(self, tmp_vault: Path) -> None:
        """parse_tools returns a list of dicts with required keys."""
        items = parse_tools(tmp_vault)
        assert isinstance(items, list)
        assert len(items) > 0
        for item in items:
            assert "name" in item
            assert "category" in item
            assert "source_type" in item
            assert item["source_type"] == "tool"

    def test_methods_returns_list_of_dicts(self, tmp_vault: Path) -> None:
        """parse_methods returns a list of dicts with required keys."""
        items = parse_methods(tmp_vault)
        assert isinstance(items, list)
        assert len(items) > 0
        for item in items:
            assert "name" in item
            assert "source_type" in item
            assert item["source_type"] == "method"

    def test_journalclub_reports_returns_sorted_list(self, tmp_vault: Path) -> None:
        """JournalClub reports have date, sections, content."""
        reports = parse_journalclub_reports(tmp_vault)
        assert isinstance(reports, list)
        assert len(reports) > 0
        for report in reports:
            assert "date" in report
            assert "sections" in report
            assert "content" in report

    def test_tldr_reports_returns_ai_signal(self, tmp_vault: Path) -> None:
        """TLDR reports include ai_signal field."""
        reports = parse_tldr_reports(tmp_vault)
        assert isinstance(reports, list)
        assert len(reports) > 0
        for report in reports:
            assert "date" in report
            assert "ai_signal" in report
            assert "sections" in report

    def test_empty_vault_returns_empty_lists(self, empty_vault: Path) -> None:
        """All parsers return empty lists for empty vault."""
        assert parse_blog_queue(empty_vault) == []
        assert parse_tools(empty_vault) == []
        assert parse_methods(empty_vault) == []
        assert parse_journalclub_reports(empty_vault) == []
        assert parse_tldr_reports(empty_vault) == []


# ---------------------------------------------------------------------------
# Filter logic
# ---------------------------------------------------------------------------


class TestFilterLogic:
    """Filter operations for dashboard tabs."""

    def test_filter_blog_by_status(self, tmp_vault: Path) -> None:
        """Blog items can be filtered by status."""
        items = parse_blog_queue(tmp_vault)
        draft_items = [i for i in items if i["status"] == "Draft"]
        idea_items = [i for i in items if i["status"] == "Idea"]
        assert len(draft_items) >= 1
        assert len(idea_items) >= 1
        assert len(draft_items) + len(idea_items) == len(items)

    def test_filter_tools_by_category(self, tmp_vault: Path) -> None:
        """Tools can be filtered by category."""
        items = parse_tools(tmp_vault)
        categories = {i["category"] for i in items}
        assert len(categories) >= 1
        for cat in categories:
            filtered = [i for i in items if i["category"] == cat]
            assert len(filtered) >= 1

    def test_filter_by_source_type(self, tmp_vault: Path) -> None:
        """Items can be differentiated by source_type."""
        methods = parse_methods(tmp_vault)
        tools = parse_tools(tmp_vault)
        blog = parse_blog_queue(tmp_vault)
        all_items: list[dict[str, Any]] = methods + tools + blog
        source_types = {i["source_type"] for i in all_items}
        assert source_types == {"method", "tool", "blog"}

    def test_keyword_search_filter(self, tmp_vault: Path) -> None:
        """Reports can be filtered by keyword search in content."""
        reports = parse_journalclub_reports(tmp_vault)
        keyword = "Graph"
        matching = [r for r in reports if keyword.lower() in r["content"].lower()]
        assert len(matching) >= 1


# ---------------------------------------------------------------------------
# Status write persistence
# ---------------------------------------------------------------------------


class TestStatusPersistence:
    """set_item_status persists through reload."""

    def test_set_and_get_status(self, tmp_path: Path) -> None:
        """Status set for an item is retrievable after reload."""
        status_file = tmp_path / "status.json"
        set_item_status("tool::cursor-tab", "reviewed", status_file=status_file)
        result = get_item_status("tool::cursor-tab", status_file=status_file)
        assert result == "reviewed"

    def test_default_status_is_new(self, tmp_path: Path) -> None:
        """Items without explicit status default to 'new'."""
        status_file = tmp_path / "status.json"
        result = get_item_status("nonexistent-item", status_file=status_file)
        assert result == "new"

    def test_status_survives_reload(self, tmp_path: Path) -> None:
        """Status persists to disk and survives re-read."""
        status_file = tmp_path / "status.json"
        set_item_status("blog::code-graph", "queued", status_file=status_file)
        # Re-read fresh from disk
        result = get_item_status("blog::code-graph", status_file=status_file)
        assert result == "queued"

    def test_multiple_statuses_independent(self, tmp_path: Path) -> None:
        """Multiple item statuses don't overwrite each other."""
        status_file = tmp_path / "status.json"
        set_item_status("item-a", "reviewed", status_file=status_file)
        set_item_status("item-b", "skipped", status_file=status_file)
        assert get_item_status("item-a", status_file=status_file) == "reviewed"
        assert get_item_status("item-b", status_file=status_file) == "skipped"


# ---------------------------------------------------------------------------
# Page helpers
# ---------------------------------------------------------------------------


class TestPageHelpers:
    """Tests for shared page utility functions."""

    def test_get_vault_path_returns_path(self) -> None:
        """get_vault_path returns a Path object from env var."""
        with patch.dict("os.environ", {"OBSIDIAN_VAULT_PATH": "/tmp/test-vault"}):
            result = get_vault_path()
            assert isinstance(result, Path)
            assert str(result) == "/tmp/test-vault"

    def test_get_vault_path_missing_env_raises(self) -> None:
        """get_vault_path raises ValueError when env var is missing."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="OBSIDIAN_VAULT_PATH"):
                get_vault_path()

    def test_safe_html_escapes_angle_brackets(self) -> None:
        """safe_html escapes HTML special characters."""
        result = safe_html("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_safe_html_escapes_ampersand(self) -> None:
        """safe_html escapes ampersands."""
        result = safe_html("foo & bar")
        assert "&amp;" in result

    def test_safe_html_preserves_normal_text(self) -> None:
        """safe_html preserves text without special characters."""
        result = safe_html("Hello World 123")
        assert result == "Hello World 123"

    def test_safe_html_escapes_quotes(self) -> None:
        """safe_html escapes quotation marks."""
        result = safe_html('value="test"')
        assert '"' not in result or "&quot;" in result
