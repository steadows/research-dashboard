"""Ingestion router — Instagram refresh endpoint."""

import logging
from typing import Any

from fastapi import APIRouter, Depends

from api.deps import get_vault_path_str
from api.models import IngestionRequest
from utils.instagram_ingester import run_ingestion

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/instagram", tags=["ingestion"])


@router.post("/refresh")
def refresh_instagram(
    body: IngestionRequest,
    vault_path: str = Depends(get_vault_path_str),
) -> dict[str, Any]:
    """Trigger Instagram ingestion for a username.

    Downloads recent videos, transcribes, extracts keywords, writes vault notes.

    Args:
        body: Request with username and days parameters.
        vault_path: Vault path from dependency injection.

    Returns:
        Dict with notes_written count and note_paths list.
    """
    from pathlib import Path

    notes = run_ingestion(
        username=body.username,
        vault_path=Path(vault_path),
        days=body.days,
    )

    return {
        "notes_written": len(notes),
        "note_paths": [p.name for p in notes],
    }
