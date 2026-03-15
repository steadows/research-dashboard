"""Tools parser — parses Research/Tools Radar.md into structured items."""

import logging
from pathlib import Path
from typing import Any

from utils.parser_helpers import build_item, split_h2_sections

logger = logging.getLogger(__name__)

_TOOLS_FILE = "Research/Tools Radar.md"

_TOOL_DEFAULTS: dict[str, Any] = {
    "category": "Uncategorized",
    "source": "",
    "status": "New",
    "what it does": "",
}


def parse_tools(vault_path: Path) -> list[dict[str, Any]]:
    """Parse the Tools Radar file into structured tool items.

    Args:
        vault_path: Root path to the Obsidian vault.

    Returns:
        List of tool item dicts with name, category, source, projects, etc.
    """
    tools_path = vault_path / _TOOLS_FILE
    if not tools_path.is_file():
        logger.debug("Tools file not found: %s", tools_path)
        return []

    content = tools_path.read_text(encoding="utf-8")
    sections = split_h2_sections(content)

    tools: list[dict[str, Any]] = []
    for section in sections:
        item = build_item(
            name=section["name"],
            body=section["body"],
            source_type="tool",
            defaults=_TOOL_DEFAULTS,
        )
        tools.append(item)

    logger.debug("Parsed %d tools from %s", len(tools), tools_path)
    return tools
