"""Tests for workbench_tracker — workbench JSON state CRUD with atomic writes."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from utils.workbench_tracker import (
    add_to_workbench,
    get_slug,
    get_workbench_item,
    get_workbench_items,
    make_item_key,
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
        add_to_workbench(tool, workbench_file=wb_file)

        items = get_workbench_items(wb_file)
        assert "tool::Cursor Tab" in items

        entry = items["tool::Cursor Tab"]
        assert entry["item"] == tool
        assert entry["source_type"] == "tool"
        assert entry["source_item_id"] == "tool::Cursor Tab"
        assert entry["previous_status"] == "new"
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
        add_to_workbench(tool, workbench_file=wb_file)

        # Modify the tool and re-add — original should be preserved
        tool_v2 = {**tool, "category": "Changed"}
        add_to_workbench(tool_v2, workbench_file=wb_file)

        entry = get_workbench_item("tool::Cursor Tab", wb_file)
        assert entry is not None
        assert entry["item"]["category"] == "IDE"  # Original preserved

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        """Add creates the parent directory if missing."""
        wb_file = tmp_path / "nested" / "deep" / "workbench.json"
        add_to_workbench(_sample_tool(), workbench_file=wb_file)
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
        add_to_workbench(_sample_tool("Tool A"), workbench_file=wb_file)
        add_to_workbench(_sample_tool("Tool B"), workbench_file=wb_file)
        items = get_workbench_items(wb_file)
        assert len(items) == 2
        assert "tool::Tool A" in items
        assert "tool::Tool B" in items


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
        add_to_workbench(_sample_tool(), workbench_file=wb_file)
        result = get_workbench_item("tool::Cursor Tab", wb_file)
        assert result is not None
        assert result["item"]["name"] == "Cursor Tab"


class TestUpdateWorkbenchItem:
    """Tests for update_workbench_item."""

    def test_merges_partial_updates(self, tmp_path: Path) -> None:
        """Update merges fields without clobbering unrelated keys."""
        wb_file = tmp_path / "workbench.json"
        add_to_workbench(_sample_tool(), workbench_file=wb_file)

        update_workbench_item(
            "tool::Cursor Tab", {"status": "researching", "pid": 12345}, wb_file
        )

        entry = get_workbench_item("tool::Cursor Tab", wb_file)
        assert entry is not None
        assert entry["status"] == "researching"
        assert entry["pid"] == 12345
        # Unrelated fields preserved
        assert entry["item"]["name"] == "Cursor Tab"
        assert entry["reviewed"] is False

    def test_update_unknown_is_noop(self, tmp_path: Path) -> None:
        """Updating a non-existent item does nothing (no error)."""
        wb_file = tmp_path / "workbench.json"
        # Should not raise
        update_workbench_item("tool::Ghost Tool", {"status": "researching"}, wb_file)
        assert get_workbench_item("tool::Ghost Tool", wb_file) is None

    def test_rejects_disallowed_fields(self, tmp_path: Path) -> None:
        """Update raises ValueError for fields not in the allowlist."""
        wb_file = tmp_path / "workbench.json"
        add_to_workbench(_sample_tool(), workbench_file=wb_file)
        with pytest.raises(ValueError, match="Disallowed"):
            update_workbench_item("tool::Cursor Tab", {"evil_field": "bad"}, wb_file)


class TestRemoveFromWorkbench:
    """Tests for remove_from_workbench."""

    def test_removes_existing_item(self, tmp_path: Path) -> None:
        """Remove deletes the item from workbench."""
        wb_file = tmp_path / "workbench.json"
        status_file = tmp_path / "status.json"
        add_to_workbench(_sample_tool(), workbench_file=wb_file)
        remove_from_workbench(
            "tool::Cursor Tab", workbench_file=wb_file, status_file=status_file
        )
        assert get_workbench_item("tool::Cursor Tab", wb_file) is None

    def test_idempotent_on_missing(self, tmp_path: Path) -> None:
        """Remove on a non-existent key does not raise."""
        wb_file = tmp_path / "workbench.json"
        status_file = tmp_path / "status.json"
        remove_from_workbench(
            "tool::Ghost Tool", workbench_file=wb_file, status_file=status_file
        )
        assert get_workbench_items(wb_file) == {}


class TestAtomicWrite:
    """Tests for atomic write safety."""

    def test_no_temp_files_linger(self, tmp_path: Path) -> None:
        """After a successful write, no temp files remain."""
        wb_file = tmp_path / "workbench.json"
        add_to_workbench(_sample_tool(), workbench_file=wb_file)
        temp_files = list(tmp_path.glob("*.tmp"))
        assert temp_files == []

    def test_partial_write_does_not_corrupt(self, tmp_path: Path) -> None:
        """Simulated crash during write preserves existing file."""
        wb_file = tmp_path / "workbench.json"
        add_to_workbench(_sample_tool("Original"), workbench_file=wb_file)

        # Simulate crash during json.dump by making os.replace fail
        with patch("utils.workbench_tracker.os.replace", side_effect=OSError("crash")):
            try:
                add_to_workbench(_sample_tool("Crasher"), workbench_file=wb_file)
            except OSError:
                pass

        # Original data should still be intact
        items = get_workbench_items(wb_file)
        assert "tool::Original" in items
        assert "tool::Crasher" not in items


# ===========================================================================
# Session 9: Methods workbench — namespaced keys + generalized schema
# ===========================================================================


def _sample_method(
    name: str = "Graph RAG", source: str = "JournalClub 2026-03-07"
) -> dict:
    """Return a minimal method dict matching methods_parser output."""
    return {
        "name": name,
        "source": source,
        "source_type": "method",
        "status": "New",
        "why it matters": "Combines graph structure with RAG for better retrieval.",
        "projects": ["Research Intelligence Dashboard"],
    }


class TestMakeItemKey:
    """Tests for make_item_key helper."""

    def test_tool_key(self) -> None:
        assert make_item_key("tool", "Cursor Tab") == "tool::Cursor Tab"

    def test_method_key(self) -> None:
        assert make_item_key("method", "Graph RAG") == "method::Graph RAG"


class TestNamespacedKeys:
    """Tests for namespaced key format in add/get/remove."""

    def test_add_method_creates_namespaced_key(self, tmp_path: Path) -> None:
        """add_to_workbench creates key like 'method::Graph RAG' for methods."""
        wb_file = tmp_path / "workbench.json"
        method = _sample_method()
        add_to_workbench(method, workbench_file=wb_file)

        items = get_workbench_items(wb_file)
        assert "method::Graph RAG" in items

    def test_add_tool_creates_namespaced_key(self, tmp_path: Path) -> None:
        """add_to_workbench creates key like 'tool::Cursor Tab' for tools."""
        wb_file = tmp_path / "workbench.json"
        tool = _sample_tool()
        add_to_workbench(tool, workbench_file=wb_file)

        items = get_workbench_items(wb_file)
        assert "tool::Cursor Tab" in items

    def test_tool_and_method_same_name_coexist(self, tmp_path: Path) -> None:
        """Tool and method with the same name don't collide."""
        wb_file = tmp_path / "workbench.json"
        tool = _sample_tool("Overlap")
        method = _sample_method("Overlap")
        add_to_workbench(tool, workbench_file=wb_file)
        add_to_workbench(method, workbench_file=wb_file)

        items = get_workbench_items(wb_file)
        assert "tool::Overlap" in items
        assert "method::Overlap" in items
        assert len(items) == 2

    def test_get_with_full_key(self, tmp_path: Path) -> None:
        """get_workbench_item with full namespaced key returns correct entry."""
        wb_file = tmp_path / "workbench.json"
        add_to_workbench(_sample_method(), workbench_file=wb_file)

        entry = get_workbench_item("method::Graph RAG", wb_file)
        assert entry is not None
        assert entry["item"]["name"] == "Graph RAG"


