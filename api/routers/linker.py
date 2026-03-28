"""Linker router — Knowledge Linker vault-wide wiki-link injection.

Exposes POST /api/linker/run (background task, 202) and GET /api/linker/status
(polling). Single-job model — only one run at a time (409 on concurrent
attempts). Each run gets a UUID for frontend identity tracking.

IMPORTANT: This router uses in-memory state and is only safe with a single
uvicorn worker (--workers 1).
"""

from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from api.deps import get_vault_path_str
from api.models import LinkerStatusResponse
from utils.knowledge_linker import link_vault_all_with_progress

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/linker", tags=["linker"])

# In-memory single-job state — safe only with --workers 1
_job: dict[str, Any] = {"status": "idle"}
_job_lock = threading.Lock()


def reset_job() -> None:
    """Reset job state to idle. Test helper for state isolation."""
    with _job_lock:
        _job.clear()
        _job["status"] = "idle"


def _run_linker_job(vault_path: str, run_id: str) -> None:
    """Background worker for vault-wide wiki-link injection.

    Uses the shared orchestrator from knowledge_linker. Tracks mutations
    incrementally via the on_step callback so that graph cache invalidation
    happens even if the orchestrator throws mid-loop.

    Args:
        vault_path: Vault path string.
        run_id: UUID for this run.
    """
    mutated = False

    def _on_step(directory: str, modified_count: int, warnings: list[str]) -> None:
        nonlocal mutated
        if modified_count > 0:
            mutated = True
        with _job_lock:
            _job["current_directory"] = directory

    try:
        result = link_vault_all_with_progress(
            Path(vault_path),
            on_step=_on_step,
        )

        with _job_lock:
            _job.update(
                {
                    "status": "partial" if result.warnings else "complete",
                    "results": result.results,
                    "total_modified": result.total_modified,
                    "warnings": result.warnings,
                    "current_directory": None,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        logger.info(
            "Knowledge linker complete (run=%s): %d files modified",
            run_id,
            result.total_modified,
        )
    except Exception as exc:
        logger.error("Knowledge linker failed (run=%s): %s", run_id, exc, exc_info=True)
        with _job_lock:
            _job.update(
                {
                    "status": "error",
                    "error": str(exc),
                    "current_directory": None,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }
            )
    finally:
        # Invalidate graph cache if any mutations occurred
        if mutated:
            try:
                from api.routers.graph import invalidate_graph_cache

                vault_str = vault_path
                invalidate_graph_cache(vault_str)
                logger.info("Graph cache invalidated after linker run (run=%s)", run_id)
            except Exception as cache_exc:
                logger.warning("Failed to invalidate graph cache: %s", cache_exc)


@router.post("/run", status_code=202)
def run_linker(
    background_tasks: BackgroundTasks,
    vault_path: str = Depends(get_vault_path_str),
) -> dict[str, str]:
    """Trigger vault-wide wiki-link injection (async).

    Returns 202 with a run_id. Poll GET /api/linker/status for progress.
    Returns 409 if a run is already in progress.

    Args:
        background_tasks: FastAPI background task runner.
        vault_path: Vault path from dependency injection.

    Returns:
        Dict with accepted status and run_id.
    """
    run_id = str(uuid.uuid4())

    with _job_lock:
        if _job.get("status") == "running":
            raise HTTPException(
                status_code=409,
                detail="Knowledge linker is already running",
            )
        _job.clear()
        _job.update(
            {
                "run_id": run_id,
                "status": "running",
                "current_directory": None,
                "results": None,
                "total_modified": None,
                "warnings": [],
                "started_at": datetime.now(timezone.utc).isoformat(),
                "completed_at": None,
                "error": None,
            }
        )

    background_tasks.add_task(_run_linker_job, vault_path, run_id)

    return {"status": "accepted", "run_id": run_id}


@router.get("/status", response_model=LinkerStatusResponse)
def linker_status() -> dict[str, Any]:
    """Check status of the knowledge linker background job.

    Returns:
        Current job state (idle/running/complete/partial/error).
    """
    with _job_lock:
        return dict(_job)
