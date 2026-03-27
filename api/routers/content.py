"""Content router — methods, tools, blog queue, reports, instagram, summaries."""

import hashlib
import logging
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_vault_path_str
from api.models import BlogDraftRequest, SummarizeInstagramRequest

from utils.blog_queue_parser import parse_blog_queue
from utils.claude_client import (
    analyze_blog_potential,
    deep_read_paper,
    generate_blog_draft,
    summarize_instagram_post,
    summarize_paper,
    summarize_tool,
)
from utils.paper_fetcher import fetch_paper_context
from utils.blog_publisher import write_draft_mdx
from utils.instagram_parser import parse_instagram_posts
from utils.methods_parser import parse_methods
from utils.reports_parser import (
    parse_journalclub_papers,
    parse_journalclub_reports,
    parse_tldr_reports,
)
from utils.status_tracker import load_status
from utils.tools_parser import parse_tools
from utils.vault_parser import parse_projects

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["content"])


# ---------------------------------------------------------------------------
# Field mapping helpers — transform parser output to frontend contract
# ---------------------------------------------------------------------------


def _dismissed_keys() -> set[str]:
    """Return the set of item keys with 'dismissed' status."""
    data = load_status()
    return {
        k
        for k, v in data.get("items", {}).items()
        if (v == "dismissed")
        or (isinstance(v, dict) and v.get("status") == "dismissed")
    }


def _strip_markdown(text: str) -> str:
    """Remove markdown bold/italic and wiki-link syntax from text."""
    text = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", text)
    text = re.sub(r"\[\[(.+?)(?:\|.+?)?\]\]", r"\1", text)
    return text


_URL_RE = re.compile(r"https?://\S+")


def _extract_url(text: str) -> str:
    """Extract the first URL from a text string."""
    match = _URL_RE.search(text)
    return match.group(0) if match else ""


def _clean_source(text: str) -> str:
    """Strip markdown, URLs, and 'Link:' labels from a source field."""
    cleaned = _strip_markdown(text)
    cleaned = _URL_RE.sub("", cleaned)
    # Remove leftover "Link:" labels and pipe separators
    cleaned = re.sub(r"\bLink:\s*", "", cleaned)
    cleaned = re.sub(r"\s*\|\s*$", "", cleaned).strip()
    return cleaned


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
        "hook": item.get("hook", ""),
        "source_paper": item.get("source paper", ""),
        "projects": item.get("projects", []),
        "added": item.get("added", ""),
    }


def _get_cached_tool_summary(tool: dict[str, Any]) -> str:
    """Return cached Haiku summary if available, empty string otherwise.

    Never makes an API call — use the /tools/summarize endpoint to generate.
    """
    raw = f"v2:{tool.get('name', '')}::tool_summary_v2:nograph"
    cache_key = hashlib.sha256(raw.encode()).hexdigest()
    data = load_status()
    cached = data.get("cache", {}).get(cache_key)
    if cached is not None:
        return cached.get("response", "")
    return ""


def _to_tool_item(item: dict[str, Any]) -> dict[str, Any]:
    """Map parser tool item → frontend ToolItem contract."""
    raw_source = item.get("source", "")
    url = item.get("url", "") or _extract_url(raw_source)
    source_label = _clean_source(raw_source)
    return {
        "name": item.get("name", ""),
        "category": item.get("category", "Uncategorized"),
        "status": item.get("status", "New"),
        "source": source_label,
        "url": url,
        "notes": item.get("what it does", ""),
        "summary": _get_cached_tool_summary(item),
        "tags": _parse_tags(item.get("tags", "")),
        "projects": item.get("projects", []),
    }


def _to_method_item(item: dict[str, Any]) -> dict[str, Any]:
    """Map parser method item → frontend MethodItem contract."""
    # Derive short category from source field: "JournalClub 2026-03-14 | ..." → "JournalClub"
    source_raw = item.get("source", "")
    category = source_raw.split(" ")[0] if source_raw else ""

    # Use the method description as notes (it's the richest text field)
    notes = (
        item.get("why it matters", "") or item.get("method", "") or item.get("idea", "")
    )

    return {
        "name": item.get("name", ""),
        "category": category,
        "status": item.get("status", "New"),
        "source": source_raw,
        "paper_url": item.get("paper_url", ""),
        "notes": notes,
        "tags": _parse_tags(item.get("tags", "")),
    }


