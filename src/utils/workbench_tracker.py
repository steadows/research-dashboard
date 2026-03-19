"""Workbench tracker — JSON-based workbench state CRUD with atomic writes.

Manages the item experimentation pipeline: queued → researching → researched →
sandbox_creating → sandbox_ready | manual | failed.

Supports both tools (from Tools Radar) and methods (from Project Cockpit).
Keys are namespaced as ``{source_type}::{name}`` to avoid collisions.

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
from utils.status_tracker import set_item_status

logger = logging.getLogger(__name__)

_DEFAULT_WORKBENCH_DIR = Path.home() / ".research-dashboard"
_DEFAULT_WORKBENCH_FILE = _DEFAULT_WORKBENCH_DIR / "workbench.json"
_DEFAULT_STATUS_FILE = _DEFAULT_WORKBENCH_DIR / "status.json"

# Statuses that can be restored when removing from workbench
_RESTORABLE_STATUSES = frozenset({"new", "reviewed", "queued", "skipped"})


# ---------------------------------------------------------------------------
# Key helpers
# ---------------------------------------------------------------------------


def make_item_key(source_type: str, name: str) -> str:
    """Build a namespaced workbench key.

    Args:
        source_type: Item source type (e.g. "tool", "method").
        name: Item display name.

    Returns:
        Key string in ``{source_type}::{name}`` format.
    """
    return f"{source_type}::{name}"


def get_slug(name: str, source_type: str = "tool") -> str:
    """Get a namespaced slug for directory/file naming.

    Args:
        name: Item display name.
        source_type: Item source type prefix.

    Returns:
        Kebab-case slug like ``tool-cursor-tab`` or ``method-graph-rag``.
    """
    return f"{source_type}-{slugify(name)}"


# ---------------------------------------------------------------------------
# Internal I/O
# ---------------------------------------------------------------------------


def _ensure_parent(path: Path) -> None:
    """Ensure the parent directory of a path exists."""
    path.parent.mkdir(parents=True, exist_ok=True)


def _normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Normalize a legacy entry to the v2 schema.

    Renames ``"tool"`` field to ``"item"`` and fills missing provenance fields.

    Args:
        entry: Raw entry dict from JSON.

    Returns:
        New entry dict with v2 field names.
    """
    if "tool" in entry and "item" not in entry:
        new_entry = {**entry, "item": entry["tool"]}
        del new_entry["tool"]
    else:
        new_entry = {**entry}

    # Fill provenance defaults for legacy entries
    new_entry.setdefault(
        "source_type", new_entry.get("item", {}).get("source_type", "tool")
    )
    new_entry.setdefault("source_item_id", "")
    new_entry.setdefault("previous_status", "new")

    return new_entry


def _load_workbench(workbench_file: Path) -> dict[str, Any]:
    """Load workbench data from JSON file with legacy normalization.

    Legacy bare-name keys (no ``::`` separator) are promoted to
    ``tool::{name}`` format. Legacy ``"tool"`` fields become ``"item"``.

    Args:
        workbench_file: Path to the workbench JSON file.

    Returns:
        Dict mapping namespaced keys to their normalized workbench entries.
        Returns empty dict if file is missing or corrupt.
    """
    if not workbench_file.is_file():
        return {}

    try:
        content = workbench_file.read_text(encoding="utf-8")
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError("Workbench file root must be a dict")
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Corrupt workbench file %s, resetting: %s", workbench_file, exc)
        return {}

    # Normalize keys and entries
    normalized: dict[str, Any] = {}
    for key, entry in data.items():
        if "::" not in key:
            # Legacy bare key — infer tool:: prefix
            new_key = make_item_key("tool", key)
        else:
            new_key = key

        normalized[new_key] = _normalize_entry(entry)

    return normalized


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


# ---------------------------------------------------------------------------
# Entry builder
# ---------------------------------------------------------------------------


