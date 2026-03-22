"""Content router — methods, tools, blog queue, reports, instagram, summaries."""

import logging
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["content"])


@router.get("/methods")
def list_methods(
    vault_path: str = Depends(get_vault_path_str),
) -> list[dict[str, Any]]:
    """List all methods from the vault."""
    from pathlib import Path

    return parse_methods(Path(vault_path))


@router.get("/tools")
def list_tools(
    vault_path: str = Depends(get_vault_path_str),
) -> list[dict[str, Any]]:
    """List all tools from the vault."""
    from pathlib import Path

    return parse_tools(Path(vault_path))


@router.get("/blog-queue")
def list_blog_queue(
    vault_path: str = Depends(get_vault_path_str),
) -> list[dict[str, Any]]:
    """List all blog queue items from the vault."""
    from pathlib import Path

    return parse_blog_queue(Path(vault_path))


@router.get("/reports/{report_type}")
def list_reports(
    report_type: str,
    vault_path: str = Depends(get_vault_path_str),
) -> list[dict[str, Any]]:
    """List reports by type (journalclub or tldr)."""
    from pathlib import Path

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


@router.get("/instagram")
def list_instagram(
    vault_path: str = Depends(get_vault_path_str),
) -> list[dict[str, Any]]:
    """List all Instagram posts from the vault."""
    from pathlib import Path

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