def _extract_report_brief(report: dict[str, Any], report_type: str) -> dict[str, Any]:
    """Extract structured brief from a single report.

    Always returns a fully normalized dict with all fields present.
    JournalClub → top_picks populated. TLDR → top_tools + ai_signal populated.
    """
    sections = report.get("sections", {})

    top_picks: list[str] = []
    top_tools: list[dict[str, str]] = []
    ai_signal: str | None = None
    ai_signal_source: str | None = None

    if report_type == "journalclub":
        picks_md = sections.get("Top Picks This Week", "") or sections.get(
            "Top Picks", ""
        )
        if picks_md:
            for line in picks_md.strip().splitlines():
                clean = re.sub(r"^(?:\d+\.\s*|[-*]\s*)", "", line.strip()).strip()
                if clean:
                    top_picks.append(_strip_markdown(clean))

    elif report_type == "tldr":
        tools_md = sections.get("Tools", "") or sections.get("Tools Mentioned", "")
        if tools_md:
            for line in tools_md.strip().splitlines():
                clean = line.strip().lstrip("- ").strip()
                if clean:
                    top_tools.append({"name": _strip_markdown(clean), "category": ""})

        signal = report.get("ai_signal", "")
        if signal:
            signal = _strip_markdown(signal)
            ai_signal = signal[:500] + "..." if len(signal) > 500 else signal
            ai_signal_source = f"TLDR {report.get('date', '')}"

    return {
        "top_picks": top_picks,
        "top_tools": top_tools,
        "blog_ideas": [],
        "ai_signal": ai_signal,
        "ai_signal_source": ai_signal_source,
    }


def _to_report_item(report: dict[str, Any], report_type: str) -> dict[str, Any]:
    """Map parser report → frontend ReportItem contract."""
    filename = report.get("filename", "")
    date = report.get("date", "")
    # Derive a readable title: "JournalClub 2026-03-07" or "TLDR 2026-03-20"
    type_label = "JournalClub" if report_type == "journalclub" else "TLDR"
    title = filename.replace(".md", "") if filename else f"{type_label} {date}"

    # Extract highlights: first 5 non-empty section keys as summary (legacy)
    sections = report.get("sections", {})
    highlights = [k for k in sections.keys() if k][:5]

    # Build a brief summary from section content (legacy)
    summary_parts: list[str] = []
    for key, body in list(sections.items())[:5]:
        if not body or not body.strip():
            continue
        for line in body.strip().splitlines():
            clean = line.strip().lstrip("- ").strip()
            if clean:
                summary_parts.append(clean[:120] + ("…" if len(clean) > 120 else ""))
                break

    return {
        "title": title,
        "date": report.get("date", ""),
        "source": "journalclub" if report_type == "journalclub" else "tldr",
        "type": report_type,
        "highlights": highlights,
        "summary": " · ".join(summary_parts) if summary_parts else None,
        "brief": _extract_report_brief(report, report_type),
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
    """Aggregated counts for dashboard metric cards (excludes dismissed)."""
    vault = Path(vault_path)
    dismissed = _dismissed_keys()
    papers = [
        p
        for p in parse_journalclub_papers(vault)
        if f"paper::{p.get('title', '')}" not in dismissed
    ]
    tools = [
        t for t in parse_tools(vault) if f"tool::{t.get('name', '')}" not in dismissed
    ]
    blog = [
        b
        for b in parse_blog_queue(vault)
        if f"blog::{b.get('name', '')}" not in dismissed
    ]
    return {
        "papers": len(papers),
        "tools": len(tools),
        "blog_queue": len(blog),
        "active_projects": len(parse_projects(vault)),
    }


@router.get("/dashboard/home-summary")
def get_home_summary(
    vault_path: str = Depends(get_vault_path_str),
) -> dict[str, Any]:
    """Cross-source summary for the Home tab — mirrors the Streamlit homepage."""
    vault = Path(vault_path)

    # JournalClub top picks
    jc_reports = parse_journalclub_reports(vault)
    top_picks: list[str] = []
    if jc_reports:
        latest_jc = jc_reports[0]
        sections = latest_jc.get("sections", {})
        picks_md = sections.get("Top Picks This Week", "") or sections.get(
            "Top Picks", ""
        )
        if picks_md:
            for line in picks_md.strip().splitlines():
                clean = line.strip().lstrip("- ").strip()
                if clean:
                    clean = _strip_markdown(clean)
                    top_picks.append(clean)

    # Top tools (first 3)
    tools = parse_tools(vault)
    top_tools = [
        {"name": t.get("name", ""), "category": t.get("category", "")}
        for t in tools[:3]
    ]

    # Blog ideas (first 3)
    blog_items = parse_blog_queue(vault)
    blog_ideas = [
        {"title": b.get("name", ""), "status": b.get("status", "Idea")}
        for b in blog_items[:3]
    ]

    # AI signal excerpt
    tldr_reports = parse_tldr_reports(vault)
    ai_signal: str | None = None
    ai_signal_source: str | None = None
    if tldr_reports:
        latest_tldr = tldr_reports[0]
        signal = latest_tldr.get("ai_signal", "")
        if signal:
            signal = _strip_markdown(signal)
            ai_signal = signal[:500] + "..." if len(signal) > 500 else signal
            ai_signal_source = f"TLDR {latest_tldr['date']}"

    return {
        "top_picks": top_picks,
        "top_tools": top_tools,
        "blog_ideas": blog_ideas,
        "ai_signal": ai_signal,
        "ai_signal_source": ai_signal_source,
    }


@router.get("/methods")
def list_methods(
    vault_path: str = Depends(get_vault_path_str),
) -> list[dict[str, Any]]:
    """List all methods from the vault (excludes dismissed)."""
    dismissed = _dismissed_keys()
    return [
        _to_method_item(m)
        for m in parse_methods(Path(vault_path))
        if f"method::{m.get('name', '')}" not in dismissed
    ]


@router.get("/tools")
def list_tools(
    vault_path: str = Depends(get_vault_path_str),
) -> list[dict[str, Any]]:
    """List all tools from the vault (excludes dismissed)."""
    dismissed = _dismissed_keys()
    return [
        _to_tool_item(t)
        for t in parse_tools(Path(vault_path))
        if f"tool::{t.get('name', '')}" not in dismissed
    ]


@router.post("/tools/summarize")
def summarize_tool_endpoint(
    body: dict[str, Any],
    vault_path: str = Depends(get_vault_path_str),
) -> dict[str, str]:
    """Generate a plain-English summary for a tool using Haiku (cached).

    Args:
        body: Dict with 'name' key identifying the tool.

    Returns:
        Dict with 'summary' field.
    """
    name = body.get("name", "")
    tools = parse_tools(Path(vault_path))
    tool = next((t for t in tools if t.get("name") == name), None)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")
    summary = summarize_tool(tool)
    return {"summary": summary}


@router.get("/blog-queue")
def list_blog_queue(
    vault_path: str = Depends(get_vault_path_str),
) -> list[dict[str, Any]]:
    """List all blog queue items from the vault (excludes dismissed)."""
    dismissed = _dismissed_keys()
    return [
        _to_blog_item(b)
        for b in parse_blog_queue(Path(vault_path))
        if f"blog::{b.get('name', '')}" not in dismissed
    ]


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


@router.get("/papers")
def list_papers(
    vault_path: str = Depends(get_vault_path_str),
) -> list[dict[str, Any]]:
    """List all individual papers extracted from JournalClub reports (excludes dismissed)."""
    dismissed = _dismissed_keys()
    return [
        p
        for p in parse_journalclub_papers(Path(vault_path))
        if f"paper::{p.get('title', '')}" not in dismissed
    ]


@router.get("/instagram/feed")
def list_instagram_feed(
    vault_path: str = Depends(get_vault_path_str),
) -> list[dict[str, Any]]:
    """List Instagram posts mapped to frontend InstagramPost contract (excludes dismissed)."""
    dismissed = _dismissed_keys()
    posts = [_to_instagram_post(p) for p in parse_instagram_posts(Path(vault_path))]
    return [p for p in posts if f"instagram::{p['title']}" not in dismissed]


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
            detail="Draft already exists for this item.",
        ) from exc

    return {"draft": draft, "draft_path": path.name}


