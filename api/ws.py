"""WebSocket handler — research log streaming.

Streams research agent log output to the frontend via WebSocket.
Polls tail_log() every 2 seconds and sends JSON frames.
Closes when the agent process exits.
"""

import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, WebSocket

from utils.research_agent import is_agent_running, tail_log
from utils.workbench_tracker import get_workbench_item

logger = logging.getLogger(__name__)

router = APIRouter()

_POLL_INTERVAL_SECONDS = 2


@router.websocket("/ws/research/{key:path}")
async def research_log_stream(websocket: WebSocket, key: str) -> None:
    """Stream research agent log output over WebSocket.

    Sends JSON frames with structure:
        {"type": "log", "lines": "...tail output..."}
        {"type": "done", "lines": "...final output..."}
        {"type": "error", "message": "..."}

    Args:
        websocket: The WebSocket connection.
        key: Namespaced workbench key (e.g. 'tool::Cursor Tab').
    """
    await websocket.accept()

    entry = get_workbench_item(key)
    if entry is None:
        await websocket.send_json(
            {"type": "error", "message": f"Item '{key}' not found"}
        )
        await websocket.close()
        return

    pid = entry.get("pid")
    log_file_str = entry.get("log_file", "")
    log_file = Path(log_file_str) if log_file_str else None

    if not pid or not log_file:
        await websocket.send_json(
            {"type": "error", "message": "No active research agent"}
        )
        await websocket.close()
        return

    try:
        while True:
            running = is_agent_running(pid)
            lines = tail_log(log_file) if log_file else ""

            if running:
                await websocket.send_json({"type": "log", "lines": lines})
                await asyncio.sleep(_POLL_INTERVAL_SECONDS)
            else:
                await websocket.send_json({"type": "done", "lines": lines})
                break
    except Exception as exc:
        logger.warning("WebSocket error for %s: %s", key, exc)
    finally:
        await websocket.close()
