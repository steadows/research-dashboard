"""Tests for status_tracker — status persistence and analysis cache."""

import json
from pathlib import Path

from utils.status_tracker import (
    get_analysis_cache,
    get_item_status,
    load_status,
    save_status,
    set_analysis_cache,
    set_item_status,
)


class TestLoadSave:
    """Tests for load/save roundtrip."""

    def test_roundtrip(self, tmp_path: Path) -> None:
        """Save then load returns the same data."""
        status_file = tmp_path / "status.json"
        data = {"items": {"item1": "reviewed"}, "cache": {}}
        save_status(data, status_file)
        loaded = load_status(status_file)
        assert loaded == data

    def test_load_missing_file_returns_default(self, tmp_path: Path) -> None:
        """Loading a nonexistent file returns default structure."""
        status_file = tmp_path / "nonexistent.json"
        result = load_status(status_file)
        assert "items" in result
        assert "cache" in result

    def test_corrupt_file_resets(self, tmp_path: Path) -> None:
        """Corrupt JSON resets to default with a warning log."""
        status_file = tmp_path / "status.json"
        status_file.write_text("NOT VALID JSON {{{")
        result = load_status(status_file)
        assert result == {"items": {}, "cache": {}}

    def test_atomic_write_safety(self, tmp_path: Path) -> None:
        """Save writes atomically — no partial writes on crash."""
        status_file = tmp_path / "status.json"
        data = {"items": {"x": "new"}, "cache": {}}
        save_status(data, status_file)
        # Verify the file exists and is valid JSON
        content = json.loads(status_file.read_text())
        assert content == data
        # Verify no temp files linger
        temp_files = list(tmp_path.glob("*.tmp"))
        assert temp_files == []


class TestItemStatus:
    """Tests for get/set item status."""

    def test_get_set_status(self, tmp_path: Path) -> None:
        """Set then get returns the status."""
        status_file = tmp_path / "status.json"
        set_item_status("method::Graph RAG", "reviewed", status_file)
        result = get_item_status("method::Graph RAG", status_file)
        assert result == "reviewed"

    def test_get_unknown_returns_new(self, tmp_path: Path) -> None:
        """Unknown items return 'new' as default status."""
        status_file = tmp_path / "status.json"
        result = get_item_status("nonexistent", status_file)
        assert result == "new"


class TestAnalysisCache:
    """Tests for analysis cache get/set."""

    def test_cache_miss_returns_none(self, tmp_path: Path) -> None:
        """Cache miss returns None."""
        status_file = tmp_path / "status.json"
        result = get_analysis_cache("key1", status_file)
        assert result is None

    def test_cache_hit_returns_data(self, tmp_path: Path) -> None:
        """Set then get returns cached analysis."""
        status_file = tmp_path / "status.json"
        set_analysis_cache("key1", {"result": "analysis text"}, status_file)
        result = get_analysis_cache("key1", status_file)
        assert result == {"result": "analysis text"}
