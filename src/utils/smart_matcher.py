"""Smart matcher — hybrid item-to-project matching with explicit + inferred links."""

import logging
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import streamlit as st

from utils.blog_queue_parser import parse_blog_queue
from utils.cockpit_components import get_project_overview
from utils.methods_parser import parse_methods
from utils.tools_parser import parse_tools
from utils.vault_parser import parse_projects

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stop words — generic terms that should not drive matching
# ---------------------------------------------------------------------------

_STOP_WORDS: frozenset[str] = frozenset({
    "a", "an", "the", "and", "or", "but", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "shall", "should", "may", "might", "must", "can",
    "could", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above",
    "below", "between", "under", "about", "against", "without", "within",
    "it", "its", "this", "that", "these", "those", "i", "you", "we",
    "they", "he", "she", "my", "your", "our", "their", "what", "which",
    "who", "how", "when", "where", "why", "if", "then", "than", "so",
    "not", "no", "nor", "up", "out", "off", "over", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such",
    "only", "own", "same", "too", "very", "just", "also", "now",
    # Generic tech/business terms that are too broad for matching
    "data", "system", "tool", "app", "application", "use", "using",
    "used", "new", "make", "way", "get", "set", "see", "try", "run",
    "work", "build", "code", "file", "like", "good", "well", "first",
    "one", "two", "many", "much", "still", "even", "back", "here",
    "there", "where", "need", "take", "come", "think", "know",
})

# ---------------------------------------------------------------------------
# Multi-word tech names — recognized as single tokens
# ---------------------------------------------------------------------------

_MULTI_WORD_TERMS: tuple[str, ...] = (
    "nova act", "aws bedrock", "amazon bedrock", "graph rag",
    "knowledge graph", "code intelligence", "machine learning",
    "deep learning", "reinforcement learning", "natural language",
    "large language model", "language model", "neural network",
    "computer vision", "prompt engineering", "prompt caching",
    "fine tuning", "transfer learning", "few shot", "zero shot",
    "chain of thought", "retrieval augmented", "vector database",
    "vector store", "time series", "real time", "event driven",
    "github actions", "ci cd", "google cloud", "azure openai",
    "open source", "rest api", "web scraping", "data pipeline",
    "swift ui", "swiftui", "react native", "vue js", "next js",
    "node js", "ruby on rails", "spring boot", "fast api", "fastapi",
)


# ---------------------------------------------------------------------------
# Keyword extraction
# ---------------------------------------------------------------------------


def _normalize_text(text: str) -> str:
    """Lowercase and strip non-alphanumeric characters (keep spaces).

    Args:
        text: Raw text to normalize.

    Returns:
        Cleaned lowercase string.
    """
    return re.sub(r"[^a-z0-9\s]", " ", text.lower()).strip()


def _extract_keywords(text: str) -> set[str]:
    """Extract meaningful keywords from text, including multi-word terms.

    Args:
        text: Raw text to extract keywords from.

    Returns:
        Set of lowercase keyword strings.
    """
    normalized = _normalize_text(text)
    keywords: set[str] = set()

    # Extract multi-word terms first
    for term in _MULTI_WORD_TERMS:
        if term in normalized:
            keywords.add(term)

    # Extract single-word tokens, filtering stop words and short tokens
    for word in normalized.split():
        if len(word) >= 2 and word not in _STOP_WORDS:
            keywords.add(word)

    return keywords


def _extract_item_keywords(item: dict[str, Any]) -> set[str]:
    """Extract keywords from an item based on its source type.

    Methods: name + why it matters
    Tools: name + what it does + category
    Blog: name + hook + tags

    Args:
        item: Parsed item dict.

    Returns:
        Set of keywords extracted from the item.
    """
    source_type = item.get("source_type", "")
    parts: list[str] = [item.get("name", "")]

    if source_type == "method":
        parts.append(item.get("why it matters", ""))
    elif source_type == "tool":
        parts.append(item.get("what it does", ""))
        parts.append(item.get("category", ""))
    elif source_type == "blog":
        parts.append(item.get("hook", ""))
        parts.append(item.get("tags", ""))

    return _extract_keywords(" ".join(parts))


def _extract_project_keywords(project: dict[str, Any]) -> set[str]:
    """Build a keyword profile from a project's metadata and content.

    Uses: tech list + domain + name + overview text (first 600 chars).

    Args:
        project: Parsed project dict.

    Returns:
        Set of keywords from the project.
    """
    parts: list[str] = [
        project.get("name", ""),
        project.get("domain", ""),
    ]

    # Tech list items as individual keywords
    for tech_item in project.get("tech", []):
        parts.append(tech_item)

    # Overview text (first 600 chars of content before first ##)
    overview = get_project_overview(project)
    parts.append(overview)

    return _extract_keywords(" ".join(parts))


def _extract_project_tech_keywords(project: dict[str, Any]) -> set[str]:
    """Extract just the tech stack keywords for high-weight matching.

    Args:
        project: Parsed project dict.

    Returns:
        Set of keywords from the project's tech list only.
    """
    tech_parts: list[str] = []
    for tech_item in project.get("tech", []):
        tech_parts.append(tech_item)
    return _extract_keywords(" ".join(tech_parts))


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------


