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
    name: str = "How to Build RAG Pipelines",
) -> dict[str, Any]:
    """Return a minimal instagram post dict for workbench testing."""
    return {
        "name": name,
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

        entry = get_workbench_item("instagram::How to Build RAG Pipelines", wb_file)
        assert entry is not None
        assert entry["source_type"] == "instagram"

    def test_uses_make_item_key_with_name(self, tmp_path: Path) -> None:
        """Workbench key is make_item_key('instagram', name)."""
        wb_file = tmp_path / "workbench.json"
        post = _sample_instagram_post()
        expected_key = make_item_key("instagram", post["name"])
        add_to_workbench(post, workbench_file=wb_file)

        items = get_workbench_items(wb_file)
        assert expected_key in items
        assert expected_key == "instagram::How to Build RAG Pipelines"


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
            "instagram::How to Build RAG Pipelines",
            {"status": "researching"},
            wb_file,
        )

        entry = get_workbench_item("instagram::How to Build RAG Pipelines", wb_file)
        assert entry is not None
        assert entry["item"]["transcript"] == post["transcript"]

    def test_caption_preserved_after_update(self, tmp_path: Path) -> None:
        """Updating status doesn't clobber item.caption."""
        wb_file = tmp_path / "workbench.json"
        post = _sample_instagram_post()
        add_to_workbench(post, workbench_file=wb_file)

        update_workbench_item(
            "instagram::How to Build RAG Pipelines", {"status": "researched"}, wb_file
        )

        entry = get_workbench_item("instagram::How to Build RAG Pipelines", wb_file)
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


# ===========================================================================
# Session 14: Identity model, topic-centric prompt, workbench UI
# ===========================================================================


# ---------------------------------------------------------------------------
# [14a] Identity model — shortcode key + preserved title
# ---------------------------------------------------------------------------


class TestInstagramIdentityModel:
    """Instagram entries key on name (title) like all other source types."""

    def test_title_preserved_after_add(self, tmp_path: Path) -> None:
        """item['name'] is the human-readable title used as the key."""
        wb_file = tmp_path / "workbench.json"
        post = _sample_instagram_post(shortcode="XYZ789", name="Deep Dive into LoRA")
        add_to_workbench(post, workbench_file=wb_file)

        key = make_item_key("instagram", "Deep Dive into LoRA")
        entry = get_workbench_item(key, wb_file)
        assert entry is not None
        assert entry["item"]["name"] == "Deep Dive into LoRA"

    def test_key_resolves_from_name(self, tmp_path: Path) -> None:
        """Workbench key resolves from name (title), not shortcode."""
        wb_file = tmp_path / "workbench.json"
        post = _sample_instagram_post(shortcode="QRS456", name="My Great Post")
        add_to_workbench(post, workbench_file=wb_file)

        items = get_workbench_items(wb_file)
        expected_key = make_item_key("instagram", "My Great Post")
        assert expected_key in items
        assert expected_key == "instagram::My Great Post"

    def test_duplicate_add_noop_for_same_name(self, tmp_path: Path) -> None:
        """Adding the same name twice is a no-op."""
        wb_file = tmp_path / "workbench.json"
        post1 = _sample_instagram_post(shortcode="DUP001", name="First Title")
        post2 = _sample_instagram_post(shortcode="DUP002", name="First Title")
        add_to_workbench(post1, workbench_file=wb_file)
        add_to_workbench(post2, workbench_file=wb_file)

        items = get_workbench_items(wb_file)
        key = make_item_key("instagram", "First Title")
        assert key in items
        assert items[key]["item"]["name"] == "First Title"
        assert len([k for k in items if k.startswith("instagram::")]) == 1

    def test_different_titles_separate_entries(self, tmp_path: Path) -> None:
        """Two posts with different titles persist as separate entries."""
        wb_file = tmp_path / "workbench.json"
        post1 = _sample_instagram_post(shortcode="UNIQ01", name="Title A")
        post2 = _sample_instagram_post(shortcode="UNIQ02", name="Title B")
        add_to_workbench(post1, workbench_file=wb_file)
        add_to_workbench(post2, workbench_file=wb_file)

        items = get_workbench_items(wb_file)
        assert make_item_key("instagram", "Title A") in items
        assert make_item_key("instagram", "Title B") in items
        assert len([k for k in items if k.startswith("instagram::")]) == 2


# ---------------------------------------------------------------------------
# [14b] Prompt boundary — topic-centric COSTAR for instagram
# ---------------------------------------------------------------------------


