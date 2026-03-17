"""Methods parser — parses Research/Methods to Try.md into structured items."""

import logging
from pathlib import Path
from typing import Any

from utils.parser_helpers import build_item, split_h2_sections

logger = logging.getLogger(__name__)

_METHODS_FILE = "Research/Methods to Try.md"

_METHOD_DEFAULTS: dict[str, Any] = {
    "source": "",
    "status": "New",
    "why it matters": "",
    "method": "",
    "idea": "",
}


def parse_methods(vault_path: Path) -> list[dict[str, Any]]:
    """Parse the Methods to Try file into structured method items.

    Args:
        vault_path: Root path to the Obsidian vault.

    Returns:
        List of method item dicts with name, source, status, projects, etc.
    """
    methods_path = vault_path / _METHODS_FILE
    if not methods_path.is_file():
        logger.debug("Methods file not found: %s", methods_path)
        return []

    content = methods_path.read_text(encoding="utf-8")
    sections = split_h2_sections(content)

    methods: list[dict[str, Any]] = []
    for section in sections:
        item = build_item(
            name=section["name"],
            body=section["body"],
            source_type="method",
            defaults=_METHOD_DEFAULTS,
        )
        methods.append(item)

    logger.debug("Parsed %d methods from %s", len(methods), methods_path)
    return methods
