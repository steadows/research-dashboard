"""Tests for workbench_tracker — workbench JSON state CRUD with atomic writes."""

from pathlib import Path
from unittest.mock import patch

import pytest

from utils.workbench_tracker import (
    add_to_workbench,
    get_workbench_item,
    get_workbench_items,
    remove_from_workbench,
    update_workbench_item,
)


def _sample_tool(name: str = "Cursor Tab", category: str = "IDE") -> dict:
    """Return a minimal tool dict matching tools_parser output."""
    return {
        "name": name,
        "category": category,
        "source": "TLDR 2026-03-07",
        "source_type": "tool",
        "status": "New",
        "what it does": "AI-powered tab completion.",
        "projects": ["Axon"],
    }


class TestAddToWorkbench:
    """Tests for add_to_workbench."""

    def test_creates_entry_with_correct_schema(self, tmp_path: Path) -> None:
        """Add creates an entry with all required schema fields."""
        wb_file = tmp_path / "workbench.json"
        tool = _sample_tool()
        add_to_workbench(tool, wb_file)

        items = get_workbench_items(wb_file)
        assert "Cursor Tab" in items

        entry = items["Cursor Tab"]
        assert entry["tool"] == tool
        assert entry["status"] == "queued"
        assert entry["experiment_type"] is None
        assert entry["sandbox_dir"] is None
        assert entry["vault_note"] is None
        assert entry["pid"] is None
        assert entry["log_file"] is None
        assert entry["reviewed"] is False
        # ISO date string
        assert len(entry["added"]) == 10  # YYYY-MM-DD

    def test_duplicate_add_is_noop(self, tmp_path: Path) -> None:
        """Adding the same tool twice preserves the original entry."""
        wb_file = tmp_path / "workbench.json"
        tool = _sample_tool()
        add_to_workbench(tool, wb_file)

        # Modify the tool and re-add — original should be preserved
        tool_v2 = {**tool, "category": "Changed"}
        add_to_workbench(tool_v2, wb_file)

        entry = get_workbench_item("Cursor Tab", wb_file)
        assert entry is not None
        assert entry["tool"]["category"] == "IDE"  # Original preserved

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        """Add creates the parent directory if missing."""
        wb_file = tmp_path / "nested" / "deep" / "workbench.json"
        add_to_workbench(_sample_tool(), wb_file)
        assert wb_file.exists()


class TestGetWorkbenchItems:
    """Tests for get_workbench_items."""

    def test_returns_empty_dict_when_file_missing(self, tmp_path: Path) -> None:
        """Returns empty dict when workbench file does not exist."""
        wb_file = tmp_path / "nonexistent.json"
        result = get_workbench_items(wb_file)
        assert result == {}

    def test_returns_empty_dict_on_corrupt_file(self, tmp_path: Path) -> None:
        """Returns empty dict when file contains invalid JSON."""
        wb_file = tmp_path / "workbench.json"
        wb_file.write_text("NOT JSON {{{{")
        result = get_workbench_items(wb_file)
        assert result == {}

    def test_returns_all_items(self, tmp_path: Path) -> None:
        """Returns all added items."""
        wb_file = tmp_path / "workbench.json"
        add_to_workbench(_sample_tool("Tool A"), wb_file)
        add_to_workbench(_sample_tool("Tool B"), wb_file)
        items = get_workbench_items(wb_file)
        assert len(items) == 2
        assert "Tool A" in items
        assert "Tool B" in items


class TestGetWorkbenchItem:
    """Tests for get_workbench_item."""

    def test_returns_none_for_unknown(self, tmp_path: Path) -> None:
        """Returns None for a tool name that isn't in the workbench."""
        wb_file = tmp_path / "workbench.json"
        result = get_workbench_item("Unknown Tool", wb_file)
        assert result is None

    def test_returns_entry_for_known(self, tmp_path: Path) -> None:
        """Returns the entry dict for a known tool name."""
        wb_file = tmp_path / "workbench.json"
        add_to_workbench(_sample_tool(), wb_file)
        result = get_workbench_item("Cursor Tab", wb_file)
        assert result is not None
        assert result["tool"]["name"] == "Cursor Tab"


class TestUpdateWorkbenchItem:
    """Tests for update_workbench_item."""

    def test_merges_partial_updates(self, tmp_path: Path) -> None:
        """Update merges fields without clobbering unrelated keys."""
        wb_file = tmp_path / "workbench.json"
        add_to_workbench(_sample_tool(), wb_file)

        update_workbench_item(
            "Cursor Tab", {"status": "researching", "pid": 12345}, wb_file
        )

        entry = get_workbench_item("Cursor Tab", wb_file)
        assert entry is not None
        assert entry["status"] == "researching"
        assert entry["pid"] == 12345
        # Unrelated fields preserved
        assert entry["tool"]["name"] == "Cursor Tab"
        assert entry["reviewed"] is False

    def test_update_unknown_is_noop(self, tmp_path: Path) -> None:
        """Updating a non-existent item does nothing (no error)."""
        wb_file = tmp_path / "workbench.json"
        # Should not raise
        update_workbench_item("Ghost Tool", {"status": "researching"}, wb_file)
        assert get_workbench_item("Ghost Tool", wb_file) is None

    def test_rejects_disallowed_fields(self, tmp_path: Path) -> None:
        """Update raises ValueError for fields not in the allowlist."""
        wb_file = tmp_path / "workbench.json"
        add_to_workbench(_sample_tool(), wb_file)
        with pytest.raises(ValueError, match="Disallowed"):
            update_workbench_item("Cursor Tab", {"evil_field": "bad"}, wb_file)


class TestRemoveFromWorkbench:
    """Tests for remove_from_workbench."""

    def test_removes_existing_item(self, tmp_path: Path) -> None:
        """Remove deletes the item from workbench."""
        wb_file = tmp_path / "workbench.json"
        add_to_workbench(_sample_tool(), wb_file)
        remove_from_workbench("Cursor Tab", wb_file)
        assert get_workbench_item("Cursor Tab", wb_file) is None

    def test_idempotent_on_missing(self, tmp_path: Path) -> None:
        """Remove on a non-existent key does not raise."""
        wb_file = tmp_path / "workbench.json"
        remove_from_workbench("Ghost Tool", wb_file)
        assert get_workbench_items(wb_file) == {}


class TestAtomicWrite:
    """Tests for atomic write safety."""

    def test_no_temp_files_linger(self, tmp_path: Path) -> None:
        """After a successful write, no temp files remain."""
        wb_file = tmp_path / "workbench.json"
        add_to_workbench(_sample_tool(), wb_file)
        temp_files = list(tmp_path.glob("*.tmp"))
        assert temp_files == []

    def test_partial_write_does_not_corrupt(self, tmp_path: Path) -> None:
        """Simulated crash during write preserves existing file."""
        wb_file = tmp_path / "workbench.json"
        add_to_workbench(_sample_tool("Original"), wb_file)

        # Simulate crash during json.dump by making os.replace fail
        with patch("utils.workbench_tracker.os.replace", side_effect=OSError("crash")):
            try:
                add_to_workbench(_sample_tool("Crasher"), wb_file)
            except OSError:
                pass

        # Original data should still be intact
        items = get_workbench_items(wb_file)
        assert "Original" in items
        assert "Crasher" not in items
