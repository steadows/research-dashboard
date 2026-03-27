"""Workbench router — CRUD for workbench items."""

import logging
import re
from typing import Any

from fastapi import APIRouter, HTTPException

from api.models import WorkbenchAddRequest, WorkbenchUpdateRequest
from utils.workbench_tracker import (
    add_to_workbench,
    get_workbench_item,
    get_workbench_items,
    make_item_key,
    remove_from_workbench,
    update_workbench_item,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workbench", tags=["workbench"])


def _parse_source_field(raw: str) -> tuple[str, str]:
    """Extract a clean label and URL from a source field.

    Handles patterns like:
      ``TLDR 2026-03-11 | **Link:** https://example.com``
      ``JournalClub 2026-03-23``

    Args:
        raw: Raw source string, possibly with markdown.

    Returns:
        Tuple of (clean_label, url). URL is empty if none found.
    """
    if not raw:
        return ("", "")

    # Extract URL (https or http)
    url_match = re.search(r"(https?://\S+)", raw)
    url = url_match.group(1) if url_match else ""

    # Remove the "| **Link:** URL" or similar suffix to get the label
    label = raw
    if url:
        # Remove everything from the pipe/link marker onwards
        label = re.sub(
            r"\s*\|\s*\*{0,2}[Ll]ink:?\*{0,2}\s*" + re.escape(url), "", label
        )
        # If no pipe marker, just remove the bare URL
        label = label.replace(url, "").strip().rstrip("|").strip()

    # Clean any remaining markdown bold markers
    label = label.replace("**", "").strip()

    return (label, url)


def _flatten_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Flatten a workbench entry for the frontend.

    The backend stores the original item as a nested ``item`` dict.
    The frontend expects ``name``, ``notes``, and rich metadata at the
    top level. This function promotes those fields without mutating
    the original entry.

    Args:
        entry: Raw workbench entry from the tracker.

    Returns:
        New dict with frontend-expected field layout.
    """
    nested = entry.get("item", {})
    source_type = entry.get("source_type", nested.get("source_type", "tool"))

    # Tools store description as "what it does"; methods/IG use "notes"
    notes = nested.get("notes", "") or nested.get("what it does", "")

    # Parse source field — strip markdown link markup like "**Link:** URL"
    raw_source = nested.get("source", "")
    source_label, source_link = _parse_source_field(raw_source)

    # If no explicit url, use the one extracted from source
    url = nested.get("url", "") or source_link

    result: dict[str, Any] = {
        "source_type": source_type,
        "name": nested.get("name", ""),
        "notes": notes,
        "status": entry.get("status", "queued"),
        "previous_status": entry.get("previous_status"),
        "added_at": entry.get("added"),
        "verdict": entry.get("experiment_type"),
        "pid": bool(entry.get("pid")),
        "log_file": bool(entry.get("log_file")),
        # Rich metadata from nested item
        "category": nested.get("category", ""),
        "source": source_label,
        "tags": nested.get("tags", ""),
        "url": url,
    }

    # Project associations — from parser wiki-links or cockpit context
    result["projects"] = nested.get("projects", [])
    result["vault_note"] = entry.get("vault_note")

    # Sandbox gate fields
    result["reviewed"] = entry.get("reviewed", False)
    result["cost_flagged"] = entry.get("cost_flagged", False)
    result["cost_notes"] = entry.get("cost_notes", "")
    result["cost_approved"] = entry.get("cost_approved", False)

    # Sandbox output fields
    result["sandbox_dir"] = entry.get("sandbox_dir")
    result["findings_path"] = entry.get("findings_path")

    # Source-type-specific fields
    if source_type == "tool":
        result["description"] = nested.get("what it does", "")
    elif source_type == "method":
        result["description"] = nested.get("why it matters", "") or nested.get(
            "description", ""
        )
        result["paper_url"] = nested.get("paper_url", "")
    elif source_type == "instagram":
        result["key_points"] = nested.get("key_points", [])
        result["keywords"] = nested.get("keywords", [])
        result["caption"] = nested.get("caption", "")
        result["account"] = nested.get("account", "")
        result["shortcode"] = nested.get("shortcode", "")

    return result


@router.get("")
def list_workbench_items_endpoint() -> dict[str, dict[str, Any]]:
    """List all workbench items, flattened for frontend consumption.

    This is a read-only endpoint. Auto-finalisation of agent states
    happens in GET /api/research/status/{key} which the frontend
    polls for each active item individually.
    """
    raw = get_workbench_items()
    return {key: _flatten_entry(entry) for key, entry in raw.items()}


@router.post("", status_code=201)
def add_workbench_item(body: WorkbenchAddRequest) -> dict[str, str]:
    """Add an item to the workbench.

    Args:
        body: Request with item dict and optional previous_status.

    Returns:
        Dict with the generated workbench key.
    """
    item = body.item
    source_type = item.get("source_type", "tool")
    name = item.get("name", "unknown")
    key = make_item_key(source_type, name)

    add_to_workbench(item, previous_status=body.previous_status)
    return {"key": key}


@router.get("/{key:path}")
def get_single_workbench_item(key: str) -> dict[str, Any]:
    """Get a single workbench item by namespaced key, flattened."""
    item = get_workbench_item(key)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Workbench item '{key}' not found")
    return _flatten_entry(item)


@router.patch("/{key:path}")
def update_workbench_item_endpoint(
    key: str,
    body: WorkbenchUpdateRequest,
) -> dict[str, str]:
    """Update fields on a workbench item.

    Args:
        key: Namespaced workbench key.
        body: Request with updates dict.

    Returns:
        Dict confirming the update.

    Raises:
        HTTPException: 400 if updates contain disallowed fields.
    """
    try:
        update_workbench_item(key, body.updates)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"updated": key}


@router.delete("/{key:path}")
def delete_workbench_item(key: str) -> dict[str, str]:
    """Remove an item from the workbench.

    Args:
        key: Namespaced workbench key.

    Returns:
        Dict confirming the removal.
    """
    remove_from_workbench(key)
    return {"removed": key}
