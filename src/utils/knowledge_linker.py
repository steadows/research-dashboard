"""Knowledge linker — builds an entity index from the vault and injects wiki-links.

Scans Projects, Skills, Tech, Patterns, Tools Radar, and Methods to Try to build
a lookup of known entity names. Then scans target notes and replaces plain-text
mentions with [[wiki-links]], connecting orphaned graph nodes.
"""

import logging
import os
import re
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def build_entity_index(vault_path: Path) -> dict[str, str]:
    """Build a mapping of entity names to their vault note names.

    Scans multiple vault directories to collect all linkable entities.
    Keys are lowercase for case-insensitive matching; values are the
    exact note name (without .md) for wiki-link insertion.

    Args:
        vault_path: Root path to the Obsidian vault.

    Returns:
        Dict mapping lowercase entity name → display name for wiki-link.
    """
    entities: dict[str, str] = {}

    # Directories where each .md file is an entity
    entity_dirs = [
        "Projects",
        "Skills",
        "Tech",
        "Patterns",
        "Blueprints",
        "Plans",
        "Reference",
    ]
    for dir_name in entity_dirs:
        dir_path = vault_path / dir_name
        if not dir_path.is_dir():
            continue
        for md_file in dir_path.glob("*.md"):
            name = md_file.stem
            entities[name.lower()] = name

    # Also add common aliases for tech/tools that Whisper might transcribe
    _ALIASES: dict[str, str] = {
        "claude code": "Claude Code",
        "claude": "Claude API",
        "streamlit": "Streamlit",
        "fastapi": "FastAPI",
        "langchain": "LangChain",
        "langgraph": "LangGraph",
        "supabase": "Supabase",
        "neo4j": "Neo4j",
        "swiftui": "SwiftUI",
        "swiftdata": "SwiftData",
        "react native": "React Native",
        "next.js": "Next.js",
        "nextjs": "Next.js",
        "tailwind": "Tailwind CSS",
        "postgres": "PostgreSQL",
        "postgresql": "PostgreSQL",
        "pytorch": "PyTorch",
        "chromadb": "ChromaDB",
        "pgvector": "pgvector",
        "redis": "Redis",
        "gsd": "GSD Planning",
        "costar": "COSTAR Prompting",
        "graphrag": "GraphRAG",
    }
    for alias, target in _ALIASES.items():
        if alias not in entities:
            entities[alias] = target

    # Root-level vault files (e.g., MCP Setup Guide.md)
    for md_file in vault_path.glob("*.md"):
        name = md_file.stem
        if name.startswith("_"):  # Skip index files
            continue
        entities[name.lower()] = name

    logger.info("Built entity index with %d entries", len(entities))
    return entities


def inject_wiki_links(text: str, entities: dict[str, str]) -> str:
    """Replace plain-text entity mentions with [[wiki-links]].

    Only replaces mentions that are NOT already inside wiki-links or
    YAML frontmatter. Matches whole words only (word-boundary aware).
    Longest-match-first to avoid partial replacements.

    Args:
        text: Full note content.
        entities: Entity index from build_entity_index().

    Returns:
        Text with wiki-links injected.
    """
    # Sort by length descending so "React Native" matches before "React"
    sorted_names = sorted(entities.keys(), key=len, reverse=True)

    # Split frontmatter from body to avoid linking inside YAML
    body = text
    frontmatter = ""
    if text.startswith("---"):
        try:
            end_idx = text.index("---", 4)
            frontmatter = text[: end_idx + 3]
            body = text[end_idx + 3 :]
        except ValueError:
            pass

    for name_lower in sorted_names:
        display_name = entities[name_lower]

        # Skip if this entity is already wiki-linked somewhere in the body
        if f"[[{display_name}]]" in body:
            continue

        # Build a pattern that matches the entity name (case-insensitive)
        # but NOT inside existing [[ ]] brackets
        escaped = re.escape(name_lower)
        # Word boundary match, case-insensitive
        pattern = re.compile(
            r"(?<!\[\[)"  # Not preceded by [[
            r"\b(" + escaped + r")\b"
            r"(?!\]\])",  # Not followed by ]]
            re.IGNORECASE,
        )

        # Replace only the FIRST occurrence to keep notes clean
        match = pattern.search(body)
        if match:
            start, end = match.span()
            body = body[:start] + f"[[{display_name}]]" + body[end:]

    return frontmatter + body


