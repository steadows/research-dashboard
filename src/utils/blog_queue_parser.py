"""Blog queue parser — parses Writing/Blog Queue.md into structured items."""

import logging
from pathlib import Path
from typing import Any

from utils.parser_helpers import build_item, split_h2_sections

logger = logging.getLogger(__name__)

_BLOG_QUEUE_FILE = "Writing/Blog Queue.md"

_BLOG_DEFAULTS: dict[str, Any] = {
    "status": "Idea",
    "hook": "",
    "source": "",
    "source paper": "",
    "tags": "",
    "added": "",
}


def parse_blog_queue(vault_path: Path) -> list[dict[str, Any]]:
    """Parse the Blog Queue file into structured blog idea items.

    Args:
        vault_path: Root path to the Obsidian vault.

    Returns:
        List of blog item dicts with name, status, angle, target, projects.
    """
    blog_path = vault_path / _BLOG_QUEUE_FILE
    if not blog_path.is_file():
        logger.debug("Blog Queue file not found: %s", blog_path)
        return []

    content = blog_path.read_text(encoding="utf-8")
    sections = split_h2_sections(content)

    items: list[dict[str, Any]] = []
    for section in sections:
        item = build_item(
            name=section["name"],
            body=section["body"],
            source_type="blog",
            defaults=_BLOG_DEFAULTS,
        )
        items.append(item)

    logger.debug("Parsed %d blog items from %s", len(items), blog_path)
    return items
