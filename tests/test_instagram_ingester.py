"""Tests for instagram_ingester — Instagram video ingestion pipeline."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# --- Helpers ---


def _make_post(
    shortcode: str = "ABC123",
    is_video: bool = True,
    days_ago: int = 3,
    caption: str = "Check out Claude Code!",
) -> MagicMock:
    """Build a mock instaloader Post object."""
    post = MagicMock()
    post.shortcode = shortcode
    post.is_video = is_video
    post.video_url = f"https://example.com/video/{shortcode}.mp4"
    post.caption = caption
    post.date_utc = datetime.now(tz=timezone.utc) - timedelta(days=days_ago)
    return post


def _make_profile(posts: list[MagicMock]) -> MagicMock:
    """Build a mock instaloader Profile."""
    profile = MagicMock()
    profile.get_posts.return_value = iter(posts)
    return profile


# --- fetch_recent_posts ---


class TestFetchRecentPosts:
    """Tests for fetch_recent_posts — filtering, state, error handling."""

    @patch("utils.instagram_ingester.time.sleep")
    @patch("utils.instagram_ingester.instaloader")
    def test_returns_only_video_posts(
        self, mock_il: MagicMock, mock_sleep: MagicMock, tmp_path: Path
    ) -> None:
        """Non-video posts are skipped gracefully (no exception)."""
        video = _make_post("VID1", is_video=True)
        image = _make_post("IMG1", is_video=False)
        profile = _make_profile([video, image])

        mock_il.Instaloader.return_value = MagicMock()
        mock_il.Profile.from_username.return_value = profile

        from utils.instagram_ingester import fetch_recent_posts

        state_file = tmp_path / "state.json"
        result = fetch_recent_posts("testuser", days=14, state_file=state_file)

        assert len(result) == 1
        assert result[0]["shortcode"] == "VID1"

    @patch("utils.instagram_ingester.time.sleep")
    @patch("utils.instagram_ingester.instaloader")
    def test_filters_by_days_cutoff(
        self, mock_il: MagicMock, mock_sleep: MagicMock, tmp_path: Path
    ) -> None:
        """Posts older than `days` cutoff are excluded."""
        recent = _make_post("RECENT", days_ago=3)
        old = _make_post("OLD", days_ago=30)
        profile = _make_profile([recent, old])

        mock_il.Instaloader.return_value = MagicMock()
        mock_il.Profile.from_username.return_value = profile

        from utils.instagram_ingester import fetch_recent_posts

        state_file = tmp_path / "state.json"
        result = fetch_recent_posts("testuser", days=14, state_file=state_file)

        assert len(result) == 1
        assert result[0]["shortcode"] == "RECENT"

    @patch("utils.instagram_ingester.time.sleep")
    @patch("utils.instagram_ingester.instaloader")
    def test_skips_shortcodes_in_state(
        self, mock_il: MagicMock, mock_sleep: MagicMock, tmp_path: Path
    ) -> None:
        """Posts already in state file are skipped."""
        post = _make_post("ALREADY_DONE")
        profile = _make_profile([post])

        mock_il.Instaloader.return_value = MagicMock()
        mock_il.Profile.from_username.return_value = profile

        from utils.instagram_ingester import fetch_recent_posts

        state_file = tmp_path / "state.json"
        state_file.write_text(
            json.dumps({"ALREADY_DONE": {"ingested_at": "2026-03-01"}})
        )

        result = fetch_recent_posts("testuser", days=14, state_file=state_file)
        assert len(result) == 0

    @patch("utils.instagram_ingester.time.sleep")
    @patch("utils.instagram_ingester.instaloader")
    def test_logs_warning_for_non_video(
        self,
        mock_il: MagicMock,
        mock_sleep: MagicMock,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Non-video posts should log a WARNING, not raise."""
        image = _make_post("IMG1", is_video=False)
        profile = _make_profile([image])

        mock_il.Instaloader.return_value = MagicMock()
        mock_il.Profile.from_username.return_value = profile

        from utils.instagram_ingester import fetch_recent_posts

        import logging

        with caplog.at_level(logging.WARNING):
            result = fetch_recent_posts(
                "testuser", days=14, state_file=tmp_path / "state.json"
            )

        assert len(result) == 0
        assert any(
            "non-video" in r.message.lower() or "skipping" in r.message.lower()
            for r in caplog.records
        )


# --- download_video ---


