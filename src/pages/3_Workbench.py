"""Workbench page — item experimentation queue and pipeline.

Displays tools and methods sent to the workbench from the Tools Radar tab
and Project Cockpit. Each item shows its current status, synthesis, and
action buttons for the research and sandbox pipeline (wired in Sessions 10–11).
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any

import streamlit as st

from utils.page_helpers import get_category_color, get_vault_path, safe_html
from utils.research_agent import (
    _MAX_RETRIES,
    _WORKBENCH_ROOT,
    get_fallback_model,
    is_agent_running,
    is_retryable_failure,
    launch_research_agent,
    launch_sandbox_agent,
    parse_agent_activity,
    parse_log_status,
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
    "instagram": "#6366F1",
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


def _render_sidebar(items: dict[str, dict[str, Any]] | None = None) -> None:
    """Render sidebar with refresh button and workbench summary.

    Args:
        items: Workbench items dict. If provided, renders status summary.
    """
    with st.sidebar:
        if st.button("🔄 Refresh", key="workbench__refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        if items is not None:
            st.divider()
            st.caption(f"**{len(items)}** item{'s' if len(items) != 1 else ''}")
            status_counts: dict[str, int] = {}
            for entry in items.values():
                s = entry.get("status", "unknown")
                status_counts[s] = status_counts.get(s, 0) + 1
            for s, count in sorted(status_counts.items()):
                color = _get_status_color(s)
                st.markdown(
                    f'<span style="color:{color}">{safe_html(s)}</span>: {count}',
                    unsafe_allow_html=True,
                )


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
        proc, model_used = launch_research_agent(item, output_dir)
        update_workbench_item(
            wb_key,
            {
                "status": "researching",
                "pid": proc.pid,
                "log_file": str(log_file),
                "retry_count": 0,
                "model": model_used,
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
    log_file = output_dir / "agent.log"
    item = entry.get("item", {})
    tool_name = item.get("name", "")
    retry_count = entry.get("retry_count", 0)
    current_model = entry.get("model")

    if not research_md.exists():
        # Check if this was an overload failure we can retry
        if is_retryable_failure(log_file) and retry_count < _MAX_RETRIES:
            fallback = get_fallback_model(current_model)
            next_model = fallback or current_model
            retry_num = retry_count + 1
            logger.warning(
                "Research agent overloaded for '%s' (attempt %d/%d, model=%s). "
                "Retrying with model=%s...",
                tool_name,
                retry_num,
                _MAX_RETRIES,
                current_model,
                next_model,
            )
            try:
                proc, model_used = launch_research_agent(
                    item, output_dir, model=next_model
                )
                update_workbench_item(
                    wb_key,
                    {
                        "status": "researching",
                        "pid": proc.pid,
                        "retry_count": retry_num,
                        "model": model_used,
                    },
                )
            except FileNotFoundError:
                update_workbench_item(wb_key, {"status": "failed"})
            st.rerun()
            return

        # Non-retryable failure or retries exhausted
        log_tail = tail_log(log_file, n=10)
        logger.warning(
            "Research failed for '%s': research.md absent (retries=%d). Log tail:\n%s",
            tool_name,
            retry_count,
            log_tail,
        )
        update_workbench_item(
            wb_key,
            {"status": "failed", "experiment_type": None},
        )
        st.rerun()
        return

    # Success — parse and render
    parsed = parse_research_output(research_md)
    html_path = render_research_html(research_md, output_dir, tool_name=tool_name)
    experiment_type = parsed.get("experiment_type")

    update_workbench_item(
        wb_key,
        {
            "status": "researched",
            "experiment_type": experiment_type,
            "cost_flagged": parsed.get("cost_flagged", False),
            "cost_notes": parsed.get("cost_notes", ""),
        },
    )
    logger.info(
        "Research complete for '%s': status=%s experiment_type=%s html=%s "
        "(attempts=%d, model=%s)",
        tool_name,
        "researched",
        experiment_type,
        html_path,
        retry_count + 1,
        current_model,
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

    if source_type == "instagram":
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
        # Topic preview: title + key_points + keywords
        parts: list[str] = []
        key_points = item.get("key_points", [])
        if key_points:
            bullets = " ".join(f"• {safe_html(kp)}" for kp in key_points[:3])
            parts.append(
                f'<div style="color:#D1D5DB;font-size:0.85rem;line-height:1.5">'
                f"{bullets}</div>"
            )
        keywords = item.get("keywords", [])
        if keywords:
            chips = " ".join(
                f'<span style="background:#1F2937;color:#9CA3AF;padding:2px 8px;'
                f'border-radius:10px;font-size:0.75rem;margin-right:4px">'
                f"{safe_html(kw)}</span>"
                for kw in keywords[:6]
            )
            parts.append(f'<div style="margin-top:4px">{chips}</div>')
        if parts:
            return f'  <div style="margin-bottom:12px">{"".join(parts)}</div>\n'
        caption = item.get("caption", "")
        if caption:
            truncated = caption[:200] + ("…" if len(caption) > 200 else "")
            return (
                f'  <div style="color:#D1D5DB;font-size:0.9rem;line-height:1.6;'
                f'margin-bottom:12px">{safe_html(truncated)}</div>\n'
            )
        return (
            '  <div style="color:#6B7280;font-size:0.8rem;font-style:italic;'
            'margin-bottom:12px">No caption available</div>\n'
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
    elif status == "sandbox_creating":
        _render_sandbox_creating_panel(wb_key, entry)
    elif status == "sandbox_ready":
        _render_sandbox_ready_panel(wb_key, entry)
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

    model = entry.get("model", "unknown")
    retry_count = entry.get("retry_count", 0)
    retry_label = f" (retry {retry_count})" if retry_count > 0 else ""
    st.caption(f"🔬 Research agent running on **{model}**{retry_label}…")

    if log_file:
        activities = parse_agent_activity(log_file, max_items=8)
        if activities:
            # Show activity feed as a styled list
            feed_html = "".join(
                f'<div style="color:#9CA3AF;font-size:0.82rem;padding:2px 0">'
                f'<span style="color:#3B82F6;margin-right:6px">▸</span>{safe_html(step)}</div>'
                for step in activities
            )
            st.markdown(
                f'<div style="background:#111827;border:1px solid #1F2937;'
                f'border-radius:6px;padding:10px 14px;margin:8px 0">'
                f"{feed_html}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.info("Starting up…")

    if st.button("🔄 Refresh", key=f"workbench__refresh_log_{wb_key}"):
        st.rerun()


def _render_report_buttons(wb_key: str, research_html: Path, research_md: Path) -> None:
    """Render Open Full Report and View Inline buttons.

    Args:
        wb_key: Namespaced workbench key.
        research_html: Path to the generated HTML report.
        research_md: Path to the research markdown file.
    """
    col_open, col_inline, _spacer = st.columns([1, 1, 3])
    with col_open:
        if research_html.exists() and st.button(
            "📄 Open Full Report",
            key=f"workbench__open_report_{wb_key}",
        ):
            subprocess.Popen(["open", str(research_html)])  # noqa: S603 S607

    # Full-width inline report (outside columns)
    with st.expander("📊 View Inline"):
        if research_md.exists():
            st.markdown(research_md.read_text(encoding="utf-8"))
        else:
            st.caption("research.md not found.")


def _render_cost_warning(wb_key: str, entry: dict[str, Any]) -> None:
    """Render cost/subscription warning banner with acknowledgement button.

    Args:
        wb_key: Namespaced workbench key.
        entry: Workbench entry dict with cost_notes set.
    """
    cost_notes = entry.get("cost_notes", "")
    st.warning(
        "⚠️ **Cost / Subscription Detected**\n\n"
        f"The research report flags potential costs for this tool:\n\n"
        f"*{cost_notes}*\n\n"
        "Review the pricing before running the experiment. Click below to acknowledge."
    )
    if st.button(
        "💳 I Acknowledge the Cost — Proceed",
        key=f"workbench__cost_ack_{wb_key}",
    ):
        logger.info("UI: Cost acknowledged for '%s'", wb_key)
        update_workbench_item(wb_key, {"cost_approved": True})
        st.rerun()


def _render_programmatic_gate(wb_key: str, entry: dict[str, Any]) -> None:
    """Render programmatic experiment review gate.

    Gate order:
    1. Show "Ready to Experiment" if not yet reviewed.
    2. Show cost warning if cost flagged and not approved.
    3. Show "Start Sandbox" once reviewed and cost cleared.

    Args:
        wb_key: Namespaced workbench key.
        entry: Workbench entry dict.
    """
    reviewed = entry.get("reviewed", False)
    cost_flagged = entry.get("cost_flagged", False)
    cost_approved = entry.get("cost_approved", False)

    if not reviewed:
        if st.button("✅ Ready to Experiment", key=f"workbench__ready_{wb_key}"):
            logger.info("UI: Ready to Experiment clicked for '%s'", wb_key)
            update_workbench_item(wb_key, {"reviewed": True})
            st.rerun()
        return

    # Reviewed — check cost gate before sandbox
    if cost_flagged and not cost_approved:
        _render_cost_warning(wb_key, entry)
        return

    # Reviewed + cost cleared — show sandbox button
    if st.button("🧪 Start Sandbox", key=f"workbench__sandbox_{wb_key}"):
        logger.info("UI: Start Sandbox clicked for '%s'", wb_key)
        _handle_sandbox_click(wb_key, entry)


def _handle_sandbox_click(wb_key: str, entry: dict[str, Any]) -> None:
    """Handle Start Sandbox button click — launch sandbox agent.

    Args:
        wb_key: Namespaced workbench key.
        entry: Workbench entry dict.
    """
    item = entry.get("item", {})
    output_dir = _get_output_dir(wb_key, entry)
    research_md = output_dir / "research.md"
    sandbox_log = output_dir / "sandbox_agent.log"

    try:
        proc = launch_sandbox_agent(item, research_md, output_dir)
        update_workbench_item(
            wb_key,
            {
                "status": "sandbox_creating",
                "pid": proc.pid,
                "log_file": str(sandbox_log),
            },
        )
    except FileNotFoundError as exc:
        logger.error("Sandbox agent launch failed: %s", exc, exc_info=True)
        st.error(f"Failed to start sandbox: {exc}")
        update_workbench_item(wb_key, {"status": "failed"})
    st.rerun()


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

    _render_report_buttons(wb_key, research_html, research_md)

    if experiment_type == "programmatic":
        _render_programmatic_gate(wb_key, entry)
    elif experiment_type == "manual":
        _render_manual_panel(research_md)


def _render_failed_panel(wb_key: str, entry: dict[str, Any]) -> None:
    """Render error state with parsed error message and retry button.

    Args:
        wb_key: Namespaced workbench key.
        entry: Workbench entry dict.
    """
    retry_count = entry.get("retry_count", 0)
    model = entry.get("model", "unknown")
    log_file_str = entry.get("log_file")
    log_file = Path(log_file_str) if log_file_str else None

    # Show parsed error message instead of raw JSON
    error_msg = "Research agent failed."
    if log_file:
        status_line = parse_log_status(log_file)
        if status_line:
            error_msg = status_line

    st.error(error_msg)
    st.caption(f"Model: **{model}** · Attempts: **{retry_count + 1}**")

    # Offer manual retry button
    if st.button("🔁 Retry Research", key=f"workbench__retry_{wb_key}"):
        _handle_research_click(wb_key, entry)
        return


def _render_sandbox_creating_panel(wb_key: str, entry: dict[str, Any]) -> None:
    """Render live log tail while sandbox agent is building experiment files.

    Polls the agent on each render. When PID exits, finalises the sandbox
    entry: reads findings, writes vault note, transitions to sandbox_ready.

    Args:
        wb_key: Namespaced workbench key.
        entry: Workbench entry dict.
    """
    pid = entry.get("pid")
    log_file_str = entry.get("log_file")
    log_file = Path(log_file_str) if log_file_str else None

    if pid and not is_agent_running(pid):
        _finalise_sandbox(wb_key, entry)
        return

    st.caption("🧪 Sandbox agent writing experiment files…")

    if log_file and log_file.exists():
        activities = parse_agent_activity(log_file, max_items=8)
        if activities:
            feed_html = "".join(
                f'<div style="color:#9CA3AF;font-size:0.82rem;padding:2px 0">'
                f'<span style="color:#059669;margin-right:6px">▸</span>'
                f"{safe_html(step)}</div>"
                for step in activities
            )
            st.markdown(
                f'<div style="background:#111827;border:1px solid #1F2937;'
                f"border-radius:6px;padding:10px 14px;margin:8px 0\">"
                f"{feed_html}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.info("Starting up…")

    if st.button("🔄 Refresh", key=f"workbench__refresh_sandbox_{wb_key}"):
        st.rerun()


def _finalise_sandbox(wb_key: str, entry: dict[str, Any]) -> None:
    """Finalise sandbox after agent completes: read findings, write vault note.

    Args:
        wb_key: Namespaced workbench key.
        entry: Workbench entry dict (sandbox_creating status).
    """
    output_dir = _get_output_dir(wb_key, entry)
    findings_md = output_dir / "experiment_findings.md"
    item = entry.get("item", {})

    updates: dict[str, Any] = {
        "status": "sandbox_ready",
        "sandbox_dir": str(output_dir),
    }

    if findings_md.exists():
        updates["findings_path"] = str(findings_md)

    # Write vault note
    try:
        vault_path = get_vault_path()
        from utils.vault_writer import write_sandbox_note

        parsed = parse_research_output(output_dir / "research.md")
        findings_text = (
            findings_md.read_text(encoding="utf-8") if findings_md.exists() else ""
        )
        note_path = write_sandbox_note(
            item,
            parsed.get("summary", ""),
            output_dir,
            vault_path,
            findings_text=findings_text,
        )
        updates["vault_note"] = str(note_path)
        logger.info("Wrote vault note: %s", note_path)
    except Exception as exc:
        logger.warning("Failed to write vault note: %s", exc)

    update_workbench_item(wb_key, updates)
    st.rerun()


def _render_results_summary(results_json: Path) -> None:
    """Render experiment results metrics from experiment_results.json.

    Args:
        results_json: Path to experiment_results.json.
    """
    if not results_json.exists():
        return
    try:
        results = json.loads(results_json.read_text(encoding="utf-8"))
    except Exception:
        return

    metric = results.get("metric_name", "")
    result_val = results.get("result", "")
    baseline = results.get("baseline")
    improvement = results.get("improvement")
    passed = results.get("passed", False)
    desc = results.get("description", "")

    status_color = "#10B981" if passed else "#EF4444"
    status_label = "PASSED" if passed else "FAILED"

    cols = st.columns([1, 1, 1])
    with cols[0]:
        st.metric("Metric", metric or "—")
    with cols[1]:
        st.metric("Result", str(result_val))
    with cols[2]:
        if baseline is not None:
            delta_str = f"{improvement:+.2f}" if improvement is not None else "—"
            st.metric("Baseline", str(baseline), delta=delta_str)

    st.markdown(
        f'<span style="background:{status_color};color:#fff;padding:3px 10px;'
        f"border-radius:4px;font-size:0.75rem;font-weight:600\">{status_label}</span>"
        f" {safe_html(desc)}",
        unsafe_allow_html=True,
    )


def _render_sandbox_ready_panel(wb_key: str, entry: dict[str, Any]) -> None:
    """Render completed sandbox with findings, metrics, and action buttons.

    Args:
        wb_key: Namespaced workbench key.
        entry: Workbench entry dict (sandbox_ready status).
    """
    output_dir = _get_output_dir(wb_key, entry)
    findings_md = output_dir / "experiment_findings.md"
    results_json = output_dir / "experiment_results.json"
    vault_note_str = entry.get("vault_note")

    # Results metrics row
    _render_results_summary(results_json)

    # Findings report
    if findings_md.exists():
        with st.expander("📊 Experiment Findings", expanded=True):
            st.markdown(findings_md.read_text(encoding="utf-8"))

    # Action buttons
    col_open, col_obsidian = st.columns([1, 1])
    with col_open:
        if st.button(
            "📂 Open Sandbox Dir", key=f"workbench__open_sandbox_{wb_key}"
        ):
            subprocess.Popen(["open", str(output_dir)])  # noqa: S603 S607

    with col_obsidian:
        if vault_note_str:
            try:
                vault_path = get_vault_path()
                vault_name = vault_path.name
                rel = Path(vault_note_str).relative_to(vault_path)
                from utils.cockpit_components import build_obsidian_url
                url = build_obsidian_url(vault_name, str(rel))
                st.link_button("🗂️ Open in Obsidian", url)
            except Exception:
                pass

    # Run instructions
    with st.expander("🐳 Run Experiment"):
        run_sh = output_dir / "run.sh"
        if run_sh.exists():
            st.code(f"cd {output_dir}\nbash run.sh", language="bash")
        else:
            st.caption(
                "run.sh not found — sandbox agent may not have written all files."
            )


def _render_action_buttons(wb_key: str, entry: dict[str, Any]) -> None:
    """Render action buttons row for a workbench item.

    Args:
        wb_key: Namespaced workbench key.
        entry: Workbench entry dict.
    """
    status = entry.get("status", "queued")
    col_research, col_remove = st.columns([1, 1])

    with col_research:
        research_disabled = status not in ("queued", "failed")
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


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------


def _run_workbench() -> None:
    """Main entry point for the Workbench page."""
    st.header("🔬 Workbench")

    items = get_workbench_items()
    _render_sidebar(items)

    if not items:
        st.info(
            "No items in workbench yet. Use 🔬 Workbench on any tool or method "
            "to add one."
        )
        return

    for wb_key, entry in items.items():
        _render_item_card(wb_key, entry)


_run_workbench()