def link_note(file_path: Path, entities: dict[str, str]) -> bool:
    """Inject wiki-links into a single vault note file.

    Args:
        file_path: Path to the markdown file.
        entities: Entity index from build_entity_index().

    Returns:
        True if the file was modified, False otherwise.
    """
    content = file_path.read_text(encoding="utf-8")
    linked = inject_wiki_links(content, entities)

    if linked == content:
        return False

    # Atomic write
    fd, tmp_path = tempfile.mkstemp(
        dir=file_path.parent, suffix=".tmp", prefix=".link_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(linked)
        os.replace(tmp_path, file_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return True


def link_directory(
    vault_path: Path,
    target_dir: Path,
    entities: dict[str, str] | None = None,
) -> int:
    """Inject wiki-links into all markdown files in a directory tree.

    Args:
        vault_path: Root path to the Obsidian vault (for entity index).
        target_dir: Directory to scan for markdown files.
        entities: Pre-built entity index (built from vault if None).

    Returns:
        Number of files modified.
    """
    if entities is None:
        entities = build_entity_index(vault_path)

    if not target_dir.is_dir():
        logger.warning("Target directory not found: %s", target_dir)
        return 0

    modified = 0
    for md_file in sorted(target_dir.rglob("*.md")):
        try:
            if link_note(md_file, entities):
                modified += 1
                logger.info("Linked: %s", md_file.name)
        except Exception as exc:
            logger.warning("Failed to link %s: %s", md_file, exc)

    logger.info("Linked %d files in %s", modified, target_dir)
    return modified


def link_vault_instagram(vault_path: Path) -> int:
    """Link all Instagram notes to known vault entities.

    Args:
        vault_path: Root path to the Obsidian vault.

    Returns:
        Number of files modified.
    """
    ig_dir = vault_path / "Research" / "Instagram"
    return link_directory(vault_path, ig_dir)


def link_satellites_to_projects(vault_path: Path) -> int:
    """Connect satellite files to their parent project by filename prefix.

    Files like "March Madness Blueprint.md" or "March Madness - Data Engineering.md"
    get a [[March Madness]] wiki-link injected if the project exists and isn't
    already linked.

    Args:
        vault_path: Root path to the Obsidian vault.

    Returns:
        Number of files modified.
    """
    # Collect project names
    projects_dir = vault_path / "Projects"
    if not projects_dir.is_dir():
        return 0
    project_names = sorted(
        [f.stem for f in projects_dir.glob("*.md")], key=len, reverse=True
    )

    # Directories containing satellite files
    satellite_dirs = ["Plans", "Blueprints", "Reference", "Skills"]
    modified = 0

    for dir_name in satellite_dirs:
        dir_path = vault_path / dir_name
        if not dir_path.is_dir():
            continue
        for md_file in dir_path.glob("*.md"):
            file_stem = md_file.stem
            for project in project_names:
                if not file_stem.startswith(project):
                    continue

                content = md_file.read_text(encoding="utf-8")
                link = f"[[{project}]]"
                if link in content:
                    break  # Already linked

                # Inject link at the top of body (after frontmatter)
                if content.startswith("---"):
                    try:
                        end_idx = content.index("---", 4)
                        insert_pos = end_idx + 3
                        content = (
                            content[:insert_pos]
                            + f"\n\nParent project: {link}\n"
                            + content[insert_pos:]
                        )
                    except ValueError:
                        content = f"Parent project: {link}\n\n" + content
                else:
                    content = f"Parent project: {link}\n\n" + content

                fd, tmp_path = tempfile.mkstemp(
                    dir=md_file.parent, suffix=".tmp", prefix=".sat_"
                )
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        f.write(content)
                    os.replace(tmp_path, md_file)
                    modified += 1
                    logger.info("Satellite linked: %s → %s", md_file.name, project)
                except Exception:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
                    raise
                break  # One project match per file

    return modified


def link_single_file(vault_path: Path, file_path: Path) -> bool:
    """Build entity index and link a single file.

    Args:
        vault_path: Root path to the Obsidian vault.
        file_path: Path to the markdown file.

    Returns:
        True if the file was modified.
    """
    entities = build_entity_index(vault_path)
    return link_note(file_path, entities)


def link_vault_all(vault_path: Path) -> dict[str, int]:
    """Link all linkable directories in the vault to known entities.

    Scans Dev Journal, Blog Queue, JournalClub, TLDR, and Instagram.
    Builds the entity index once and reuses across all directories.

    Args:
        vault_path: Root path to the Obsidian vault.

    Returns:
        Dict mapping directory name to number of files modified.
    """
    entities = build_entity_index(vault_path)
    results: dict[str, int] = {}

    targets = [
        ("Instagram", vault_path / "Research" / "Instagram"),
        ("Dev Journal", vault_path / "Dev Journal"),
        ("JournalClub", vault_path / "Research" / "JournalClub"),
        ("TLDR", vault_path / "Research" / "TLDR"),
        ("Blog Queue", vault_path / "Writing"),
        ("Blueprints", vault_path / "Blueprints"),
        ("Plans", vault_path / "Plans"),
        ("Reference", vault_path / "Reference"),
        ("Journal", vault_path / "Journal"),
    ]

    for name, target_dir in targets:
        modified = link_directory(vault_path, target_dir, entities=entities)
        results[name] = modified

    # Connect satellite files to parent projects by filename prefix
    satellites = link_satellites_to_projects(vault_path)
    results["Satellites"] = satellites

    total = sum(results.values())
    logger.info(
        "Knowledge linker total: %d files across %d directories", total, len(results)
    )
    return results