class TestDownloadVideo:
    """Tests for download_video — file lifecycle."""

    @patch("utils.instagram_ingester.time.sleep")
    @patch("utils.instagram_ingester.urllib.request.urlretrieve")
    def test_downloads_to_dir(
        self, mock_retrieve: MagicMock, mock_sleep: MagicMock, tmp_path: Path
    ) -> None:
        """Downloads video URL to download_dir and returns local Path."""
        post = {
            "shortcode": "ABC123",
            "url": "https://example.com/video.mp4",
            "username": "test",
        }
        expected = tmp_path / "ABC123.mp4"
        mock_retrieve.return_value = (str(expected), {})
        # Create the file to simulate download
        expected.write_bytes(b"fake video data")

        from utils.instagram_ingester import download_video

        result = download_video(post, tmp_path)
        assert result == expected
        mock_retrieve.assert_called_once()

    @patch("utils.instagram_ingester.time.sleep")
    @patch("utils.instagram_ingester.urllib.request.urlretrieve")
    def test_cleans_partial_on_failure(
        self, mock_retrieve: MagicMock, mock_sleep: MagicMock, tmp_path: Path
    ) -> None:
        """On failure, partial file is deleted and exception re-raised."""
        post = {
            "shortcode": "FAIL1",
            "url": "https://example.com/video.mp4",
            "username": "test",
        }
        target = tmp_path / "FAIL1.mp4"
        # Create a partial file
        target.write_bytes(b"partial")
        mock_retrieve.side_effect = OSError("Network error")

        from utils.instagram_ingester import download_video

        with pytest.raises(OSError, match="Network error"):
            download_video(post, tmp_path)

        assert not target.exists()


# --- transcribe_video ---


class TestTranscribeVideo:
    """Tests for transcribe_video — whisper model, term corrections."""

    @patch("utils.instagram_ingester._get_whisper_model")
    def test_returns_transcript_string(
        self, mock_get_model: MagicMock, tmp_path: Path
    ) -> None:
        """Transcription returns joined segment texts."""
        mock_model = MagicMock()
        segment1 = MagicMock()
        segment1.text = "Hello world. "
        segment2 = MagicMock()
        segment2.text = "This is a test."
        mock_model.transcribe.return_value = ([segment1, segment2], None)
        mock_get_model.return_value = mock_model

        video = tmp_path / "test.mp4"
        video.write_bytes(b"fake")

        from utils.instagram_ingester import transcribe_video

        result = transcribe_video(video)
        assert "Hello world" in result
        assert "This is a test" in result

    @patch("utils.instagram_ingester._get_whisper_model")
    def test_applies_term_corrections(
        self, mock_get_model: MagicMock, tmp_path: Path
    ) -> None:
        """'Cloud Code' is corrected to 'Claude Code'."""
        mock_model = MagicMock()
        segment = MagicMock()
        segment.text = "I love Cloud Code and Cloud Agents."
        mock_model.transcribe.return_value = ([segment], None)
        mock_get_model.return_value = mock_model

        video = tmp_path / "test.mp4"
        video.write_bytes(b"fake")

        from utils.instagram_ingester import transcribe_video

        result = transcribe_video(video)
        assert "Claude Code" in result
        assert "Claude Agents" in result
        assert "Cloud Code" not in result


# --- extract_keywords_and_summary ---


class TestExtractKeywordsAndSummary:
    """Tests for extract_keywords_and_summary — Haiku call, wiki-links."""

    @patch("utils.instagram_ingester.claude_client.call_haiku_json")
    def test_calls_haiku_and_returns_dict(self, mock_haiku: MagicMock) -> None:
        """Returns dict with key_points, keywords, title."""
        mock_haiku.return_value = json.dumps(
            {
                "title": "Building with Claude",
                "key_points": ["Point 1", "Point 2"],
                "keywords": ["AI", "agents"],
            }
        )

        from utils.instagram_ingester import extract_keywords_and_summary

        result = extract_keywords_and_summary(
            transcript="A talk about building AI agents.",
            caption="Great video",
            known_projects=["Claude Code"],
        )

        assert result["title"] == "Building with Claude"
        assert len(result["key_points"]) == 2
        mock_haiku.assert_called_once()

    @patch("utils.instagram_ingester.claude_client.call_haiku_json")
    def test_includes_project_wiki_links(self, mock_haiku: MagicMock) -> None:
        """Known project names in transcript become wiki-link keywords."""
        mock_haiku.return_value = json.dumps(
            {
                "title": "Demo",
                "key_points": ["Point"],
                "keywords": ["[[Claude Code]]", "AI"],
            }
        )

        from utils.instagram_ingester import extract_keywords_and_summary

        result = extract_keywords_and_summary(
            transcript="Using Claude Code to build agents.",
            caption="Demo",
            known_projects=["Claude Code"],
        )

        assert any("Claude Code" in k for k in result["keywords"])

    @patch("utils.instagram_ingester.claude_client.call_haiku_json")
    def test_parse_failure_returns_defaults(self, mock_haiku: MagicMock) -> None:
        """On JSON parse failure, returns safe defaults."""
        mock_haiku.return_value = "NOT VALID JSON {{"

        from utils.instagram_ingester import extract_keywords_and_summary

        result = extract_keywords_and_summary(
            transcript="Some transcript",
            caption="A caption that is at least sixty characters long for the fallback",
            known_projects=[],
        )

        assert "title" in result
        assert isinstance(result["key_points"], list)
        assert isinstance(result["keywords"], list)


