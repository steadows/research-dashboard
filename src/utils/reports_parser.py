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


def parse_journalclub_papers(vault_path: Path) -> list[dict[str, Any]]:
    """Extract individual papers from all JournalClub reports.

    Args:
        vault_path: Root path to the Obsidian vault.

    Returns:
        List of paper dicts with title, authors, year, synthesis, relevance,
        blog_potential, project_applications, etc. Sorted newest-report first.
    """
    reports = parse_journalclub_reports(vault_path)
    papers: list[dict[str, Any]] = []

    for report in reports:
        report_date = report.get("date", "")
        content = report.get("content", "")
        extracted = _extract_papers_from_content(content, report_date)
        papers.extend(extracted)

    logger.debug("Parsed %d total papers from JournalClub reports", len(papers))
    return papers


# Match paper headings like "### 1. Paper Title" or "### Paper Title"
_PAPER_HEADING_RE = re.compile(r"^###\s+(?:\d+\.\s+)?(.+)$", re.MULTILINE)

# Field extractors for paper metadata
_FIELD_PATTERNS: dict[str, re.Pattern[str]] = {
    "authors": re.compile(r"\*\*Authors?:\*\*\s*(.+?)(?:\s*\||\s*$)"),
    "year": re.compile(r"\*\*Year:\*\*\s*(\S+)"),
    "link": re.compile(r"\*\*Link:\*\*\s*(.+?)(?:\s*\||\s*$)"),
    "snippet": re.compile(r"\*\*Snippet:\*\*\s*(.+?)(?=\n\n|\Z)", re.DOTALL),
    "synthesis": re.compile(r"\*\*Synthesis:\*\*\s*(.+?)(?=\n\n\*\*|\Z)", re.DOTALL),
    "relevance": re.compile(r"\*\*Relevance:\*\*\s*(.+?)(?=\n\n\*\*|\Z)", re.DOTALL),
    "blog_potential": re.compile(
        r"\*\*Blog Potential:\*\*\s*(.+?)(?=\n\n\*\*|\Z)", re.DOTALL
    ),
}


def _extract_papers_from_content(
    content: str, report_date: str
) -> list[dict[str, Any]]:
    """Extract individual papers from a JournalClub report's markdown content."""
    papers: list[dict[str, Any]] = []

    # Split on ### headings (paper sections)
    headings = list(_PAPER_HEADING_RE.finditer(content))
    if not headings:
        return papers

    for idx, match in enumerate(headings):
        title = match.group(1).strip()

        # Get the body between this heading and the next (or EOF)
        start = match.end()
        end = headings[idx + 1].start() if idx + 1 < len(headings) else len(content)
        body = content[start:end].strip()

        paper: dict[str, Any] = {
            "title": title,
            "report_date": report_date,
        }

        # Extract structured fields
        for field, pattern in _FIELD_PATTERNS.items():
            field_match = pattern.search(body)
            if field_match:
                value = field_match.group(1).strip().rstrip("|").strip()
                # Strip markdown formatting
                value = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", value)
                value = re.sub(r"\[\[(.+?)(?:\|.+?)?\]\]", r"\1", value)
                paper[field] = value
            else:
                paper[field] = None

        # Extract project applications (bulleted list after "Project Applications:")
        apps_match = re.search(
            r"\*\*Project Applications:\*\*\s*\n((?:\s*[-*]\s+.+\n?)+)", body
        )
        if apps_match:
            raw_apps = apps_match.group(1).strip()
            app_lines = [
                re.sub(
                    r"\[\[(.+?)(?:\|.+?)?\]\]",
                    r"\1",
                    line.strip().lstrip("- *").strip(),
                )
                for line in raw_apps.splitlines()
                if line.strip()
            ]
            paper["project_applications"] = app_lines
        else:
            paper["project_applications"] = []

        # Extract relevance level (High/Medium/Low/None)
        if paper.get("relevance"):
            level_match = re.match(
                r"(High|Medium|Low|None)", paper["relevance"], re.IGNORECASE
            )
            paper["relevance_level"] = (
                level_match.group(1).capitalize() if level_match else None
            )
        else:
            paper["relevance_level"] = None

        papers.append(paper)

    return papers


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