def _build_entry(
    item: dict[str, Any],
    source_item_id: str,
    previous_status: str,
) -> dict[str, Any]:
    """Build a new workbench entry with schema defaults.

    Args:
        item: Full item dict snapshot (tool or method from parser).
        source_item_id: The status_tracker item ID for status restore.
        previous_status: The item's status before being sent to workbench.

    Returns:
        Workbench entry dict with all required fields.
    """
    return {
        "item": item,
        "source_type": item.get("source_type", "tool"),
        "source_item_id": source_item_id,
        "previous_status": previous_status,
        "added": date.today().isoformat(),
        "status": "queued",
        "experiment_type": None,
        "sandbox_dir": None,
        "vault_note": None,
        "pid": None,
        "log_file": None,
        "reviewed": False,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _identity_key(item: dict[str, Any]) -> str:
    """Return the identity value used for workbench keying.

    Instagram items key on ``shortcode`` (globally unique per post) while
    preserving the human-readable ``name`` for display.  All other source
    types key on ``name`` as before.

    Args:
        item: Item dict from parser.

    Returns:
        The string used as the second segment of the namespaced key.
    """
    source_type = item.get("source_type", "tool")
    if source_type == "instagram":
        shortcode = item.get("shortcode", "").strip()
        if not shortcode:
            raise ValueError(f"Instagram item missing shortcode: {item.get('name')!r}")
        return shortcode
    return item["name"]


def add_to_workbench(
    item: dict[str, Any],
    previous_status: str = "new",
    workbench_file: Path = _DEFAULT_WORKBENCH_FILE,
) -> None:
    """Add an item to the workbench. Duplicate adds are a no-op.

    Args:
        item: Full item dict snapshot (tool or method from parser).
        previous_status: The item's status before being sent to workbench.
        workbench_file: Path to the workbench JSON file.
    """
    data = _load_workbench(workbench_file)
    source_type = item.get("source_type", "tool")
    identity = _identity_key(item)
    key = make_item_key(source_type, identity)
    source_item_id = make_item_key(source_type, identity)

    if key in data:
        logger.debug("Item '%s' already in workbench, skipping", key)
        return

    new_data = {**data, key: _build_entry(item, source_item_id, previous_status)}
    _save_workbench(new_data, workbench_file)
    logger.info("Added '%s' to workbench", key)


def get_workbench_items(
    workbench_file: Path = _DEFAULT_WORKBENCH_FILE,
) -> dict[str, dict[str, Any]]:
    """Get all workbench items.

    Args:
        workbench_file: Path to the workbench JSON file.

    Returns:
        Dict mapping namespaced keys to their workbench entries.
    """
    return _load_workbench(workbench_file)


def get_workbench_item(
    key: str,
    workbench_file: Path = _DEFAULT_WORKBENCH_FILE,
) -> dict[str, Any] | None:
    """Get a single workbench item by key.

    Supports both full namespaced keys (``tool::Cursor Tab``) and
    legacy bare names as a read shim. Bare-name lookup returns None
    with a warning if ambiguous (same name exists as both tool and method).

    Args:
        key: Namespaced key or bare name.
        workbench_file: Path to the workbench JSON file.

    Returns:
        Workbench entry dict, or None if not found or ambiguous.
    """
    data = _load_workbench(workbench_file)

    # Full key lookup
    if "::" in key:
        return data.get(key)

    # Legacy bare-name lookup — find all matching entries
    matches = {k: v for k, v in data.items() if k.endswith(f"::{key}")}

    if len(matches) == 1:
        return next(iter(matches.values()))

    if len(matches) > 1:
        logger.warning(
            "Ambiguous bare-name lookup '%s' matches %d entries: %s",
            key,
            len(matches),
            list(matches.keys()),
        )
        return None

    return None


_ALLOWED_UPDATE_FIELDS = frozenset(
    {
        "status",
        "experiment_type",
        "sandbox_dir",
        "vault_note",
        "pid",
        "log_file",
        "reviewed",
        "retry_count",
        "model",
    }
)


def update_workbench_item(
    key: str,
    updates: dict[str, Any],
    workbench_file: Path = _DEFAULT_WORKBENCH_FILE,
) -> None:
    """Merge partial updates into an existing workbench item.

    No-op if the item is not in the workbench. Only fields in the
    allowed set may be updated — unknown fields raise ValueError.

    Args:
        key: Namespaced workbench key.
        updates: Dict of fields to merge into the entry.
        workbench_file: Path to the workbench JSON file.

    Raises:
        ValueError: If updates contain disallowed field names.
    """
    unknown = set(updates) - _ALLOWED_UPDATE_FIELDS
    if unknown:
        raise ValueError(f"Disallowed workbench update fields: {unknown}")

    data = _load_workbench(workbench_file)

    if key not in data:
        logger.debug("Item '%s' not in workbench, update skipped", key)
        return

    updated_entry = {**data[key], **updates}
    new_data = {**data, key: updated_entry}
    _save_workbench(new_data, workbench_file)
    logger.debug("Updated '%s' in workbench: %s", key, list(updates.keys()))


def remove_from_workbench(
    key: str,
    workbench_file: Path = _DEFAULT_WORKBENCH_FILE,
    status_file: Path = _DEFAULT_STATUS_FILE,
) -> None:
    """Remove an item from the workbench and restore its source status.

    Idempotent on missing keys. If the entry has provenance fields
    (source_item_id + previous_status), restores the source feed status
    in status.json.

    Args:
        key: Namespaced workbench key.
        workbench_file: Path to the workbench JSON file.
        status_file: Path to the status JSON file (for status restore).
    """
    data = _load_workbench(workbench_file)

    if key not in data:
        logger.debug("Item '%s' not in workbench, remove skipped", key)
        return

    entry = data[key]

    # Restore source status if provenance is available and valid
    source_item_id = entry.get("source_item_id", "")
    previous_status = entry.get("previous_status", "")
    if source_item_id and previous_status and previous_status in _RESTORABLE_STATUSES:
        set_item_status(source_item_id, previous_status, status_file)
        logger.info("Restored status of '%s' to '%s'", source_item_id, previous_status)
    elif source_item_id and previous_status:
        logger.warning(
            "Skipping status restore for '%s': previous_status '%s' not in allowlist",
            source_item_id,
            previous_status,
        )

    new_data = {k: v for k, v in data.items() if k != key}
    _save_workbench(new_data, workbench_file)
    logger.info("Removed '%s' from workbench", key)
