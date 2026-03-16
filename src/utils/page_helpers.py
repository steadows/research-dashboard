"""Shared page utilities — common helpers used across all Streamlit pages."""

import html
import logging
import os
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from utils.paper_fetcher import PaperContext

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


# ---------------------------------------------------------------------------
# Context sources expander — UI transparency for LLM enrichment
# ---------------------------------------------------------------------------

_FETCH_STATE_BADGES: dict[str, tuple[str, str]] = {
    "not_fetched": ("#6B7280", "Not fetched"),
    "not_found": ("#9CA3AF", "Not found"),
    "failed": ("#EF4444", "Failed"),
    "abstract_only": ("#F59E0B", "Abstract only"),
    "pdf": ("#10B981", "PDF full text"),
    "arxiv_html": ("#10B981", "arXiv HTML"),
}


def render_context_sources(
    paper_context: "PaperContext | None",
    connected_projects: list[str],
) -> None:
    """Render a context sources expander showing what data the LLM has access to.

    Uses the paper_context's explicit fetch_state field for status display.
    Safe for import — streamlit is imported lazily inside the function body
    since this module is also imported in test contexts.

    Args:
        paper_context: PaperContext dict or None if not yet fetched.
        connected_projects: List of connected project names.
    """
    import streamlit as st

    with st.expander("📊 Context Sources"):
        # Paper context status
        if paper_context is None:
            fetch_state = "not_fetched"
            abstract_len = 0
            full_text_len = 0
            error_msg = ""
        else:
            fetch_state = paper_context.get("fetch_state", "not_fetched")
            abstract_len = len(paper_context.get("abstract", ""))
            full_text_len = len(paper_context.get("full_text", ""))
            error_msg = paper_context.get("error", "")

        color, label = _FETCH_STATE_BADGES.get(fetch_state, ("#6B7280", fetch_state))

        st.markdown(
            f'**Paper Context:** <span style="color:{color};font-weight:600">'
            f"{safe_html(label)}</span>",
            unsafe_allow_html=True,
        )

        if abstract_len:
            tokens_est = abstract_len // 4
            st.caption(f"Abstract: {abstract_len:,} chars (~{tokens_est:,} tokens)")

        if full_text_len:
            tokens_est = full_text_len // 4
            st.caption(f"Full text: {full_text_len:,} chars (~{tokens_est:,} tokens)")

        if error_msg:
            st.caption(f"Error: {safe_html(error_msg)}")

        # Connected projects
        if connected_projects:
            project_list = ", ".join(safe_html(p) for p in connected_projects)
            st.markdown(
                f"**Connected Projects:** {project_list}",
                unsafe_allow_html=True,
            )
        else:
            st.caption("No connected projects")
