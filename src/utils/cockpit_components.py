"""Cockpit components — reusable UI helpers for the Project Cockpit page."""

import logging
from pathlib import Path
from urllib.parse import quote

logger = logging.getLogger(__name__)


def build_obsidian_url(vault_name: str, file_path: str) -> str:
    """Build an obsidian://open URL for a vault file.

    Args:
        vault_name: Name of the Obsidian vault.
        file_path: Relative path to the file within the vault.

    Returns:
        Obsidian protocol URL string.
    """
    encoded_vault = quote(vault_name, safe="")
    encoded_file = quote(file_path, safe="/")
    return f"obsidian://open?vault={encoded_vault}&file={encoded_file}"


def get_project_gsd_plan(project_name: str, vault_path: Path) -> str | None:
    """Load GSD plan content for a project from the vault.

    Looks for Plans/<project_name> GSD Plan.md in the vault.
    Includes path traversal guard to prevent directory escape.

    Args:
        project_name: Name of the project.
        vault_path: Root path to the Obsidian vault.

    Returns:
        Plan file content as string, or None if not found.
    """
    if not project_name or not project_name.strip():
        return None

    plans_dir = vault_path / "Plans"
    if not plans_dir.is_dir():
        logger.debug("Plans directory not found: %s", plans_dir)
        return None

    # Build candidate filename
    plan_filename = f"{project_name} GSD Plan.md"
    plan_path = plans_dir / plan_filename

    # Path traversal guard: resolved path must be inside plans_dir
    try:
        resolved = plan_path.resolve()
        if not str(resolved).startswith(str(plans_dir.resolve())):
            logger.warning("Path traversal attempt blocked: %s", project_name)
            return None
    except (OSError, ValueError):
        return None

    if not plan_path.is_file():
        logger.debug("No GSD plan found for project: %s", project_name)
        return None

    return plan_path.read_text(encoding="utf-8")
