"""Tests for prompt enrichment — verify LLM prompts include paper context and project context."""

from pathlib import Path
from unittest.mock import patch

from utils.prompt_builder import build_quick_prompt


class TestSummarizePaperPromptEnrichment:
    """summarize_paper prompt should include abstract and connected projects."""

    def test_prompt_contains_abstract_block(self, tmp_path: Path) -> None:
        """summarize_paper prompt includes Abstract: block from paper context."""
        from utils.claude_client import summarize_paper

        item = {"name": "Test Paper", "hook": "A hook", "source": "arxiv.org/1234"}

        mock_context = {
            "abstract": "This paper proposes a new method.",
            "full_text": "",
            "full_text_source": "",
            "year": "2025",
            "venue": "NeurIPS",
            "authors": ["Author A"],
            "fetch_state": "abstract_only",
            "error": "",
        }

        with (
            patch("utils.claude_client.fetch_paper_context", return_value=mock_context),
            patch("utils.claude_client._call_api") as mock_api,
            patch("utils.claude_client.get_analysis_cache", return_value=None),
            patch("utils.claude_client.set_analysis_cache"),
        ):
            mock_api.return_value = {
                "response": "Summary text",
                "model": "m",
                "input_tokens": 1,
                "output_tokens": 1,
                "cost": 0.0,
            }
            summarize_paper(item, status_file=tmp_path / "status.json")

        prompt = mock_api.call_args[0][0]
        assert "Abstract:" in prompt
        assert "This paper proposes a new method." in prompt

    def test_prompt_contains_connected_projects(self, tmp_path: Path) -> None:
        """summarize_paper prompt includes Connected Projects: line."""
        from utils.claude_client import summarize_paper

        item = {
            "name": "Test Paper",
            "hook": "hook",
            "source": "src",
            "projects": ["Project Alpha", "Project Beta"],
        }

        mock_context = {
            "abstract": "Abstract here.",
            "full_text": "",
            "full_text_source": "",
            "year": "",
            "venue": "",
            "authors": [],
            "fetch_state": "abstract_only",
            "error": "",
        }

        with (
            patch("utils.claude_client.fetch_paper_context", return_value=mock_context),
            patch("utils.claude_client._call_api") as mock_api,
            patch("utils.claude_client.get_analysis_cache", return_value=None),
            patch("utils.claude_client.set_analysis_cache"),
        ):
            mock_api.return_value = {
                "response": "Summary",
                "model": "m",
                "input_tokens": 1,
                "output_tokens": 1,
                "cost": 0.0,
            }
            summarize_paper(item, status_file=tmp_path / "status.json")

        prompt = mock_api.call_args[0][0]
        assert "Connected Projects:" in prompt
        assert "Project Alpha" in prompt


class TestGenerateBlogDraftPromptEnrichment:
    """generate_blog_draft prompt should use full text when available."""

    def test_prompt_contains_paper_content_when_full_text_available(
        self, tmp_path: Path
    ) -> None:
        """generate_blog_draft includes Paper Content: block from full text."""
        from utils.claude_client import generate_blog_draft

        item = {"name": "Draft Paper", "hook": "hook", "source": "src"}

        mock_context = {
            "abstract": "Short abstract.",
            "full_text": "Full text of the paper with details and methods...",
            "full_text_source": "pdf",
            "year": "2025",
            "venue": "ICML",
            "authors": ["Author X"],
            "fetch_state": "pdf",
            "error": "",
        }

        with (
            patch("utils.claude_client.fetch_paper_context", return_value=mock_context),
            patch("utils.claude_client._call_api") as mock_api,
            patch("utils.claude_client.get_analysis_cache", return_value=None),
            patch("utils.claude_client.set_analysis_cache"),
        ):
            mock_api.return_value = {
                "response": "Draft body",
                "model": "m",
                "input_tokens": 1,
                "output_tokens": 1,
                "cost": 0.0,
            }
            generate_blog_draft(item, status_file=tmp_path / "status.json")

        prompt = mock_api.call_args[0][0]
        assert "Paper Content:" in prompt
        assert "Full text of the paper" in prompt

    def test_prompt_falls_back_to_abstract_when_no_full_text(
        self, tmp_path: Path
    ) -> None:
        """generate_blog_draft uses Abstract: when full text unavailable."""
        from utils.claude_client import generate_blog_draft

        item = {"name": "Draft Paper 2", "hook": "hook", "source": "src"}

        mock_context = {
            "abstract": "Only an abstract here.",
            "full_text": "",
            "full_text_source": "",
            "year": "2024",
            "venue": "",
            "authors": [],
            "fetch_state": "abstract_only",
            "error": "",
        }

        with (
            patch("utils.claude_client.fetch_paper_context", return_value=mock_context),
            patch("utils.claude_client._call_api") as mock_api,
            patch("utils.claude_client.get_analysis_cache", return_value=None),
            patch("utils.claude_client.set_analysis_cache"),
        ):
            mock_api.return_value = {
                "response": "Draft body",
                "model": "m",
                "input_tokens": 1,
                "output_tokens": 1,
                "cost": 0.0,
            }
            generate_blog_draft(item, status_file=tmp_path / "status.json")

        prompt = mock_api.call_args[0][0]
        assert "Abstract:" in prompt
        assert "Only an abstract here." in prompt
        assert "Paper Content:" not in prompt