def _compute_confidence(
    item_keywords: set[str],
    project_keywords: set[str],
    project_tech_keywords: set[str],
) -> float:
    """Compute a confidence score for an item-project match.

    Tech stack matches are weighted higher than general keyword overlap.

    Args:
        item_keywords: Keywords from the item.
        project_keywords: All keywords from the project.
        project_tech_keywords: Tech-only keywords from the project.

    Returns:
        Confidence float between 0.0 and 1.0.
    """
    if not item_keywords or not project_keywords:
        return 0.0

    # Count tech stack overlaps (high weight)
    tech_overlap = item_keywords & project_tech_keywords
    tech_count = len(tech_overlap)

    # Count general keyword overlaps (lower weight)
    general_overlap = item_keywords & project_keywords
    general_count = len(general_overlap) - tech_count  # Exclude already-counted tech

    # Score: tech matches are worth 0.3 each, general 0.1 each, capped at 0.9
    score = (tech_count * 0.3) + (general_count * 0.1)

    # Clamp to [0.0, 0.9] — explicit matches are always 1.0
    return min(score, 0.9)


# ---------------------------------------------------------------------------
# Index builders
# ---------------------------------------------------------------------------


_CONFIDENCE_THRESHOLD = 0.3


def _build_explicit_index(
    items: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Build the explicit (Tier 1) index from wiki-link project references.

    Args:
        items: List of parsed item dicts with 'projects' field.

    Returns:
        Dict mapping project name to list of items with match_type/confidence.
    """
    index: dict[str, list[dict[str, Any]]] = {}

    for item in items:
        for project_name in item.get("projects", []):
            enriched = deepcopy(item)
            enriched["match_type"] = "explicit"
            enriched["confidence"] = 1.0
            if project_name not in index:
                index[project_name] = []
            index[project_name].append(enriched)

    return index


def _add_inferred_matches(
    index: dict[str, list[dict[str, Any]]],
    items: list[dict[str, Any]],
    projects: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Add inferred (Tier 2) matches to the index without duplicating explicit ones.

    Args:
        index: Existing explicit index (will not be mutated).
        items: All parsed items.
        projects: All parsed projects.

    Returns:
        New index dict with both explicit and inferred matches.
    """
    # Build a new index from the existing one
    result: dict[str, list[dict[str, Any]]] = {
        k: list(v) for k, v in index.items()
    }

    # Build lookup of (item_name, source_type) -> set of explicitly linked projects
    explicit_links: dict[tuple[str, str], set[str]] = {}
    for project_name, project_items in index.items():
        for item in project_items:
            key = (item["name"], item.get("source_type", ""))
            if key not in explicit_links:
                explicit_links[key] = set()
            explicit_links[key].add(project_name)

    # Pre-compute project keyword profiles
    project_profiles: list[tuple[dict[str, Any], set[str], set[str]]] = []
    for project in projects:
        all_kw = _extract_project_keywords(project)
        tech_kw = _extract_project_tech_keywords(project)
        project_profiles.append((project, all_kw, tech_kw))

    # Score each item against each project
    for item in items:
        item_kw = _extract_item_keywords(item)
        item_key = (item["name"], item.get("source_type", ""))
        already_linked = explicit_links.get(item_key, set())

        for project, proj_kw, tech_kw in project_profiles:
            proj_name = project["name"]

            # Skip if already explicitly linked
            if proj_name in already_linked:
                continue

            confidence = _compute_confidence(item_kw, proj_kw, tech_kw)

            if confidence >= _CONFIDENCE_THRESHOLD:
                enriched = deepcopy(item)
                enriched["match_type"] = "inferred"
                enriched["confidence"] = round(confidence, 2)
                if proj_name not in result:
                    result[proj_name] = []
                result[proj_name].append(enriched)

    return result


def _sort_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort items: explicit first, then inferred by confidence descending.

    Args:
        items: List of items with match_type and confidence.

    Returns:
        New sorted list.
    """
    return sorted(
        items,
        key=lambda i: (
            0 if i.get("match_type") == "explicit" else 1,
            -i.get("confidence", 0.0),
        ),
    )


@st.cache_data(ttl=3600)
def build_smart_project_index(
    vault_path_str: str,
) -> dict[str, list[dict[str, Any]]]:
    """Build a hybrid project index with explicit wiki-link and inferred matches.

    Tier 1 (explicit): Items linked via wiki-links in vault markdown.
    Tier 2 (inferred): Items matched via tech/keyword overlap scoring.

    Items are sorted: explicit first, then inferred by confidence descending.
    Duplicate matches (same item already explicitly linked) are excluded from
    inferred results.

    Args:
        vault_path_str: String path to the Obsidian vault root.

    Returns:
        Dict mapping project name to sorted list of enriched item dicts.
        Each item includes 'match_type' ("explicit"|"inferred") and
        'confidence' (float 0.0-1.0).
    """
    vault_path = Path(vault_path_str)

    # Parse all item sources
    methods = parse_methods(vault_path)
    tools = parse_tools(vault_path)
    blog_items = parse_blog_queue(vault_path)
    all_items = methods + tools + blog_items

    # Parse projects for keyword profiles
    projects = parse_projects(vault_path)

    # Build explicit index (Tier 1)
    explicit_index = _build_explicit_index(all_items)

    # Add inferred matches (Tier 2)
    combined_index = _add_inferred_matches(explicit_index, all_items, projects)

    # Sort items within each project
    sorted_index = {
        name: _sort_items(items)
        for name, items in combined_index.items()
    }

    explicit_count = sum(
        1 for items in sorted_index.values()
        for i in items if i.get("match_type") == "explicit"
    )
    inferred_count = sum(
        1 for items in sorted_index.values()
        for i in items if i.get("match_type") == "inferred"
    )
    logger.debug(
        "Smart index: %d projects, %d explicit, %d inferred",
        len(sorted_index),
        explicit_count,
        inferred_count,
    )

    return sorted_index