class TestGeneralizedSchema:
    """Tests for the item/source_type/provenance fields."""

    def test_entry_has_item_field(self, tmp_path: Path) -> None:
        """New entries use 'item' field (not 'tool')."""
        wb_file = tmp_path / "workbench.json"
        add_to_workbench(_sample_method(), workbench_file=wb_file)

        entry = get_workbench_item("method::Graph RAG", wb_file)
        assert "item" in entry
        assert "tool" not in entry

    def test_entry_has_source_type(self, tmp_path: Path) -> None:
        """Entries store source_type at top level."""
        wb_file = tmp_path / "workbench.json"
        add_to_workbench(_sample_method(), workbench_file=wb_file)

        entry = get_workbench_item("method::Graph RAG", wb_file)
        assert entry["source_type"] == "method"

    def test_entry_stores_source_item_id(self, tmp_path: Path) -> None:
        """Entries store source_item_id for status restore."""
        wb_file = tmp_path / "workbench.json"
        add_to_workbench(_sample_method(), workbench_file=wb_file)

        entry = get_workbench_item("method::Graph RAG", wb_file)
        assert entry["source_item_id"] == "method::Graph RAG"

    def test_entry_stores_previous_status(self, tmp_path: Path) -> None:
        """Entries store previous_status passed at add time."""
        wb_file = tmp_path / "workbench.json"
        add_to_workbench(
            _sample_method(), previous_status="reviewed", workbench_file=wb_file
        )

        entry = get_workbench_item("method::Graph RAG", wb_file)
        assert entry["previous_status"] == "reviewed"

    def test_default_previous_status_is_new(self, tmp_path: Path) -> None:
        """previous_status defaults to 'new' when not specified."""
        wb_file = tmp_path / "workbench.json"
        add_to_workbench(_sample_method(), workbench_file=wb_file)

        entry = get_workbench_item("method::Graph RAG", wb_file)
        assert entry["previous_status"] == "new"


