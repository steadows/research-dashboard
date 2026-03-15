"""Shared page utilities — common helpers used across all Streamlit pages."""

import html
import logging
import os
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
    return Path(vault_str)


def safe_html(text: str) -> str:
    """Escape text for safe use in Streamlit unsafe_allow_html contexts.

    Wraps html.escape() to prevent XSS when rendering vault-sourced
    strings via st.markdown(unsafe_allow_html=True).

    Args:
        text: Raw text that may contain HTML special characters.

    Returns:
        HTML-escaped string safe for rendering.
    """
    return html.escape(text, quote=True)


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
