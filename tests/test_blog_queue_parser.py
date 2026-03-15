"""Tests for blog_queue_parser — Blog Queue parsing."""

from pathlib import Path

from utils.blog_queue_parser import parse_blog_queue


class TestParseBlogQueue:
    """Tests for parse_blog_queue()."""

    def test_parses_full_entries(self, tmp_vault: Path) -> None:
        """Parses ## sections with all fields."""
        items = parse_blog_queue(tmp_vault)
        assert len(items) == 2
        axon_post = next(
            i for i in items if i["name"] == "Building a Code Knowledge Graph"
        )
        assert axon_post["status"] == "Draft"
        assert axon_post["target"] == "Dev.to"
        assert "Axon" in axon_post["projects"]

    def test_partial_entry_has_defaults(self, tmp_path: Path) -> None:
        """Entries missing optional fields get defaults."""
        writing_dir = tmp_path / "Writing"
        writing_dir.mkdir(parents=True)
        (writing_dir / "Blog Queue.md").write_text(
            "# Blog Queue\n\n## Quick Idea\n**Status:** Idea\n"
        )
        items = parse_blog_queue(tmp_path)
        assert len(items) == 1
        assert items[0]["name"] == "Quick Idea"
        assert items[0]["projects"] == []
        assert items[0].get("target", "") == ""

    def test_empty_queue_returns_empty(self, empty_vault: Path) -> None:
        """Returns empty list when Blog Queue.md is missing."""
        result = parse_blog_queue(empty_vault)
        assert result == []
