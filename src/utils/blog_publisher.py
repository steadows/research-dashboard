"""Blog publisher — draft generation, MDX writing, and archive utilities.

Handles the full blog post pipeline: slugify titles, write MDX drafts to
the portfolio repo, read existing drafts, and archive dismissed items back
to the Obsidian vault.
"""

import logging
import re
from datetime import date
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Portfolio blog directory
_BLOG_REPO_PATH = Path.home() / "portfolio-v2" / "src" / "content" / "blog"

# Vault archive file (relative to vault root)
_ARCHIVE_FILE = "Writing/Blog Archive.md"


def slugify(title: str) -> str:
    """Convert a title to a kebab-case URL slug.

    Args:
        title: Post title string.

    Returns:
        Lowercase kebab-case slug with non-alphanumeric chars removed.
    """
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def estimate_read_time(word_count: int) -> str:
    """Estimate reading time from word count at 200 wpm.

    Args:
        word_count: Number of words in the post.

    Returns:
        Human-readable string like "5 min read".
    """
    minutes = max(1, round(word_count / 200))
    return f"{minutes} min read"


def infer_category(tags: str) -> str:
    """Infer post category from tags string.

    Args:
        tags: Comma-separated tags string.

    Returns:
        One of "research", "tutorial", or "article".
    """
    tags_lower = tags.lower()
    research_terms = {
        "research",
        "paper",
        "ml",
        "ai",
        "arxiv",
        "study",
        "survey",
        "model",
    }
    tutorial_terms = {"tutorial", "how-to", "guide", "walkthrough", "step-by-step"}

    tag_set = {t.strip() for t in tags_lower.split(",")}
    if tag_set & research_terms:
        return "research"
    if tag_set & tutorial_terms:
        return "tutorial"
    return "article"


def write_draft_mdx(item: dict[str, Any], body: str) -> Path:
    """Write a draft MDX file to the portfolio blog directory.

    Assembles YAML frontmatter from the item and appends the body.
    Raises FileExistsError if the slug already exists (no clobber).

    Args:
        item: Blog item dict with at least 'name', optionally 'hook', 'tags'.
        body: Raw MDX body text (no frontmatter block).

    Returns:
        Path to the written MDX file.

    Raises:
        FileExistsError: If an MDX file for this slug already exists.
    """
    title = item.get("name", "Untitled")
    slug = slugify(title)
    dest = _BLOG_REPO_PATH / f"{slug}.mdx"

    if dest.exists():
        raise FileExistsError(f"Draft already exists: {dest}")

    dest.parent.mkdir(parents=True, exist_ok=True)

    tags_raw = item.get("tags", "")
    tag_list = [t.strip() for t in tags_raw.split(",") if t.strip()]
    tags_yaml = (
        "\n".join(f'  - "{t}"' for t in tag_list) if tag_list else '  - "general"'
    )

    hook = item.get("hook", "")
    subtitle = hook[:120] if hook else title
    excerpt = hook[:200] if hook else f"A deep dive into {title}."
    category = infer_category(tags_raw)
    today = date.today().isoformat()
    word_count = len(body.split())
    read_time = estimate_read_time(word_count)

    frontmatter = f"""---
title: "{title}"
subtitle: "{subtitle}"
date: "{today}"
excerpt: "{excerpt}"
tags:
{tags_yaml}
category: "{category}"
readTime: "{read_time}"
featured: false
status: "draft"
---

"""

    dest.write_text(frontmatter + body, encoding="utf-8")
    logger.info("Wrote draft MDX: %s", dest)
    return dest


def read_draft_body(item: dict[str, Any]) -> str | None:
    """Read the MDX body for an item, stripping the frontmatter block.

    Args:
        item: Blog item dict with at least 'name'.

    Returns:
        Raw markdown body string, or None if the file does not exist.
    """
    title = item.get("name", "")
    slug = slugify(title)
    dest = _BLOG_REPO_PATH / f"{slug}.mdx"

    if not dest.exists():
        logger.debug("No draft found for slug: %s", slug)
        return None

    content = dest.read_text(encoding="utf-8")

    # Strip YAML frontmatter block (--- ... ---)
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            # Skip past the closing --- and any leading newlines
            body = content[end + 3 :].lstrip("\n")
            return body

    return content


def get_draft_path(item: dict[str, Any]) -> Path | None:
    """Return the draft MDX path for an item, or None if it does not exist.

    Args:
        item: Blog item dict with at least 'name'.

    Returns:
        Path to the MDX file, or None if not found.
    """
    slug = slugify(item.get("name", ""))
    dest = _BLOG_REPO_PATH / f"{slug}.mdx"
    return dest if dest.exists() else None


def archive_item(item: dict[str, Any], vault_path: Path) -> None:
    """Append a dismissed item to Writing/Blog Archive.md in the vault.

    Creates the archive file if absent. Appends an H2 section with the
    item's title and an Archived date field.

    Args:
        item: Blog item dict with at least 'name' and other optional fields.
        vault_path: Root path to the Obsidian vault.
    """
    archive_path = vault_path / _ARCHIVE_FILE
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    title = item.get("name", "Untitled")
    hook = item.get("hook", "")
    source = item.get("source paper") or item.get("source", "")
    tags = item.get("tags", "")
    today = date.today().isoformat()

    section_lines = [f"## {title}", ""]
    if hook:
        section_lines += [f"**Hook:** {hook}", ""]
    if source:
        section_lines += [f"**Source:** {source}", ""]
    if tags:
        section_lines += [f"**Tags:** {tags}", ""]
    section_lines += [f"**Archived:** {today}", "", ""]

    section = "\n".join(section_lines)

    if not archive_path.exists():
        archive_path.write_text(f"# Blog Archive\n\n{section}", encoding="utf-8")
        logger.info("Created blog archive: %s", archive_path)
    else:
        with archive_path.open("a", encoding="utf-8") as f:
            f.write(section)
        logger.info("Archived item '%s' to %s", title, archive_path)
