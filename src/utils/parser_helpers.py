"""Shared parser helpers — DRY utilities for methods/tools/blog parsers."""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
_FIELD_RE = re.compile(r"^\*\*([^*:]+):\*\*\s*(.+)$", re.MULTILINE)


def parse_wiki_links(text: str) -> list[str]:
    """Extract deduplicated wiki-link targets from markdown text.

    Args:
        text: Markdown text potentially containing [[Link]] patterns.

    Returns:
        List of unique link targets, in order of first appearance.
    """
    seen: set[str] = set()
    result: list[str] = []
    for match in _WIKI_LINK_RE.finditer(text):
        name = match.group(1).strip()
        if name not in seen:
            seen.add(name)
            result.append(name)
    return result


def split_h2_sections(text: str) -> list[dict[str, str]]:
    """Split markdown into H2 sections.

    Args:
        text: Full markdown file content.

    Returns:
        List of dicts with 'name' (H2 title) and 'body' (content until next H2 or EOF).
    """
    sections: list[dict[str, str]] = []
    parts = re.split(r"^## ", text, flags=re.MULTILINE)

    for part in parts[1:]:  # Skip content before first ##
        lines = part.split("\n", 1)
        name = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        if name:
            sections.append({"name": name, "body": body})

    return sections


def parse_fields(body: str) -> dict[str, str]:
    """Extract **Key:** Value fields from a section body.

    Args:
        body: Markdown section body text.

    Returns:
        Dict mapping lowercase field names to their values.
    """
    fields: dict[str, str] = {}
    for match in _FIELD_RE.finditer(body):
        key = match.group(1).strip().lower()
        value = match.group(2).strip()
        fields[key] = value
    return fields


_PROJECT_FIELD_ALIASES = ("projects", "apply to", "try on", "connect to")


def parse_project_links(body: str) -> list[str]:
    """Extract project names from a project-reference field line.

    Checks multiple field name aliases used across vault file types:
    - ``**Projects:**`` (test fixtures, blog queue)
    - ``**Apply to:**`` (Tools Radar)
    - ``**Try on:**`` (Methods to Try)

    Args:
        body: Section body containing a project field with wiki-links.

    Returns:
        List of project names referenced.
    """
    fields = parse_fields(body)
    for alias in _PROJECT_FIELD_ALIASES:
        projects_line = fields.get(alias, "")
        if projects_line:
            return parse_wiki_links(projects_line)
    return []


def build_item(
    name: str,
    body: str,
    source_type: str,
    defaults: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a structured item dict from a parsed section.

    Args:
        name: Item name (H2 title).
        body: Section body text.
        source_type: Type label (e.g. 'method', 'tool', 'blog').
        defaults: Default values for missing fields.

    Returns:
        Structured item dict with name, fields, projects, and source_type.
    """
    merged_defaults: dict[str, Any] = defaults or {}
    fields = parse_fields(body)
    projects = parse_project_links(body)

    item: dict[str, Any] = {
        "name": name,
        "source_type": source_type,
        "projects": projects,
    }

    for key, default_val in merged_defaults.items():
        item[key] = fields.get(key, default_val)

    # Always include commonly expected fields
    for key in ("source", "status"):
        if key not in item:
            item[key] = fields.get(key, "")

    return item
