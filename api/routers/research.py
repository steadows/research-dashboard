"""Research router — launch research agents and check status."""

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from utils.research_agent import is_agent_running, launch_research_agent, tail_log
from utils.workbench_tracker import (
    get_slug,
    get_workbench_item,
    update_workbench_item,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/research", tags=["research"])

_WORKBENCH_ROOT = Path.home() / "research-workbench"


@router.post("/{key:path}", status_code=202)
def launch_research(key: str) -> dict[str, Any]:
    """Launch a research agent for a workbench item.

    Args:
        key: Namespaced workbench key (e.g. 'tool::Cursor Tab').

    Returns:
        Dict with pid, model, output_dir, and key.

    Raises:
        HTTPException: 404 if item not found in workbench.
    """
    entry = get_workbench_item(key)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Workbench item '{key}' not found")

    item = entry.get("item", {})
    source_type = entry.get("source_type", "tool")
    name = item.get("name", "unknown")
    slug = get_slug(name, source_type)
    output_dir = _WORKBENCH_ROOT / slug

    proc, model = launch_research_agent(item, output_dir)

    # Update workbench entry with agent metadata
    update_workbench_item(
        key,
        {
            "status": "researching",
            "pid": proc.pid,
            "log_file": str(output_dir / "agent.log"),
            "model": model,
        },
    )

    return {
        "key": key,
        "pid": proc.pid,
        "model": model,
        "output_dir": str(output_dir),
    }


@router.get("/{key:path}/status")
def get_research_status(key: str) -> dict[str, Any]:
    """Check research agent status for a workbench item.

    Args:
        key: Namespaced workbench key.

    Returns:
        Dict with running status, log tail, and key.

    Raises:
        HTTPException: 404 if item not found in workbench.
    """
    entry = get_workbench_item(key)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Workbench item '{key}' not found")

    pid = entry.get("pid")
    log_file = entry.get("log_file", "")
    running = is_agent_running(pid) if pid else False
    log_tail = tail_log(Path(log_file)) if log_file else ""

    return {
        "key": key,
        "running": running,
        "pid": pid,
        "log_tail": log_tail,
    }
