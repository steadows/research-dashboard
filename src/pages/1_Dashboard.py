"""Dashboard page — global intel feed with 7 tabs.

Tabs: Home, Blog Queue, Tools Radar, Research Archive, Weekly AI Signal, Agentic Hub, Graph Insights.
All vault-sourced strings are escaped via safe_html() before unsafe_allow_html.
Parser calls are wrapped with @st.cache_data(ttl=3600) for performance.
"""

import logging
from pathlib import Path
from typing import Any

import streamlit as st

from utils.knowledge_linker import (
    build_entity_index,
    link_directory,
    link_satellites_to_projects,
)
from utils.blog_publisher import (
    archive_item,
    get_draft_path,
    read_draft_body,
    write_draft_mdx,
)
from utils.blog_queue_parser import parse_blog_queue
from utils.graph_engine import (
    build_vault_graph,
    compute_centrality_metrics,
    detect_communities,
    get_graph_health,
    suggest_links,
)
from utils.claude_client import (
    analyze_blog_potential,
    deep_read_paper,
    generate_blog_draft,
    generate_linkedin_post,
    summarize_instagram_post,
    summarize_paper,
    summarize_tool,
)
from utils.page_helpers import (
    EMPTY_NO_BLOG,
    EMPTY_NO_REPORTS,
    EMPTY_NO_TOOLS,
    get_category_color,
    get_vault_path,
    render_context_sources,
    safe_html,
    safe_parse,
)
from utils.paper_fetcher import get_cached_paper_context
from utils.instagram_parser import parse_instagram_posts
from utils.reports_parser import parse_journalclub_reports, parse_tldr_reports
from utils.status_tracker import get_item_status, set_item_status
from utils.tools_parser import parse_tools
from utils.workbench_tracker import (
    add_to_workbench,
    get_workbench_items,
    make_item_key,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Knowledge linker — auto-link vault on first load, manual re-link button
# ---------------------------------------------------------------------------


_LINK_TARGETS: list[tuple[str, str]] = [
    ("Instagram", "Research/Instagram"),
    ("Dev Journal", "Dev Journal"),
    ("JournalClub", "Research/JournalClub"),
    ("TLDR", "Research/TLDR"),
    ("Blog Queue", "Writing"),
    ("Blueprints", "Blueprints"),
    ("Plans", "Plans"),
    ("Reference", "Reference"),
    ("Journal", "Journal"),
]


def _link_vault_with_progress(vault_path: Path, progress_bar: Any) -> dict[str, int]:
    """Run knowledge linker across all vault directories with progress updates.

    Args:
        vault_path: Root path to the Obsidian vault.
        progress_bar: Streamlit progress bar element to update.

    Returns:
        Dict mapping directory name to number of files modified.
    """
    total_steps = len(_LINK_TARGETS) + 2  # +1 entity index, +1 satellites
    results: dict[str, int] = {}

    progress_bar.progress(0, text="Building entity index…")
    entities = build_entity_index(vault_path)

    for i, (name, rel_path) in enumerate(_LINK_TARGETS):
        frac = (i + 1) / total_steps
        progress_bar.progress(frac, text=f"Linking {name}…")
        target_dir = vault_path / rel_path
        results[name] = link_directory(vault_path, target_dir, entities=entities)

    progress_bar.progress(
        (len(_LINK_TARGETS) + 1) / total_steps, text="Linking satellites…"
    )
    results["Satellites"] = link_satellites_to_projects(vault_path)

    progress_bar.progress(1.0, text="Done")
    return results


def _auto_link_vault(vault_path: Path) -> None:
    """Run knowledge linker once per session on Dashboard startup.

    Uses session state guard to avoid re-running on every Streamlit rerun.
    Must be called before cached parsers so wiki-links are present when parsed.

    Args:
        vault_path: Root path to the Obsidian vault.
    """
    if st.session_state.get("dashboard__vault_linked"):
        return

    progress = st.progress(0, text="Linking vault…")
    results = _link_vault_with_progress(vault_path, progress)
    progress.empty()

    st.session_state["dashboard__vault_linked"] = True
    st.session_state["dashboard__vault_link_results"] = results

    total = sum(results.values())
    if total > 0:
        st.toast(f"🔗 Vault linked: {total} files updated")
    logger.info("Auto-link results: %s", results)


def _run_manual_link(vault_path: Path) -> None:
    """Run knowledge linker on demand and refresh cached data.

    Args:
        vault_path: Root path to the Obsidian vault.
    """
    progress = st.progress(0, text="Linking vault…")
    results = _link_vault_with_progress(vault_path, progress)
    progress.empty()

    total = sum(results.values())
    st.session_state["dashboard__vault_linked"] = True
    st.session_state["dashboard__vault_link_results"] = results

    if total > 0:
        parts = [f"{k}: {v}" for k, v in results.items() if v > 0]
        st.toast(f"🔗 Linked {total} files — {', '.join(parts)}")
        st.cache_resource.clear()
        st.cache_data.clear()
        st.rerun()
    else:
        st.toast("🔗 All vault files already linked")


# ---------------------------------------------------------------------------
# Cached parser wrappers — @st.cache_data(ttl=3600)
# ---------------------------------------------------------------------------


@st.cache_data(ttl=3600)
def _load_blog_queue(vault_path_str: str) -> list[dict[str, Any]]:
    """Load blog queue items with caching."""
    return parse_blog_queue(Path(vault_path_str))


@st.cache_data(ttl=3600)
def _load_tools(vault_path_str: str) -> list[dict[str, Any]]:
    """Load tools radar items with caching."""
    return parse_tools(Path(vault_path_str))


@st.cache_data(ttl=3600)
def _load_journalclub_reports(vault_path_str: str) -> list[dict[str, Any]]:
    """Load JournalClub reports with caching."""
    return parse_journalclub_reports(Path(vault_path_str))


@st.cache_data(ttl=3600)
def _load_tldr_reports(vault_path_str: str) -> list[dict[str, Any]]:
    """Load TLDR reports with caching."""
    return parse_tldr_reports(Path(vault_path_str))


@st.cache_data(ttl=3600)
def _load_instagram_posts(vault_path_str: str) -> list[dict[str, Any]]:
    """Load Instagram posts with caching."""
    return parse_instagram_posts(Path(vault_path_str))


@st.cache_resource(ttl=3600)
def _load_vault_graph(vault_path_str: str):
    """Load vault graph with caching (non-serializable, uses cache_resource)."""
    return build_vault_graph(vault_path_str)


@st.cache_data(ttl=3600)
def _load_graph_metrics(vault_path_str: str) -> dict:
    """Load graph metrics with caching."""
    G = _load_vault_graph(vault_path_str)
    metrics = compute_centrality_metrics(G)
    communities = detect_communities(G)
    health = get_graph_health(G)
    return {
        "metrics": metrics,
        "communities": [list(c) for c in communities],
        "health": health,
        "node_count": G.number_of_nodes(),
    }


# ---------------------------------------------------------------------------
# Sidebar — refresh button
# ---------------------------------------------------------------------------


def _render_sidebar() -> None:
    """Render sidebar with refresh button."""
    with st.sidebar:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_resource.clear()
            st.cache_data.clear()
            st.rerun()


# ---------------------------------------------------------------------------
# Home tab
# ---------------------------------------------------------------------------


def _render_home_tab(
    jc_reports: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    blog_items: list[dict[str, Any]],
    tldr_reports: list[dict[str, Any]],
) -> None:
    """Render the Home tab with summary widgets."""
    st.subheader("Welcome to Research Intelligence")

    col1, col2 = st.columns(2)

    with col1:
        _render_top_picks(jc_reports)
        _render_top_tools(tools)

    with col2:
        _render_top_blog_ideas(blog_items)
        _render_ai_signal_excerpt(tldr_reports)


def _render_top_picks(jc_reports: list[dict[str, Any]]) -> None:
    """Show latest JournalClub Top Picks."""
    st.markdown("#### 📋 Latest JournalClub Top Picks")
    if not jc_reports:
        st.caption(EMPTY_NO_REPORTS)
        return

    latest = jc_reports[0]
    top_picks = latest.get("sections", {}).get("Top Picks This Week", "") or latest.get(
        "sections", {}
    ).get("Top Picks", "")
    if top_picks:
        # No unsafe_allow_html — Streamlit markdown is XSS-safe by default
        st.markdown(top_picks)
    else:
        st.caption(f"No Top Picks in report from {latest['date']}")


def _render_top_tools(tools: list[dict[str, Any]]) -> None:
    """Show top 3 tools from the Tools Radar."""
    st.markdown("#### 🔧 Top Tools")
    if not tools:
        st.caption(EMPTY_NO_TOOLS)
        return

    for tool in tools[:3]:
        name = safe_html(tool["name"])
        category = safe_html(tool.get("category", ""))
        color = get_category_color(tool.get("category", ""))
        st.markdown(
            f'<span style="color:{color};font-weight:600">{name}</span>'
            f' <span style="color:#9CA3AF;font-size:0.8em">({category})</span>',
            unsafe_allow_html=True,
        )


def _render_top_blog_ideas(blog_items: list[dict[str, Any]]) -> None:
    """Show top 3 blog ideas."""
    st.markdown("#### ✍️ Blog Ideas")
    if not blog_items:
        st.caption(EMPTY_NO_BLOG)
        return

    for item in blog_items[:3]:
        name = safe_html(item["name"])
        status = safe_html(item.get("status", ""))
        st.markdown(
            f'**{name}** <span class="status-badge">{status}</span>',
            unsafe_allow_html=True,
        )


def _render_ai_signal_excerpt(tldr_reports: list[dict[str, Any]]) -> None:
    """Show latest AI Signal excerpt from TLDR."""
    st.markdown("#### 📰 Weekly AI Signal")
    if not tldr_reports:
        st.caption(EMPTY_NO_REPORTS)
        return

    latest = tldr_reports[0]
    signal = latest.get("ai_signal", "")
    if signal:
        # Truncate long signals for the home tab excerpt
        excerpt = signal[:500] + "..." if len(signal) > 500 else signal
        # No unsafe_allow_html — Streamlit markdown is XSS-safe by default
        st.markdown(excerpt)
        st.caption(f"From TLDR {latest['date']}")
    else:
        st.caption(f"No AI Signal in report from {latest['date']}")


# ---------------------------------------------------------------------------
# Blog Queue tab
# ---------------------------------------------------------------------------


def _render_blog_queue_tab(blog_items: list[dict[str, Any]]) -> None:
    """Render Blog Queue tab as a single-item review flow."""
    st.subheader("✍️ Blog Queue")

    if not blog_items:
        st.info(EMPTY_NO_BLOG)
        return

    # Status filter
    all_statuses = sorted({i.get("status", "") for i in blog_items})
    selected_status = st.selectbox(
        "Filter by status",
        ["All"] + all_statuses,
        key="dashboard__blog_status_filter",
    )

    filtered = _filter_by_status(blog_items, selected_status)
    if not filtered:
        st.info("No items match the selected filter.")
        return

    # Reset index when filter changes or index out of range
    idx_key = "dashboard__blog_queue_idx"
    if idx_key not in st.session_state or st.session_state[idx_key] >= len(filtered):
        st.session_state[idx_key] = 0

    idx = st.session_state[idx_key]
    item = filtered[idx]
    item_id = f"blog::{item['name']}"
    current_status = get_item_status(item_id)

    # Navigation row
    nav_left, nav_mid, nav_right = st.columns([1, 3, 1])
    with nav_left:
        if st.button("← Prev", key="dashboard__blog_prev", disabled=idx == 0):
            st.session_state[idx_key] = idx - 1
            st.rerun()
    with nav_mid:
        st.markdown(
            f'<div style="text-align:center;color:#6B7280;padding:6px 0">'
            f"{idx + 1} of {len(filtered)}"
            f' · <span style="color:#9CA3AF">{safe_html(current_status)}</span></div>',
            unsafe_allow_html=True,
        )
    with nav_right:
        if st.button(
            "Next →", key="dashboard__blog_next", disabled=idx == len(filtered) - 1
        ):
            st.session_state[idx_key] = idx + 1
            st.rerun()

    _render_blog_review_card(item, item_id, current_status)


_STATUS_OPTIONS = ["new", "reviewed", "queued", "drafted", "dismissed", "skipped"]


def _render_blog_review_card(
    item: dict[str, Any], item_id: str, current_status: str
) -> None:
    """Render a single full-width blog review card with full action pipeline."""
    name = safe_html(item["name"])
    hook = safe_html(item.get("hook", ""))
    source = safe_html(item.get("source paper") or item.get("source", ""))
    tags_raw = item.get("tags", "")
    projects = item.get("projects", [])
    added = safe_html(item.get("added", ""))

    tag_html = _build_tag_html(tags_raw)
    project_html = _build_project_html(projects)

    # Auto-fetch paper summary (Haiku, cached) — shown inline on the card
    summary_key = f"dashboard__blog_summary_{item['name']}"
    if summary_key not in st.session_state:
        with st.spinner("Summarizing paper…"):
            st.session_state[summary_key] = summarize_paper(item)
    summary = safe_html(st.session_state[summary_key])

    _render_card_html(name, hook, summary, source, project_html, tag_html, added)
    _render_action_row(item, item_id, current_status)
    _render_analysis_panel(item, current_status)


def _build_tag_html(tags_raw: str) -> str:
    """Build HTML badge string for comma-separated tags."""
    if not tags_raw:
        return ""
    tag_list = [t.strip() for t in tags_raw.split(",") if t.strip()]
    return " ".join(
        f'<span style="background:#1F2937;color:#9CA3AF;font-size:0.72rem;'
        f'padding:2px 8px;border-radius:4px">{safe_html(t)}</span>'
        for t in tag_list
    )


def _build_project_html(projects: list[str]) -> str:
    """Build HTML badge string for project wiki-link names."""
    if not projects:
        return ""
    return " ".join(
        f'<span style="background:#1E3A5F;color:#60A5FA;font-size:0.72rem;'
        f'padding:2px 8px;border-radius:4px">{safe_html(p)}</span>'
        for p in projects
    )


def _render_card_html(
    name: str,
    hook: str,
    summary: str,
    source: str,
    project_html: str,
    tag_html: str,
    added: str,
) -> None:
    """Render the main card HTML block."""
    card_html = f"""
<div class="surface-card" style="padding:24px">
  <div style="font-size:1.2rem;font-weight:600;line-height:1.4;margin-bottom:12px">{name}</div>
"""
    if hook:
        card_html += (
            f'  <div style="color:#D1D5DB;font-size:0.95rem;line-height:1.6;margin-bottom:16px;'
            f'border-left:3px solid #3B82F6;padding-left:12px">{hook}</div>\n'
        )
    if summary:
        card_html += (
            f'  <div style="color:#9CA3AF;font-size:0.875rem;line-height:1.65;'
            f'margin-bottom:16px">{summary}</div>\n'
        )
    if source:
        card_html += (
            f'  <div style="color:#6B7280;font-size:0.8rem;margin-bottom:12px">'
            f'<span style="color:#9CA3AF">Source:</span> {source}</div>\n'
        )
    if project_html:
        card_html += f'  <div style="margin-bottom:10px">{project_html}</div>\n'
    if tag_html:
        card_html += f'  <div style="margin-bottom:8px">{tag_html}</div>\n'
    if added:
        card_html += f'  <div style="color:#4B5563;font-size:0.72rem;margin-top:8px">Added {added}</div>\n'
    card_html += "</div>"
    st.markdown(card_html, unsafe_allow_html=True)


def _render_action_row(item: dict[str, Any], item_id: str, current_status: str) -> None:
    """Render the action buttons row: Deep Read, Analyze, Generate Draft, Status, Dismiss."""
    item_name = item["name"]
    col_deep, col_analyze, col_draft, col_status, col_dismiss = st.columns(
        [1, 2, 2, 1, 1]
    )

    with col_deep:
        _handle_deep_read_button(item, item_name)

    with col_analyze:
        _handle_analyze_button(item, item_name)

    with col_draft:
        _handle_draft_button(item, item_name, current_status)

    with col_status:
        _handle_status_selector(item_id, item_name, current_status)

    with col_dismiss:
        _handle_dismiss_button(item, item_id, item_name, current_status)


def _handle_deep_read_button(item: dict[str, Any], item_name: str) -> None:
    """Render and handle the Deep Read toggle button."""
    deep_key = f"dashboard__blog_deep_read_{item_name}"
    if st.button("🔬 Deep Read", key=f"dashboard__blog_deep_btn_{item_name}"):
        if deep_key not in st.session_state:
            with st.spinner("Deep reading with Sonnet…"):
                st.session_state[deep_key] = deep_read_paper(item)


def _handle_analyze_button(item: dict[str, Any], item_name: str) -> None:
    """Render and handle the Analyze Blog Potential button."""
    analysis_key = f"dashboard__blog_analysis_{item_name}"
    if st.button("✨ Analyze", key=f"dashboard__blog_analyze_{item_name}"):
        with st.spinner("Analyzing…"):
            try:
                result = analyze_blog_potential(item)
                st.session_state[analysis_key] = result["response"]
            except Exception as exc:
                st.error(f"Analysis failed: {exc}")


def _handle_draft_button(
    item: dict[str, Any], item_name: str, current_status: str
) -> None:
    """Render and handle the Generate Draft button."""
    draft_exists = get_draft_path(item) is not None
    disabled = draft_exists or current_status == "drafted"

    if st.button(
        "📝 Generate Draft",
        key=f"dashboard__blog_draft_btn_{item_name}",
        disabled=disabled,
    ):
        _run_draft_generation(item, item_name)


def _run_draft_generation(item: dict[str, Any], item_name: str) -> None:
    """Execute the full draft generation pipeline."""
    linkedin_key = f"dashboard__blog_linkedin_{item_name}"
    draft_path_key = f"dashboard__blog_draft_path_{item_name}"

    with st.spinner("Drafting with Sonnet…"):
        body = generate_blog_draft(item)

    if not body:
        st.error("Draft generation failed. Check API key and try again.")
        return

    with st.spinner("Generating LinkedIn post…"):
        excerpt = body[:200]
        linkedin = generate_linkedin_post(item, excerpt)

    try:
        dest = write_draft_mdx(item, body)
    except FileExistsError as exc:
        st.warning(str(exc))
        dest = get_draft_path(item)

    set_item_status(f"blog::{item_name}", "drafted")
    st.session_state[linkedin_key] = linkedin
    st.session_state[draft_path_key] = str(dest)
    st.success(f"Draft written to `{dest}`")
    st.rerun()


def _handle_status_selector(item_id: str, item_name: str, current_status: str) -> None:
    """Render the status dropdown."""
    current_idx = (
        _STATUS_OPTIONS.index(current_status)
        if current_status in _STATUS_OPTIONS
        else 0
    )
    new_status = st.selectbox(
        "Status",
        _STATUS_OPTIONS,
        index=current_idx,
        key=f"dashboard__blog_status_{item_name}",
        label_visibility="collapsed",
    )
    if new_status != current_status:
        set_item_status(item_id, new_status)


def _handle_dismiss_button(
    item: dict[str, Any],
    item_id: str,
    item_name: str,
    current_status: str,
) -> None:
    """Render and handle the Dismiss button."""
    if current_status == "dismissed":
        st.markdown(
            '<span style="color:#6B7280;font-size:0.75rem">archived</span>',
            unsafe_allow_html=True,
        )
        return

    vault_path_str = st.session_state.get("vault_path_str", "")
    if st.button("🗃️ Dismiss", key=f"dashboard__blog_dismiss_{item_name}"):
        if vault_path_str:
            try:
                archive_item(item, Path(vault_path_str))
            except Exception as exc:
                logger.warning("archive_item failed for %s: %s", item_name, exc)
        set_item_status(item_id, "dismissed")
        st.rerun()


def _render_analysis_panel(item: dict[str, Any], current_status: str) -> None:
    """Render deep read, analysis results, and draft expanders below the card."""
    item_name = item["name"]

    # Context sources expander — passive cache inspection only (no network calls)
    source = item.get("source paper") or item.get("source", "")
    paper_ctx = get_cached_paper_context(source) if source else None
    connected_projects = item.get("projects", [])
    render_context_sources(paper_ctx, connected_projects)

    # Deep Read result
    deep_key = f"dashboard__blog_deep_read_{item_name}"
    if deep_key in st.session_state and st.session_state[deep_key]:
        with st.expander("🔬 Deep Read"):
            st.markdown(st.session_state[deep_key])

    # Blog potential analysis
    analysis_key = f"dashboard__blog_analysis_{item_name}"
    if analysis_key in st.session_state:
        _render_blog_potential_panel(st.session_state[analysis_key])

    # Draft view — auto-load for drafted items
    draft_path_key = f"dashboard__blog_draft_path_{item_name}"
    linkedin_key = f"dashboard__blog_linkedin_{item_name}"

    if current_status == "drafted" or draft_path_key in st.session_state:
        _render_draft_panel(item, draft_path_key, linkedin_key)


def _render_blog_potential_panel(analysis_text: str) -> None:
    """Render the blog potential analysis as a formatted card."""
    lines = analysis_text.strip().splitlines()
    analysis_html = '<div class="surface-card" style="padding:16px;margin-top:8px">'
    for line in lines:
        if ":" in line:
            label, _, rest = line.partition(":")
            analysis_html += (
                f'<div style="margin-bottom:8px">'
                f'<span style="color:#F59E0B;font-size:0.75rem;font-weight:600">'
                f"{safe_html(label.strip())}</span>"
                f'<span style="color:#D1D5DB;font-size:0.85rem"> {safe_html(rest.strip())}</span>'
                f"</div>"
            )
        elif line.strip():
            analysis_html += (
                f'<div style="color:#9CA3AF;font-size:0.85rem">{safe_html(line)}</div>'
            )
    analysis_html += "</div>"
    st.markdown(analysis_html, unsafe_allow_html=True)


def _render_draft_panel(
    item: dict[str, Any], draft_path_key: str, linkedin_key: str
) -> None:
    """Render the draft expander and LinkedIn post for drafted items."""
    # Resolve path
    draft_path = st.session_state.get(draft_path_key)
    if not draft_path:
        path_obj = get_draft_path(item)
        draft_path = str(path_obj) if path_obj else None

    if draft_path:
        st.markdown(
            f'<div style="color:#10B981;font-size:0.8rem;margin:8px 0">📄 Draft: '
            f"<code>{safe_html(draft_path)}</code></div>",
            unsafe_allow_html=True,
        )

    # Render body
    body = read_draft_body(item)
    if body:
        with st.expander("📄 View Draft"):
            st.markdown(body)

    # LinkedIn post
    linkedin = st.session_state.get(linkedin_key)
    if linkedin:
        st.text_area(
            "LinkedIn announcement",
            value=linkedin,
            height=120,
            key=f"dashboard__blog_linkedin_display_{item['name']}",
        )


def _filter_by_status(items: list[dict[str, Any]], status: str) -> list[dict[str, Any]]:
    """Filter items by status. 'All' returns everything."""
    if status == "All":
        return items
    return [i for i in items if i.get("status", "") == status]


# ---------------------------------------------------------------------------
# Tools Radar tab
# ---------------------------------------------------------------------------

_TOOL_STATUS_OPTIONS = [
    "new",
    "reviewed",
    "queued",
    "skipped",
    "dismissed",
    "workbench",
]


def _render_tools_radar_tab(tools: list[dict[str, Any]]) -> None:
    """Render Tools Radar tab as a single-item review flow."""
    st.subheader("🔧 Tools Radar")

    if not tools:
        st.info(EMPTY_NO_TOOLS)
        return

    # Category filter
    all_categories = sorted({t.get("category", "Uncategorized") for t in tools})
    selected_cat = st.selectbox(
        "Filter by category",
        ["All"] + all_categories,
        key="dashboard__tools_category_filter",
    )

    filtered = _filter_tools_by_category(tools, selected_cat)
    if not filtered:
        st.info("No tools match the selected filter.")
        return

    # Reset index when filter changes or index out of range
    idx_key = "dashboard__tools_radar_idx"
    if idx_key not in st.session_state or st.session_state[idx_key] >= len(filtered):
        st.session_state[idx_key] = 0

    idx = st.session_state[idx_key]
    tool = filtered[idx]
    item_id = f"tool::{tool['name']}"
    current_status = get_item_status(item_id)

    # Navigation row
    nav_left, nav_mid, nav_right = st.columns([1, 3, 1])
    with nav_left:
        if st.button("← Prev", key="dashboard__tools_prev", disabled=idx == 0):
            st.session_state[idx_key] = idx - 1
            st.rerun()
    with nav_mid:
        st.markdown(
            f'<div style="text-align:center;color:#6B7280;padding:6px 0">'
            f"{idx + 1} of {len(filtered)}"
            f' · <span style="color:#9CA3AF">{safe_html(current_status)}</span></div>',
            unsafe_allow_html=True,
        )
    with nav_right:
        if st.button(
            "Next →",
            key="dashboard__tools_next",
            disabled=idx == len(filtered) - 1,
        ):
            st.session_state[idx_key] = idx + 1
            st.rerun()

    _render_tool_review_card(tool, item_id, current_status)


def _filter_tools_by_category(
    tools: list[dict[str, Any]], category: str
) -> list[dict[str, Any]]:
    """Filter tools by category. 'All' returns everything."""
    if category == "All":
        return tools
    return [t for t in tools if t.get("category", "Uncategorized") == category]


def _render_tool_review_card(
    tool: dict[str, Any], item_id: str, current_status: str
) -> None:
    """Render a single full-width tool review card with synthesis."""
    name = safe_html(tool["name"])
    category = safe_html(tool.get("category", "Uncategorized"))
    color = get_category_color(tool.get("category", ""))
    source = safe_html(tool.get("source", ""))
    projects = tool.get("projects", [])

    project_html = " ".join(
        f'<span class="amber-chip">{safe_html(p)}</span>' for p in projects
    )

    # Auto-synthesize plain-English description (Haiku, cached)
    summary_key = f"dashboard__tool_summary_{tool['name']}"
    if summary_key not in st.session_state:
        with st.spinner("Synthesizing…"):
            st.session_state[summary_key] = summarize_tool(tool)
    summary = safe_html(st.session_state[summary_key])

    card_html = f"""
<div class="surface-card" style="padding:24px">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px">
    <span style="font-size:1.2rem;font-weight:600">{name}</span>
    <span style="background:{color};color:#fff;padding:2px 10px;
                 border-radius:4px;font-size:0.7rem;font-weight:600">{category}</span>
  </div>
"""
    if summary:
        card_html += (
            f'  <div style="color:#D1D5DB;font-size:0.925rem;line-height:1.65;'
            f'margin-bottom:16px">{summary}</div>\n'
        )
    if source:
        card_html += (
            f'  <div style="color:#6B7280;font-size:0.8rem;margin-bottom:12px">'
            f'<span style="color:#9CA3AF">Source:</span> {source}</div>\n'
        )
    if project_html:
        card_html += f'  <div style="margin-top:4px">{project_html}</div>\n'
    card_html += "</div>"

    st.markdown(card_html, unsafe_allow_html=True)

    # Action row: status, workbench, dismiss
    col_status, col_workbench, col_dismiss = st.columns([1, 1, 1])

    with col_status:
        _handle_tool_status_selector(item_id, tool["name"], current_status)

    with col_workbench:
        _handle_workbench_button(tool, item_id, current_status)

    with col_dismiss:
        _handle_tool_dismiss_button(item_id, tool["name"], current_status)


def _handle_tool_status_selector(
    item_id: str, tool_name: str, current_status: str
) -> None:
    """Render the tool status dropdown."""
    current_idx = (
        _TOOL_STATUS_OPTIONS.index(current_status)
        if current_status in _TOOL_STATUS_OPTIONS
        else 0
    )
    new_status = st.selectbox(
        "Status",
        _TOOL_STATUS_OPTIONS,
        index=current_idx,
        key=f"dashboard__tool_status_{tool_name}",
        label_visibility="collapsed",
    )
    if new_status != current_status:
        set_item_status(item_id, new_status)


def _handle_workbench_button(
    tool: dict[str, Any], item_id: str, current_status: str
) -> None:
    """Render the Workbench button for sending a tool to the workbench."""
    disabled = current_status == "workbench"
    if st.button(
        "🔬 Workbench",
        key=f"dashboard__tool_workbench_{tool['name']}",
        disabled=disabled,
    ):
        add_to_workbench(tool, previous_status=current_status)
        set_item_status(item_id, "workbench")
        st.rerun()


def _handle_tool_dismiss_button(
    item_id: str, tool_name: str, current_status: str
) -> None:
    """Render the Dismiss button for archiving a tool."""
    if current_status == "dismissed":
        st.markdown(
            '<span style="color:#6B7280;font-size:0.75rem">archived</span>',
            unsafe_allow_html=True,
        )
        return

    if st.button("🗃️ Dismiss", key=f"dashboard__tool_dismiss_{tool_name}"):
        set_item_status(item_id, "dismissed")
        st.rerun()


# ---------------------------------------------------------------------------
# Research Archive tab
# ---------------------------------------------------------------------------


def _render_research_archive_tab(
    jc_reports: list[dict[str, Any]],
    tldr_reports: list[dict[str, Any]],
) -> None:
    """Render Research Archive with source toggle and keyword search."""
    st.subheader("📚 Research Archive")

    source = st.radio(
        "Source",
        ["JournalClub", "TLDR"],
        horizontal=True,
        key="dashboard__archive_source",
    )

    keyword = st.text_input(
        "Search by keyword",
        key="dashboard__archive_keyword",
        placeholder="e.g. RAG, agents, fine-tuning...",
    )

    reports = jc_reports if source == "JournalClub" else tldr_reports

    if keyword:
        reports = _filter_reports_by_keyword(reports, keyword)

    if not reports:
        st.info(f"No {source} reports found in the vault.")
        return

    _render_report_list(reports)


def _filter_reports_by_keyword(
    reports: list[dict[str, Any]], keyword: str
) -> list[dict[str, Any]]:
    """Filter reports by keyword match in content."""
    kw_lower = keyword.lower()
    return [r for r in reports if kw_lower in r.get("content", "").lower()]


def _render_report_list(reports: list[dict[str, Any]]) -> None:
    """Render a list of reports with expandable content."""
    for report in reports:
        date = safe_html(report["date"])
        filename = safe_html(report["filename"])
        with st.expander(f"📄 {date} — {filename}"):
            sections = report.get("sections", {})
            if sections:
                for title, body in sections.items():
                    # No unsafe_allow_html — Streamlit markdown is XSS-safe
                    st.markdown(f"**{title}**")
                    st.markdown(body)
            else:
                st.markdown(report.get("content", ""))


# ---------------------------------------------------------------------------
# Weekly AI Signal tab
# ---------------------------------------------------------------------------


def _render_weekly_ai_signal_tab(
    tldr_reports: list[dict[str, Any]],
) -> None:
    """Render timeline of AI Signal sections from TLDR reports, newest first."""
    st.subheader("📰 Weekly AI Signal")

    signals = _extract_ai_signals(tldr_reports)

    if not signals:
        st.info(
            "No AI Signal sections found in TLDR reports. Signals are extracted from the 📰 AI Signal header in each report."
        )
        return

    for signal in signals:
        _render_signal_entry(signal)


def _extract_ai_signals(
    tldr_reports: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Extract non-empty AI Signal entries from TLDR reports."""
    return [
        {"date": r["date"], "signal": r["ai_signal"]}
        for r in tldr_reports
        if r.get("ai_signal")
    ]


def _render_signal_entry(signal: dict[str, str]) -> None:
    """Render a single AI Signal timeline entry."""
    date = safe_html(signal["date"])
    content = safe_html(signal["signal"])
    st.markdown(
        f'<div class="surface-card">'
        f'<span style="color:#60A5FA;font-weight:600">{date}</span>'
        f"<br>{content}</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Agentic Hub tab
# ---------------------------------------------------------------------------


def _render_agentic_hub_tab(posts: list[dict[str, Any]], vault_path: Path) -> None:
    """Render Agentic Hub tab with instagram post cards, filters, and refresh."""
    st.subheader("🤖 Agentic Hub")

    # Link Vault button + status — always visible, even with no posts
    col_link_spacer, col_link_status, col_link_btn = st.columns([3, 2, 1])
    with col_link_btn:
        if st.button("🔗 Link Vault", key="dashboard__link_vault_btn"):
            _run_manual_link(vault_path)
    with col_link_status:
        link_results = st.session_state.get("dashboard__vault_link_results")
        if link_results is not None:
            total = sum(link_results.values())
            if total > 0:
                parts = [f"{k}: {v}" for k, v in link_results.items() if v > 0]
                st.caption(f"🔗 Last run: {total} linked — {', '.join(parts)}")
            else:
                st.caption("🔗 Last run: all files up to date")

    if not posts:
        st.info(
            "No Instagram posts ingested yet. Run the ingester for an account "
            "to populate this tab."
        )
        return

    # --- Filter bar: account dropdown, date filter, refresh button ---
    sorted_accounts = sorted({p["account"] for p in posts})
    account_options = ["All accounts"] + sorted_accounts
    date_options = ["All time", "This week", "This month", "This year"]

    col_account, col_date, col_refresh = st.columns([2, 2, 1])

    with col_account:
        selected_account = st.selectbox(
            "Account",
            account_options,
            key="dashboard__agentic_hub_account_filter",
            label_visibility="collapsed",
        )

    with col_date:
        selected_date = st.selectbox(
            "Date range",
            date_options,
            key="dashboard__agentic_hub_date_filter",
            label_visibility="collapsed",
        )

    with col_refresh:
        if st.button("🔄 Refresh", key="dashboard__agentic_hub_refresh"):
            _run_ingester_refresh(sorted_accounts)

    # Filter by account
    filtered = (
        posts
        if selected_account == "All accounts"
        else [p for p in posts if p["account"] == selected_account]
    )

    # Filter by date range
    filtered = _filter_by_date_range(filtered, selected_date)

    if not filtered:
        st.info("No posts match the selected filters.")
        return

    st.caption(f"{len(filtered)} posts")

    # Render post cards
    wb_items = get_workbench_items()
    for post in filtered:
        _render_post_card(post, wb_items)


def _filter_by_date_range(
    posts: list[dict[str, Any]], date_range: str
) -> list[dict[str, Any]]:
    """Filter posts by date range relative to today.

    Args:
        posts: List of post dicts with 'date' key (YYYY-MM-DD string).
        date_range: One of 'All time', 'This week', 'This month', 'This year'.

    Returns:
        Filtered list of posts.
    """
    if date_range == "All time":
        return posts

    from datetime import date, timedelta

    today = date.today()

    if date_range == "This week":
        cutoff = today - timedelta(days=today.weekday())  # Monday
    elif date_range == "This month":
        cutoff = today.replace(day=1)
    elif date_range == "This year":
        cutoff = today.replace(month=1, day=1)
    else:
        return posts

    cutoff_str = cutoff.isoformat()
    return [p for p in posts if p.get("date", "") >= cutoff_str]


def _run_ingester_refresh(accounts: list[str]) -> None:
    """Run the instagram ingester for all known accounts.

    Args:
        accounts: List of account usernames to refresh.
    """
    from utils.instagram_ingester import run_ingestion

    vault_path = get_vault_path()
    total = 0

    progress = st.progress(0, text="Refreshing Instagram feeds…")
    for i, account in enumerate(accounts):
        progress.progress(
            (i + 1) / len(accounts),
            text=f"Ingesting {account}…",
        )
        try:
            results = run_ingestion(account, vault_path, days=14)
            total += len(results)
        except Exception as exc:
            logger.warning("Ingester refresh failed for %s: %s", account, exc)

    progress.empty()

    if total > 0:
        st.toast(f"Ingested {total} new posts across {len(accounts)} accounts")
        _load_instagram_posts.clear()
        st.rerun()
    else:
        st.toast("No new posts found")


def _render_post_card(
    post: dict[str, Any], wb_items: dict[str, dict[str, Any]]
) -> None:
    """Render a single instagram post card with actions."""
    account = safe_html(post["account"])
    date_str = safe_html(post["date"])
    title = safe_html(post["name"])
    shortcode = post["shortcode"]

    # Key points HTML
    kp_html = ""
    if post.get("key_points"):
        kp_items = "".join(f"<li>{safe_html(p)}</li>" for p in post["key_points"])
        kp_html = (
            f'<ul style="color:#D1D5DB;font-size:0.9rem;line-height:1.6;'
            f'margin:8px 0 12px;padding-left:20px">{kp_items}</ul>'
        )

    # Keyword chips HTML
    kw_html = ""
    if post.get("keywords"):
        kw_html = " ".join(
            f'<span style="background:#78350F;color:#F59E0B;font-size:0.72rem;'
            f'padding:2px 8px;border-radius:4px">{safe_html(k)}</span>'
            for k in post["keywords"]
        )
        kw_html = f'<div style="margin-top:8px">{kw_html}</div>'

    card_html = f"""
<div class="surface-card" style="padding:20px;margin-bottom:12px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
    <span style="background:#1E40AF;color:#fff;padding:2px 10px;
                 border-radius:4px;font-size:0.7rem;font-weight:600">{account}</span>
    <span style="color:#6B7280;font-size:0.8rem">{date_str}</span>
  </div>
  <div style="font-size:1.1rem;font-weight:600;margin-bottom:8px">{title}</div>
{kp_html}{kw_html}
</div>"""
    st.markdown(card_html, unsafe_allow_html=True)

    # Action row
    _render_post_actions(post, shortcode, wb_items)

    # Inline summary (if already generated)
    summary_key = f"dashboard__agentic_hub_summary_{shortcode}"
    if summary_key in st.session_state:
        st.markdown(
            f'<div class="surface-card" style="padding:14px;margin-bottom:16px;'
            f'border-left:3px solid #3B82F6">'
            f'<span style="color:#9CA3AF;font-size:0.8rem;font-weight:600">'
            f"Summary</span><br>"
            f'<span style="color:#D1D5DB;font-size:0.9rem">'
            f"{safe_html(st.session_state[summary_key])}</span></div>",
            unsafe_allow_html=True,
        )


def _render_post_actions(
    post: dict[str, Any],
    shortcode: str,
    wb_items: dict[str, dict[str, Any]],
) -> None:
    """Render Summarize and Workbench action buttons for a post card."""
    summary_key = f"dashboard__agentic_hub_summary_{shortcode}"
    wb_key = make_item_key("instagram", shortcode)
    summary_exists = summary_key in st.session_state
    in_workbench = wb_key in wb_items

    col_summarize, col_workbench = st.columns([1, 1])

    with col_summarize:
        if st.button(
            "📝 Summarize",
            key=f"dashboard__agentic_hub_summarize_{shortcode}",
            disabled=summary_exists,
        ):
            with st.spinner("Summarizing with Haiku…"):
                result = summarize_instagram_post(post)
                st.session_state[summary_key] = result
                st.rerun()

    with col_workbench:
        if st.button(
            "🔬 Workbench",
            key=f"dashboard__agentic_hub_workbench_{shortcode}",
            disabled=in_workbench,
        ):
            # Identity model keys on shortcode; original title preserved for display
            add_to_workbench(post, previous_status="new")
            st.rerun()


# ---------------------------------------------------------------------------
# Graph Insights tab
# ---------------------------------------------------------------------------


def _render_graph_insights_tab(vault_str: str) -> None:
    """Render the Graph Insights tab with vault structure analysis.

    Args:
        vault_str: String path to the Obsidian vault root.
    """
    graph_data = safe_parse(
        _load_graph_metrics, vault_str, fallback=None, label="graph metrics"
    )
    if graph_data is None:
        st.warning("Graph data unavailable — check vault path.")
        return

    health = graph_data["health"]
    metrics = graph_data["metrics"]
    communities = graph_data["communities"]

    # --- Graph Health ---
    st.subheader("Graph Health")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Nodes", health["node_count"])
    c2.metric("Edges", health["edge_count"])
    c3.metric("Orphans", health["orphan_count"])
    c4.metric("Components", health["component_count"])
    c5.metric("Bridges", health["bridge_count"])

    # --- Hub Notes ---
    st.subheader("Hub Notes")
    pagerank = metrics.get("pagerank", {})
    in_degree = metrics.get("in_degree", {})
    betweenness = metrics.get("betweenness", {})

    if pagerank:
        sorted_notes = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)[:15]
        hub_rows = []
        for rank, (note, pr_score) in enumerate(sorted_notes, 1):
            btwn = betweenness.get(note)
            hub_rows.append(
                {
                    "Rank": rank,
                    "Note": note,
                    "PageRank": f"{pr_score:.4f}",
                    "In-Degree": in_degree.get(note, 0),
                    "Betweenness": f"{btwn:.4f}" if btwn is not None else "—",
                }
            )
        st.dataframe(hub_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No PageRank data available.")

    # --- Research Communities ---
    st.subheader("Research Communities")
    if communities:
        # Sort by size descending
        sorted_communities = sorted(communities, key=len, reverse=True)
        large = [c for c in sorted_communities if len(c) >= 3]
        small_count = len(sorted_communities) - len(large)

        for idx, community in enumerate(large[:10], 1):
            with st.expander(f"Cluster {idx} ({len(community)} notes)"):
                for member in sorted(community):
                    st.text(member)

        if small_count > 0:
            st.caption(f"{small_count} small clusters not shown")
    else:
        st.info("No communities detected.")

    # --- Suggested Links ---
    st.subheader("Suggested Links")
    if pagerank:
        G = _load_vault_graph(vault_str)
        top_hubs = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)[:5]
        any_suggestions = False
        for hub_name, _ in top_hubs:
            suggestions = suggest_links(G, hub_name, top_n=3)
            if suggestions:
                any_suggestions = True
                for target, score in suggestions:
                    st.caption(f"{hub_name} → {target} (score: {score:.2f})")
        if not any_suggestions:
            st.info("No link suggestions available.")
    else:
        st.info("No PageRank data available for link suggestions.")


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------


def _run_dashboard() -> None:
    """Main entry point for the Dashboard page."""
    st.header("Dashboard")

    _render_sidebar()

    vault_path = get_vault_path()
    vault_str = str(vault_path)
    st.session_state["vault_path_str"] = vault_str

    # Auto-link vault on first load (before parsers read files)
    _auto_link_vault(vault_path)

    # Load all data through cached wrappers with graceful fallbacks
    jc_reports = safe_parse(
        _load_journalclub_reports, vault_str, fallback=[], label="JournalClub reports"
    )
    tldr_reports = safe_parse(
        _load_tldr_reports, vault_str, fallback=[], label="TLDR reports"
    )
    tools = safe_parse(_load_tools, vault_str, fallback=[], label="tools")
    blog_items = safe_parse(
        _load_blog_queue, vault_str, fallback=[], label="blog queue"
    )
    instagram_posts = safe_parse(
        _load_instagram_posts, vault_str, fallback=[], label="instagram posts"
    )

    # Tab navigation
    tab_home, tab_blog, tab_tools, tab_archive, tab_signal, tab_agentic, tab_graph = (
        st.tabs(
            [
                "🏠 Home",
                "✍️ Blog Queue",
                "🔧 Tools Radar",
                "📚 Research Archive",
                "📰 Weekly AI Signal",
                "🤖 Agentic Hub",
                "🕸️ Graph Insights",
            ]
        )
    )

    with tab_home:
        _render_home_tab(jc_reports, tools, blog_items, tldr_reports)

    with tab_blog:
        _render_blog_queue_tab(blog_items)

    with tab_tools:
        _render_tools_radar_tab(tools)

    with tab_archive:
        _render_research_archive_tab(jc_reports, tldr_reports)

    with tab_signal:
        _render_weekly_ai_signal_tab(tldr_reports)

    with tab_agentic:
        _render_agentic_hub_tab(instagram_posts, vault_path)

    with tab_graph:
        _render_graph_insights_tab(vault_str)


_run_dashboard()
