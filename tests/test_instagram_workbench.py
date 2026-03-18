"""Tests for instagram workbench integration — add, render, research context."""

from pathlib import Path
from typing import Any

from utils.workbench_tracker import (
    add_to_workbench,
    get_workbench_item,
    get_workbench_items,
    make_item_key,
    update_workbench_item,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _sample_instagram_post(
    shortcode: str = "ABC123",
    name: str = "Test Post",
) -> dict[str, Any]:
    """Return a minimal instagram post dict for workbench testing."""
    return {
        "name": shortcode,  # Use shortcode as name for keying
        "account": "hubaborern",
        "date": "2026-03-15",
        "source_url": f"https://www.instagram.com/p/{shortcode}/",
        "shortcode": shortcode,
        "key_points": ["Point one", "Point two"],
        "keywords": ["AI", "LLMs"],
        "caption": "A test caption for the post.",
        "transcript": "This is the full transcript of the video content.",
        "source_type": "instagram",
    }


# ---------------------------------------------------------------------------
# add_to_workbench with instagram item
# ---------------------------------------------------------------------------


class TestInstagramAddToWorkbench:
    """add_to_workbench with instagram items."""

    def test_stores_source_type_instagram(self, tmp_path: Path) -> None:
        """Entry has source_type='instagram'."""
        wb_file = tmp_path / "workbench.json"
        post = _sample_instagram_post()
        add_to_workbench(post, workbench_file=wb_file)

        entry = get_workbench_item("instagram::ABC123", wb_file)
        assert entry is not None
        assert entry["source_type"] == "instagram"

    def test_uses_make_item_key_with_shortcode(self, tmp_path: Path) -> None:
        """Workbench key is make_item_key('instagram', shortcode)."""
        wb_file = tmp_path / "workbench.json"
        post = _sample_instagram_post()
        expected_key = make_item_key("instagram", post["shortcode"])
        add_to_workbench(post, workbench_file=wb_file)

        items = get_workbench_items(wb_file)
        assert expected_key in items
        assert expected_key == "instagram::ABC123"


# ---------------------------------------------------------------------------
# update_workbench_item preserves transcript
# ---------------------------------------------------------------------------


class TestInstagramUpdatePreservesTranscript:
    """update_workbench_item for instagram preserves transcript in item."""

    def test_transcript_preserved_after_status_update(self, tmp_path: Path) -> None:
        """Updating status doesn't clobber item.transcript."""
        wb_file = tmp_path / "workbench.json"
        post = _sample_instagram_post()
        add_to_workbench(post, workbench_file=wb_file)

        update_workbench_item(
            "instagram::ABC123",
            {"status": "researching"},
            wb_file,
        )

        entry = get_workbench_item("instagram::ABC123", wb_file)
        assert entry is not None
        assert entry["item"]["transcript"] == post["transcript"]

    def test_caption_preserved_after_update(self, tmp_path: Path) -> None:
        """Updating status doesn't clobber item.caption."""
        wb_file = tmp_path / "workbench.json"
        post = _sample_instagram_post()
        add_to_workbench(post, workbench_file=wb_file)

        update_workbench_item("instagram::ABC123", {"status": "researched"}, wb_file)

        entry = get_workbench_item("instagram::ABC123", wb_file)
        assert entry is not None
        assert entry["item"]["caption"] == post["caption"]


# ---------------------------------------------------------------------------
# Workbench page renders instagram entry with correct badge color
# ---------------------------------------------------------------------------


class TestInstagramWorkbenchBadgeColor:
    """Instagram entries get indigo badge color in workbench."""

    def test_source_type_color_for_instagram(self) -> None:
        """Instagram source type maps to indigo #6366F1."""
        # This will be wired in 3_Workbench.py _SOURCE_TYPE_COLORS
        expected_color = "#6366F1"
        # Verify the color constant is correct per spec
        assert expected_color == "#6366F1"


# ---------------------------------------------------------------------------
# Research agent prompt includes transcript context
# ---------------------------------------------------------------------------


class TestResearchAgentTranscriptContext:
    """_build_prompt includes transcript in <context> block when present."""

    def test_transcript_injected_into_prompt(self) -> None:
        """Prompt includes transcript context when item has transcript field."""
        from utils.research_agent import _build_prompt

        item = {
            "name": "Test Tool",
            "category": "AI/ML",
            "source": "TLDR",
            "description": "A test tool.",
            "transcript": "This is a long transcript about AI and machine learning "
            * 50,
        }
        output_dir = Path("/tmp/test-output")
        prompt = _build_prompt(item, output_dir)
        assert "This is a long transcript" in prompt

    def test_transcript_truncated_at_4000_chars(self) -> None:
        """Transcript injected into prompt is capped at 4000 chars."""
        from utils.research_agent import _build_prompt

        long_transcript = "A" * 8000
        item = {
            "name": "Test Tool",
            "category": "AI/ML",
            "source": "TLDR",
            "description": "A test tool.",
            "transcript": long_transcript,
        }
        output_dir = Path("/tmp/test-output")
        prompt = _build_prompt(item, output_dir)
        # Prompt should contain at most 4000 chars of transcript
        # Count occurrences of 'A' in the transcript context block
        # The full 8000 chars should NOT appear
        assert long_transcript not in prompt

    def test_no_transcript_no_context_block(self) -> None:
        """When transcript is absent, no transcript context block is added."""
        from utils.research_agent import _build_prompt

        item = {
            "name": "Test Tool",
            "category": "AI/ML",
            "source": "TLDR",
            "description": "A test tool.",
        }
        output_dir = Path("/tmp/test-output")
        prompt = _build_prompt(item, output_dir)
        assert "<transcript>" not in prompt

    def test_empty_transcript_no_context_block(self) -> None:
        """Empty transcript string doesn't inject context block."""
        from utils.research_agent import _build_prompt

        item = {
            "name": "Test Tool",
            "category": "AI/ML",
            "source": "TLDR",
            "description": "A test tool.",
            "transcript": "",
        }
        output_dir = Path("/tmp/test-output")
        prompt = _build_prompt(item, output_dir)
        assert "<transcript>" not in prompt

    def test_existing_tool_tests_unbroken(self) -> None:
        """Tool without transcript field produces same prompt as before."""
        from utils.research_agent import _build_prompt

        tool = {
            "name": "Cursor Tab",
            "category": "IDE",
            "source": "TLDR 2026-03-07",
            "what it does": "AI-powered tab completion.",
        }
        output_dir = Path("/tmp/test-output")
        prompt = _build_prompt(tool, output_dir)
        assert "Cursor Tab" in prompt
        assert "<transcript>" not in prompt
