"""Research Intelligence Dashboard — entry point, navigation, and CSS injection."""

import logging
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

load_dotenv(Path(__file__).resolve().parent.parent / ".env.local")

logger = logging.getLogger(__name__)

# Wire up llm_trace logger so LLM_TRACE=1 output reaches the console.
# propagate=False is set in claude_client to prevent bleed-through on prod;
# we attach a stderr handler here so it's visible when running locally.
_llm_trace_log = logging.getLogger("llm_trace")
if not _llm_trace_log.handlers:
    _llm_handler = logging.StreamHandler()
    _llm_handler.setFormatter(
        logging.Formatter("%(asctime)s [llm_trace] %(levelname)s — %(message)s")
    )
    _llm_trace_log.addHandler(_llm_handler)
_llm_trace_log.setLevel(logging.DEBUG)

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Research Intelligence",
    page_icon=":material/science:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Environment validation
# ---------------------------------------------------------------------------


def _validate_env() -> bool:
    """Check required environment variables. Returns True if valid."""
    vault_path = os.environ.get("OBSIDIAN_VAULT_PATH", "").strip()
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()

    missing: list[str] = []
    if not vault_path:
        missing.append("OBSIDIAN_VAULT_PATH")
    elif not Path(vault_path).is_dir():
        st.error(
            f"OBSIDIAN_VAULT_PATH points to a directory that does not exist: "
            f"`{vault_path}`"
        )
        return False

    if not api_key:
        missing.append("ANTHROPIC_API_KEY")

    if missing:
        st.error(
            "Missing required environment variable(s): "
            + ", ".join(f"`{v}`" for v in missing)
            + ". Set them in `.env.local` or your shell environment."
        )
        return False

    return True


# ---------------------------------------------------------------------------
# CSS injection — Exo headings, card hover, amber chips
# ---------------------------------------------------------------------------

_CUSTOM_CSS = """
<style>
/* Card hover effect */
div[data-testid="stExpander"] {
    border: 1px solid #1F2937;
    border-radius: 8px;
    transition: border-color 200ms ease;
}
div[data-testid="stExpander"]:hover {
    border-color: #3B82F6;
}

/* Amber CTA chips */
.amber-chip {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    background-color: #F59E0B;
    color: #0A0A0A;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}

/* Status badges */
.status-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 500;
    letter-spacing: 0.03em;
    text-transform: uppercase;
}
.status-badge.new { background-color: #3B82F6; color: #F9FAFB; }
.status-badge.reviewed { background-color: #10B981; color: #0A0A0A; }
.status-badge.skipped { background-color: #6B7280; color: #F9FAFB; }
.status-badge.queued { background-color: #F59E0B; color: #0A0A0A; }

/* Surface cards */
.surface-card {
    background-color: #111827;
    border: 1px solid #1F2937;
    border-radius: 8px;
    padding: 1rem;
    transition: border-color 200ms ease;
}
.surface-card:hover {
    border-color: #3B82F6;
}
</style>
"""

# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------


def _init_session_state() -> None:
    """Initialize namespaced session state keys."""
    st.session_state.setdefault("dashboard__active_tab", 0)
    st.session_state.setdefault("cockpit__selected_project", None)
    st.session_state.setdefault("workbench__selected_item", None)


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------


def _build_navigation() -> st.Page:
    """Define multipage navigation and return the selected page."""
    dashboard_page = st.Page(
        "pages/1_Dashboard.py",
        title="Dashboard",
        icon=":material/dashboard:",
    )
    cockpit_page = st.Page(
        "pages/2_Project_Cockpit.py",
        title="Project Cockpit",
        icon=":material/rocket_launch:",
    )
    workbench_page = st.Page(
        "pages/3_Workbench.py",
        title="Workbench",
        icon="🔬",
    )

    page = st.navigation([dashboard_page, cockpit_page, workbench_page])
    return page


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Application entry point."""
    _init_session_state()

    # Inject custom CSS
    st.html(_CUSTOM_CSS)

    # Validate environment before proceeding
    if not _validate_env():
        st.stop()

    # Build navigation and run selected page
    page = _build_navigation()
    page.run()


if __name__ == "__main__":
    main()
else:
    # Streamlit runs this module directly (not via __main__)
    main()
