"""Status tracker — JSON-based status persistence and analysis cache.

Uses atomic writes (temp file + os.replace) to prevent corruption.
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_STATUS: dict[str, Any] = {"items": {}, "cache": {}}
_DEFAULT_STATUS_DIR = Path.home() / ".research-dashboard"
_DEFAULT_STATUS_FILE = _DEFAULT_STATUS_DIR / "status.json"


def _ensure_parent(path: Path) -> None:
    """Ensure the parent directory of a path exists."""
    path.parent.mkdir(parents=True, exist_ok=True)


def load_status(status_file: Path = _DEFAULT_STATUS_FILE) -> dict[str, Any]:
    """Load status data from JSON file.

    Args:
        status_file: Path to the status JSON file.

    Returns:
        Status dict with 'items' and 'cache' keys.
        Returns default structure if file is missing or corrupt.
    """
    if not status_file.is_file():
        logger.debug("Status file not found, returning defaults: %s", status_file)
        return {"items": {}, "cache": {}}

    try:
        content = status_file.read_text(encoding="utf-8")
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError("Status file root must be a dict")
        # Ensure required keys
        data.setdefault("items", {})
        data.setdefault("cache", {})
        return data
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Corrupt status file %s, resetting: %s", status_file, exc)
        return {"items": {}, "cache": {}}


def save_status(
    data: dict[str, Any],
    status_file: Path = _DEFAULT_STATUS_FILE,
) -> None:
    """Save status data to JSON file atomically.

    Writes to a temp file first, then uses os.replace() for atomic swap.

    Args:
        data: Status dict to persist.
        status_file: Path to the status JSON file.
    """
    _ensure_parent(status_file)

    # Write to temp file in the same directory (same filesystem for atomic replace)
    fd, tmp_path = tempfile.mkstemp(
        dir=status_file.parent, suffix=".tmp", prefix=".status_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, status_file)
        logger.debug("Status saved to %s", status_file)
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def get_item_status(
    item_id: str,
    status_file: Path = _DEFAULT_STATUS_FILE,
) -> str:
    """Get the status of a specific item.

    Args:
        item_id: Unique item identifier.
        status_file: Path to the status JSON file.

    Returns:
        Status string (e.g. 'new', 'reviewed', 'skipped'). Defaults to 'new'.
    """
    data = load_status(status_file)
    return data["items"].get(item_id, "new")


def set_item_status(
    item_id: str,
    status: str,
    status_file: Path = _DEFAULT_STATUS_FILE,
) -> None:
    """Set the status of a specific item and persist.

    Args:
        item_id: Unique item identifier.
        status: New status value.
        status_file: Path to the status JSON file.
    """
    data = load_status(status_file)
    new_items = {**data["items"], item_id: status}
    new_data = {**data, "items": new_items}
    save_status(new_data, status_file)


def get_analysis_cache(
    cache_key: str,
    status_file: Path = _DEFAULT_STATUS_FILE,
) -> dict[str, Any] | None:
    """Get cached analysis result.

    Args:
        cache_key: Cache key (typically hash of item + project + type).
        status_file: Path to the status JSON file.

    Returns:
        Cached analysis dict, or None on cache miss.
    """
    data = load_status(status_file)
    return data["cache"].get(cache_key)


def set_analysis_cache(
    cache_key: str,
    result: dict[str, Any],
    status_file: Path = _DEFAULT_STATUS_FILE,
) -> None:
    """Cache an analysis result and persist.

    Args:
        cache_key: Cache key.
        result: Analysis result dict to cache.
        status_file: Path to the status JSON file.
    """
    data = load_status(status_file)
    new_cache = {**data["cache"], cache_key: result}
    new_data = {**data, "cache": new_cache}
    save_status(new_data, status_file)
