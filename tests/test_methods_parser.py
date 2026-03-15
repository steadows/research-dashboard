"""Tests for methods_parser — Methods to Try parsing."""

from pathlib import Path

from utils.methods_parser import parse_methods


class TestParseMethods:
    """Tests for parse_methods()."""

    def test_parses_valid_sections(self, tmp_vault: Path) -> None:
        """Parses ## sections into structured method items."""
        methods = parse_methods(tmp_vault)
        assert len(methods) == 2
        graph_rag = next(m for m in methods if m["name"] == "Graph RAG for Code Search")
        assert graph_rag["source"] == "JournalClub 2026-03-07"
        assert graph_rag["status"] == "New"
        assert "Axon" in graph_rag["projects"]

    def test_missing_fields_have_defaults(self, tmp_vault: Path) -> None:
        """Methods with missing optional fields get sensible defaults."""
        methods = parse_methods(tmp_vault)
        for method in methods:
            assert "name" in method
            assert "status" in method
            assert "projects" in method

    def test_empty_file_returns_empty(self, empty_vault: Path) -> None:
        """Returns empty list when Methods to Try.md is missing."""
        result = parse_methods(empty_vault)
        assert result == []

    def test_file_with_no_sections(self, tmp_path: Path) -> None:
        """File with only a title and no ## sections returns empty."""
        research_dir = tmp_path / "Research"
        research_dir.mkdir(parents=True)
        (research_dir / "Methods to Try.md").write_text(
            "# Methods to Try\n\nNothing here.\n"
        )
        result = parse_methods(tmp_path)
        assert result == []
