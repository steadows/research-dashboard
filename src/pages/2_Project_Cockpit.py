"""Project Cockpit page — project-scoped workspace with analysis buttons.

Renders a sidebar with project selection, a project header with metadata,
a flagged items feed, and Analyze/Go Deep buttons for Claude API analysis.
All vault-sourced strings are escaped via safe_html() before unsafe_allow_html.
"""

import hashlib
import logging
from pathlib import Path
from typing import Any

import streamlit as st

from utils.claude_client import analyze_item_deep, analyze_item_quick
from utils.cockpit_components import build_obsidian_url, get_project_gsd_plan
from utils.page_helpers import (
    EMPTY_NO_API_KEY,
    EMPTY_NO_ITEMS,
    EMPTY_NO_PROJECTS,
    get_vault_path,
    safe_html,
    safe_parse,
)
from utils.status_tracker import get_item_status, load_status, set_item_status
from utils.vault_parser import build_project_index, parse_projects

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_STATUS_FILE = Path.home() / ".research-dashboard" / "status.json"

_SOURCE_COLORS: dict[str, str] = {
    "method": "#8B5CF6",
    "tool": "#10B981",
}


# ---------------------------------------------------------------------------
# Cached data loaders
# ---------------------------------------------------------------------------


@st.cache_data(ttl=3600)
def _load_projects(vault_path_str: str) -> list[dict[str, Any]]:
    """Load projects with caching."""
    return parse_projects(Path(vault_path_str))


@st.cache_data(ttl=3600)
def _load_project_index(vault_path_str: str) -> dict[str, list[dict[str, Any]]]:
    """Load project index with caching."""
    return build_project_index(Path(vault_path_str))


# ---------------------------------------------------------------------------
# Sidebar — project selection [5c]
# ---------------------------------------------------------------------------


def _render_project_sidebar(
    projects: list[dict[str, Any]],
    project_index: dict[str, list[dict[str, Any]]],
) -> str | None:
    """Render sidebar with project selector and search filter.

    Uses selectbox for potentially many projects (per selection widget skill).

    Args:
        projects: List of project dicts from vault.
        project_index: Mapping of project name to flagged items.

    Returns:
        Selected project name, or None if no projects.
    """
    with st.sidebar:
        st.subheader("Projects")

        if not projects:
            st.caption(EMPTY_NO_PROJECTS)
            return None

        # Text search filter
        search = st.text_input(
            "Search projects",
            key="cockpit__project_search",
            placeholder="Filter by name...",
        )

        filtered = projects
        if search:
            search_lower = search.lower()
            filtered = [p for p in projects if search_lower in p["name"].lower()]

        if not filtered:
            st.caption("No projects match your search.")
            return None

        # Build option labels with item counts
        options = [p["name"] for p in filtered]
        labels = []
        for name in options:
            count = len(project_index.get(name, []))
            label = f"{name} ({count})" if count else name
            labels.append(label)

        # Key-only pattern (per widget pitfalls skill)
        if "cockpit__project_selector" not in st.session_state:
            default = st.session_state.get("cockpit__selected_project")
            if default and default in options:
                st.session_state.cockpit__project_selector = default
            else:
                st.session_state.cockpit__project_selector = options[0]

        selected_name = st.selectbox(
            "Select project",
            options=options,
            format_func=lambda n: labels[options.index(n)],
            key="cockpit__project_selector",
        )

        st.session_state.cockpit__selected_project = selected_name

        # Sidebar refresh
        if st.button(
            "Refresh data", use_container_width=True, icon=":material/refresh:"
        ):
            st.cache_data.clear()
            st.rerun()

        return selected_name


# ---------------------------------------------------------------------------
# Project header [5d]
# ---------------------------------------------------------------------------


def _render_project_header(
    project: dict[str, Any],
    vault_path: Path,
    vault_name: str,
) -> None:
    """Render project header with metadata, badges, and Obsidian link.

    Args:
        project: Project dict with name, status, domain, tech, file_path.
        vault_path: Vault root path.
        vault_name: Vault directory name for Obsidian URL.
    """
    name = safe_html(project["name"])
    status = safe_html(project.get("status", ""))
    domain = safe_html(project.get("domain", ""))
    tech_list = project.get("tech", [])

    # Header row
    st.markdown(f"## {name}")

    # Badges row
    badge_parts = []
    if status:
        badge_parts.append(f'<span class="status-badge">{status}</span>')
    if domain:
        badge_parts.append(
            f'<span style="color:#60A5FA;font-weight:500">{domain}</span>'
        )
    if badge_parts:
        st.markdown(" ".join(badge_parts), unsafe_allow_html=True)

    # Tech stack chips
    if tech_list:
        chips = " ".join(
            f'<span class="amber-chip">{safe_html(t)}</span>' for t in tech_list
        )
        st.markdown(chips, unsafe_allow_html=True)

    # Obsidian link
    rel_path = f"Projects/{project['name']}.md"
    obs_url = build_obsidian_url(vault_name, rel_path)
    st.markdown(f"[:material/open_in_new: Open in Obsidian]({obs_url})")

    # GSD plan summary
    gsd_plan = get_project_gsd_plan(project["name"], vault_path)
    if gsd_plan:
        with st.expander(
            "GSD plan summary", expanded=False, icon=":material/checklist:"
        ):
            st.markdown(gsd_plan)


