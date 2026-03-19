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
from utils.cockpit_components import (
    build_obsidian_url,
    extract_gsd_context,
    get_project_gsd_plan,
    get_project_overview,
    get_project_plan_files,
)
from utils.page_helpers import (
    EMPTY_NO_API_KEY,
    EMPTY_NO_ITEMS,
    EMPTY_NO_PROJECTS,
    get_vault_path,
    safe_html,
    safe_parse,
)
from utils.smart_matcher import build_smart_project_index
from utils.status_tracker import load_status, set_item_status
from utils.vault_parser import parse_projects
from utils.workbench_tracker import add_to_workbench

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
    """Load smart project index with explicit + inferred matches."""
    return build_smart_project_index(vault_path_str)


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
    gsd_plan_text: str | None = None,
) -> None:
    """Render project header with metadata, badges, and Obsidian link.

    Args:
        project: Project dict with name, status, domain, tech, file_path.
        vault_path: Vault root path.
        vault_name: Vault directory name for Obsidian URL.
        gsd_plan_text: Pre-loaded GSD plan content, or None to load on demand.
    """
    status = safe_html(project.get("status", ""))
    domain = safe_html(project.get("domain", ""))
    tech_list = project.get("tech", [])

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
    gsd_plan = (
        gsd_plan_text
        if gsd_plan_text is not None
        else get_project_gsd_plan(project["name"], vault_path)
    )
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

    # Inferred match indicator
    match_type = item.get("match_type", "explicit")
    confidence = item.get("confidence", 1.0)
    if match_type == "inferred":
        header += (
            f' <span style="background:#374151;color:#9CA3AF;padding:1px 6px;'
            f'border-radius:3px;font-size:0.65rem;margin-left:4px">'
            f"suggested ({confidence:.0%})</span>"
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
    for field in ("why it matters", "what it does", "description", "method", "idea"):
        value = item.get(field, "")
        if value:
            body += f"<br><em>{safe_html(value)}</em>"
            break
    return body


_ITEM_STATUS_OPTIONS = ["new", "reviewed", "queued", "skipped", "workbench"]


def _render_item_card(
    item: dict[str, Any],
    item_id: str,
    current_status: str,
    project: dict[str, Any] | None = None,
) -> None:
    """Render item card with description, quick analysis, actions — all in one container.

    The card contains: header + description, quick analyze button + cached result,
    and the action row (status, workbench, dismiss). Go deep is rendered separately.

    Args:
        item: Item dict from the project index.
        item_id: Unique item identifier for status persistence.
        current_status: Current status string.
        project: Optional project dict — used to attach source_dir when
            sending items to the workbench.
    """
    source_type = item.get("source_type", "item")
    item_name = item["name"]

    with st.container(border=True):
        # Card header + body (description)
        card_html = _render_item_card_header(item)
        card_html += _render_item_card_body(item)
        card_html += "</div>"
        st.markdown(card_html, unsafe_allow_html=True)

        # Quick analyze button + inline result
        if project is not None:
            quick_key = hashlib.sha256(
                f"{item_name}:{project['name']}:quick".encode()
            ).hexdigest()

            if st.button(
                "Analyze",
                key=f"cockpit__analyze_{source_type}_{item_name}",
                icon=":material/bolt:",
                use_container_width=True,
            ):
                _run_analysis(analyze_item_quick, item, project, "Quick analysis")
            else:
                _show_cached_result(quick_key, "Quick analysis")

        # Action row: status selector + workbench + dismiss
        col_status, col_workbench, col_dismiss = st.columns([2, 1, 1])

        with col_status:
            safe_idx = (
                _ITEM_STATUS_OPTIONS.index(current_status)
                if current_status in _ITEM_STATUS_OPTIONS
                else 0
            )
            new_status = st.selectbox(
                "Status",
                _ITEM_STATUS_OPTIONS,
                index=safe_idx,
                key=f"cockpit__item_status_{source_type}_{item_name}",
                label_visibility="collapsed",
            )
            if new_status != current_status:
                set_item_status(item_id, new_status, _STATUS_FILE)

        with col_workbench:
            disabled = current_status == "workbench"
            if st.button(
                "🔬 Workbench",
                key=f"cockpit__item_workbench_{source_type}_{item_name}",
                disabled=disabled,
                use_container_width=True,
            ):
                wb_item = {**item}
                if project:
                    source_dir = project.get("source_dir", "")
                    if source_dir:
                        wb_item["project_dir"] = str(Path(source_dir).expanduser())
                        wb_item["project_name"] = project.get("name", "")
                add_to_workbench(wb_item, previous_status=current_status)
                set_item_status(item_id, "workbench", _STATUS_FILE)
                st.rerun()

        with col_dismiss:
            if st.button(
                "🗃️ Dismiss",
                key=f"cockpit__item_dismiss_{source_type}_{item_name}",
                use_container_width=True,
            ):
                set_item_status(item_id, "dismissed", _STATUS_FILE)
                st.rerun()


# ---------------------------------------------------------------------------
# Flagged items feed [5e] — single-item navigator
# ---------------------------------------------------------------------------


def _render_flagged_items(
    items: list[dict[str, Any]],
    project: dict[str, Any],
) -> None:
    """Render the flagged items feed as a single-item navigator.

    Shows one item at a time with prev/next navigation for readability.
    Dismissed items are hidden by default.

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
        non_dismissed = sorted(
            {s for s in {_item_status(i) for i in items} if s != "dismissed"}
        )
        selected_status = st.segmented_control(
            "Status",
            ["All"] + non_dismissed,
            key="cockpit__status_filter",
            default="All",
        )

    # Apply filters — always exclude dismissed items
    filtered = [i for i in items if _item_status(i) != "dismissed"]
    if selected_source and selected_source != "All":
        filtered = [i for i in filtered if i.get("source_type") == selected_source]
    if selected_status and selected_status != "All":
        filtered = [i for i in filtered if _item_status(i) == selected_status]

    if not filtered:
        st.info("No items match the selected filter.")
        return

    # Navigator index — reset when filter or project changes
    idx_key = f"cockpit__item_idx_{project['name']}"
    if idx_key not in st.session_state or st.session_state[idx_key] >= len(filtered):
        st.session_state[idx_key] = 0

    idx = st.session_state[idx_key]
    item = filtered[idx]
    item_id = f"{item.get('source_type', 'item')}::{item['name']}"
    current_status = _item_status(item)

    # Navigation row
    nav_left, nav_mid, nav_right = st.columns([1, 3, 1])
    with nav_left:
        if st.button("← Prev", key="cockpit__item_prev", disabled=idx == 0):
            st.session_state[idx_key] = idx - 1
            st.rerun()
    with nav_mid:
        st.markdown(
            f'<div style="text-align:center;color:#6B7280;padding:6px 0">'
            f"{idx + 1} of {len(filtered)}"
            f' · <span style="color:#9CA3AF">{current_status}</span></div>',
            unsafe_allow_html=True,
        )
    with nav_right:
        if st.button(
            "Next →", key="cockpit__item_next", disabled=idx == len(filtered) - 1
        ):
            st.session_state[idx_key] = idx + 1
            st.rerun()

    _render_item_card(item, item_id, current_status, project=project)
    _render_deep_analysis(item, project)


# ---------------------------------------------------------------------------
# Analysis buttons [5f] + [5g]
# ---------------------------------------------------------------------------


def _render_deep_analysis(
    item: dict[str, Any],
    project: dict[str, Any],
) -> None:
    """Render Go Deep button and its result below the item card.

    Args:
        item: Item dict.
        project: Project dict.
    """
    source_type = item.get("source_type", "item")
    item_name = item["name"]

    deep_key = hashlib.sha256(
        f"{item_name}:{project['name']}:deep".encode()
    ).hexdigest()

    if st.button(
        "Go deep",
        key=f"cockpit__deep_{source_type}_{item_name}",
        icon=":material/psychology:",
        use_container_width=True,
    ):
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
# Context sources transparency
# ---------------------------------------------------------------------------


def _render_context_sources(
    project: dict[str, Any],
    vault_path: Path,
    plan_files: list[tuple[str, Path]],
    enriched_project: dict[str, Any],
) -> None:
    """Render a transparency expander showing exactly what context Claude receives.

    Args:
        project: Base project dict with file_path.
        vault_path: Vault root path for display.
        plan_files: List of (plan_name, resolved_path) from get_project_plan_files.
        enriched_project: Enriched project dict with 'overview' and 'gsd_plan' keys.
    """
    overview = enriched_project.get("overview", "")
    gsd_context = enriched_project.get("gsd_plan", "")
    total_chars = len(overview) + len(gsd_context)
    n_files = 1 + len(plan_files)

    with st.expander(
        f"📋 Analysis context — {total_chars:,} chars from {n_files} file(s)",
        expanded=False,
    ):
        # File list
        vault_str = str(vault_path)
        project_rel = f"Projects/{project['name']}.md"
        file_lines = [f"📄 <code>{project_rel}</code>"]
        for _, plan_path in plan_files:
            plan_rel = str(plan_path).replace(vault_str + "/", "")
            file_lines.append(f"📄 <code>{plan_rel}</code>")

        st.markdown(
            '<div style="font-size:0.8rem;color:#9CA3AF;margin-bottom:8px">'
            '<strong style="color:#D1D5DB">Files on tap</strong><br>'
            + "<br>".join(file_lines)
            + (
                ""
                if plan_files
                else "<br><span style='color:#6B7280'>⚠ No plan files linked in ## Plans section</span>"
            )
            + "</div>",
            unsafe_allow_html=True,
        )

        # Extracted context preview
        if overview:
            st.caption("Project overview (from .md)")
            st.code(overview, language=None)

        if gsd_context:
            st.caption(
                "GSD context (Context + Architecture sections + active work headers)"
            )
            st.code(gsd_context, language=None)
        elif plan_files:
            st.caption(
                "⚠ No Context / Architecture sections or incomplete headers found in plan files."
            )


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

    # Resolve all plan files linked from the project's ## Plans section
    plan_files = get_project_plan_files(project, vault_path)
    plan_texts = [(name, p.read_text(encoding="utf-8")) for name, p in plan_files]

    # Combined GSD plan text for header UI expander (all plans concatenated)
    combined_plan_text = (
        "\n\n---\n\n".join(f"# {name}\n\n{text}" for name, text in plan_texts)
        if plan_texts
        else None
    )

    # Build enriched project dict for LLM context
    combined_gsd_context = "\n\n".join(
        extract_gsd_context(text) for _, text in plan_texts
    )
    enriched_project = {
        **project,
        "overview": get_project_overview(project),
        "gsd_plan": combined_gsd_context,
    }

    # Project name at top, flagged items next (highest value), metadata at bottom
    st.markdown(f"## {safe_html(project['name'])}")

    # Flagged items feed
    items = project_index.get(selected_name, [])
    _render_flagged_items(items, enriched_project)

    # Project metadata and context below the feed
    st.divider()
    _render_project_header(project, vault_path, vault_name, combined_plan_text)

    # Context sources transparency expander
    _render_context_sources(project, vault_path, plan_files, enriched_project)


_run_cockpit()