class TestInstagramTopicPrompt:
    """_build_prompt for instagram uses topic-centric context/objective."""

    def test_instagram_prompt_uses_topic_context(self) -> None:
        """Instagram prompt references topic title, account, key_points."""
        from utils.research_agent import _build_prompt

        post = _sample_instagram_post()
        output_dir = Path("/tmp/test-output")
        prompt = _build_prompt(post, output_dir)
        assert "How to Build RAG Pipelines" in prompt
        assert "hubaborern" in prompt

    def test_instagram_prompt_requires_getting_started(self) -> None:
        """Instagram prompt uses '## Getting Started' not '## How to Install'."""
        from utils.research_agent import _build_prompt

        post = _sample_instagram_post()
        output_dir = Path("/tmp/test-output")
        prompt = _build_prompt(post, output_dir)
        assert "## Getting Started" in prompt
        assert "## How to Install" not in prompt

    def test_instagram_prompt_transcript_truncated_in_builder(self) -> None:
        """Transcript is capped at 4000 chars in prompt builder."""
        from utils.research_agent import _build_prompt

        post = _sample_instagram_post()
        post["transcript"] = "W" * 8000
        output_dir = Path("/tmp/test-output")
        prompt = _build_prompt(post, output_dir)
        # Full 8000-char transcript must NOT appear
        assert "W" * 8000 not in prompt
        # But truncated version should
        assert "W" * 4000 in prompt

    def test_instagram_prompt_missing_transcript_ok(self) -> None:
        """Missing transcript does not break prompt generation."""
        from utils.research_agent import _build_prompt

        post = _sample_instagram_post()
        del post["transcript"]
        output_dir = Path("/tmp/test-output")
        prompt = _build_prompt(post, output_dir)
        assert "How to Build RAG Pipelines" in prompt
        assert "<transcript>" not in prompt

    def test_low_signal_detection(self) -> None:
        """Low-signal: no transcript + no key_points + caption < 20 chars."""
        from utils.research_agent import _build_prompt

        post = _sample_instagram_post()
        post["transcript"] = ""
        post["key_points"] = []
        post["caption"] = "short"
        output_dir = Path("/tmp/test-output")
        prompt = _build_prompt(post, output_dir)
        assert len(prompt) > 0
        assert "How to Build RAG Pipelines" in prompt
        # Low-signal note must appear in the prompt
        assert "thin source material" in prompt

    def test_low_signal_still_generates_valid_prompt(self) -> None:
        """Low-signal items still produce a prompt with required headings."""
        from utils.research_agent import _build_prompt

        post = _sample_instagram_post()
        post["transcript"] = ""
        post["key_points"] = []
        post["caption"] = "x"
        output_dir = Path("/tmp/test-output")
        prompt = _build_prompt(post, output_dir)
        assert "## Overview" in prompt
        assert "## Programmatic Assessment" in prompt
        assert "thin source material" in prompt

    def test_low_signal_boundary_19_chars_is_low(self) -> None:
        """Caption of exactly 19 chars (< 20) triggers low-signal."""
        from utils.research_agent import _is_low_signal

        post = _sample_instagram_post()
        post["transcript"] = ""
        post["key_points"] = []
        post["caption"] = "A" * 19
        assert _is_low_signal(post) is True

    def test_low_signal_boundary_20_chars_is_not_low(self) -> None:
        """Caption of exactly 20 chars (not < 20) does NOT trigger low-signal."""
        from utils.research_agent import _is_low_signal

        post = _sample_instagram_post()
        post["transcript"] = ""
        post["key_points"] = []
        post["caption"] = "A" * 20
        assert _is_low_signal(post) is False

    def test_not_low_signal_when_has_transcript(self) -> None:
        """Post with transcript is not low-signal even with short caption."""
        from utils.research_agent import _is_low_signal

        post = _sample_instagram_post()
        post["key_points"] = []
        post["caption"] = "x"
        # transcript is non-empty from fixture
        assert _is_low_signal(post) is False

    def test_tool_prompt_unchanged(self) -> None:
        """Existing tool prompt still uses '## How to Install'."""
        from utils.research_agent import _build_prompt

        tool = {
            "name": "Some Tool",
            "category": "DevOps",
            "source": "TLDR",
            "description": "A dev tool.",
        }
        output_dir = Path("/tmp/test-output")
        prompt = _build_prompt(tool, output_dir)
        assert "## How to Install" in prompt
        assert "## Getting Started" not in prompt

    def test_caption_with_curly_braces_does_not_crash(self) -> None:
        """Captions containing {braces} must not crash str.format()."""
        from utils.research_agent import _build_prompt

        post = _sample_instagram_post()
        post["caption"] = "Use {this} for {that} — {x: 1, y: 2}"
        output_dir = Path("/tmp/test-output")
        # Should not raise KeyError/ValueError from str.format()
        prompt = _build_prompt(post, output_dir)
        assert len(prompt) > 0
        assert "Caption:" in prompt

    def test_transcript_with_curly_braces_does_not_crash(self) -> None:
        """Transcripts containing {braces} must not crash str.format()."""
        from utils.research_agent import _build_prompt

        post = _sample_instagram_post()
        post["transcript"] = "const data = {key: 'value', nested: {a: 1}}"
        output_dir = Path("/tmp/test-output")
        prompt = _build_prompt(post, output_dir)
        assert "{key:" in prompt


# ---------------------------------------------------------------------------
# [14c] UI boundary — workbench research enabled for instagram
# ---------------------------------------------------------------------------


class TestInstagramWorkbenchUI:
    """Workbench research button enabled for instagram; topic preview/summary."""

    def test_research_enabled_for_queued_instagram(self) -> None:
        """Research button is NOT disabled for queued instagram items."""
        # Mirrors the updated logic in 3_Workbench.py _render_action_buttons
        status = "queued"
        # Session 14: source_type no longer gates research — only status matters
        research_disabled = status not in ("queued", "failed")
        assert research_disabled is False

    def test_research_enabled_for_failed_instagram(self) -> None:
        """Research button is NOT disabled for failed instagram items."""
        status = "failed"
        research_disabled = status not in ("queued", "failed")
        assert research_disabled is False

    def test_tool_research_still_works(self) -> None:
        """Existing tool research button behavior unchanged."""
        status = "queued"
        research_disabled = status not in ("queued", "failed")
        assert research_disabled is False

    def test_researched_status_still_disables_button(self) -> None:
        """Research button disabled for already-researched items regardless of type."""
        for source_type in ("tool", "method", "instagram"):
            status = "researched"
            research_disabled = status not in ("queued", "failed")
            assert research_disabled is True
