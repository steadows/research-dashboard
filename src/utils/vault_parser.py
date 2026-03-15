"""Vault parser — project parsing, wiki-link extraction, project index builder."""

import logging
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from utils.methods_parser import parse_methods
from utils.parser_helpers import parse_wiki_links
from utils.tools_parser import parse_tools

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_INLINE_FIELD_RE = re.compile(r"^\*\*([^*]+)\*\*:\s*(.+)$", re.MULTILINE)


def parse_projects(vault_path: Path) -> list[dict[str, Any]]:
    """Parse all project markdown files from the vault.

    Args:
        vault_path: Root path to the Obsidian vault.

    Returns:
        List of project dicts with name, status, domain, tech, and content.
        Returns new copies on each call (immutable output).
    """
    projects_dir = vault_path / "Projects"
    if not projects_dir.is_dir():
        logger.debug("Projects directory not found at %s", projects_dir)
        return []

    projects: list[dict[str, Any]] = []
    for md_file in sorted(projects_dir.glob("*.md")):
        project = _parse_single_project(md_file)
        if project:
            projects.append(project)

    logger.debug("Parsed %d projects from %s", len(projects), projects_dir)
    return projects


def _parse_single_project(md_file: Path) -> dict[str, Any]:
    """Parse a single project markdown file.

    Args:
        md_file: Path to the project .md file.

    Returns:
        Project dict with extracted metadata.
    """
    name = md_file.stem
    content = md_file.read_text(encoding="utf-8")

    project: dict[str, Any] = {
        "name": name,
        "status": "",
        "domain": "",
        "tech": [],
        "file_path": str(md_file),
    }

    # Try YAML frontmatter first
    fm_match = _FRONTMATTER_RE.match(content)
    if fm_match:
        try:
            fm = yaml.safe_load(fm_match.group(1)) or {}
            project["status"] = fm.get("status", "")
            project["domain"] = fm.get("domain", "")
            tech = fm.get("tech", [])
            project["tech"] = list(tech) if isinstance(tech, list) else [tech]
        except yaml.YAMLError:
            logger.warning("Invalid YAML frontmatter in %s", md_file)

    # Fallback: extract inline **Key:** Value fields
    if not project["status"]:
        for match in _INLINE_FIELD_RE.finditer(content):
            key = match.group(1).strip().lower()
            value = match.group(2).strip()
            if key == "status":
                project["status"] = value
            elif key == "type":
                project["domain"] = value
            elif key == "stack":
                project["tech"] = [t.strip() for t in value.split(",")]

    # Extract body (content after frontmatter)
    if fm_match:
        project["content"] = content[fm_match.end() :]
    else:
        project["content"] = content

    project["wiki_links"] = parse_wiki_links(content)

    return project


def build_project_index(vault_path: Path) -> dict[str, list[dict[str, Any]]]:
    """Build an index mapping project names to their tagged items.

    Aggregates methods and tools that reference each project via wiki-links.

    Args:
        vault_path: Root path to the Obsidian vault.

    Returns:
        Dict mapping project name to list of items tagged for that project.
    """
    methods = parse_methods(vault_path)
    tools = parse_tools(vault_path)

    index: dict[str, list[dict[str, Any]]] = {}

    for item in methods + tools:
        for project_name in item.get("projects", []):
            if project_name not in index:
                index[project_name] = []
            index[project_name].append(deepcopy(item))

    logger.debug("Built project index: %d projects with items", len(index))
    return index


# Re-export parse_wiki_links for backward compatibility
__all__ = ["parse_projects", "parse_wiki_links", "build_project_index"]
parse_wiki_links = parse_wiki_links
