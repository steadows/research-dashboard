"""Content router — methods, tools, blog queue, reports, instagram, summaries."""

import hashlib
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_vault_path_str
from api.models import BlogDraftRequest, SummarizeInstagramRequest

from utils.blog_queue_parser import parse_blog_queue
from utils.claude_client import generate_blog_draft, summarize_instagram_post
from utils.blog_publisher import write_draft_mdx
from utils.instagram_parser import parse_instagram_posts
from utils.methods_parser import parse_methods
from utils.reports_parser import parse_journalclub_reports, parse_tldr_reports
from utils.tools_parser import parse_tools
from utils.vault_parser import parse_projects

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["content"])


# ---------------------------------------------------------------------------
# Field mapping helpers — transform parser output to frontend contract
# ---------------------------------------------------------------------------


def _parse_tags(raw: str) -> list[str]:
    """Split a comma-separated tags string into a list."""
    if not raw:
        return []
    return [t.strip() for t in raw.split(",") if t.strip()]


def _to_blog_item(item: dict[str, Any]) -> dict[str, Any]:
    """Map parser blog item → frontend BlogItem contract."""
    return {
        "title": item.get("name", ""),
        "status": item.get("status", "Idea"),
        "category": item.get("source_type", "blog"),
        "tags": _parse_tags(item.get("tags", "")),
        "source": item.get("source", ""),
        "notes": item.get("hook", ""),
    }


def _to_tool_item(item: dict[str, Any]) -> dict[str, Any]:
    """Map parser tool item → frontend ToolItem contract."""
    return {
        "name": item.get("name", ""),
        "category": item.get("category", "Uncategorized"),
        "status": item.get("status", "New"),
        "source": item.get("source", ""),
        "url": item.get("url", ""),
        "notes": item.get("what it does", ""),
        "tags": _parse_tags(item.get("tags", "")),
    }


def _to_method_item(item: dict[str, Any]) -> dict[str, Any]:
    """Map parser method item → frontend MethodItem contract."""
    # Derive short category from source field: "JournalClub 2026-03-14 | ..." → "JournalClub"
    source_raw = item.get("source", "")
    category = source_raw.split(" ")[0] if source_raw else ""

    # Use the method description as notes (it's the richest text field)
    notes = item.get("why it matters", "") or item.get("method", "") or item.get("idea", "")

    return {
        "name": item.get("name", ""),
        "category": category,
        "status": item.get("status", "New"),
        "source": source_raw,
        "paper_url": item.get("paper_url", ""),
        "notes": notes,
        "tags": _parse_tags(item.get("tags", "")),
    }


def _to_report_item(
    report: dict[str, Any], report_type: str
) -> dict[str, Any]:
    """Map parser report → frontend ReportItem contract."""
    filename = report.get("filename", "")
    date = report.get("date", "")
    # Derive a readable title: "JournalClub 2026-03-07" or "TLDR 2026-03-20"
    type_label = "JournalClub" if report_type == "journalclub" else "TLDR"
    title = filename.replace(".md", "") if filename else f"{type_label} {date}"

    # Extract highlights: first 5 non-empty section keys as summary
    sections = report.get("sections", {})
    highlights = [k for k in sections.keys() if k][:5]

    return {
        "title": title,
        "date": report.get("date", ""),
        "source": "journalclub" if report_type == "journalclub" else "tldr",
        "type": report_type,
        "highlights": highlights,
        "file_path": filename,
    }