class TestProvenanceImmutability:
    """Tests that source_item_id and previous_status cannot be mutated."""

    def test_update_rejects_source_item_id(self, tmp_path: Path) -> None:
        """update_workbench_item rejects source_item_id."""
        wb_file = tmp_path / "workbench.json"
        add_to_workbench(_sample_tool(), workbench_file=wb_file)

        with pytest.raises(ValueError, match="Disallowed"):
            update_workbench_item(
                "tool::Cursor Tab", {"source_item_id": "hacked"}, wb_file
            )

    def test_update_rejects_previous_status(self, tmp_path: Path) -> None:
        """update_workbench_item rejects previous_status."""
        wb_file = tmp_path / "workbench.json"
        add_to_workbench(_sample_tool(), workbench_file=wb_file)

        with pytest.raises(ValueError, match="Disallowed"):
            update_workbench_item(
                "tool::Cursor Tab", {"previous_status": "hacked"}, wb_file
            )


class TestRemoveRestoresStatus:
    """Tests that remove_from_workbench restores source status."""

    def test_restores_previous_status(self, tmp_path: Path) -> None:
        """Remove restores the source item's status to previous_status."""
        wb_file = tmp_path / "workbench.json"
        status_file = tmp_path / "status.json"

        # Set up source status
        status_file.write_text(
            json.dumps({"items": {"method::Graph RAG": "workbench"}, "cache": {}}),
            encoding="utf-8",
        )

        add_to_workbench(
            _sample_method(),
            previous_status="reviewed",
            workbench_file=wb_file,
        )

        remove_from_workbench(
            "method::Graph RAG",
            workbench_file=wb_file,
            status_file=status_file,
        )

        # Workbench item gone
        assert get_workbench_item("method::Graph RAG", wb_file) is None

        # Source status restored
        status_data = json.loads(status_file.read_text(encoding="utf-8"))
        assert status_data["items"]["method::Graph RAG"] == "reviewed"


class TestLegacyCompat:
    """Tests for backward compatibility with legacy bare-name keys."""

    def test_legacy_bare_key_normalised_on_load(self, tmp_path: Path) -> None:
        """Legacy entries with bare keys and 'tool' field are readable."""
        wb_file = tmp_path / "workbench.json"
        legacy_data = {
            "Cursor Tab": {
                "tool": _sample_tool(),
                "added": "2026-03-15",
                "status": "queued",
                "experiment_type": None,
                "sandbox_dir": None,
                "vault_note": None,
                "pid": None,
                "log_file": None,
                "reviewed": False,
            }
        }
        wb_file.write_text(json.dumps(legacy_data), encoding="utf-8")

        items = get_workbench_items(wb_file)
        # Legacy key should be normalised to tool:: prefix
        assert "tool::Cursor Tab" in items
        # 'tool' field should be normalised to 'item'
        entry = items["tool::Cursor Tab"]
        assert "item" in entry
        assert entry["item"]["name"] == "Cursor Tab"

    def test_bare_name_lookup_returns_entry_when_unambiguous(
        self, tmp_path: Path
    ) -> None:
        """Bare-name lookup returns the entry when only one source type matches."""
        wb_file = tmp_path / "workbench.json"
        add_to_workbench(_sample_tool(), workbench_file=wb_file)

        # Bare name lookup (legacy shim)
        entry = get_workbench_item("Cursor Tab", wb_file)
        assert entry is not None
        assert entry["item"]["name"] == "Cursor Tab"

    def test_bare_name_lookup_returns_none_when_ambiguous(self, tmp_path: Path) -> None:
        """Bare-name lookup returns None when tool+method share a name."""
        wb_file = tmp_path / "workbench.json"
        add_to_workbench(_sample_tool("Overlap"), workbench_file=wb_file)
        add_to_workbench(_sample_method("Overlap"), workbench_file=wb_file)

        entry = get_workbench_item("Overlap", wb_file)
        assert entry is None


class TestGetSlugNamespaced:
    """Tests for get_slug with source_type prefix."""

    def test_tool_slug(self) -> None:
        assert get_slug("Cursor Tab", "tool") == "tool-cursor-tab"

    def test_method_slug(self) -> None:
        assert get_slug("Graph RAG", "method") == "method-graph-rag"

    def test_default_source_type_is_tool(self) -> None:
        assert get_slug("Cursor Tab") == "tool-cursor-tab"
