"""Tests for page_helpers split — pure functions stay, Streamlit functions move."""

import importlib
import sys


class TestPageHelpersPure:
    """page_helpers.py should contain only pure functions (no Streamlit imports)."""

    def test_no_streamlit_import_at_module_level(self) -> None:
        """page_helpers.py should not import streamlit at module level."""
        mod_name = "utils.page_helpers"
        if mod_name in sys.modules:
            del sys.modules[mod_name]

        st_backup = sys.modules.pop("streamlit", None)
        try:
            mod = importlib.import_module(mod_name)
            assert hasattr(mod, "get_vault_path")
            assert hasattr(mod, "safe_html")
            assert hasattr(mod, "safe_parse")
            assert hasattr(mod, "strip_wiki_links")
            assert hasattr(mod, "get_category_color")
        finally:
            if st_backup is not None:
                sys.modules["streamlit"] = st_backup
            if mod_name in sys.modules:
                del sys.modules[mod_name]
            importlib.import_module(mod_name)

    def test_render_context_sources_not_in_page_helpers(self) -> None:
        """render_context_sources should NOT be in page_helpers after split."""
        from utils import page_helpers

        assert not hasattr(page_helpers, "render_context_sources")


class TestStreamlitRemoved:
    """page_helpers_st.py should no longer exist after Streamlit deprecation."""

    def test_page_helpers_st_removed(self) -> None:
        """page_helpers_st module should not be importable."""
        with __import__("pytest").raises(ModuleNotFoundError):
            importlib.import_module("utils.page_helpers_st")