# ---------------------------------------------------------------------------
# Item card rendering [5e] + [5h] refactor
# ---------------------------------------------------------------------------


def _render_item_card_header(item: dict[str, Any]) -> str:
    """Build the HTML header section of an item card.

    Args:
        item: Item dict with name, source_type, source, status.

    Returns:
        HTML string for the card header.
    """
    name = safe_html(item["name"])
    source_type = item.get("source_type", "")
    color = _SOURCE_COLORS.get(source_type, "#6B7280")
    source_label = safe_html(source_type.capitalize())
    source = safe_html(item.get("source", ""))
    status = safe_html(item.get("status", ""))

    header = (
        f'<div class="surface-card">'
        f'<span style="background:{color};color:#fff;padding:2px 8px;'
        f'border-radius:4px;font-size:0.7rem">{source_label}</span> '
        f"<strong>{name}</strong>"
    )
    if source:
        header += f'<br><span style="color:#9CA3AF;font-size:0.8em">{source}</span>'
    if status:
        header += f' <span class="status-badge">{status}</span>'

    return header


def _render_item_card_body(item: dict[str, Any]) -> str:
    """Build the HTML body section of an item card.

    Args:
        item: Item dict with optional description fields.

    Returns:
        HTML string for the card body.
    """
    body = ""
    for field in ("why it matters", "what it does", "description"):
        value = item.get(field, "")
        if value:
            body += f"<br><em>{safe_html(value)}</em>"
            break
    return body


def _render_item_card(item: dict[str, Any], idx: int) -> None:
    """Render a single item card with source badge and status selector.

    Args:
        item: Item dict from the project index.
        idx: Index for unique widget keys.
    """
    card_html = _render_item_card_header(item)
    card_html += _render_item_card_body(item)
    card_html += "</div>"
    st.markdown(card_html, unsafe_allow_html=True)

    # Status selector
    item_id = f"{item.get('source_type', 'item')}::{item['name']}"
    current = get_item_status(item_id, _STATUS_FILE)
    status_options = ["new", "reviewed", "queued", "skipped"]
    current_idx = status_options.index(current) if current in status_options else 0
    new_status = st.selectbox(
        "Status",
        status_options,
        index=current_idx,
        key=f"cockpit__item_status_{item.get('source_type', 'item')}_{item.get('name', idx)}",
        label_visibility="collapsed",
    )
    if new_status != current:
        set_item_status(item_id, new_status, _STATUS_FILE)


# ---------------------------------------------------------------------------
# Flagged items feed [5e]
# ---------------------------------------------------------------------------


def _render_flagged_items(
    items: list[dict[str, Any]],
    project: dict[str, Any],
) -> None:
    """Render the flagged items feed with filters and analysis buttons.

    Args:
        items: List of item dicts for the selected project.
        project: Project dict for analysis context.
    """
    st.subheader("Flagged items")

    if not items:
        st.caption(EMPTY_NO_ITEMS)
        return

    # Load status once to avoid N+1 disk reads
    status_data = load_status(_STATUS_FILE)
    item_statuses = status_data.get("items", {})

    def _item_status(item: dict[str, Any]) -> str:
        item_id = f"{item.get('source_type', 'item')}::{item.get('name', '')}"
        return item_statuses.get(item_id, "new")

    # Filters
    col1, col2 = st.columns(2)

    with col1:
        source_types = sorted({i.get("source_type", "") for i in items})
        selected_source = st.segmented_control(
            "Source",
            ["All"] + source_types,
            key="cockpit__source_filter",
            default="All",
        )

    with col2:
        status_opts = sorted({_item_status(i) for i in items})
        selected_status = st.segmented_control(
            "Status",
            ["All"] + status_opts,
            key="cockpit__status_filter",
            default="All",
        )

    # Apply filters
    filtered = items
    if selected_source and selected_source != "All":
        filtered = [i for i in filtered if i.get("source_type") == selected_source]
    if selected_status and selected_status != "All":
        filtered = [i for i in filtered if _item_status(i) == selected_status]

    # Render cards in 2-column grid
    cols = st.columns(2)
    for idx, item in enumerate(filtered):
        with cols[idx % 2]:
            _render_item_card(item, idx)
            _render_analysis_buttons(item, project, idx)


# ---------------------------------------------------------------------------
# Analysis buttons [5f] + [5g]
# ---------------------------------------------------------------------------


