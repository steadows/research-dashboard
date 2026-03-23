"""Vault writer — write sandbox experiment notes to Obsidian vault.

Creates structured markdown notes in Projects/Sandbox/ within the Obsidian
vault after a sandbox experiment completes.
"""

import logging
from datetime import date
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def write_sandbox_note(
    tool: dict[str, Any],
    research_summary: str,
    sandbox_dir: Path,
    vault_path: Path,
    findings_text: str = "",
) -> Path:
    """Write a sandbox experiment note to the Obsidian vault.

    Creates ``Projects/Sandbox/{ToolName}.md``. If the file already exists,
    appends an ISO date suffix to avoid overwriting.

    Args:
        tool: Item dict (tool or method from parser).
        research_summary: Text of the ## Overview section from research.md.
        sandbox_dir: Path to the sandbox experiment directory on disk.
        vault_path: Path to the Obsidian vault root.
        findings_text: Content of experiment_findings.md if available.

    Returns:
        Path to the written .md file.

    Raises:
        ValueError: If the resolved note path escapes the vault boundary.
    """
    tool_name = tool.get("name", "Unknown")
    category = tool.get("category", "")

    sandbox_notes_dir = vault_path / "Projects" / "Sandbox"

    # Path traversal guard
    resolved_notes = sandbox_notes_dir.resolve()
    resolved_vault = vault_path.resolve()
    try:
        resolved_notes.relative_to(resolved_vault)
    except ValueError as exc:
        raise ValueError(
            f"Sandbox notes dir {sandbox_notes_dir} escapes vault {vault_path}"
        ) from exc

    sandbox_notes_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize filename — allow alphanumeric, space, hyphen, underscore
    safe_name = "".join(
        c if c.isalnum() or c in " _-" else "_" for c in tool_name
    ).strip()
    note_path = sandbox_notes_dir / f"{safe_name}.md"

    # Never overwrite — append date suffix
    if note_path.exists():
        suffix = date.today().strftime("%Y%m%d")
        note_path = sandbox_notes_dir / f"{safe_name}_{suffix}.md"

    frontmatter = (
        "---\n"
        f"status: sandbox_ready\n"
        f"date: {date.today().isoformat()}\n"
        f"tool_name: {tool_name}\n"
        f"category: {category}\n"
        f"sandbox_dir: {sandbox_dir!s}\n"
        "---\n"
    )

    if findings_text:
        findings_section = f"\n## Experiment Findings\n\n{findings_text}\n"
    else:
        findings_section = (
            f"\n## Experiment Findings\n\nSee `{sandbox_dir}/experiment_findings.md`\n"
        )

    body = (
        f"## Research Summary\n\n{research_summary}\n\n"
        f"## Experiment\n\nSee `{sandbox_dir}/experiment_plan.md`\n"
        f"{findings_section}"
        f"\n## Run\n\n```bash\ncd {sandbox_dir}\nbash run.sh\n```\n"
    )

    note_path.write_text(frontmatter + "\n" + body, encoding="utf-8")
    logger.info("Wrote sandbox note to %s", note_path)
    return note_path
