"""API dependency stubs and sys.path setup for src/utils/ access."""

import os
import sys
from pathlib import Path

from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Path setup — ensure src/ is on sys.path so `from utils.*` imports work
# at runtime (not just under pytest which configures pythonpath separately).
# ---------------------------------------------------------------------------

_SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.append(str(_SRC_DIR))

# Re-export get_vault_path from the canonical location
from utils.page_helpers import get_vault_path  # noqa: E402

__all__ = ["get_vault_path", "get_vault_path_str", "get_api_key"]


def get_vault_path_str() -> str:
    """Get validated vault path as string, raising HTTP 500 on failure.

    Returns:
        String path to the Obsidian vault root.

    Raises:
        HTTPException: If vault path is not configured or doesn't exist.
    """
    try:
        return str(get_vault_path())
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def get_api_key() -> str:
    """Read ANTHROPIC_API_KEY from environment.

    Returns:
        The API key string.

    Raises:
        ValueError: If ANTHROPIC_API_KEY is not set or empty.
    """
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set or empty.")
    return key
