"""Research router — launch research agents and check status."""

import html as html_module
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from api.deps import get_vault_path_str
from fastapi import Depends
from utils.research_agent import is_agent_running, launch_research_agent, tail_log
from utils.workbench_tracker import (
    get_slug,
    get_workbench_item,
    update_workbench_item,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/research", tags=["research"])

_WORKBENCH_ROOT = Path.home() / "research-workbench"


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
    """Check research agent status for a workbench item.

    Args:
        key: Namespaced workbench key.

    Returns:
        Dict with running status, log tail, and key.

    Raises:
        HTTPException: 404 if item not found in workbench.
    """
    entry = get_workbench_item(key)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Workbench item '{key}' not found")

    pid = entry.get("pid")
    log_file = entry.get("log_file", "")
    running = is_agent_running(pid) if pid else False
    log_tail, _ = tail_log(Path(log_file)) if log_file else ("", 0)

    return {
        "key": key,
        "running": running,
        "pid": pid,
        "log_tail": log_tail,
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
    return HTMLResponse(content=html_content)


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
