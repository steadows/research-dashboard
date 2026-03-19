"""Instagram vault note parser — reads structured markdown into data model.

Parses Instagram video notes from the Obsidian vault (Research/Instagram/**/*.md)
into structured dicts for the dashboard. Pure utility — no Streamlit import.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

from utils.parser_helpers import split_h2_sections

logger = logging.getLogger(__name__)


def _parse_key_points(body: str) -> list[str]:
    """Parse bullet lines from a Key Points section body.

    Args:
        body: Raw section body text.

    Returns:
        List of key point strings with leading '- ' stripped.
    """
    points: list[str] = []
    for line in body.strip().splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            points.append(stripped[2:].strip())
    return points


def _parse_keywords(body: str) -> list[str]:
    """Parse comma-separated keywords, stripping wiki-link brackets.

    Args:
        body: Raw keywords section body (single line expected).

    Returns:
        List of keyword strings with [[ ]] removed.
    """
    line = body.strip().splitlines()[0] if body.strip() else ""
    if not line:
        return []
    raw = [k.strip() for k in line.split(",")]
    return [k.replace("[[", "").replace("]]", "").strip() for k in raw if k.strip()]


def parse_instagram_posts(
    vault_path: Path,
    accounts: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Parse Instagram notes from the vault into structured dicts.

    Args:
        vault_path: Root path to the Obsidian vault.
        accounts: Optional list of account names to filter by (case-insensitive).

    Returns:
        List of post dicts sorted by date descending.
    """
    ig_dir = vault_path / "Research" / "Instagram"
    if not ig_dir.exists():
        logger.debug("Instagram directory not found: %s", ig_dir)
        return []

    posts: list[dict[str, Any]] = []
    accounts_lower = [a.lower() for a in accounts] if accounts else None

    for md_file in ig_dir.rglob("*.md"):
        # Skip account hub pages (live directly in Instagram/, not in subdirs)
        if md_file.parent == ig_dir:
            continue

        try:
            content = md_file.read_text(encoding="utf-8")
            post = _parse_single_note(content, md_file)
            if post is None:
                continue

            # Filter by account if specified
            if accounts_lower and post["account"].lower() not in accounts_lower:
                continue

            posts.append(post)
        except Exception as exc:
            logger.warning("Skipping malformed instagram note %s: %s", md_file, exc)

    # Sort by date descending
    posts.sort(key=lambda p: p.get("date", ""), reverse=True)
    return posts


def _parse_single_note(content: str, file_path: Path) -> dict[str, Any] | None:
    """Parse a single Instagram note file into a structured dict.

    Args:
        content: Full file content.
        file_path: Path to the file (for fallback name).

    Returns:
        Parsed post dict, or None if frontmatter is missing/invalid.
    """
    # Parse YAML frontmatter
    if not content.startswith("---"):
        logger.warning(
            "Skipping malformed instagram note %s: no frontmatter", file_path
        )
        return None

    try:
        end_idx = content.index("---", 4)
        fm_text = content[4:end_idx]
        fm = yaml.safe_load(fm_text)
    except (ValueError, yaml.YAMLError) as exc:
        logger.warning("Skipping malformed instagram note %s: %s", file_path, exc)
        return None

    if not isinstance(fm, dict):
        logger.warning(
            "Skipping malformed instagram note %s: frontmatter is not a dict", file_path
        )
        return None

    # Parse body sections
    body_text = content[end_idx + 3 :].strip()
    sections = split_h2_sections(body_text)
    section_map = {s["name"]: s["body"] for s in sections}

    key_points = _parse_key_points(section_map.get("Key Points", ""))
    keywords = _parse_keywords(section_map.get("Keywords", ""))
    caption = section_map.get("Caption", "").strip()
    transcript = section_map.get("Transcript", "").strip()

    # Strip wiki-link brackets from account field (e.g. "[[username]]" → "username")
    raw_account = str(fm.get("account", ""))
    account = raw_account.replace("[[", "").replace("]]", "").strip()

    return {
        "name": fm.get("title") or file_path.stem,
        "account": account,
        "date": str(fm.get("date", "")),
        "source_url": fm.get("source_url", ""),
        "shortcode": fm.get("shortcode", ""),
        "key_points": key_points,
        "keywords": keywords,
        "caption": caption,
        "transcript": transcript,
        "source_type": "instagram",
    }
