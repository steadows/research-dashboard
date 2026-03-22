"""Workbench router — read-only workbench item access."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from utils.workbench_tracker import get_workbench_item, get_workbench_items

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workbench", tags=["workbench"])


@router.get("")
def list_workbench_items() -> dict[str, dict[str, Any]]:
    """List all workbench items."""
    return get_workbench_items()


@router.get("/{key:path}")
def get_single_workbench_item(key: str) -> dict[str, Any]:
    """Get a single workbench item by namespaced key."""
    item = get_workbench_item(key)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Workbench item '{key}' not found")
    return item
