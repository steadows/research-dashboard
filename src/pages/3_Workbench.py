"""Workbench page — tool experimentation queue and pipeline.

Displays tools sent to the workbench from the Tools Radar tab. Each item
shows its current status, synthesis, and action buttons for the research
and sandbox pipeline (wired in Sessions 9–10).
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


def _get_status_color(status: str) -> str:
    """Return hex color for a workbench status."""
    return _STATUS_COLORS.get(status, "#6B7280")


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
# Item card rendering
# ---------------------------------------------------------------------------


def _render_item_card(name: str, entry: dict[str, Any]) -> None:
    """Render a single workbench item card.

    Args:
        name: Tool name (dict key in workbench.json).
        entry: Workbench entry dict with tool, status, etc.
    """
    tool = entry.get("tool", {})
    status = entry.get("status", "queued")
    category = tool.get("category", "Uncategorized")

    cat_color = get_category_color(category)
    status_color = _get_status_color(status)

    card_html = f"""
<div class="surface-card" style="padding:20px;margin-bottom:12px">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
    <span style="font-size:1.1rem;font-weight:600">{safe_html(name)}</span>
    <span style="background:{cat_color};color:#fff;padding:2px 10px;
                 border-radius:4px;font-size:0.7rem;font-weight:600">{safe_html(category)}</span>
    <span style="background:{status_color};color:#fff;padding:2px 10px;
                 border-radius:4px;font-size:0.7rem;font-weight:600">{safe_html(status)}</span>
  </div>
"""

    # Synthesis line — from session state if available
    summary_key = f"dashboard__tool_summary_{name}"
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

    _render_action_buttons(name, entry)


def _render_action_buttons(name: str, entry: dict[str, Any]) -> None:
    """Render action buttons row for a workbench item.

    Args:
        name: Tool name.
        entry: Workbench entry dict.
    """
    status = entry.get("status", "queued")
    col_research, col_remove = st.columns([1, 1])

    with col_research:
        # Research button — placeholder, wired in Session 9
        st.button(
            "🔍 Research",
            key=f"workbench__research_{name}",
            disabled=status != "queued",
        )

    with col_remove:
        if st.button("🗑️ Remove", key=f"workbench__remove_{name}"):
            remove_from_workbench(name)
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
            "No tools in workbench yet. Use 🔬 Workbench on any tool in the "
            "Tools Radar to add one."
        )
        _render_parser_health(items)
        return

    for name, entry in items.items():
        _render_item_card(name, entry)

    _render_parser_health(items)


_run_workbench()
