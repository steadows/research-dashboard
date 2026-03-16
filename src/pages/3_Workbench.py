"""Workbench page — item experimentation queue and pipeline.

Displays tools and methods sent to the workbench from the Tools Radar tab
and Project Cockpit. Each item shows its current status, synthesis, and
action buttons for the research and sandbox pipeline (wired in Sessions 10–11).
"""

import logging
import subprocess
from pathlib import Path
from typing import Any

import streamlit as st

from utils.page_helpers import get_category_color, safe_html
from utils.research_agent import (
    _WORKBENCH_ROOT,
    is_agent_running,
    launch_research_agent,
    parse_research_output,
    render_research_html,
    tail_log,
)
from utils.workbench_tracker import (
    get_slug,
    get_workbench_items,
    remove_from_workbench,
    update_workbench_item,
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
# Research lifecycle helpers
# ---------------------------------------------------------------------------


def _get_output_dir(wb_key: str, entry: dict[str, Any]) -> Path:
    """Build the output directory path for a workbench item.

    Args:
        wb_key: Namespaced workbench key.
        entry: Workbench entry dict.

    Returns:
        Path under _WORKBENCH_ROOT.
    """
    item = entry.get("item", {})
    name = item.get("name", wb_key)
    source_type = entry.get("source_type", "tool")
    return _WORKBENCH_ROOT / get_slug(name, source_type)


def _handle_research_click(wb_key: str, entry: dict[str, Any]) -> None:
    """Handle Research button click — launch agent and update workbench state.

    Args:
        wb_key: Namespaced workbench key.
        entry: Workbench entry dict.
    """
    item = entry.get("item", {})
    output_dir = _get_output_dir(wb_key, entry)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_file = output_dir / "agent.log"

    logger.info("UI: Research clicked for '%s'", item.get("name"))
    try:
        proc = launch_research_agent(item, output_dir)
        update_workbench_item(
            wb_key,
            {
                "status": "researching",
                "pid": proc.pid,
                "log_file": str(log_file),
            },
        )
    except FileNotFoundError as exc:
        logger.error("Research agent launch failed: %s", exc, exc_info=True)
        update_workbench_item(wb_key, {"status": "failed"})
    st.rerun()


def _poll_research_status(wb_key: str, entry: dict[str, Any]) -> None:
    """Check if a running research agent has finished; update state if done.

    Args:
        wb_key: Namespaced workbench key.
        entry: Workbench entry dict with pid and log_file set.
    """
    pid = entry.get("pid")
    if pid is None:
        return

    if is_agent_running(pid):
        return  # Still running — nothing to do yet

    # Agent finished — parse output and update
    output_dir = _get_output_dir(wb_key, entry)
    research_md = output_dir / "research.md"
    item = entry.get("item", {})
    tool_name = item.get("name", "")

    parsed = parse_research_output(research_md)
    html_path = render_research_html(research_md, output_dir, tool_name=tool_name)

    experiment_type = parsed.get("experiment_type")
    new_status = "researched" if research_md.exists() else "failed"

    if new_status == "failed":
        log_tail = tail_log(output_dir / "agent.log", n=10)
        logger.warning(
            "Research failed for '%s': research.md absent. Log tail:\n%s",
            tool_name,
            log_tail,
        )

    update_workbench_item(
        wb_key,
        {
            "status": new_status,
            "experiment_type": experiment_type,
        },
    )
    logger.info(
        "Research complete for '%s': status=%s experiment_type=%s html=%s",
        tool_name,
        new_status,
        experiment_type,
        html_path,
    )
    st.rerun()


# ---------------------------------------------------------------------------
# Item card rendering
# ---------------------------------------------------------------------------


def _build_summary_html(wb_key: str, entry: dict[str, Any]) -> str:
    """Build the summary/description line HTML for a workbench card.

    Args:
        wb_key: Namespaced workbench key.
        entry: Workbench entry dict.

    Returns:
        HTML string for the summary div.
    """
    item = entry.get("item", {})
    status = entry.get("status", "queued")
    source_type = entry.get("source_type", item.get("source_type", "tool"))

    if source_type == "method":
        desc = item.get("why it matters", "") or item.get("description", "")
        if desc:
            return (
                f'  <div style="color:#D1D5DB;font-size:0.9rem;line-height:1.6;'
                f'margin-bottom:12px">{safe_html(desc)}</div>\n'
            )
        return (
            '  <div style="color:#6B7280;font-size:0.8rem;font-style:italic;'
            'margin-bottom:12px">No description available</div>\n'
        )

    if status == "researched":
        output_dir = _get_output_dir(wb_key, entry)
        parsed = parse_research_output(output_dir / "research.md")
        summary = parsed.get("summary", "")
        if summary:
            truncated = summary[:300] + ("…" if len(summary) > 300 else "")
            return (
                f'  <div style="color:#D1D5DB;font-size:0.9rem;line-height:1.6;'
                f'margin-bottom:12px">{safe_html(truncated)}</div>\n'
            )
        return (
            '  <div style="color:#6B7280;font-size:0.8rem;font-style:italic;'
            'margin-bottom:12px">Research complete — no overview found</div>\n'
        )

    return (
        '  <div style="color:#6B7280;font-size:0.8rem;font-style:italic;'
        'margin-bottom:12px">Run research to generate summary</div>\n'
    )


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

    card_html = (
        f'\n<div class="surface-card" style="padding:20px;margin-bottom:12px">\n'
        f'  <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">\n'
        f'    <span style="font-size:1.1rem;font-weight:600">{safe_html(display_name)}</span>\n'
        f'    <span style="background:{source_color};color:#fff;padding:2px 10px;'
        f'border-radius:4px;font-size:0.7rem;font-weight:600">{safe_html(source_type)}</span>\n'
        f'    <span style="background:{cat_color};color:#fff;padding:2px 10px;'
        f'border-radius:4px;font-size:0.7rem;font-weight:600">{safe_html(category)}</span>\n'
        f'    <span style="background:{status_color};color:#fff;padding:2px 10px;'
        f'border-radius:4px;font-size:0.7rem;font-weight:600">{safe_html(status)}</span>\n'
        f"  </div>\n" + _build_summary_html(wb_key, entry) + "</div>"
    )
    st.markdown(card_html, unsafe_allow_html=True)

    _render_status_panel(wb_key, entry)
    _render_action_buttons(wb_key, entry)


def _render_status_panel(wb_key: str, entry: dict[str, Any]) -> None:
    """Render status-specific panels (log tail, research report, etc.).

    Args:
        wb_key: Namespaced workbench key.
        entry: Workbench entry dict.
    """
    status = entry.get("status", "queued")

    if status == "researching":
        _render_researching_panel(wb_key, entry)
    elif status == "researched":
        _render_researched_panel(wb_key, entry)
    elif status == "failed":
        _render_failed_panel(wb_key, entry)


def _render_researching_panel(wb_key: str, entry: dict[str, Any]) -> None:
    """Render live log tail while research agent is running.

    Args:
        wb_key: Namespaced workbench key.
        entry: Workbench entry dict.
    """
    log_file_str = entry.get("log_file")
    log_file = Path(log_file_str) if log_file_str else None

    # Poll on each render — update state if agent finished
    _poll_research_status(wb_key, entry)

    st.caption("🔬 Research agent running…")
    if log_file:
        tail = tail_log(log_file, n=20)
        if tail:
            st.code(tail, language=None)

    if st.button("🔄 Refresh", key=f"workbench__refresh_log_{wb_key}"):
        st.rerun()


def _render_report_buttons(wb_key: str, research_html: Path, research_md: Path) -> None:
    """Render Open Full Report and View Inline buttons.

    Args:
        wb_key: Namespaced workbench key.
        research_html: Path to the generated HTML report.
        research_md: Path to the research markdown file.
    """
    col_open, col_inline = st.columns([1, 1])
    with col_open:
        if research_html.exists() and st.button(
            "📄 Open Full Report",
            key=f"workbench__open_report_{wb_key}",
        ):
            subprocess.Popen(["open", str(research_html)])  # noqa: S603 S607

    with col_inline:
        with st.expander("📊 View Inline"):
            if research_md.exists():
                st.markdown(research_md.read_text(encoding="utf-8"))
            else:
                st.caption("research.md not found.")


def _render_programmatic_gate(wb_key: str, reviewed: bool) -> None:
    """Render programmatic experiment review gate buttons.

    Args:
        wb_key: Namespaced workbench key.
        reviewed: Whether the item has been marked ready to experiment.
    """
    if not reviewed:
        if st.button("✅ Ready to Experiment", key=f"workbench__ready_{wb_key}"):
            logger.info("UI: Ready to Experiment clicked for '%s'", wb_key)
            update_workbench_item(wb_key, {"reviewed": True})
            st.rerun()
    else:
        st.button(
            "🧪 Start Sandbox",
            key=f"workbench__sandbox_{wb_key}",
            disabled=True,
            help="Sandbox wired in Session 11",
        )


def _render_manual_panel(research_md: Path) -> None:
    """Render manual evaluation badge and experiment design section.

    Args:
        research_md: Path to the research markdown file.
    """
    st.markdown(
        '<span style="background:#F97316;color:#fff;padding:3px 10px;'
        'border-radius:4px;font-size:0.75rem;font-weight:600">'
        "Manual Evaluation</span>",
        unsafe_allow_html=True,
    )
    if research_md.exists():
        content = research_md.read_text(encoding="utf-8")
        exp_design = _extract_section(content, "Experiment Design")
        if exp_design:
            with st.expander("📋 Experiment Design"):
                st.markdown(exp_design)


def _render_researched_panel(wb_key: str, entry: dict[str, Any]) -> None:
    """Render research results with report links and review gate.

    Args:
        wb_key: Namespaced workbench key.
        entry: Workbench entry dict.
    """
    output_dir = _get_output_dir(wb_key, entry)
    research_md = output_dir / "research.md"
    research_html = output_dir / "research.html"
    experiment_type = entry.get("experiment_type")
    reviewed = entry.get("reviewed", False)

    _render_report_buttons(wb_key, research_html, research_md)

    if experiment_type == "programmatic":
        _render_programmatic_gate(wb_key, reviewed)
    elif experiment_type == "manual":
        _render_manual_panel(research_md)


def _render_failed_panel(wb_key: str, entry: dict[str, Any]) -> None:
    """Render error state with last log lines.

    Args:
        wb_key: Namespaced workbench key.
        entry: Workbench entry dict.
    """
    st.error("Research agent failed.")
    log_file_str = entry.get("log_file")
    if log_file_str:
        tail = tail_log(Path(log_file_str), n=10)
        if tail:
            st.code(tail, language=None)


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
        research_disabled = status != "queued" or source_type == "method"
        if st.button(
            "🔍 Research",
            key=f"workbench__research_{wb_key}",
            disabled=research_disabled,
        ):
            logger.info("UI: Research button clicked for '%s'", wb_key)
            _handle_research_click(wb_key, entry)

    with col_remove:
        if st.button("🗑️ Remove", key=f"workbench__remove_{wb_key}"):
            remove_from_workbench(wb_key)
            st.rerun()


# ---------------------------------------------------------------------------
# Section extractor helper
# ---------------------------------------------------------------------------


def _extract_section(content: str, heading: str) -> str:
    """Extract the body text of a ## heading from a markdown string.

    Args:
        content: Raw markdown text.
        heading: Heading text to find (without ## prefix).

    Returns:
        Section body as a string, or empty string if not found.
    """
    lines = content.splitlines()
    in_section = False
    body: list[str] = []

    for line in lines:
        if line.startswith("## "):
            if in_section:
                break
            if line[3:].strip() == heading:
                in_section = True
        elif in_section:
            body.append(line)

    return "\n".join(body).strip()


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