# --- write_vault_note ---


class TestWriteVaultNote:
    """Tests for write_vault_note — file creation, YAML, sections."""

    def test_creates_file_with_correct_path(self, tmp_path: Path) -> None:
        """Output path follows the pattern: Research/Instagram/{username}/YYYY-MM-DD-{shortcode}.md"""
        post = {
            "shortcode": "XYZ789",
            "username": "testaccount",
            "date": "2026-03-15",
            "caption": "Great video!",
            "url": "https://instagram.com/p/XYZ789",
        }
        extracted = {
            "title": "Test Title",
            "key_points": ["Point 1", "Point 2"],
            "keywords": ["AI", "[[Claude Code]]"],
        }

        from utils.instagram_ingester import write_vault_note

        with patch("utils.instagram_ingester.os.replace") as mock_replace:
            mock_replace.side_effect = lambda src, dst: Path(src).rename(dst)
            result = write_vault_note(
                post, "Transcript text here.", extracted, tmp_path
            )

        expected = (
            tmp_path / "Research" / "Instagram" / "testaccount" / "2026-03-15-XYZ789.md"
        )
        assert result == expected
        assert result.exists()

    def test_creates_intermediate_directories(self, tmp_path: Path) -> None:
        """Missing directories are created automatically."""
        post = {
            "shortcode": "DIR1",
            "username": "newaccount",
            "date": "2026-03-15",
            "caption": "Video",
            "url": "https://instagram.com/p/DIR1",
        }
        extracted = {"title": "Title", "key_points": [], "keywords": []}

        from utils.instagram_ingester import write_vault_note

        with patch("utils.instagram_ingester.os.replace") as mock_replace:
            mock_replace.side_effect = lambda src, dst: Path(src).rename(dst)
            result = write_vault_note(post, "Text", extracted, tmp_path)

        assert result.parent.exists()

    def test_returns_path(self, tmp_path: Path) -> None:
        """write_vault_note returns Path to written file."""
        post = {
            "shortcode": "RET1",
            "username": "user",
            "date": "2026-03-15",
            "caption": "Cap",
            "url": "https://instagram.com/p/RET1",
        }
        extracted = {"title": "T", "key_points": [], "keywords": []}

        from utils.instagram_ingester import write_vault_note

        with patch("utils.instagram_ingester.os.replace") as mock_replace:
            mock_replace.side_effect = lambda src, dst: Path(src).rename(dst)
            result = write_vault_note(post, "Txt", extracted, tmp_path)

        assert isinstance(result, Path)

    def test_yaml_frontmatter_fields(self, tmp_path: Path) -> None:
        """Written file contains YAML frontmatter with required fields."""
        import yaml

        post = {
            "shortcode": "YAML1",
            "username": "user",
            "date": "2026-03-15",
            "caption": "Cap",
            "url": "https://instagram.com/p/YAML1",
        }
        extracted = {
            "title": "My Title",
            "key_points": ["P1"],
            "keywords": ["AI", "[[Axon]]"],
        }

        from utils.instagram_ingester import write_vault_note

        with patch("utils.instagram_ingester.os.replace") as mock_replace:
            mock_replace.side_effect = lambda src, dst: Path(src).rename(dst)
            result = write_vault_note(post, "Transcript", extracted, tmp_path)

        content = result.read_text(encoding="utf-8")
        # Parse YAML frontmatter
        assert content.startswith("---\n")
        yaml_end = content.index("---", 4)
        fm = yaml.safe_load(content[4:yaml_end])

        assert fm["title"] == "My Title"
        assert fm["shortcode"] == "YAML1"
        assert fm["account"] == "[[user]]"
        assert fm["date"] == "2026-03-15"
        assert fm["source_url"] == "https://instagram.com/p/YAML1"
        assert fm["tags"] == []

    def test_body_sections(self, tmp_path: Path) -> None:
        """Written file contains ## Caption, Key Points, Keywords, Transcript sections."""
        post = {
            "shortcode": "SEC1",
            "username": "user",
            "date": "2026-03-15",
            "caption": "My caption here",
            "url": "https://instagram.com/p/SEC1",
        }
        extracted = {
            "title": "Title",
            "key_points": ["First point", "Second point"],
            "keywords": ["AI", "[[Claude Code]]"],
        }

        from utils.instagram_ingester import write_vault_note

        with patch("utils.instagram_ingester.os.replace") as mock_replace:
            mock_replace.side_effect = lambda src, dst: Path(src).rename(dst)
            result = write_vault_note(
                post, "Full transcript text.", extracted, tmp_path
            )

        content = result.read_text(encoding="utf-8")
        assert "## Caption" in content
        assert "My caption here" in content
        assert "## Key Points" in content
        assert "- First point" in content
        assert "- Second point" in content
        assert "## Keywords" in content
        assert "AI" in content
        assert "## Transcript" in content
        assert "Full transcript text." in content


