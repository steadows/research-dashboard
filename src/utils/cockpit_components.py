"""Cockpit components — reusable UI helpers for the Project Cockpit page."""

import logging
import re
from pathlib import Path
from urllib.parse import quote

logger = logging.getLogger(__name__)

# Sections by name that are worth including verbatim (short, high-signal)
_NAMED_SECTIONS = ("Context", "Architecture", "Overview")

# Section/subsection headers that carry an incomplete task marker
_ACTIVE_HEADER_RE = re.compile(r"^#{1,3} [^\n]*\[[ ~!]\][^\n]*$", re.MULTILINE)

# Named section extractor: ## SectionName … up to next ## or EOF
_NAMED_SECTION_RE = re.compile(
    r"^## ({names})\s*\n(.*?)(?=^## |\Z)",
    re.MULTILINE | re.DOTALL,
)


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


def get_project_plan_files(project: dict, vault_path: Path) -> list[tuple[str, Path]]:
    """Resolve plan files for a project by following ## Plans wiki-links.

    Parses the ``## Plans`` section of the project's content and resolves
    each ``[[Wiki Link]]`` to ``Plans/{name}.md`` in the vault. Handles
    projects with zero, one, or multiple plan files.

    Includes a path traversal guard: resolved paths must stay inside Plans/.

    Args:
        project: Project dict with 'content' key from vault_parser.
        vault_path: Root path to the Obsidian vault.

    Returns:
        List of (plan_name, resolved_path) tuples for files that exist.
    """
    content = project.get("content", "")
    plans_dir = vault_path / "Plans"

    if not plans_dir.is_dir():
        return []

    # Extract the ## Plans section body
    plans_section_match = re.search(
        r"^## Plans\s*\n(.*?)(?=^## |\Z)", content, re.MULTILINE | re.DOTALL
    )
    if not plans_section_match:
        return []

    plans_body = plans_section_match.group(1)
    wiki_links = re.findall(r"\[\[([^\]]+)\]\]", plans_body)

    results: list[tuple[str, Path]] = []
    plans_dir_resolved = plans_dir.resolve()

    for link_name in wiki_links:
        candidate = plans_dir / f"{link_name}.md"
        try:
            resolved = candidate.resolve()
            if not str(resolved).startswith(str(plans_dir_resolved)):
                logger.warning("Path traversal blocked for plan link: %s", link_name)
                continue
        except (OSError, ValueError):
            continue
        if resolved.is_file():
            results.append((link_name, resolved))
        else:
            logger.debug("Plan file not found: %s", candidate)

    return results


def get_project_overview(project: dict) -> str:
    """Extract the introductory paragraph from a project's content.

    Takes text before the first ## heading, which is typically a 1–3 sentence
    description of what the project is.

    Args:
        project: Project dict with optional 'content' key.

    Returns:
        Stripped intro text, capped at 600 characters.
    """
    content = project.get("content", "").strip()
    if not content:
        return ""
    first_h2 = re.search(r"^## ", content, re.MULTILINE)
    intro = content[: first_h2.start()].strip() if first_h2 else content
    return intro[:600]


def extract_gsd_context(plan_text: str) -> str:
    """Extract high-signal sections from a GSD plan for LLM context.

    Pulls:
    - Named overview sections (Context, Architecture, Overview) verbatim
    - Active work: ## / ### header lines that carry a [ ], [~], or [!] marker
      (section-level granularity only — individual bullet tasks are omitted)
    - Fallback: intro content before the first ## heading (for non-GSD plans)

    Args:
        plan_text: Full GSD plan markdown text.

    Returns:
        Compact context string, typically 300–600 tokens.
    """
    parts: list[str] = []

    # Strip YAML frontmatter if present
    body = re.sub(r"^---\n.*?\n---\n", "", plan_text, flags=re.DOTALL).strip()

    # Named high-signal sections — grab verbatim (they're short)
    section_pattern = re.compile(
        r"^## (" + "|".join(_NAMED_SECTIONS) + r")\s*\n(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    for match in section_pattern.finditer(body):
        section_name = match.group(1)
        section_body = match.group(2).strip()
        # Cap Architecture at 800 chars — diagrams can be long
        if section_name == "Architecture":
            section_body = section_body[:800]
        parts.append(f"## {section_name}\n{section_body}")

    # Active work: section/subsection headers with incomplete markers only
    active_headers = _ACTIVE_HEADER_RE.findall(body)
    if active_headers:
        parts.append("## Active / Incomplete Work\n" + "\n".join(active_headers))

    # Fallback for non-GSD plans (no named sections, no active-work markers):
    # grab intro content before the first ## heading — captures title + objective
    if not parts:
        first_h2 = re.search(r"^## ", body, re.MULTILINE)
        intro = body[: first_h2.start()].strip() if first_h2 else body
        # Strip code blocks and horizontal rules to keep it clean
        intro = re.sub(r"```.*?```", "", intro, flags=re.DOTALL).strip()
        intro = re.sub(r"^---+$", "", intro, flags=re.MULTILINE).strip()
        if intro:
            parts.append(intro[:1000])

    return "\n\n".join(parts)
