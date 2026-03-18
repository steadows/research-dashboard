"""Tests for instagram_parser — vault Instagram note parsing."""

from pathlib import Path

import pytest


# --- Fixtures ---


@pytest.fixture
def ig_vault(tmp_path: Path) -> Path:
    """Create a vault with Instagram notes for testing."""
    ig_dir = tmp_path / "Research" / "Instagram" / "testaccount"
    ig_dir.mkdir(parents=True)

    (ig_dir / "2026-03-15-ABC123.md").write_text(
        "---\n"
        "title: Building AI Agents\n"
        "tags:\n  - instagram\n  - ai\n"
        "date: '2026-03-15'\n"
        "account: testaccount\n"
        "shortcode: ABC123\n"
        "source_url: https://instagram.com/p/ABC123\n"
        "---\n\n"
        "## Caption\n"
        "Check out this amazing demo!\n\n"
        "## Key Points\n"
        "- Agents can reason autonomously\n"
        "- Tool use enables real-world actions\n"
        "- Cost is dropping fast\n\n"
        "## Keywords\n"
        "[[Claude Code]], AI, agents\n\n"
        "## Transcript\n"
        "Welcome to the demo. Today we're going to look at AI agents.\n"
    )

    (ig_dir / "2026-03-10-DEF456.md").write_text(
        "---\n"
        "title: Whisper Tips\n"
        "tags:\n  - instagram\n  - ml\n"
        "date: '2026-03-10'\n"
        "account: testaccount\n"
        "shortcode: DEF456\n"
        "source_url: https://instagram.com/p/DEF456\n"
        "---\n\n"
        "## Caption\n"
        "Whisper transcription tricks.\n\n"
        "## Key Points\n"
        "- Use base model for speed\n"
        "- int8 quantization works great\n\n"
        "## Keywords\n"
        "whisper, transcription, ML\n\n"
        "## Transcript\n"
        "Let me show you some tips for using Whisper.\n"
    )

    # Second account
    ig_dir2 = tmp_path / "Research" / "Instagram" / "otheraccount"
    ig_dir2.mkdir(parents=True)

    (ig_dir2 / "2026-03-12-GHI789.md").write_text(
        "---\n"
        "title: Other Account Post\n"
        "tags:\n  - instagram\n"
        "date: '2026-03-12'\n"
        "account: otheraccount\n"
        "shortcode: GHI789\n"
        "source_url: https://instagram.com/p/GHI789\n"
        "---\n\n"
        "## Caption\n"
        "Different account content.\n\n"
        "## Key Points\n"
        "- A point\n\n"
        "## Keywords\n"
        "misc\n\n"
        "## Transcript\n"
        "Other account transcript.\n"
    )

    return tmp_path


# --- Tests ---


