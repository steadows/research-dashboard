"""Ingestion router — Instagram refresh endpoint."""

import logging
import threading
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from api.deps import get_vault_path_str
from api.models import IngestionRequest
from utils.instagram_ingester import run_ingestion

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/instagram", tags=["ingestion"])

# In-memory job status — keyed by username
_jobs: dict[str, dict[str, Any]] = {}
_jobs_lock = threading.Lock()


def _run_ingestion_job(username: str, vault_path: str, days: int) -> None:
    """Background worker for Instagram ingestion.

    Updates _jobs[username] with status/results when complete.

    Args:
        username: Instagram username to ingest from.
        vault_path: Vault path string.
        days: Number of days to look back.
    """
    try:
        notes = run_ingestion(
            username=username,
            vault_path=Path(vault_path),
            days=days,
        )
        with _jobs_lock:
            _jobs[username] = {
                "status": "complete",
                "notes_written": len(notes),
                "note_paths": [p.name for p in notes],
            }
        logger.info("Ingestion complete for %s: %d notes", username, len(notes))
    except Exception as exc:
        logger.error(
            "Instagram refresh failed for %s: %s", username, exc, exc_info=True
        )
        with _jobs_lock:
            _jobs[username] = {
                "status": "error",
                "detail": "Ingestion failed — check server logs",
            }


@router.post("/refresh", status_code=202)
def refresh_instagram(
    body: IngestionRequest,
    background_tasks: BackgroundTasks,
    vault_path: str = Depends(get_vault_path_str),
) -> dict[str, Any]:
    """Trigger Instagram ingestion for a username (async).

    Kicks off ingestion in a background task and returns immediately.
    Poll GET /api/instagram/refresh-status/{username} for results.

    Args:
        body: Request with username and days parameters.
        background_tasks: FastAPI background task runner.
        vault_path: Vault path from dependency injection.

    Returns:
        Dict with accepted status and username.
    """
    with _jobs_lock:
        if _jobs.get(body.username, {}).get("status") == "running":
            raise HTTPException(
                status_code=409,
                detail=f"Ingestion already running for {body.username}",
            )
        _jobs[body.username] = {"status": "running"}

    background_tasks.add_task(_run_ingestion_job, body.username, vault_path, body.days)

    return {"status": "accepted", "username": body.username}


@router.get("/refresh-status/{username}")
def refresh_status(username: str) -> dict[str, Any]:
    """Check status of a background ingestion job.

    Args:
        username: Instagram username to check.

    Returns:
        Job status dict (running/complete/error).
    """
    with _jobs_lock:
        job = _jobs.get(username)
        if job is None:
            return {"status": "idle"}
        return dict(job)
