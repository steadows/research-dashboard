"""Workbench tracker — JSON-based workbench state CRUD with atomic writes.

Manages the tool experimentation pipeline: queued → researching → researched →
sandbox_creating → sandbox_ready | manual | failed.

State file: ~/.research-dashboard/workbench.json (separate from status.json).
Uses the same atomic write pattern as status_tracker.py.
"""

import json
import logging
import os
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

from utils.blog_publisher import slugify

logger = logging.getLogger(__name__)

_DEFAULT_WORKBENCH_DIR = Path.home() / ".research-dashboard"
_DEFAULT_WORKBENCH_FILE = _DEFAULT_WORKBENCH_DIR / "workbench.json"


def _ensure_parent(path: Path) -> None:
    """Ensure the parent directory of a path exists."""
    path.parent.mkdir(parents=True, exist_ok=True)


def _load_workbench(workbench_file: Path) -> dict[str, Any]:
    """Load workbench data from JSON file.

    Args:
        workbench_file: Path to the workbench JSON file.

    Returns:
        Dict mapping tool names to their workbench entries.
        Returns empty dict if file is missing or corrupt.
    """
    if not workbench_file.is_file():
        return {}

    try:
        content = workbench_file.read_text(encoding="utf-8")
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError("Workbench file root must be a dict")
        return data
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Corrupt workbench file %s, resetting: %s", workbench_file, exc)
        return {}


def _save_workbench(data: dict[str, Any], workbench_file: Path) -> None:
    """Save workbench data to JSON file atomically.

    Writes to a temp file first, then uses os.replace() for atomic swap.

    Args:
        data: Workbench dict to persist.
        workbench_file: Path to the workbench JSON file.
    """
    _ensure_parent(workbench_file)

    fd, tmp_path = tempfile.mkstemp(
        dir=workbench_file.parent, suffix=".tmp", prefix=".workbench_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, workbench_file)
        logger.debug("Workbench saved to %s", workbench_file)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _build_entry(tool: dict[str, Any]) -> dict[str, Any]:
    """Build a new workbench entry with schema defaults.

    Args:
        tool: Full tool dict snapshot from tools_parser.

    Returns:
        Workbench entry dict with all required fields.
    """
    return {
        "tool": tool,
        "added": date.today().isoformat(),
        "status": "queued",
        "experiment_type": None,
        "sandbox_dir": None,
        "vault_note": None,
        "pid": None,
        "log_file": None,
        "reviewed": False,
    }


def add_to_workbench(
    tool: dict[str, Any],
    workbench_file: Path = _DEFAULT_WORKBENCH_FILE,
) -> None:
    """Add a tool to the workbench. Duplicate adds are a no-op.

    Args:
        tool: Full tool dict snapshot from tools_parser.
        workbench_file: Path to the workbench JSON file.
    """
    data = _load_workbench(workbench_file)
    name = tool["name"]

    if name in data:
        logger.debug("Tool '%s' already in workbench, skipping", name)
        return

    new_data = {**data, name: _build_entry(tool)}
    _save_workbench(new_data, workbench_file)
    logger.info("Added '%s' to workbench", name)


def get_workbench_items(
    workbench_file: Path = _DEFAULT_WORKBENCH_FILE,
) -> dict[str, dict[str, Any]]:
    """Get all workbench items.

    Args:
        workbench_file: Path to the workbench JSON file.

    Returns:
        Dict mapping tool names to their workbench entries.
    """
    return _load_workbench(workbench_file)


def get_workbench_item(
    tool_name: str,
    workbench_file: Path = _DEFAULT_WORKBENCH_FILE,
) -> dict[str, Any] | None:
    """Get a single workbench item by tool name.

    Args:
        tool_name: Name of the tool.
        workbench_file: Path to the workbench JSON file.

    Returns:
        Workbench entry dict, or None if not found.
    """
    data = _load_workbench(workbench_file)
    return data.get(tool_name)


_ALLOWED_UPDATE_FIELDS = frozenset(
    {
        "status",
        "experiment_type",
        "sandbox_dir",
        "vault_note",
        "pid",
        "log_file",
        "reviewed",
    }
)


def update_workbench_item(
    tool_name: str,
    updates: dict[str, Any],
    workbench_file: Path = _DEFAULT_WORKBENCH_FILE,
) -> None:
    """Merge partial updates into an existing workbench item.

    No-op if the tool is not in the workbench. Only fields in the
    allowed set may be updated — unknown fields raise ValueError.

    Args:
        tool_name: Name of the tool to update.
        updates: Dict of fields to merge into the entry.
        workbench_file: Path to the workbench JSON file.

    Raises:
        ValueError: If updates contain disallowed field names.
    """
    unknown = set(updates) - _ALLOWED_UPDATE_FIELDS
    if unknown:
        raise ValueError(f"Disallowed workbench update fields: {unknown}")

    data = _load_workbench(workbench_file)

    if tool_name not in data:
        logger.debug("Tool '%s' not in workbench, update skipped", tool_name)
        return

    updated_entry = {**data[tool_name], **updates}
    new_data = {**data, tool_name: updated_entry}
    _save_workbench(new_data, workbench_file)
    logger.debug("Updated '%s' in workbench: %s", tool_name, list(updates.keys()))


def remove_from_workbench(
    tool_name: str,
    workbench_file: Path = _DEFAULT_WORKBENCH_FILE,
) -> None:
    """Remove a tool from the workbench. Idempotent on missing keys.

    Args:
        tool_name: Name of the tool to remove.
        workbench_file: Path to the workbench JSON file.
    """
    data = _load_workbench(workbench_file)

    if tool_name not in data:
        logger.debug("Tool '%s' not in workbench, remove skipped", tool_name)
        return

    new_data = {k: v for k, v in data.items() if k != tool_name}
    _save_workbench(new_data, workbench_file)
    logger.info("Removed '%s' from workbench", tool_name)


def get_slug(tool_name: str) -> str:
    """Get the slug for a tool name, reusing blog_publisher.slugify.

    Args:
        tool_name: Name of the tool.

    Returns:
        Kebab-case slug for use in directory names.
    """
    return slugify(tool_name)
