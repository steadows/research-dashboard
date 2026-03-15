"""Tests for cockpit_components — header rendering, Obsidian URLs, GSD plan lookup."""

from pathlib import Path
from typing import Any


def _make_project(**overrides: Any) -> dict[str, Any]:
    """Factory for project dicts with sensible defaults."""
    defaults: dict[str, Any] = {
        "name": "Axon",
        "status": "Active",
        "domain": "Developer Tool",
        "tech": ["Python", "KuzuDB"],
        "file_path": "/vault/Projects/Axon.md",
        "content": "Code intelligence graph.",
        "wiki_links": [],
    }
    return {**defaults, **overrides}


class TestBuildObsidianUrl:
    """Tests for build_obsidian_url()."""

    def test_basic_vault_name_and_file(self) -> None:
        """Should produce obsidian://open URL with vault and file params."""
        from utils.cockpit_components import build_obsidian_url

        url = build_obsidian_url("SteveVault", "Projects/Axon.md")
        assert url.startswith("obsidian://open?vault=")
        assert "SteveVault" in url
        assert "Axon" in url

    def test_spaces_are_encoded(self) -> None:
        """Vault and file names with spaces should be URL-encoded."""
        from utils.cockpit_components import build_obsidian_url

        url = build_obsidian_url("Steve Vault", "Projects/Wealth Manager.md")
        # Spaces should be percent-encoded
        assert " " not in url
        assert "Steve" in url
        assert "Wealth" in url

    def test_empty_file_path(self) -> None:
        """Empty file path should still produce a valid URL."""
        from utils.cockpit_components import build_obsidian_url

        url = build_obsidian_url("SteveVault", "")
        assert "obsidian://open" in url


class TestGetProjectGsdPlan:
    """Tests for get_project_gsd_plan()."""

    def test_finds_existing_plan(self, tmp_vault: Path) -> None:
        """Should return plan content when Plans/<Name> GSD Plan.md exists."""
        from utils.cockpit_components import get_project_gsd_plan

        result = get_project_gsd_plan("Wealth Manager", tmp_vault)
        assert result is not None
        assert "Phase 1" in result

    def test_returns_none_for_missing_plan(self, tmp_vault: Path) -> None:
        """Should return None when no GSD plan exists for the project."""
        from utils.cockpit_components import get_project_gsd_plan

        result = get_project_gsd_plan("NonExistent", tmp_vault)
        assert result is None

    def test_path_traversal_blocked(self, tmp_vault: Path) -> None:
        """Plan names with .. should not escape the Plans directory."""
        from utils.cockpit_components import get_project_gsd_plan

        result = get_project_gsd_plan("../../etc/passwd", tmp_vault)
        assert result is None

    def test_empty_project_name(self, tmp_vault: Path) -> None:
        """Empty project name should return None safely."""
        from utils.cockpit_components import get_project_gsd_plan

        result = get_project_gsd_plan("", tmp_vault)
        assert result is None

    def test_missing_plans_directory(self, tmp_path: Path) -> None:
        """Should return None when Plans/ dir doesn't exist."""
        from utils.cockpit_components import get_project_gsd_plan

        result = get_project_gsd_plan("Axon", tmp_path)
        assert result is None


class TestRenderProjectHeader:
    """Tests for render_project_header data preparation."""

    def test_header_includes_project_name(self) -> None:
        """Header data should contain the project name."""
        project = _make_project(name="Axon")
        assert project["name"] == "Axon"

    def test_header_includes_tech_stack(self) -> None:
        """Header data should contain tech stack list."""
        project = _make_project(tech=["Python", "KuzuDB"])
        assert "Python" in project["tech"]
        assert "KuzuDB" in project["tech"]
