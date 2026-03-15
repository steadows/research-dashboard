"""Tests for vault_parser — project parsing, wiki-links, project index."""

from pathlib import Path

from utils.vault_parser import build_project_index, parse_projects, parse_wiki_links


class TestParseProjects:
    """Tests for parse_projects()."""

    def test_parses_projects_with_frontmatter(self, tmp_vault: Path) -> None:
        """Projects with YAML frontmatter extract status, domain, tech."""
        projects = parse_projects(tmp_vault)
        wm = next(p for p in projects if p["name"] == "Wealth Manager")
        assert wm["status"] == "active"
        assert wm["domain"] == "Native Apps"
        assert "SwiftUI" in wm["tech"]

    def test_parses_projects_without_frontmatter(self, tmp_vault: Path) -> None:
        """Projects without frontmatter extract inline metadata."""
        projects = parse_projects(tmp_vault)
        axon = next(p for p in projects if p["name"] == "Axon")
        assert axon["name"] == "Axon"

    def test_returns_empty_for_missing_dir(self, tmp_path: Path) -> None:
        """Returns empty list when Projects/ directory is missing."""
        result = parse_projects(tmp_path)
        assert result == []

    def test_returns_empty_for_empty_dir(self, empty_vault: Path) -> None:
        """Returns empty list when Projects/ has no .md files."""
        result = parse_projects(empty_vault)
        assert result == []

    def test_output_is_immutable(self, tmp_vault: Path) -> None:
        """Returned dicts should be independent copies — mutation doesn't affect source."""
        projects_a = parse_projects(tmp_vault)
        projects_b = parse_projects(tmp_vault)
        projects_a[0]["name"] = "MUTATED"
        assert projects_b[0]["name"] != "MUTATED"


class TestParseWikiLinks:
    """Tests for parse_wiki_links()."""

    def test_extracts_wiki_links(self) -> None:
        """Extracts [[Link]] patterns from text."""
        text = "Uses [[Axon]] and [[Wealth Manager]] for analysis."
        links = parse_wiki_links(text)
        assert links == ["Axon", "Wealth Manager"]

    def test_no_links_returns_empty(self) -> None:
        """Returns empty list when no wiki-links present."""
        assert parse_wiki_links("No links here.") == []

    def test_deduplicates_links(self) -> None:
        """Duplicate wiki-links are deduplicated."""
        text = "[[Axon]] and [[Axon]] again."
        links = parse_wiki_links(text)
        assert links == ["Axon"]


class TestBuildProjectIndex:
    """Tests for build_project_index()."""

    def test_indexes_methods_and_tools_by_project(self, tmp_vault: Path) -> None:
        """Methods and tools tagged with [[Project]] appear in that project's index."""
        index = build_project_index(tmp_vault)
        assert "Axon" in index
        axon_items = index["Axon"]
        names = [item["name"] for item in axon_items]
        assert "Graph RAG for Code Search" in names
        assert "Cursor Tab" in names

    def test_empty_vault_returns_empty_index(self, empty_vault: Path) -> None:
        """Empty vault produces empty project index."""
        index = build_project_index(empty_vault)
        assert index == {}
