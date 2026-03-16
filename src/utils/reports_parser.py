"""Reports parser — parses JournalClub and TLDR weekly reports."""

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_JC_DIR = "Research/JournalClub"
_TLDR_DIR = "Research/TLDR"

# Match date in filenames like "JournalClub 2026-03-07.md"
_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")

# Use actual unicode 📰 emoji — NOT raw \U0001f4f0 in regex
_AI_SIGNAL_HEADER = re.compile(r"^##\s*📰\s*(?:Weekly\s+)?AI Signal\s*$", re.MULTILINE)


def parse_journalclub_reports(vault_path: Path) -> list[dict[str, Any]]:
    """Parse JournalClub weekly reports from the vault.

    Args:
        vault_path: Root path to the Obsidian vault.

    Returns:
        List of report dicts with date, sections, and raw content.
        Sorted newest first.
    """
    jc_dir = vault_path / _JC_DIR
    if not jc_dir.is_dir():
        logger.debug("JournalClub directory not found: %s", jc_dir)
        return []

    reports: list[dict[str, Any]] = []
    for md_file in sorted(jc_dir.glob("*.md"), reverse=True):
        report = _parse_jc_report(md_file)
        if report:
            reports.append(report)

    logger.debug("Parsed %d JournalClub reports", len(reports))
    return reports


def _parse_jc_report(md_file: Path) -> dict[str, Any] | None:
    """Parse a single JournalClub report file."""
    date_match = _DATE_RE.search(md_file.stem)
    if not date_match:
        logger.warning("Could not extract date from %s", md_file.name)
        return None

    content = md_file.read_text(encoding="utf-8")
    sections = _extract_h2_sections(content)

    return {
        "date": date_match.group(1),
        "filename": md_file.name,
        "sections": sections,
        "content": content,
    }


def parse_tldr_reports(vault_path: Path) -> list[dict[str, Any]]:
    """Parse TLDR weekly reports from the vault.

    Args:
        vault_path: Root path to the Obsidian vault.

    Returns:
        List of report dicts with date, ai_signal, sections, and raw content.
        Sorted newest first.
    """
    tldr_dir = vault_path / _TLDR_DIR
    if not tldr_dir.is_dir():
        logger.debug("TLDR directory not found: %s", tldr_dir)
        return []

    reports: list[dict[str, Any]] = []
    for md_file in sorted(tldr_dir.glob("*.md"), reverse=True):
        report = _parse_tldr_report(md_file)
        if report:
            reports.append(report)

    logger.debug("Parsed %d TLDR reports", len(reports))
    return reports


def _parse_tldr_report(md_file: Path) -> dict[str, Any] | None:
    """Parse a single TLDR report file."""
    date_match = _DATE_RE.search(md_file.stem)
    if not date_match:
        logger.warning("Could not extract date from %s", md_file.name)
        return None

    content = md_file.read_text(encoding="utf-8")
    sections = _extract_h2_sections(content)
    ai_signal = _extract_ai_signal(content)

    return {
        "date": date_match.group(1),
        "filename": md_file.name,
        "sections": sections,
        "ai_signal": ai_signal,
        "content": content,
    }


def _extract_ai_signal(content: str) -> str:
    """Extract the AI Signal section content.

    Uses the actual 📰 unicode emoji in the header match.
    """
    match = _AI_SIGNAL_HEADER.search(content)
    if not match:
        return ""

    # Get content after the header until next ## or EOF
    rest = content[match.end() :]
    next_section = re.search(r"^## ", rest, re.MULTILINE)
    if next_section:
        signal_text = rest[: next_section.start()]
    else:
        signal_text = rest

    return signal_text.strip()


def _extract_h2_sections(content: str) -> dict[str, str]:
    """Extract H2 sections as a dict of section_name -> content."""
    sections: dict[str, str] = {}
    parts = re.split(r"^## ", content, flags=re.MULTILINE)

    for part in parts[1:]:
        lines = part.split("\n", 1)
        title = lines[0].strip()
        # Strip emoji prefix for clean key
        clean_title = re.sub(r"^[\U0001f300-\U0001faff\u2600-\u27bf]\s*", "", title)
        body = lines[1].strip() if len(lines) > 1 else ""
        if clean_title:
            sections[clean_title] = body

    return sections