class TestParseInstagramPosts:
    """Tests for parse_instagram_posts — parsing, filtering, error handling."""

    def test_empty_when_dir_missing(self, tmp_path: Path) -> None:
        """Returns empty list when Research/Instagram/ does not exist."""
        from utils.instagram_parser import parse_instagram_posts

        result = parse_instagram_posts(tmp_path)
        assert result == []

    def test_parses_yaml_frontmatter(self, ig_vault: Path) -> None:
        """Parses title, account, date, shortcode, source_url from frontmatter."""
        from utils.instagram_parser import parse_instagram_posts

        posts = parse_instagram_posts(ig_vault)
        abc = next(p for p in posts if p["shortcode"] == "ABC123")

        assert abc["name"] == "Building AI Agents"
        assert abc["account"] == "testaccount"
        assert abc["date"] == "2026-03-15"
        assert abc["source_url"] == "https://instagram.com/p/ABC123"

    def test_uses_title_as_name(self, ig_vault: Path) -> None:
        """name field comes from frontmatter title."""
        from utils.instagram_parser import parse_instagram_posts

        posts = parse_instagram_posts(ig_vault)
        abc = next(p for p in posts if p["shortcode"] == "ABC123")
        assert abc["name"] == "Building AI Agents"

    def test_falls_back_to_file_stem(self, tmp_path: Path) -> None:
        """Falls back to file.stem when title is missing from frontmatter."""
        ig_dir = tmp_path / "Research" / "Instagram" / "user"
        ig_dir.mkdir(parents=True)

        (ig_dir / "2026-03-15-NOTITLE.md").write_text(
            "---\n"
            "tags:\n  - instagram\n"
            "date: '2026-03-15'\n"
            "account: user\n"
            "shortcode: NOTITLE\n"
            "---\n\n"
            "## Caption\n"
            "Some content.\n\n"
            "## Key Points\n\n"
            "## Keywords\n\n"
            "## Transcript\n"
            "Transcript.\n"
        )

        from utils.instagram_parser import parse_instagram_posts

        posts = parse_instagram_posts(tmp_path)
        assert posts[0]["name"] == "2026-03-15-NOTITLE"

    def test_parses_key_points(self, ig_vault: Path) -> None:
        """Parses ## Key Points bullets into key_points list."""
        from utils.instagram_parser import parse_instagram_posts

        posts = parse_instagram_posts(ig_vault)
        abc = next(p for p in posts if p["shortcode"] == "ABC123")

        assert len(abc["key_points"]) == 3
        assert "Agents can reason autonomously" in abc["key_points"]

    def test_parses_keywords_strips_wiki_links(self, ig_vault: Path) -> None:
        """Parses ## Keywords line, strips [[ and ]]."""
        from utils.instagram_parser import parse_instagram_posts

        posts = parse_instagram_posts(ig_vault)
        abc = next(p for p in posts if p["shortcode"] == "ABC123")

        assert "Claude Code" in abc["keywords"]
        assert "AI" in abc["keywords"]
        assert "agents" in abc["keywords"]
        # No raw wiki-link brackets
        assert not any("[[" in k for k in abc["keywords"])

    def test_captures_caption_and_transcript(self, ig_vault: Path) -> None:
        """Captures ## Caption and ## Transcript as plain strings."""
        from utils.instagram_parser import parse_instagram_posts

        posts = parse_instagram_posts(ig_vault)
        abc = next(p for p in posts if p["shortcode"] == "ABC123")

        assert "amazing demo" in abc["caption"]
        assert "AI agents" in abc["transcript"]

    def test_sets_source_type(self, ig_vault: Path) -> None:
        """Every returned dict has source_type = 'instagram'."""
        from utils.instagram_parser import parse_instagram_posts

        posts = parse_instagram_posts(ig_vault)
        assert all(p["source_type"] == "instagram" for p in posts)

    def test_filters_by_accounts(self, ig_vault: Path) -> None:
        """When accounts provided, only those accounts are included."""
        from utils.instagram_parser import parse_instagram_posts

        posts = parse_instagram_posts(ig_vault, accounts=["testaccount"])

        assert all(p["account"] == "testaccount" for p in posts)
        assert len(posts) == 2

    def test_tolerates_malformed_file(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Malformed file is skipped with WARNING log, not raised."""
        ig_dir = tmp_path / "Research" / "Instagram" / "bad"
        ig_dir.mkdir(parents=True)

        (ig_dir / "2026-03-15-BAD.md").write_text(
            "NOT YAML FRONTMATTER\njust random text"
        )

        from utils.instagram_parser import parse_instagram_posts

        import logging

        with caplog.at_level(logging.WARNING):
            posts = parse_instagram_posts(tmp_path)

        assert len(posts) == 0
        assert any(
            "malformed" in r.message.lower() or "skipping" in r.message.lower()
            for r in caplog.records
        )

    def test_sorted_by_date_descending(self, ig_vault: Path) -> None:
        """Results are sorted by date descending (newest first)."""
        from utils.instagram_parser import parse_instagram_posts

        posts = parse_instagram_posts(ig_vault)
        dates = [p["date"] for p in posts]

        assert dates == sorted(dates, reverse=True)


class TestRoundTrip:
    """Round-trip: write_vault_note output → parse_instagram_posts → fields match."""

    def test_roundtrip_fields_match(self, tmp_path: Path) -> None:
        """Fields written by write_vault_note are correctly parsed back."""
        post = {
            "shortcode": "RT1",
            "username": "rtuser",
            "date": "2026-03-15",
            "caption": "Round trip caption",
            "url": "https://instagram.com/p/RT1",
        }
        extracted = {
            "title": "Round Trip Title",
            "key_points": ["First point", "Second point"],
            "keywords": ["[[Axon]]", "testing", "AI"],
        }
        transcript = "This is the full transcript for round trip testing."

        from utils.instagram_ingester import write_vault_note
        from utils.instagram_parser import parse_instagram_posts

        from unittest.mock import patch as mock_patch

        with mock_patch("utils.instagram_ingester.os.replace") as mock_replace:
            mock_replace.side_effect = lambda src, dst: Path(src).rename(dst)
            write_vault_note(post, transcript, extracted, tmp_path)

        posts = parse_instagram_posts(tmp_path)
        assert len(posts) == 1

        parsed = posts[0]
        assert parsed["name"] == "Round Trip Title"
        assert parsed["account"] == "rtuser"
        assert parsed["date"] == "2026-03-15"
        assert parsed["shortcode"] == "RT1"
        assert parsed["source_url"] == "https://instagram.com/p/RT1"
        assert "First point" in parsed["key_points"]
        assert "Second point" in parsed["key_points"]
        assert "Axon" in parsed["keywords"]
        assert "testing" in parsed["keywords"]
        assert "Round trip caption" in parsed["caption"]
        assert "round trip testing" in parsed["transcript"]
        assert parsed["source_type"] == "instagram"