def _render_analysis_buttons(
    item: dict[str, Any],
    project: dict[str, Any],
    idx: int,
) -> None:
    """Render Analyze (quick) and Go Deep buttons with cached results.

    Uses key-only pattern for buttons. Shows cached results with timestamp.

    Args:
        item: Item dict.
        project: Project dict.
        idx: Index for unique widget keys.
    """
    col_quick, col_deep = st.columns(2)

    # Build cache keys for display check
    quick_key = hashlib.sha256(
        f"{item['name']}:{project['name']}:quick".encode()
    ).hexdigest()
    deep_key = hashlib.sha256(
        f"{item['name']}:{project['name']}:deep".encode()
    ).hexdigest()

    with col_quick:
        quick_clicked = st.button(
            "Analyze",
            key=f"cockpit__analyze_{item.get('source_type', 'item')}_{item.get('name', idx)}",
            icon=":material/bolt:",
            use_container_width=True,
        )
        if quick_clicked:
            _run_analysis(analyze_item_quick, item, project, "Quick analysis")
        else:
            _show_cached_result(quick_key, "Quick analysis")

    with col_deep:
        deep_clicked = st.button(
            "Go deep",
            key=f"cockpit__deep_{item.get('source_type', 'item')}_{item.get('name', idx)}",
            icon=":material/psychology:",
            use_container_width=True,
        )
        if deep_clicked:
            _run_analysis(analyze_item_deep, item, project, "Deep analysis")
        else:
            _show_cached_result(deep_key, "Deep analysis")


def _run_analysis(
    analysis_fn: Any,
    item: dict[str, Any],
    project: dict[str, Any],
    label: str,
) -> None:
    """Run an analysis function with user-friendly error handling.

    Args:
        analysis_fn: analyze_item_quick or analyze_item_deep.
        item: Item dict.
        project: Project dict.
        label: Display label (e.g. "Quick analysis").
    """
    spinner_msg = "Analyzing..." if "Quick" in label else "Deep analysis in progress..."
    try:
        with st.spinner(spinner_msg):
            result = analysis_fn(item, project, _STATUS_FILE)
        _render_analysis_result(result, label)
    except ValueError:
        st.error(EMPTY_NO_API_KEY)
    except Exception:
        logger.warning("Analysis failed for %s", item.get("name"), exc_info=True)
        st.error(
            f"{label} failed. Check your API key and network connection, "
            "then try again."
        )


def _show_cached_result(cache_key: str, label: str) -> None:
    """Show cached analysis result if available.

    Args:
        cache_key: SHA-256 cache key.
        label: Display label for the result.
    """
    from utils.status_tracker import get_analysis_cache

    cached = get_analysis_cache(cache_key, _STATUS_FILE)
    if cached is not None:
        _render_analysis_result(cached, f"{label} (cached)")


def _render_analysis_result(result: dict[str, Any], title: str) -> None:
    """Render an analysis result in a themed container.

    Uses font-family: inherit for theme consistency (per LLM apps skill).

    Args:
        result: Analysis result dict with 'response', 'model', 'cost'.
        title: Title for the result section.
    """
    response_text = safe_html(result.get("response", ""))
    model = safe_html(result.get("model", ""))
    cost = result.get("cost", 0.0)

    # Escape dollar signs for Streamlit markdown (per LLM apps skill)
    response_text = response_text.replace("$", "\\$")

    st.markdown(
        f'<div style="'
        f"font-family: inherit; font-size: 0.9rem; line-height: 1.65; "
        f"color: inherit; "
        f"background: rgba(31, 119, 180, 0.18); "
        f"border-left: 4px solid rgba(31, 119, 180, 0.6); "
        f"border-radius: 0 0.4rem 0.4rem 0; "
        f'padding: 0.75rem 1rem;">'
        f"<strong>{safe_html(title)}</strong><br>"
        f"{response_text}</div>",
        unsafe_allow_html=True,
    )
    st.caption(f"Model: {model} | Cost: ${cost:.4f}")


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------


def _run_cockpit() -> None:
    """Main entry point for the Project Cockpit page."""
    st.header("Project Cockpit")

    vault_path = get_vault_path()
    vault_str = str(vault_path)
    vault_name = vault_path.name

    # Load data with graceful fallbacks
    projects = safe_parse(_load_projects, vault_str, fallback=[], label="projects")
    project_index = safe_parse(
        _load_project_index, vault_str, fallback={}, label="project index"
    )

    # Sidebar — project selection
    selected_name = _render_project_sidebar(projects, project_index)

    if not selected_name:
        st.caption("Select a project from the sidebar to begin.")
        return

    # Find selected project
    project = next((p for p in projects if p["name"] == selected_name), None)
    if not project:
        st.caption(f"Project '{selected_name}' not found in vault.")
        return

    # Project header
    _render_project_header(project, vault_path, vault_name)

    # Flagged items feed
    items = project_index.get(selected_name, [])
    _render_flagged_items(items, project)


_run_cockpit()
