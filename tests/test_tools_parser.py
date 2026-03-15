"""Tests for tools_parser — Tools Radar parsing."""

from pathlib import Path

from utils.tools_parser import parse_tools


class TestParseTools:
    """Tests for parse_tools()."""

    def test_parses_valid_entries(self, tmp_vault: Path) -> None:
        """Parses ## sections into structured tool items."""
        tools = parse_tools(tmp_vault)
        assert len(tools) == 2
        cursor = next(t for t in tools if t["name"] == "Cursor Tab")
        assert cursor["category"] == "IDE"
        assert cursor["source"] == "TLDR 2026-03-07"
        assert "Axon" in cursor["projects"]

    def test_missing_category_defaults(self, tmp_path: Path) -> None:
        """Tools without a Category field get 'Uncategorized'."""
        research_dir = tmp_path / "Research"
        research_dir.mkdir(parents=True)
        (research_dir / "Tools Radar.md").write_text(
            "# Tools Radar\n\n"
            "## MysteryTool\n"
            "**Source:** TLDR 2026-01-01\n"
            "**What it does:** Unknown.\n"
        )
        tools = parse_tools(tmp_path)
        assert tools[0]["category"] == "Uncategorized"

    def test_unknown_project_links_preserved(self, tmp_vault: Path) -> None:
        """Project links reference names that may not exist as project files."""
        tools = parse_tools(tmp_vault)
        valkey = next(t for t in tools if t["name"] == "Valkey")
        assert "DinnerBot" in valkey["projects"]

    def test_empty_file_returns_empty(self, empty_vault: Path) -> None:
        """Returns empty list when Tools Radar.md is missing."""
        result = parse_tools(empty_vault)
        assert result == []
