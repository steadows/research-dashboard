"""Workbench router — CRUD for workbench items."""

import logging
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


@router.get("")
def list_workbench_items_endpoint() -> dict[str, dict[str, Any]]:
    """List all workbench items."""
    return get_workbench_items()


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
    """Get a single workbench item by namespaced key."""
    item = get_workbench_item(key)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Workbench item '{key}' not found")
    return item


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