@router.post("/blog-queue/summarize")
def summarize_blog_item(body: BlogDraftRequest) -> dict[str, str]:
    """Generate a quick summary of a blog item's source paper using Haiku.

    Args:
        body: Request with blog item dict (name, hook, source fields).

    Returns:
        Dict with 'summary' field.
    """
    summary = summarize_paper(body.item)
    return {"summary": summary}


@router.post("/blog-queue/deep-read")
def deep_read_blog_item(body: BlogDraftRequest) -> dict[str, str]:
    """Generate a deep read synthesis of a blog item's source paper using Sonnet.

    Args:
        body: Request with blog item dict.

    Returns:
        Dict with 'deep_read' field.
    """
    result = deep_read_paper(body.item)
    return {"deep_read": result}


@router.post("/blog-queue/analyze")
def analyze_blog_item(body: BlogDraftRequest) -> dict[str, Any]:
    """Analyze a blog item's potential using Haiku.

    Args:
        body: Request with blog item dict.

    Returns:
        Dict with 'analysis' field.
    """
    result = analyze_blog_potential(body.item)
    return {"analysis": result.get("response", "")}


@router.post("/papers/abstract")
def fetch_paper_abstract_endpoint(body: dict[str, str]) -> dict[str, Any]:
    """Fetch paper context (abstract, authors, venue) from Semantic Scholar.

    Args:
        body: Dict with 'title' field.

    Returns:
        PaperContext fields.
    """
    title = body.get("title", "")
    context = fetch_paper_context(title)
    return {
        "abstract": context["abstract"],
        "authors": context["authors"],
        "year": context["year"],
        "venue": context["venue"],
        "fetch_state": context["fetch_state"],
    }
