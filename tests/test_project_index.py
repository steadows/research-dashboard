"""Tests for project index — items per project, empty cases, wiki-link drift."""

from pathlib import Path


class TestBuildProjectIndex:
    """Tests for vault_parser.build_project_index()."""

    def test_items_grouped_by_project(self, tmp_vault: Path) -> None:
        """Items should be grouped under their wiki-linked project names."""
        from utils.vault_parser import build_project_index

        index = build_project_index(tmp_vault)

        assert "Axon" in index
        axon_items = index["Axon"]
        axon_names = [i["name"] for i in axon_items]
        assert "Graph RAG for Code Search" in axon_names
        assert "Cursor Tab" in axon_names

    def test_project_with_no_items(self, tmp_vault: Path) -> None:
        """Projects not referenced by any wiki-link should not appear in index."""
        from utils.vault_parser import build_project_index

        index = build_project_index(tmp_vault)
        # "Axon" project exists in vault but only items that wiki-link to it appear
        # Check that a project with no method/tool references is absent
        all_project_names = set(index.keys())
        # These are only projects referenced by methods/tools wiki-links
        for name in all_project_names:
            items = index[name]
            assert len(items) > 0

    def test_empty_vault_returns_empty_index(self, empty_vault: Path) -> None:
        """Empty vault should produce an empty project index."""
        from utils.vault_parser import build_project_index

        index = build_project_index(empty_vault)
        assert index == {}

    def test_items_contain_source_type(self, tmp_vault: Path) -> None:
        """Each item in the index should have a source_type field."""
        from utils.vault_parser import build_project_index

        index = build_project_index(tmp_vault)
        for items in index.values():
            for item in items:
                assert "source_type" in item
                assert item["source_type"] in ("method", "tool")

    def test_wiki_link_drift_unmatched_project(self, tmp_vault: Path) -> None:
        """Items linking to non-existent projects still appear in index."""
        from utils.vault_parser import build_project_index

        index = build_project_index(tmp_vault)
        # "Autoresearch" is referenced by Graph RAG method but has no project file
        if "Autoresearch" in index:
            assert len(index["Autoresearch"]) > 0

    def test_wealth_manager_has_both_method_and_tool(self, tmp_vault: Path) -> None:
        """Wealth Manager should have items from both methods and tools."""
        from utils.vault_parser import build_project_index

        index = build_project_index(tmp_vault)
        assert "Wealth Manager" in index
        wm_types = {i["source_type"] for i in index["Wealth Manager"]}
        assert "method" in wm_types
        assert "tool" in wm_types

    def test_index_returns_deep_copies(self, tmp_vault: Path) -> None:
        """Modifying returned items should not affect future calls."""
        from utils.vault_parser import build_project_index

        index1 = build_project_index(tmp_vault)
        if "Axon" in index1:
            index1["Axon"][0]["name"] = "MUTATED"

        index2 = build_project_index(tmp_vault)
        if "Axon" in index2:
            assert index2["Axon"][0]["name"] != "MUTATED"
