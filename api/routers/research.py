"""Research router — launch research agents and check status."""

import html as html_module
import json
import logging
import os
import re
import signal
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from api.deps import get_vault_path_str
from utils.research_agent import (
    is_agent_running,
    launch_experiment_agent,
    launch_research_agent,
    launch_sandbox_agent,
    tail_log,
)
from utils.workbench_tracker import (
    get_slug,
    get_workbench_item,
    update_workbench_item,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/research", tags=["research"])

_WORKBENCH_ROOT = Path.home() / "research-workbench"

# PIDs launched by this server process — only these can be killed
_server_owned_pids: set[int] = set()

# Max bytes to read per sandbox file to prevent OOM
_MAX_FILE_READ_BYTES = 512 * 1024


@router.post("/launch/{key:path}", status_code=202)
def launch_research(key: str) -> dict[str, Any]:
    """Launch a research agent for a workbench item.

    Args:
        key: Namespaced workbench key (e.g. 'tool::Cursor Tab').

    Returns:
        Dict with pid, model, output_dir, and key.

    Raises:
        HTTPException: 404 if item not found in workbench.
    """
    entry = get_workbench_item(key)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Workbench item '{key}' not found")

    item = entry.get("item", {})
    source_type = entry.get("source_type", "tool")
    name = item.get("name", "unknown")
    slug = get_slug(name, source_type)
    output_dir = _WORKBENCH_ROOT / slug

    proc, model = launch_research_agent(item, output_dir)
    _server_owned_pids.add(proc.pid)

    # Update workbench entry with agent metadata
    update_workbench_item(
        key,
        {
            "status": "researching",
            "pid": proc.pid,
            "log_file": str(output_dir / "agent.log"),
            "model": model,
        },
    )

    return {
        "key": key,
        "pid": proc.pid,
        "model": model,
        "output_dir": str(output_dir),
    }


@router.get("/status/{key:path}")
def get_research_status(key: str) -> dict[str, Any]:
    """Check agent status for a workbench item. Auto-transitions on completion.

    If the item is in ``researching`` or ``sandbox_creating`` and the PID is
    dead, this endpoint finalises the transition (to ``researched``/``failed``
    or ``sandbox_ready``/``failed`` respectively) so the frontend sees the
    correct state on the next poll.

    Args:
        key: Namespaced workbench key.

    Returns:
        Dict with running status, current status, log tail, and key.

    Raises:
        HTTPException: 404 if item not found in workbench.
    """
    entry = get_workbench_item(key)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Workbench item '{key}' not found")

    pid = entry.get("pid")
    log_file = entry.get("log_file", "")
    status = entry.get("status", "queued")
    running = is_agent_running(pid) if pid else False
    log_tail_str, _ = tail_log(Path(log_file)) if log_file else ("", 0)

    # Auto-transition if agent died
    if not running and pid:
        if status == "sandbox_creating":
            status = _finalise_sandbox_status(key, entry)
        elif status == "researching":
            status = _finalise_research_status(key, entry)
        elif status == "experiment_running":
            status = _finalise_experiment_status(key, entry)

    return {
        "key": key,
        "running": running,
        "status": status,
        "pid": pid,
        "log_tail": log_tail_str,
    }


def _finalise_sandbox_status(key: str, entry: dict[str, Any]) -> str:
    """Transition a sandbox_creating item after its agent exits.

    Args:
        key: Workbench key.
        entry: Current workbench entry.

    Returns:
        New status string.
    """
    item = entry.get("item", {})
    source_type = entry.get("source_type", "tool")
    name = item.get("name", "unknown")
    slug = get_slug(name, source_type)
    output_dir = _WORKBENCH_ROOT / slug

    experiment_py = output_dir / "experiment.py"
    run_sh = output_dir / "run.sh"

    if experiment_py.is_file() or run_sh.is_file():
        updates: dict[str, Any] = {
            "status": "sandbox_ready",
            "sandbox_dir": str(output_dir),
        }
        findings = output_dir / "experiment_findings.md"
        if findings.is_file():
            updates["findings_path"] = str(findings)
        update_workbench_item(key, updates)
        logger.info("Auto-finalised sandbox for '%s' → sandbox_ready", key)
        return "sandbox_ready"

    update_workbench_item(key, {"status": "failed"})
    logger.warning("Sandbox agent for '%s' exited without output files → failed", key)
    return "failed"


def _finalise_research_status(key: str, entry: dict[str, Any]) -> str:
    """Transition a researching item after its agent exits.

    Args:
        key: Workbench key.
        entry: Current workbench entry.

    Returns:
        New status string.
    """
    from utils.research_agent import parse_research_output

    item = entry.get("item", {})
    source_type = entry.get("source_type", "tool")
    name = item.get("name", "unknown")
    slug = get_slug(name, source_type)
    research_md = _WORKBENCH_ROOT / slug / "research.md"

    if research_md.is_file():
        parsed = parse_research_output(research_md)
        experiment_type = parsed.get("experiment_type")
        update_workbench_item(
            key,
            {
                "status": "researched",
                "experiment_type": experiment_type,
                "cost_flagged": parsed.get("cost_flagged", False),
                "cost_notes": parsed.get("cost_notes", ""),
            },
        )
        logger.info("Auto-finalised research for '%s' → researched", key)
        return "researched"

    update_workbench_item(key, {"status": "failed"})
    logger.warning("Research agent for '%s' exited without research.md → failed", key)
    return "failed"


def _finalise_experiment_status(key: str, entry: dict[str, Any]) -> str:
    """Transition an experiment_running item after its agent exits.

    Checks for experiment_results.json and experiment_findings.md.
    The agent is responsible for writing these even on failure, but
    if neither exists the experiment is marked failed.

    Args:
        key: Workbench key.
        entry: Current workbench entry.

    Returns:
        New status string.
    """
    item = entry.get("item", {})
    source_type = entry.get("source_type", "tool")
    name = item.get("name", "unknown")
    slug = get_slug(name, source_type)
    output_dir = _WORKBENCH_ROOT / slug

    results_json = output_dir / "experiment_results.json"
    findings_md = output_dir / "experiment_findings.md"

    updates: dict[str, Any] = {"status": "experiment_done"}

    if findings_md.is_file():
        updates["findings_path"] = str(findings_md)

    if results_json.is_file() or findings_md.is_file():
        update_workbench_item(key, updates)
        logger.info("Auto-finalised experiment for '%s' → experiment_done", key)
        return "experiment_done"

    # Revert to sandbox_ready so the user can retry — research is still valid
    update_workbench_item(key, {"status": "sandbox_ready", "pid": None})
    logger.warning(
        "Experiment agent for '%s' exited without results or findings → sandbox_ready (retry)",
        key,
    )
    return "sandbox_ready"


@router.get("/sandbox-files/{key:path}")
def get_sandbox_files(key: str) -> dict[str, Any]:
    """Return sandbox output files for a workbench item.

    Returns the experiment plan, run instructions, Dockerfile, and findings
    if they exist.

    Args:
        key: Namespaced workbench key.

    Returns:
        Dict with file contents (null if file doesn't exist).

    Raises:
        HTTPException: 404 if item not found.
    """
    entry = get_workbench_item(key)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Workbench item '{key}' not found")

    item = entry.get("item", {})
    source_type = entry.get("source_type", "tool")
    name = item.get("name", "unknown")
    slug = get_slug(name, source_type)
    output_dir = _WORKBENCH_ROOT / slug

    def _read_if_exists(filename: str) -> str | None:
        p = output_dir / filename
        if not p.is_file():
            return None
        if p.stat().st_size > _MAX_FILE_READ_BYTES:
            return f"[File too large to display: {p.stat().st_size} bytes]"
        return p.read_text(encoding="utf-8")

    return {
        "key": key,
        "experiment_plan": _read_if_exists("experiment_plan.md"),
        "run_sh": _read_if_exists("run.sh"),
        "dockerfile": _read_if_exists("Dockerfile"),
        "experiment_py": _read_if_exists("experiment.py"),
        "requirements_txt": _read_if_exists("requirements.txt"),
        "findings": _read_if_exists("experiment_findings.md"),
    }


@router.post("/run-experiment/{key:path}", status_code=202)
def run_experiment(key: str) -> dict[str, Any]:
    """Launch an experiment runner agent for a sandbox_ready item.

    The agent reads the experiment plan, executes ``bash run.sh`` (Docker),
    monitors the output, and ensures experiment_results.json and
    experiment_findings.md are written — including on failure.

    Args:
        key: Namespaced workbench key.

    Returns:
        Dict with pid and sandbox_dir.

    Raises:
        HTTPException: 404/409 if item not found or not sandbox_ready.
    """
    entry = get_workbench_item(key)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Workbench item '{key}' not found")

    status = entry.get("status", "queued")
    if status != "sandbox_ready":
        raise HTTPException(
            status_code=409, detail=f"Item not sandbox_ready (status={status})"
        )

    item = entry.get("item", {})
    source_type = entry.get("source_type", "tool")
    name = item.get("name", "unknown")
    slug = get_slug(name, source_type)
    output_dir = _WORKBENCH_ROOT / slug

    try:
        proc = launch_experiment_agent(item, output_dir)
    except Exception as exc:
        logger.error(
            "Experiment agent launch failed for '%s': %s", key, exc, exc_info=True
        )
        raise HTTPException(
            status_code=500, detail="Failed to launch experiment agent"
        ) from exc

    _server_owned_pids.add(proc.pid)
    update_workbench_item(
        key,
        {
            "status": "experiment_running",
            "pid": proc.pid,
            "log_file": str(output_dir / "experiment_agent.log"),
        },
    )

    logger.info("Launched experiment agent for '%s' (pid=%d)", key, proc.pid)
    return {"key": key, "pid": proc.pid, "sandbox_dir": str(output_dir)}


@router.get("/experiment-results/{key:path}")
def get_experiment_results(key: str) -> dict[str, Any]:
    """Return experiment results and findings if available.

    Args:
        key: Namespaced workbench key.

    Returns:
        Dict with results JSON and findings markdown (null if not yet available).
    """
    entry = get_workbench_item(key)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Workbench item '{key}' not found")

    item = entry.get("item", {})
    source_type = entry.get("source_type", "tool")
    name = item.get("name", "unknown")
    slug = get_slug(name, source_type)
    output_dir = _WORKBENCH_ROOT / slug

    results_json = output_dir / "experiment_results.json"
    findings_md = output_dir / "experiment_findings.md"
    experiment_log = output_dir / "experiment.log"

    results = None
    parse_error = False
    if results_json.is_file():
        try:
            results = json.loads(results_json.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning(
                "Failed to parse experiment_results.json for '%s': %s", key, exc
            )
            parse_error = True

    findings = None
    if findings_md.is_file() and findings_md.stat().st_size <= _MAX_FILE_READ_BYTES:
        findings = findings_md.read_text(encoding="utf-8")

    log_tail_str, _ = tail_log(experiment_log) if experiment_log.is_file() else ("", 0)

    return {
        "key": key,
        "results": results,
        "findings": findings,
        "log_tail": log_tail_str,
        "completed": results is not None,
        "parse_error": parse_error,
    }


@router.post("/kill-experiment/{key:path}")
def kill_experiment(key: str) -> dict[str, Any]:
    """Kill a running experiment process tree (docker build/run).

    Sends SIGTERM to the process group so both the shell and Docker
    child are terminated.

    Args:
        key: Namespaced workbench key.

    Returns:
        Dict confirming the kill.

    Raises:
        HTTPException: 404 if item not found, 409 if nothing running.
    """
    entry = get_workbench_item(key)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Workbench item '{key}' not found")

    pid = entry.get("pid")
    if not isinstance(pid, int) or pid <= 1:
        raise HTTPException(
            status_code=409, detail="No valid running experiment to kill"
        )

    if pid not in _server_owned_pids:
        logger.warning(
            "Refusing to kill PID %d for '%s' — not owned by this server", pid, key
        )
        raise HTTPException(
            status_code=409, detail="PID not owned by this server process"
        )

    if not is_agent_running(pid):
        _server_owned_pids.discard(pid)
        raise HTTPException(status_code=409, detail="No running experiment to kill")

    try:
        # Agents are launched with start_new_session=True, so the child's
        # PGID equals its own PID.  Kill the process group to terminate
        # the agent and any Docker children without touching the server.
        os.killpg(pid, signal.SIGTERM)
        logger.info("Killed experiment process group for '%s' (pgid=%d)", key, pid)
    except ProcessLookupError:
        logger.info("Process %d already exited for '%s'", pid, key)
    except PermissionError:
        # Fallback: kill just the PID
        try:
            os.kill(pid, signal.SIGTERM)
            logger.info("Killed experiment pid=%d for '%s' (no pgid access)", pid, key)
        except ProcessLookupError:
            pass

    _server_owned_pids.discard(pid)

    # Revert to sandbox_ready so the user can retry the experiment
    update_workbench_item(key, {"status": "sandbox_ready", "pid": None})
    return {"key": key, "killed": True}


@router.get("/experiment-design/{key:path}")
def get_experiment_design(key: str) -> dict[str, str]:
    """Return the Experiment Design section from a completed research report.

    Args:
        key: Namespaced workbench key.

    Returns:
        Dict with key and markdown content of the Experiment Design section.

    Raises:
        HTTPException: 404 if item or section not found.
    """
    entry = get_workbench_item(key)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Workbench item '{key}' not found")

    item = entry.get("item", {})
    source_type = entry.get("source_type", "tool")
    name = item.get("name", "unknown")
    slug = get_slug(name, source_type)
    research_md = _WORKBENCH_ROOT / slug / "research.md"

    if not research_md.is_file():
        raise HTTPException(status_code=404, detail="research.md not found")

    content = research_md.read_text(encoding="utf-8")
    section = _extract_section(content, "Experiment Design")
    if not section:
        raise HTTPException(
            status_code=404, detail="Experiment Design section not found"
        )

    return {"key": key, "content": section}


def _extract_section(content: str, heading: str) -> str:
    """Extract the body text of a ## heading from markdown.

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


@router.post("/sandbox/{key:path}", status_code=202)
def launch_sandbox(key: str) -> dict[str, Any]:
    """Launch a sandbox agent for a researched workbench item.

    Requires the item to have status 'researched' with experiment_type
    'programmatic' and a completed research.md file.

    Args:
        key: Namespaced workbench key (e.g. 'tool::Cursor Tab').

    Returns:
        Dict with pid, output_dir, and key.

    Raises:
        HTTPException: 404 if item not found, 409 if not ready for sandbox.
    """
    entry = get_workbench_item(key)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Workbench item '{key}' not found")

    status = entry.get("status", "queued")
    experiment_type = entry.get("experiment_type")
    if status != "researched" or experiment_type != "programmatic":
        raise HTTPException(
            status_code=409,
            detail=f"Item not ready for sandbox (status={status}, experiment_type={experiment_type})",
        )

    item = entry.get("item", {})
    source_type = entry.get("source_type", "tool")
    name = item.get("name", "unknown")
    slug = get_slug(name, source_type)
    output_dir = _WORKBENCH_ROOT / slug
    research_md = output_dir / "research.md"

    if not research_md.is_file():
        raise HTTPException(
            status_code=409, detail="research.md not found — run research first"
        )

    try:
        proc = launch_sandbox_agent(item, research_md, output_dir)
    except Exception as exc:
        logger.error("Sandbox launch failed for '%s': %s", key, exc, exc_info=True)
        raise HTTPException(
            status_code=500, detail="Sandbox agent launch failed"
        ) from exc

    _server_owned_pids.add(proc.pid)
    logger.info("Launched sandbox agent for '%s' (pid=%d)", key, proc.pid)
    update_workbench_item(
        key,
        {
            "status": "sandbox_creating",
            "pid": proc.pid,
            "log_file": str(output_dir / "sandbox_agent.log"),
        },
    )

    return {
        "key": key,
        "pid": proc.pid,
        "output_dir": str(output_dir),
    }


@router.get("/report/{key:path}")
def get_research_report(key: str) -> HTMLResponse:
    """Return the rendered research report HTML for a workbench item.

    Args:
        key: Namespaced workbench key (e.g. 'tool::Cursor Tab').

    Returns:
        HTML content of the research report.

    Raises:
        HTTPException: 404 if item or report not found.
    """
    entry = get_workbench_item(key)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Workbench item '{key}' not found")

    item = entry.get("item", {})
    source_type = entry.get("source_type", "tool")
    name = item.get("name", "unknown")
    slug = get_slug(name, source_type)
    report_path = _WORKBENCH_ROOT / slug / "research.html"

    if not report_path.is_file():
        # Fall back to markdown
        md_path = _WORKBENCH_ROOT / slug / "research.md"
        if md_path.is_file():
            md_content = md_path.read_text(encoding="utf-8")
            escaped = html_module.escape(md_content)
            return HTMLResponse(
                content=f"<pre style='white-space:pre-wrap;font-family:monospace;'>{escaped}</pre>"
            )
        raise HTTPException(status_code=404, detail="No research report found")

    html_content = report_path.read_text(encoding="utf-8")
    return HTMLResponse(
        content=html_content,
        headers={
            "Content-Security-Policy": "default-src 'self'; script-src 'none'; style-src 'unsafe-inline'",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
        },
    )


def _find_ig_post_note(vault: Path, account: str, shortcode: str) -> Path | None:
    """Find the vault note for an Instagram post by account and shortcode.

    Args:
        vault: Root vault path.
        account: Instagram account handle.
        shortcode: Instagram post shortcode.

    Returns:
        Path to the vault note, or None if not found.
    """
    ig_dir = vault / "Research" / "Instagram" / account
    if not ig_dir.is_dir():
        return None
    for md_file in ig_dir.glob(f"*{shortcode}*"):
        if md_file.suffix == ".md":
            return md_file
    return None


def _ig_note_relative_path(note_path: Path, vault: Path) -> str:
    """Get vault-relative path without extension for wiki-linking.

    Args:
        note_path: Absolute path to the vault note.
        vault: Root vault path.

    Returns:
        Relative path string without .md extension.
    """
    return str(note_path.relative_to(vault).with_suffix(""))


def _build_vault_note(
    name: str,
    source_type: str,
    projects: list[str],
    research_md_path: Path,
    source_note_link: str | None = None,
) -> str:
    """Build an Obsidian-flavoured markdown note from a research report.

    Args:
        name: Item display name.
        source_type: Item source type (tool, method, instagram).
        projects: Associated project names for wiki-links.
        research_md_path: Path to the research.md file.
        source_note_link: Optional wiki-link to the source note (e.g. IG post).

    Returns:
        Markdown string ready to write to the vault.
    """
    # Read the research content
    research_content = ""
    if research_md_path.is_file():
        research_content = research_md_path.read_text(encoding="utf-8")

    # Build frontmatter
    tags = [f"research/{source_type}", "workbench"]
    lines = [
        "---",
        f"tags: [{', '.join(tags)}]",
        f"source_type: {source_type}",
        "status: researched",
    ]
    if projects:
        lines.append(f"projects: [{', '.join(projects)}]")
    lines.append("---")
    lines.append("")

    # Source link (e.g. back to the IG post)
    if source_note_link:
        lines.append(f"**Source:** {source_note_link}")
        lines.append("")

    # Project wiki-links
    if projects:
        project_links = " · ".join(f"[[{p}]]" for p in projects)
        lines.append(f"**Projects:** {project_links}")
        lines.append("")

    # Append research content (skip its H1 if it matches name)
    for line in research_content.splitlines():
        if line.startswith("# ") and line[2:].strip() == name:
            continue
        lines.append(line)

    return "\n".join(lines)


@router.post("/publish-vault/{key:path}")
def publish_to_vault(
    key: str,
    vault_path: str = Depends(get_vault_path_str),
) -> dict[str, str]:
    """Publish a research report as an Obsidian vault note.

    Creates a note in Research/Workbench/{Name}.md with frontmatter,
    project wiki-links, and the research content. Updates the workbench
    entry with the vault_note path.

    Args:
        key: Namespaced workbench key.

    Returns:
        Dict with vault_note path and obsidian_uri for deep-linking.

    Raises:
        HTTPException: 404 if item not found.
    """
    entry = get_workbench_item(key)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Workbench item '{key}' not found")

    item = entry.get("item", {})
    source_type = entry.get("source_type", "tool")
    name = item.get("name", "unknown")
    projects = item.get("projects", [])
    slug = get_slug(name, source_type)
    research_md = _WORKBENCH_ROOT / slug / "research.md"

    vault = Path(vault_path)

    # For IG posts, find the source note and build a backlink
    source_note_link: str | None = None
    ig_source_note: Path | None = None
    if source_type == "instagram":
        account = item.get("account", "")
        shortcode = item.get("shortcode", "")
        if account and shortcode:
            ig_source_note = _find_ig_post_note(vault, account, shortcode)
            if ig_source_note:
                rel = _ig_note_relative_path(ig_source_note, vault)
                source_note_link = f"[[{rel}]]"

    # Build and write vault note — sanitize name to prevent path traversal
    safe_name = Path(name).name  # strip any directory components
    if not safe_name or safe_name in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid item name")
    vault_dir = vault / "Research" / "Workbench"
    vault_dir.mkdir(parents=True, exist_ok=True)
    note_path = (vault_dir / f"{safe_name}.md").resolve()
    if not note_path.is_relative_to(vault_dir.resolve()):
        raise HTTPException(status_code=400, detail="Invalid item name")

    note_content = _build_vault_note(
        name,
        source_type,
        projects,
        research_md,
        source_note_link=source_note_link,
    )
    note_path.write_text(note_content, encoding="utf-8")

    # Add forward link from IG post to this research note
    if ig_source_note and ig_source_note.is_file():
        research_link = f"[[Research/Workbench/{safe_name}|Research Report]]"
        ig_content = ig_source_note.read_text(encoding="utf-8")
        if research_link not in ig_content:
            ig_content += f"\n\n## Research\n{research_link}\n"
            ig_source_note.write_text(ig_content, encoding="utf-8")
            logger.info("Added research link to IG note: %s", ig_source_note)

    # Relative path within vault for obsidian:// URI
    relative_path = f"Research/Workbench/{safe_name}"

    # Update workbench entry
    update_workbench_item(key, {"vault_note": str(note_path)})

    # Build obsidian:// deep link
    vault_name = vault.name
    obsidian_uri = f"obsidian://open?vault={vault_name}&file={relative_path}"

    logger.info("Published vault note: %s (projects: %s)", note_path, projects)
    return {"vault_note": relative_path, "obsidian_uri": obsidian_uri}


# ── Reports listing ──────────────────────────────────────────────


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
_HEADING_RE = re.compile(r"^#\s+(.+)", re.MULTILINE)
_FIELD_RE = re.compile(r"^\*\*(.+?):\*\*\s*(.+)", re.MULTILINE)


def _parse_report_meta(slug: str, md_path: Path) -> dict[str, Any]:
    """Extract metadata from a research.md file for the reports listing.

    Args:
        slug: Directory name (e.g. 'tool-skore').
        md_path: Path to the research.md file.

    Returns:
        Dict with slug, title, source_type, researched date, and flags.
    """
    text = md_path.read_text(encoding="utf-8")
    meta: dict[str, Any] = {"slug": slug}

    # Detect source type from slug prefix
    if slug.startswith("instagram-"):
        meta["source_type"] = "instagram"
    elif slug.startswith("method-"):
        meta["source_type"] = "method"
    elif slug.startswith("tool-"):
        meta["source_type"] = "tool"
    else:
        meta["source_type"] = "unknown"

    # Try YAML frontmatter first
    fm_match = _FRONTMATTER_RE.match(text)
    if fm_match:
        fm_block = fm_match.group(1)
        for line in fm_block.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                k, v = k.strip(), v.strip()
                if k == "researched":
                    meta["researched"] = v
                elif k in ("tool", "method", "title"):
                    meta["title"] = v

    # Extract title from first heading if not in frontmatter
    if "title" not in meta:
        heading = _HEADING_RE.search(text)
        if heading:
            meta["title"] = heading.group(1).strip()
        else:
            meta["title"] = slug.replace("-", " ").title()

    # Extract inline fields (e.g. **Researched:** ...)
    for fm in _FIELD_RE.finditer(text):
        field_name = fm.group(1).strip().lower()
        field_val = fm.group(2).strip()
        if field_name == "researched" and "researched" not in meta:
            meta["researched"] = field_val
        elif field_name in ("source", "original"):
            meta["source_label"] = field_val

    # Fall back to file mtime for date
    if "researched" not in meta:
        mtime = md_path.stat().st_mtime
        meta["researched"] = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")

    # Check for HTML report
    meta["has_html"] = (md_path.parent / "research.html").is_file()

    # Extract first ~200 chars of body as excerpt
    body = text
    if fm_match:
        body = text[fm_match.end() :]
    # Strip headings and bold fields to get prose
    lines = [
        ln
        for ln in body.strip().splitlines()
        if ln.strip()
        and not ln.startswith("#")
        and not ln.startswith("**")
        and not ln.startswith("---")
        and not ln.startswith("|")
    ]
    excerpt = " ".join(lines[:3])[:200]
    meta["excerpt"] = excerpt

    return meta


@router.get("/reports")
def list_reports() -> list[dict[str, Any]]:
    """List all completed research reports.

    Scans ~/research-workbench/ for directories containing research.md
    and returns metadata for each.

    Returns:
        List of report metadata dicts, sorted by researched date descending.
    """
    reports: list[dict[str, Any]] = []

    if not _WORKBENCH_ROOT.is_dir():
        return reports

    for sub in sorted(_WORKBENCH_ROOT.iterdir()):
        if not sub.is_dir():
            continue
        md_path = sub / "research.md"
        if not md_path.is_file():
            continue
        try:
            meta = _parse_report_meta(sub.name, md_path)
            reports.append(meta)
        except Exception:
            logger.warning("Failed to parse report: %s", sub.name, exc_info=True)

    # Sort by researched date descending
    reports.sort(key=lambda r: r.get("researched", ""), reverse=True)
    return reports


@router.get("/reports/{slug}/content")
def get_report_content(slug: str) -> dict[str, str]:
    """Return the raw markdown content of a research report.

    Args:
        slug: Report directory name (e.g. 'tool-skore').

    Returns:
        Dict with slug and markdown content.

    Raises:
        HTTPException: 404 if report not found.
    """
    report_dir = (_WORKBENCH_ROOT / slug).resolve()
    if not report_dir.is_relative_to(_WORKBENCH_ROOT.resolve()):
        raise HTTPException(status_code=400, detail="Invalid slug")
    md_path = report_dir / "research.md"

    if not md_path.is_file():
        raise HTTPException(status_code=404, detail="Report not found")

    content = md_path.read_text(encoding="utf-8")

    # Strip YAML frontmatter for display
    fm_match = _FRONTMATTER_RE.match(content)
    if fm_match:
        content = content[fm_match.end() :].strip()

    return {"slug": slug, "content": content}
