"""Idempotency and edge-case tests for knowledge_linker.inject_wiki_links().

These tests verify that the linker can be run multiple times safely and that
it does not corrupt code blocks, existing wiki-links, custom-label wiki-links,
or markdown links.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from utils.knowledge_linker import (
    build_entity_index,
    inject_wiki_links,
    link_directory,
    link_note,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def entities() -> dict[str, str]:
    """Minimal entity index for testing."""
    return {
        "axon": "Axon",
        "fastapi": "FastAPI",
        "react native": "React Native",
        "graphrag": "GraphRAG",
        "swiftui": "SwiftUI",
    }


@pytest.fixture
def vault_with_notes(tmp_path: Path) -> Path:
    """Create a temporary vault with project files and linkable notes."""
    # Projects (entity source)
    projects = tmp_path / "Projects"
    projects.mkdir()
    (projects / "Axon.md").write_text("# Axon\nDeveloper tool.\n")
    (projects / "FastAPI.md").write_text("# FastAPI\nWeb framework.\n")

    # Target directory with linkable content
    journal = tmp_path / "Dev Journal"
    journal.mkdir()
    (journal / "2026-03-27.md").write_text(
        "---\ntitle: Today\n---\n\nWorked on Axon today. Also explored FastAPI.\n"
    )
    return tmp_path


# ---------------------------------------------------------------------------
# Idempotency: double-run produces zero new modifications
# ---------------------------------------------------------------------------


class TestIdempotency:
    """Running the linker twice should produce no changes on the second pass."""

    def test_inject_wiki_links_double_run(self, entities: dict[str, str]) -> None:
        """Injecting wiki-links into already-linked text produces no changes."""
        text = "I used Axon and FastAPI for this project."
        first_pass = inject_wiki_links(text, entities)
        second_pass = inject_wiki_links(first_pass, entities)
        assert second_pass == first_pass, (
            "Second pass should produce identical output — no double-linking"
        )

    def test_link_note_double_run(self, vault_with_notes: Path, tmp_path: Path) -> None:
        """link_note returns False on second call (no modifications)."""
        entities = build_entity_index(vault_with_notes)
        note = vault_with_notes / "Dev Journal" / "2026-03-27.md"

        first = link_note(note, entities)
        assert first is True, "First pass should modify the file"

        second = link_note(note, entities)
        assert second is False, "Second pass should find nothing to change"

    def test_link_directory_double_run(self, vault_with_notes: Path) -> None:
        """link_directory returns 0 on second call (all files already linked)."""
        journal = vault_with_notes / "Dev Journal"

        first = link_directory(vault_with_notes, journal)
        assert first >= 1, "First pass should modify at least one file"

        second = link_directory(vault_with_notes, journal)
        assert second == 0, "Second pass should modify zero files"


# ---------------------------------------------------------------------------
# Code blocks: entities inside backticks must NOT be linked
# ---------------------------------------------------------------------------


class TestCodeBlocks:
    """Entities inside inline code or fenced code blocks must not be linked."""

    def test_inline_code_not_linked(self, entities: dict[str, str]) -> None:
        """Entity inside `backticks` should not be replaced."""
        text = "Use `Axon` to build the graph."
        result = inject_wiki_links(text, entities)
        assert "[[Axon]]" not in result, (
            "Entity inside inline code should not be wiki-linked"
        )
        assert "`Axon`" in result

    def test_fenced_code_block_not_linked(self, entities: dict[str, str]) -> None:
        """Entity inside a fenced code block should not be replaced."""
        text = (
            "Example:\n"
            "```python\n"
            "from axon import GraphRAG\n"
            "```\n"
            "That was Axon in action.\n"
        )
        result = inject_wiki_links(text, entities)
        # The fenced block mention should be untouched
        assert "from axon import GraphRAG" in result, (
            "Code block content should not be modified"
        )
        # But the prose mention SHOULD be linked
        assert "[[Axon]]" in result


# ---------------------------------------------------------------------------
# Existing wiki-links: must not double-bracket
# ---------------------------------------------------------------------------


class TestExistingWikiLinks:
    """Already-linked entities must not be re-linked or double-bracketed."""

    def test_existing_wiki_link_not_doubled(self, entities: dict[str, str]) -> None:
        """[[Axon]] should not become [[[[Axon]]]]."""
        text = "I already linked [[Axon]] in this note."
        result = inject_wiki_links(text, entities)
        assert "[[[[" not in result, "Must not produce double brackets"
        assert result.count("[[Axon]]") == 1

    def test_custom_label_wiki_link_not_corrupted(
        self, entities: dict[str, str]
    ) -> None:
        """[[Axon|my custom label]] should not be re-linked or corrupted."""
        text = "See [[Axon|my custom label]] for details."
        result = inject_wiki_links(text, entities)
        assert "[[Axon|my custom label]]" in result, (
            "Custom-label wiki-link should be preserved exactly"
        )
        # Should not add a second [[Axon]] link
        assert result.count("[[") == 1


# ---------------------------------------------------------------------------
# Markdown links: entity names inside [text](url) must not be linked
# ---------------------------------------------------------------------------


class TestMarkdownLinks:
    """Entity names inside standard markdown links must not be corrupted."""

    def test_markdown_link_text_not_linked(self, entities: dict[str, str]) -> None:
        """[Axon](https://example.com) should not be corrupted."""
        text = "Check out [Axon](https://example.com) for more."
        result = inject_wiki_links(text, entities)
        assert "[Axon](https://example.com)" in result, (
            "Markdown link should be preserved"
        )
        # Should not inject a wiki-link inside the markdown link
        assert "[[Axon]](https://example.com)" not in result

    def test_markdown_link_url_not_linked(self, entities: dict[str, str]) -> None:
        """Entity name appearing in a URL path should not be linked."""
        text = "Visit [docs](https://example.com/axon/setup) for setup."
        result = inject_wiki_links(text, entities)
        assert "https://example.com/axon/setup" in result, "URL should not be modified"


# ---------------------------------------------------------------------------
# Partial failure + retry safety
# ---------------------------------------------------------------------------


class TestPartialFailureRetry:
    """Vault remains consistent after a partial failure and retry."""

    def test_partial_directory_failure_then_retry(self, vault_with_notes: Path) -> None:
        """If link_directory fails mid-way, a retry produces a consistent vault."""
        journal = vault_with_notes / "Dev Journal"

        # Add a second note
        (journal / "2026-03-28.md").write_text("Explored GraphRAG patterns today.\n")

        # Patch link_note to raise on the second file only once
        call_count = {"n": 0}
        real_link_note = link_note

        def _flaky_link_note(fp: Path, ents: dict[str, str]) -> bool:
            call_count["n"] += 1
            if fp.name == "2026-03-28.md" and call_count["n"] <= 2:
                raise OSError("Simulated disk error")
            return real_link_note(fp, ents)

        with patch("utils.knowledge_linker.link_note", side_effect=_flaky_link_note):
            first_result = link_directory(vault_with_notes, journal)

        # First note should be linked, second should have failed
        assert first_result >= 1

        # Retry — should succeed and be idempotent on already-linked files
        second_result = link_directory(vault_with_notes, journal)
        assert second_result >= 1, "Retry should link the previously-failed file"

        # Third run — everything already linked
        third_result = link_directory(vault_with_notes, journal)
        assert third_result == 0, "Third pass should find nothing to change"
