"""Shared page utilities — pure helpers used across pages and the API layer."""

import html
import logging
import os
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Consistent empty-state messages
# ---------------------------------------------------------------------------

EMPTY_VAULT = "Obsidian vault path is not configured. Set OBSIDIAN_VAULT_PATH."
EMPTY_NO_PROJECTS = "No projects found in the vault."
EMPTY_NO_ITEMS = "No items flagged for this project."
EMPTY_NO_BLOG = "No blog ideas found in the vault."
EMPTY_NO_TOOLS = "No tools found in the vault."
EMPTY_NO_REPORTS = "No reports found in the vault."
EMPTY_NO_API_KEY = (
    "Anthropic API key is not configured. Set ANTHROPIC_API_KEY to enable analysis."
)


def get_vault_path() -> Path:
    """Read OBSIDIAN_VAULT_PATH from environment and return as Path.

    Returns:
        Path to the Obsidian vault root directory.

    Raises:
        ValueError: If OBSIDIAN_VAULT_PATH is not set or empty.
    """
    vault_str = os.environ.get("OBSIDIAN_VAULT_PATH", "").strip()
    if not vault_str:
        raise ValueError(
            "OBSIDIAN_VAULT_PATH environment variable is not set or empty."
        )
    path = Path(vault_str)
    if not path.is_dir():
        raise ValueError(f"OBSIDIAN_VAULT_PATH does not exist: {path}")
    return path


_WIKI_LINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


def strip_wiki_links(text: str) -> str:
    """Replace Obsidian ``[[Link]]`` and ``[[Link|Alias]]`` with display text.

    Args:
        text: Raw string possibly containing wiki-link syntax.

    Returns:
        String with wiki-link brackets removed, using alias if present.
    """
    return _WIKI_LINK_RE.sub(lambda m: m.group(2) or m.group(1), text)


def safe_html(text: str) -> str:
    """Escape text for safe use in Streamlit unsafe_allow_html contexts.

    Strips Obsidian wiki-link brackets, then wraps html.escape() to prevent
    XSS when rendering vault-sourced strings via
    st.markdown(unsafe_allow_html=True).

    Args:
        text: Raw text that may contain HTML special characters or wiki-links.

    Returns:
        HTML-escaped string safe for rendering.
    """
    return html.escape(strip_wiki_links(text), quote=True)


def safe_parse(
    parser_fn: Any,
    *args: Any,
    fallback: Any = None,
    label: str = "data",
) -> Any:
    """Call a parser function with graceful error handling.

    On exception, logs a warning and returns the fallback value so that
    the UI can degrade gracefully instead of crashing.

    Args:
        parser_fn: Callable to invoke.
        *args: Positional arguments forwarded to parser_fn.
        fallback: Value to return on failure (default: None).
        label: Human-readable label for log messages.

    Returns:
        Parser result on success, or fallback on failure.
    """
    try:
        return parser_fn(*args)
    except Exception:
        logger.warning("Failed to load %s", label, exc_info=True)
        return fallback


# ---------------------------------------------------------------------------
# Shared color constants
# ---------------------------------------------------------------------------

CATEGORY_COLORS: dict[str, str] = {
    "IDE": "#8B5CF6",
    "Database": "#10B981",
    "Framework": "#3B82F6",
    "DevOps": "#F59E0B",
    "AI/ML": "#EC4899",
    "Security": "#EF4444",
    "Uncategorized": "#6B7280",
}


def get_category_color(category: str) -> str:
    """Return hex color for a tool category.

    Args:
        category: Tool category string.

    Returns:
        Hex color string.
    """
    return CATEGORY_COLORS.get(category, "#6B7280")