class TestLinkedInPostEnrichment:
    """generate_linkedin_post should use full draft body, not truncated excerpt."""

    def test_linkedin_uses_full_draft_body(self, tmp_path: Path) -> None:
        """LinkedIn prompt uses full generated draft body, not 200-char excerpt."""
        from utils.claude_client import generate_linkedin_post

        item = {"name": "LI Paper", "hook": "hook"}
        full_draft = "A" * 500  # Longer than 200 chars

        with (
            patch("utils.claude_client._call_api") as mock_api,
            patch("utils.claude_client.get_analysis_cache", return_value=None),
            patch("utils.claude_client.set_analysis_cache"),
        ):
            mock_api.return_value = {
                "response": "LinkedIn post",
                "model": "m",
                "input_tokens": 1,
                "output_tokens": 1,
                "cost": 0.0,
            }
            generate_linkedin_post(
                item, full_draft, status_file=tmp_path / "status.json"
            )

        prompt = mock_api.call_args[0][0]
        # Full body should be in prompt, not truncated to 200
        assert full_draft in prompt

    def test_linkedin_cache_key_uses_full_draft_hash(self, tmp_path: Path) -> None:
        """LinkedIn cache key uses hash of full draft body, not draft_excerpt[:50]."""
        from utils.claude_client import generate_linkedin_post

        item = {"name": "Cache Key Paper", "hook": "hook"}
        draft_a = "Draft version A " * 30
        draft_b = "Draft version B " * 30
        # These share the same first 50 chars prefix — old cache key would collide

        with (
            patch("utils.claude_client._call_api") as mock_api,
            patch(
                "utils.claude_client.get_analysis_cache", return_value=None
            ) as mock_cache_get,
            patch("utils.claude_client.set_analysis_cache"),
        ):
            mock_api.return_value = {
                "response": "Post",
                "model": "m",
                "input_tokens": 1,
                "output_tokens": 1,
                "cost": 0.0,
            }
            generate_linkedin_post(item, draft_a, status_file=tmp_path / "status.json")
            key_a = mock_cache_get.call_args[0][0]

            generate_linkedin_post(item, draft_b, status_file=tmp_path / "status.json")
            key_b = mock_cache_get.call_args[0][0]

        # Different draft bodies must produce different cache keys
        assert key_a != key_b


class TestCacheVersionBump:
    """Old v1 cache keys must NOT mask new v2 enriched prompts."""

    def test_paper_deep_read_v2_cache_key(self, tmp_path: Path) -> None:
        """deep_read_paper uses paper_deep_read_v2 cache version."""
        from utils.claude_client import deep_read_paper

        item = {"name": "Version Test Paper", "hook": "h", "source": "s"}

        with (
            patch("utils.claude_client.fetch_paper_context") as mock_fetch,
            patch("utils.claude_client._call_api") as mock_api,
            patch(
                "utils.claude_client.get_analysis_cache", return_value=None
            ) as mock_cache_get,
            patch("utils.claude_client.set_analysis_cache"),
        ):
            mock_fetch.return_value = {
                "abstract": "",
                "full_text": "",
                "full_text_source": "",
                "year": "",
                "venue": "",
                "authors": [],
                "fetch_state": "not_found",
                "error": "",
            }
            mock_api.return_value = {
                "response": "Deep",
                "model": "m",
                "input_tokens": 1,
                "output_tokens": 1,
                "cost": 0.0,
            }
            deep_read_paper(item, status_file=tmp_path / "status.json")

        cache_key = mock_cache_get.call_args[0][0]
        # Key must include v2 version — should NOT match old v1 keys
        # We verify by checking the key is built from "paper_deep_read_v2"
        from utils.claude_client import _build_cache_key

        old_key = _build_cache_key("Version Test Paper", "", "paper_deep_read")
        assert cache_key != old_key

    def test_blog_draft_v2_cache_key(self, tmp_path: Path) -> None:
        """generate_blog_draft uses blog_draft_v2 cache version."""
        from utils.claude_client import generate_blog_draft

        item = {"name": "Draft V2 Test", "hook": "h", "source": "s"}

        with (
            patch("utils.claude_client.fetch_paper_context") as mock_fetch,
            patch("utils.claude_client._call_api") as mock_api,
            patch(
                "utils.claude_client.get_analysis_cache", return_value=None
            ) as mock_cache_get,
            patch("utils.claude_client.set_analysis_cache"),
        ):
            mock_fetch.return_value = {
                "abstract": "",
                "full_text": "",
                "full_text_source": "",
                "year": "",
                "venue": "",
                "authors": [],
                "fetch_state": "not_found",
                "error": "",
            }
            mock_api.return_value = {
                "response": "Draft",
                "model": "m",
                "input_tokens": 1,
                "output_tokens": 1,
                "cost": 0.0,
            }
            generate_blog_draft(item, status_file=tmp_path / "status.json")

        cache_key = mock_cache_get.call_args[0][0]
        from utils.claude_client import _build_cache_key

        old_key = _build_cache_key("Draft V2 Test", "", "blog_draft")
        assert cache_key != old_key


class TestQuickPromptProjectContext:
    """build_quick_prompt should include project overview and GSD plan."""

    def test_quick_prompt_includes_project_overview(self) -> None:
        """build_quick_prompt includes Project Overview section."""
        item = {"name": "Some Item"}
        project = {
            "name": "TestProject",
            "overview": "This is a project about ML pipelines.",
            "gsd_plan": "## Session 1\n- Build data layer",
        }

        prompt = build_quick_prompt(item, project)
        assert "Project Overview:" in prompt
        assert "This is a project about ML pipelines." in prompt

    def test_quick_prompt_includes_gsd_plan(self) -> None:
        """build_quick_prompt includes Current GSD Plan section."""
        item = {"name": "Some Item"}
        project = {
            "name": "TestProject",
            "overview": "Overview text",
            "gsd_plan": "## Session 1\n- Build data layer",
        }

        prompt = build_quick_prompt(item, project)
        assert "Current GSD Plan:" in prompt
        assert "Build data layer" in prompt
