"""Status router — read/write item status tracking + archive."""

import logging
from typing import Any

from fastapi import APIRouter

from api.models import StatusUpdateRequest
from utils.status_tracker import get_item_status, load_status, set_item_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/status", tags=["status"])


@router.get("/archive")
def list_archive() -> list[dict[str, Any]]:
    """List all dismissed/archived items with metadata.

    Returns:
        List of archived item dicts with key, type, name, and any stored metadata.
    """
    data = load_status()
    items: list[dict[str, Any]] = []

    for key, value in data.get("items", {}).items():
        # Support both old format (string) and new format (dict with metadata)
        if isinstance(value, str) and value == "dismissed":
            item_type, _, name = key.partition("::")
            items.append(
                {
                    "key": key,
                    "type": item_type,
                    "name": name or key,
                    "status": "dismissed",
                }
            )
        elif isinstance(value, dict) and value.get("status") == "dismissed":
            item_type, _, name = key.partition("::")
            items.append(
                {
                    "key": key,
                    "type": item_type,
                    "name": name or key,
                    "status": "dismissed",
                    **{k: v for k, v in value.items() if k != "status"},
                }
            )

    return items


@router.delete("/archive/{key:path}")
def restore_from_archive(key: str) -> dict[str, str]:
    """Restore an item from the archive (set status back to 'new').

    Args:
        key: Item identifier (namespaced key).

    Returns:
        Dict with 'key' and 'status' fields.
    """
    set_item_status(key, "new")
    return {"key": key, "status": "new"}


@router.get("/{key:path}")
def get_status(key: str) -> dict[str, str]:
    """Get current status for an item.

    Args:
        key: Item identifier (namespaced key).

    Returns:
        Dict with 'key' and 'status' fields.
    """
    status = get_item_status(key)
    return {"key": key, "status": status}


@router.post("/{key:path}")
def set_status(key: str, body: StatusUpdateRequest) -> dict[str, str]:
    """Set status for an item.

    Args:
        key: Item identifier (namespaced key).
        body: Request body with 'status' field.

    Returns:
        Dict with 'key' and 'status' fields.
    """
    set_item_status(key, body.status)
    return {"key": key, "status": body.status}


@router.patch("/{key:path}")
def patch_status(key: str, body: StatusUpdateRequest) -> dict[str, str]:
    """Update status for an item (alias for POST).

    Args:
        key: Item identifier (namespaced key).
        body: Request body with 'status' fields.

    Returns:
        Dict with 'key' and 'status' fields.
    """
    set_item_status(key, body.status)
    return {"key": key, "status": body.status}