def _to_instagram_post(item: dict[str, Any]) -> dict[str, Any]:
    """Map parser instagram item → frontend InstagramPost contract."""
    name = item.get("name", "")
    shortcode = item.get("shortcode", "")
    # Generate stable ID from shortcode or name
    id_source = shortcode or name
    post_id = hashlib.md5(id_source.encode()).hexdigest()[:12]

    # Truncate transcript to ~200 chars for excerpt
    transcript = item.get("transcript", "")
    excerpt = (transcript[:200] + "…") if len(transcript) > 200 else transcript

    return {
        "id": post_id,
        "account": item.get("account", ""),
        "title": name,
        "key_points": item.get("key_points", []),
        "transcript_excerpt": excerpt if excerpt else None,
        "tags": item.get("keywords", []),
        "timestamp": item.get("date", ""),
        "status": item.get("status", "new"),
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/dashboard/stats")
def get_dashboard_stats(
    vault_path: str = Depends(get_vault_path_str),
) -> dict[str, int]:
    """Aggregated counts for dashboard metric cards."""
    vault = Path(vault_path)
    return {
        "papers": len(parse_methods(vault)),
        "tools": len(parse_tools(vault)),
        "blog_queue": len(parse_blog_queue(vault)),
        "active_projects": len(parse_projects(vault)),
    }


@router.get("/methods")
def list_methods(
    vault_path: str = Depends(get_vault_path_str),
) -> list[dict[str, Any]]:
    """List all methods from the vault."""
    return [_to_method_item(m) for m in parse_methods(Path(vault_path))]


@router.get("/tools")
def list_tools(
    vault_path: str = Depends(get_vault_path_str),
) -> list[dict[str, Any]]:
    """List all tools from the vault."""
    return [_to_tool_item(t) for t in parse_tools(Path(vault_path))]


@router.get("/blog-queue")
def list_blog_queue(
    vault_path: str = Depends(get_vault_path_str),
) -> list[dict[str, Any]]:
    """List all blog queue items from the vault."""
    return [_to_blog_item(b) for b in parse_blog_queue(Path(vault_path))]


@router.get("/reports")
def list_reports_unified(
    vault_path: str = Depends(get_vault_path_str),
) -> list[dict[str, Any]]:
    """List all reports (JournalClub + TLDR) merged and sorted by date."""
    vault = Path(vault_path)
    jc = [_to_report_item(r, "journalclub") for r in parse_journalclub_reports(vault)]
    tldr = [_to_report_item(r, "tldr") for r in parse_tldr_reports(vault)]
    merged = jc + tldr
    merged.sort(key=lambda r: r["date"], reverse=True)
    return merged


@router.get("/reports/{report_type}")
def list_reports(
    report_type: str,
    vault_path: str = Depends(get_vault_path_str),
) -> list[dict[str, Any]]:
    """List reports by type (journalclub or tldr)."""
    vault = Path(vault_path)
    if report_type == "journalclub":
        return parse_journalclub_reports(vault)
    elif report_type == "tldr":
        return parse_tldr_reports(vault)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid report type '{report_type}'. Use 'journalclub' or 'tldr'.",
        )


@router.get("/instagram/feed")
def list_instagram_feed(
    vault_path: str = Depends(get_vault_path_str),
) -> list[dict[str, Any]]:
    """List Instagram posts mapped to frontend InstagramPost contract."""
    return [_to_instagram_post(p) for p in parse_instagram_posts(Path(vault_path))]


@router.get("/instagram")
def list_instagram(
    vault_path: str = Depends(get_vault_path_str),
) -> list[dict[str, Any]]:
    """List all Instagram posts (raw parser output)."""
    return parse_instagram_posts(Path(vault_path))


@router.post("/summarize/instagram")
def summarize_instagram(body: SummarizeInstagramRequest) -> dict[str, str]:
    """Summarize an Instagram post using Haiku.

    Args:
        body: Request with post dict.

    Returns:
        Dict with 'summary' field.
    """
    summary = summarize_instagram_post(body.post)
    return {"summary": summary}


@router.post("/blog-queue/draft")
def create_blog_draft(body: BlogDraftRequest) -> dict[str, str]:
    """Generate a blog draft using Sonnet and write MDX file.

    Args:
        body: Request with blog item dict.

    Returns:
        Dict with 'draft' body and 'draft_path'.
    """
    draft = generate_blog_draft(body.item)
    try:
        path = write_draft_mdx(body.item, draft)
    except FileExistsError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"Draft already exists: {exc}",
        ) from exc

    return {"draft": draft, "draft_path": str(path)}
