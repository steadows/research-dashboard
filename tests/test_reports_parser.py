"""Tests for reports_parser — JournalClub and TLDR report parsing."""

from pathlib import Path

from utils.reports_parser import parse_journalclub_reports, parse_tldr_reports


class TestParseJournalClubReports:
    """Tests for parse_journalclub_reports()."""

    def test_parses_report_with_date(self, tmp_vault: Path) -> None:
        """Extracts date from filename and parses content."""
        reports = parse_journalclub_reports(tmp_vault)
        assert len(reports) == 1
        report = reports[0]
        assert report["date"] == "2026-03-07"
        assert "Top Picks" in report["sections"]

    def test_missing_dir_returns_empty(self, empty_vault: Path) -> None:
        """Returns empty when JournalClub dir doesn't exist."""
        result = parse_journalclub_reports(empty_vault)
        assert result == []


class TestParseTldrReports:
    """Tests for parse_tldr_reports()."""

    def test_parses_report_with_ai_signal(self, tmp_vault: Path) -> None:
        """Extracts AI Signal section with unicode emoji header."""
        reports = parse_tldr_reports(tmp_vault)
        assert len(reports) == 1
        report = reports[0]
        assert report["date"] == "2026-03-07"
        assert report["ai_signal"] != ""
        assert "agent-first" in report["ai_signal"]

    def test_unicode_emoji_header_match(self, tmp_path: Path) -> None:
        """The 📰 emoji in AI Signal header must match correctly."""
        research_dir = tmp_path / "Research" / "TLDR"
        research_dir.mkdir(parents=True)
        (research_dir / "TLDR 2026-01-01.md").write_text(
            "# TLDR AI — 2026-01-01\n\n"
            "## \U0001f4f0 AI Signal\n"
            "Test signal content here.\n"
        )
        reports = parse_tldr_reports(tmp_path)
        assert reports[0]["ai_signal"] == "Test signal content here."

    def test_missing_dir_returns_empty(self, empty_vault: Path) -> None:
        """Returns empty when TLDR dir doesn't exist."""
        result = parse_tldr_reports(empty_vault)
        assert result == []
