"""Workbench page — item experimentation queue and pipeline.

Displays tools and methods sent to the workbench from the Tools Radar tab
and Project Cockpit. Each item shows its current status, synthesis, and
action buttons for the research and sandbox pipeline (wired in Sessions 10–11).
"""

import logging
from typing import Any

import streamlit as st

from utils.page_helpers import get_category_color, safe_html
from utils.workbench_tracker import (
    get_workbench_items,
    remove_from_workbench,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Status badge colors
# ---------------------------------------------------------------------------

_STATUS_COLORS: dict[str, str] = {
    "queued": "#3B82F6",
    "researching": "#F59E0B",
    "researched": "#10B981",
    "sandbox_creating": "#F59E0B",
    "sandbox_ready": "#059669",
    "manual": "#F97316",
    "failed": "#EF4444",
}

_SOURCE_TYPE_COLORS: dict[str, str] = {
    "method": "#8B5CF6",
    "tool": "#10B981",
}


def _get_status_color(status: str) -> str:
    """Return hex color for a workbench status."""
    return _STATUS_COLORS.get(status, "#6B7280")


def _get_source_type_color(source_type: str) -> str:
    """Return hex color for a source type badge."""
    return _SOURCE_TYPE_COLORS.get(source_type, "#6B7280")


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------


def _render_sidebar() -> None:
    """Render sidebar with refresh button."""
    with st.sidebar:
        if st.button("🔄 Refresh", key="workbench__refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()


# ---------------------------------------------------------------------------
# Display name helper
# ---------------------------------------------------------------------------


def _get_display_name(entry: dict[str, Any], wb_key: str) -> str:
    """Extract a human-readable display name from a workbench entry.

    Args:
        entry: Workbench entry dict.
        wb_key: Workbench key (fallback).

    Returns:
        Display name string.
    """
    item = entry.get("item", {})
    return item.get("name", wb_key)


# ---------------------------------------------------------------------------
# Item card rendering
# ---------------------------------------------------------------------------


def _render_item_card(wb_key: str, entry: dict[str, Any]) -> None:
    """Render a single workbench item card.

    Args:
        wb_key: Namespaced workbench key (e.g. "tool::Cursor Tab").
        entry: Workbench entry dict with item, status, etc.
    """
    item = entry.get("item", {})
    display_name = _get_display_name(entry, wb_key)
    status = entry.get("status", "queued")
    source_type = entry.get("source_type", item.get("source_type", "tool"))
    category = item.get("category", "Uncategorized")

    cat_color = get_category_color(category)
    status_color = _get_status_color(status)
    source_color = _get_source_type_color(source_type)

    card_html = f"""
<div class="surface-card" style="padding:20px;margin-bottom:12px">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
    <span style="font-size:1.1rem;font-weight:600">{safe_html(display_name)}</span>
    <span style="background:{source_color};color:#fff;padding:2px 10px;
                 border-radius:4px;font-size:0.7rem;font-weight:600">{safe_html(source_type)}</span>
    <span style="background:{cat_color};color:#fff;padding:2px 10px;
                 border-radius:4px;font-size:0.7rem;font-weight:600">{safe_html(category)}</span>
    <span style="background:{status_color};color:#fff;padding:2px 10px;
                 border-radius:4px;font-size:0.7rem;font-weight:600">{safe_html(status)}</span>
  </div>
"""

    # Summary line — methods show description from item dict, tools use LLM summary
    if source_type == "method":
        desc = item.get("why it matters", "") or item.get("description", "")
        if desc:
            card_html += (
                f'  <div style="color:#D1D5DB;font-size:0.9rem;line-height:1.6;'
                f'margin-bottom:12px">{safe_html(desc)}</div>\n'
            )
        else:
            card_html += (
                '  <div style="color:#6B7280;font-size:0.8rem;font-style:italic;'
                'margin-bottom:12px">No description available</div>\n'
            )
    else:
        summary_key = f"workbench__summary_{wb_key}"
        summary = st.session_state.get(summary_key, "")
        if summary:
            card_html += (
                f'  <div style="color:#D1D5DB;font-size:0.9rem;line-height:1.6;'
                f'margin-bottom:12px">{safe_html(summary)}</div>\n'
            )
        else:
            card_html += (
                '  <div style="color:#6B7280;font-size:0.8rem;font-style:italic;'
                'margin-bottom:12px">Run research to generate summary</div>\n'
            )

    card_html += "</div>"
    st.markdown(card_html, unsafe_allow_html=True)

    _render_action_buttons(wb_key, entry)


def _render_action_buttons(wb_key: str, entry: dict[str, Any]) -> None:
    """Render action buttons row for a workbench item.

    Args:
        wb_key: Namespaced workbench key.
        entry: Workbench entry dict.
    """
    status = entry.get("status", "queued")
    source_type = entry.get("source_type", "tool")
    col_research, col_remove = st.columns([1, 1])

    with col_research:
        # Research disabled for methods until Sessions 10–11 generalize
        st.button(
            "🔍 Research",
            key=f"workbench__research_{wb_key}",
            disabled=status != "queued" or source_type == "method",
        )

    with col_remove:
        if st.button("🗑️ Remove", key=f"workbench__remove_{wb_key}"):
            remove_from_workbench(wb_key)
            st.rerun()


# ---------------------------------------------------------------------------
# Parser health panel
# ---------------------------------------------------------------------------


def _render_parser_health(items: dict[str, dict[str, Any]]) -> None:
    """Render parser health diagnostic panel at page bottom.

    Args:
        items: Workbench items dict (avoids redundant filesystem read).
    """
    with st.expander("🔧 Parser Health"):
        st.caption(f"Workbench items: {len(items)}")

        # Count by status
        status_counts: dict[str, int] = {}
        for entry in items.values():
            s = entry.get("status", "unknown")
            status_counts[s] = status_counts.get(s, 0) + 1

        if status_counts:
            for s, count in sorted(status_counts.items()):
                color = _get_status_color(s)
                st.markdown(
                    f'<span style="color:{color};font-weight:600">{safe_html(s)}</span>: {count}',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No items to report.")


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------


def _run_workbench() -> None:
    """Main entry point for the Workbench page."""
    st.header("🔬 Workbench")

    _render_sidebar()

    items = get_workbench_items()

    if not items:
        st.info(
            "No items in workbench yet. Use 🔬 Workbench on any tool or method "
            "to add one."
        )
        _render_parser_health(items)
        return

    for wb_key, entry in items.items():
        _render_item_card(wb_key, entry)

    _render_parser_health(items)


_run_workbench()
