"""Dashboard page — global intel feed with 5 tabs.

Tabs: Home, Blog Queue, Tools Radar, Research Archive, Weekly AI Signal.
All vault-sourced strings are escaped via safe_html() before unsafe_allow_html.
Parser calls are wrapped with @st.cache_data(ttl=3600) for performance.
"""

import logging
from pathlib import Path
from typing import Any

import streamlit as st

from utils.blog_queue_parser import parse_blog_queue
from utils.page_helpers import (
    EMPTY_NO_BLOG,
    EMPTY_NO_REPORTS,
    EMPTY_NO_TOOLS,
    get_vault_path,
    safe_html,
    safe_parse,
)
from utils.reports_parser import parse_journalclub_reports, parse_tldr_reports
from utils.status_tracker import get_item_status, set_item_status
from utils.tools_parser import parse_tools

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Category color mapping for Tools Radar
# ---------------------------------------------------------------------------

_CATEGORY_COLORS: dict[str, str] = {
    "IDE": "#8B5CF6",
    "Database": "#10B981",
    "Framework": "#3B82F6",
    "DevOps": "#F59E0B",
    "AI/ML": "#EC4899",
    "Security": "#EF4444",
    "Uncategorized": "#6B7280",
}


def _get_category_color(category: str) -> str:
    """Return hex color for a tool category."""
    return _CATEGORY_COLORS.get(category, "#6B7280")


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


# ---------------------------------------------------------------------------
# Sidebar — refresh button
# ---------------------------------------------------------------------------


def _render_sidebar() -> None:
    """Render sidebar with refresh button."""
    with st.sidebar:
        if st.button("🔄 Refresh Data", use_container_width=True):
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
    top_picks = latest.get("sections", {}).get("Top Picks", "")
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
        color = _get_category_color(tool.get("category", ""))
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
    """Render Blog Queue tab with card grid and filters."""
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
    _render_blog_cards(filtered)


def _filter_by_status(items: list[dict[str, Any]], status: str) -> list[dict[str, Any]]:
    """Filter items by status. 'All' returns everything."""
    if status == "All":
        return items
    return [i for i in items if i.get("status", "") == status]


def _render_blog_cards(items: list[dict[str, Any]]) -> None:
    """Render blog items as a card grid."""
    cols = st.columns(2)
    for idx, item in enumerate(items):
        with cols[idx % 2]:
            _render_blog_card(item, idx)


def _render_blog_card(item: dict[str, Any], idx: int) -> None:
    """Render a single blog queue card with status selector."""
    name = safe_html(item["name"])
    angle = safe_html(item.get("angle", ""))
    target = safe_html(item.get("target", ""))
    status = safe_html(item.get("status", ""))
    projects = ", ".join(safe_html(p) for p in item.get("projects", []))

    card_html = (
        f'<div class="surface-card">'
        f"<strong>{name}</strong><br>"
        f'<span class="status-badge">{status}</span>'
    )
    if angle:
        card_html += f"<br><em>{angle}</em>"
    if target:
        card_html += f'<br><span style="color:#9CA3AF">Target: {target}</span>'
    if projects:
        card_html += f'<br><span style="color:#60A5FA">{projects}</span>'
    card_html += "</div>"

    st.markdown(card_html, unsafe_allow_html=True)

    # Status selector — use item name for stable key across filter changes
    item_id = f"blog::{item['name']}"
    current = get_item_status(item_id)
    status_options = ["new", "reviewed", "queued", "skipped"]
    current_idx = status_options.index(current) if current in status_options else 0
    new_status = st.selectbox(
        "Status",
        status_options,
        index=current_idx,
        key=f"dashboard__blog_status_{item['name']}",
        label_visibility="collapsed",
    )
    if new_status != current:
        set_item_status(item_id, new_status)


# ---------------------------------------------------------------------------
# Tools Radar tab
# ---------------------------------------------------------------------------


def _render_tools_radar_tab(tools: list[dict[str, Any]]) -> None:
    """Render Tools Radar tab with category colors and filters."""
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
    _render_tool_cards(filtered)


def _filter_tools_by_category(
    tools: list[dict[str, Any]], category: str
) -> list[dict[str, Any]]:
    """Filter tools by category. 'All' returns everything."""
    if category == "All":
        return tools
    return [t for t in tools if t.get("category", "Uncategorized") == category]


def _render_tool_cards(tools: list[dict[str, Any]]) -> None:
    """Render tool items as cards."""
    cols = st.columns(2)
    for idx, tool in enumerate(tools):
        with cols[idx % 2]:
            _render_tool_card(tool, idx)


def _render_tool_card(tool: dict[str, Any], idx: int) -> None:
    """Render a single tool card with category badge and project tags."""
    name = safe_html(tool["name"])
    category = safe_html(tool.get("category", "Uncategorized"))
    color = _get_category_color(tool.get("category", ""))
    description = safe_html(tool.get("what it does", ""))
    source = safe_html(tool.get("source", ""))
    projects = tool.get("projects", [])

    # Build project tags HTML
    project_tags = " ".join(
        f'<span class="amber-chip">{safe_html(p)}</span>' for p in projects
    )

    card_html = (
        f'<div class="surface-card">'
        f"<strong>{name}</strong> "
        f'<span style="background:{color};color:#fff;padding:2px 8px;'
        f'border-radius:4px;font-size:0.7rem">{category}</span><br>'
    )
    if description:
        card_html += f"<em>{description}</em><br>"
    if source:
        card_html += (
            f'<span style="color:#9CA3AF;font-size:0.8em">Source: {source}</span><br>'
        )
    if project_tags:
        card_html += f"{project_tags}"
    card_html += "</div>"

    st.markdown(card_html, unsafe_allow_html=True)

    # Status selector — use item name for stable key across filter changes
    item_id = f"tool::{tool['name']}"
    current = get_item_status(item_id)
    status_options = ["new", "reviewed", "queued", "skipped"]
    current_idx = status_options.index(current) if current in status_options else 0
    new_status = st.selectbox(
        "Status",
        status_options,
        index=current_idx,
        key=f"dashboard__tool_status_{tool['name']}",
        label_visibility="collapsed",
    )
    if new_status != current:
        set_item_status(item_id, new_status)


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
# Main page
# ---------------------------------------------------------------------------


def _run_dashboard() -> None:
    """Main entry point for the Dashboard page."""
    st.header("Dashboard")

    _render_sidebar()

    vault_path = get_vault_path()
    vault_str = str(vault_path)

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

    # Tab navigation
    tab_home, tab_blog, tab_tools, tab_archive, tab_signal = st.tabs(
        [
            "🏠 Home",
            "✍️ Blog Queue",
            "🔧 Tools Radar",
            "📚 Research Archive",
            "📰 Weekly AI Signal",
        ]
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


_run_dashboard()
