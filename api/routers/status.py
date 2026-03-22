"""Status router — read/write item status tracking."""

import logging

from fastapi import APIRouter

from api.models import StatusUpdateRequest
from utils.status_tracker import get_item_status, set_item_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/status", tags=["status"])


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
        body: Request body with 'status' field.

    Returns:
        Dict with 'key' and 'status' fields.
    """
    set_item_status(key, body.status)
    return {"key": key, "status": body.status}