# --- run_ingestion ---


class TestRunIngestion:
    """Tests for run_ingestion — orchestration, state, error isolation."""

    @patch("utils.instagram_ingester.os.replace")
    @patch("utils.instagram_ingester.write_vault_note")
    @patch("utils.instagram_ingester.extract_keywords_and_summary")
    @patch("utils.instagram_ingester.transcribe_video")
    @patch("utils.instagram_ingester.download_video")
    @patch("utils.instagram_ingester.fetch_recent_posts")
    def test_orchestrates_full_pipeline(
        self,
        mock_fetch: MagicMock,
        mock_download: MagicMock,
        mock_transcribe: MagicMock,
        mock_extract: MagicMock,
        mock_write: MagicMock,
        mock_replace: MagicMock,
        tmp_path: Path,
    ) -> None:
        """run_ingestion calls fetch→download→transcribe→extract→write for each post."""
        mock_fetch.return_value = [
            {
                "shortcode": "A1",
                "url": "https://x.com/a1.mp4",
                "caption": "Cap",
                "date": "2026-03-15",
                "username": "u",
            },
        ]
        video_path = tmp_path / "A1.mp4"
        video_path.write_bytes(b"fake")
        mock_download.return_value = video_path
        mock_transcribe.return_value = "Transcript"
        mock_extract.return_value = {"title": "T", "key_points": [], "keywords": []}
        note_path = tmp_path / "note.md"
        note_path.write_text("note")
        mock_write.return_value = note_path

        from utils.instagram_ingester import run_ingestion

        results = run_ingestion("u", tmp_path, known_projects=["Axon"])

        assert len(results) == 1
        mock_download.assert_called_once()
        mock_transcribe.assert_called_once()
        mock_extract.assert_called_once()
        mock_write.assert_called_once()

    @patch("utils.instagram_ingester.os.replace")
    @patch("utils.instagram_ingester.write_vault_note")
    @patch("utils.instagram_ingester.extract_keywords_and_summary")
    @patch("utils.instagram_ingester.transcribe_video")
    @patch("utils.instagram_ingester.download_video")
    @patch("utils.instagram_ingester.fetch_recent_posts")
    def test_state_write_per_post(
        self,
        mock_fetch: MagicMock,
        mock_download: MagicMock,
        mock_transcribe: MagicMock,
        mock_extract: MagicMock,
        mock_write: MagicMock,
        mock_os_replace: MagicMock,
        tmp_path: Path,
    ) -> None:
        """State file is written atomically after each successful post."""
        mock_fetch.return_value = [
            {
                "shortcode": "S1",
                "url": "https://x.com/s1.mp4",
                "caption": "C",
                "date": "2026-03-15",
                "username": "u",
            },
            {
                "shortcode": "S2",
                "url": "https://x.com/s2.mp4",
                "caption": "C",
                "date": "2026-03-15",
                "username": "u",
            },
        ]
        vid = tmp_path / "v.mp4"
        vid.write_bytes(b"fake")
        mock_download.return_value = vid
        mock_transcribe.return_value = "T"
        mock_extract.return_value = {"title": "T", "key_points": [], "keywords": []}
        mock_write.return_value = tmp_path / "note.md"

        from utils.instagram_ingester import run_ingestion

        state_file = tmp_path / "state.json"
        state_file.write_text("{}")
        run_ingestion("u", tmp_path, state_file=state_file)

        # At minimum, os.replace is called for vault note writes + state writes
        assert mock_os_replace.call_count >= 2

    @patch("utils.instagram_ingester.os.replace")
    @patch("utils.instagram_ingester.write_vault_note")
    @patch("utils.instagram_ingester.extract_keywords_and_summary")
    @patch("utils.instagram_ingester.transcribe_video")
    @patch("utils.instagram_ingester.download_video")
    @patch("utils.instagram_ingester.fetch_recent_posts")
    def test_records_shortcode_in_state(
        self,
        mock_fetch: MagicMock,
        mock_download: MagicMock,
        mock_transcribe: MagicMock,
        mock_extract: MagicMock,
        mock_write: MagicMock,
        mock_os_replace: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Each shortcode is recorded in state after successful write."""
        mock_fetch.return_value = [
            {
                "shortcode": "REC1",
                "url": "https://x.com/r.mp4",
                "caption": "C",
                "date": "2026-03-15",
                "username": "u",
            },
        ]
        vid = tmp_path / "v.mp4"
        vid.write_bytes(b"fake")
        mock_download.return_value = vid
        mock_transcribe.return_value = "T"
        mock_extract.return_value = {"title": "T", "key_points": [], "keywords": []}
        mock_write.return_value = tmp_path / "note.md"

        from utils.instagram_ingester import run_ingestion

        state_file = tmp_path / "state.json"
        state_file.write_text("{}")

        # Capture what gets written to state via os.replace
        written_data = {}

        def capture_replace(src, dst):
            if "state" in str(dst):
                content = Path(src).read_text(encoding="utf-8")
                written_data.update(json.loads(content))
            # Actually perform the rename for non-state files
            try:
                Path(src).rename(dst)
            except Exception:
                pass

        mock_os_replace.side_effect = capture_replace

        run_ingestion("u", tmp_path, state_file=state_file)

        assert "REC1" in written_data

    @patch("utils.instagram_ingester.download_video")
    @patch("utils.instagram_ingester.fetch_recent_posts")
    def test_skips_post_on_transcription_error(
        self,
        mock_fetch: MagicMock,
        mock_download: MagicMock,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Transcription failure logs WARNING and continues (never propagates)."""
        mock_fetch.return_value = [
            {
                "shortcode": "ERR1",
                "url": "https://x.com/e.mp4",
                "caption": "C",
                "date": "2026-03-15",
                "username": "u",
            },
        ]
        vid = tmp_path / "v.mp4"
        vid.write_bytes(b"fake")
        mock_download.return_value = vid

        from utils.instagram_ingester import run_ingestion

        import logging

        with patch(
            "utils.instagram_ingester.transcribe_video",
            side_effect=RuntimeError("Whisper failed"),
        ):
            with caplog.at_level(logging.WARNING):
                results = run_ingestion(
                    "u", tmp_path, state_file=tmp_path / "state.json"
                )

        assert len(results) == 0
        assert any(
            "ERR1" in r.message or "failed" in r.message.lower() for r in caplog.records
        )

    @patch("utils.instagram_ingester.os.replace")
    @patch("utils.instagram_ingester.write_vault_note")
    @patch("utils.instagram_ingester.extract_keywords_and_summary")
    @patch("utils.instagram_ingester.transcribe_video")
    @patch("utils.instagram_ingester.download_video")
    @patch("utils.instagram_ingester.fetch_recent_posts")
    def test_deletes_video_in_finally(
        self,
        mock_fetch: MagicMock,
        mock_download: MagicMock,
        mock_transcribe: MagicMock,
        mock_extract: MagicMock,
        mock_write: MagicMock,
        mock_os_replace: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Downloaded video is cleaned up in finally block after each post."""
        vid = tmp_path / "DEL1.mp4"
        vid.write_bytes(b"fake video")

        mock_fetch.return_value = [
            {
                "shortcode": "DEL1",
                "url": "https://x.com/d.mp4",
                "caption": "C",
                "date": "2026-03-15",
                "username": "u",
            },
        ]
        mock_download.return_value = vid
        mock_transcribe.return_value = "T"
        mock_extract.return_value = {"title": "T", "key_points": [], "keywords": []}
        mock_write.return_value = tmp_path / "note.md"

        from utils.instagram_ingester import run_ingestion

        run_ingestion("u", tmp_path, state_file=tmp_path / "state.json")

        # Video should be deleted after processing
        assert not vid.exists()
