"""Paper fetcher — retrieves abstracts from Semantic Scholar by title.

Uses the free Semantic Scholar Graph API (no key required).
Falls back to empty string on any failure so callers are never blocked.
"""

import hashlib
import logging
from pathlib import Path
from typing import Any

import httpx

from utils.status_tracker import get_analysis_cache, set_analysis_cache

logger = logging.getLogger(__name__)

_SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
_FIELDS = "abstract,year,venue,authors"
_CACHE_TYPE = "paper_abstract_v1"
_REQUEST_TIMEOUT = 10.0  # seconds


def _abstract_cache_key(title: str) -> str:
    """Build a deterministic cache key for an abstract lookup."""
    raw = f"{title.strip().lower()}:{_CACHE_TYPE}"
    return hashlib.sha256(raw.encode()).hexdigest()


def fetch_paper_abstract(
    title: str,
    status_file: Path = Path.home() / ".research-dashboard" / "status.json",
) -> str:
    """Fetch the abstract for a paper title from Semantic Scholar.

    Checks status.json cache first. On miss, queries the Semantic Scholar
    Graph API and caches the result. Returns empty string on any failure
    (network error, no match, missing abstract).

    Args:
        title: Paper title to look up.
        status_file: Path to status JSON for caching.

    Returns:
        Abstract text string, or empty string if unavailable.
    """
    if not title or not title.strip():
        return ""

    cache_key = _abstract_cache_key(title)
    cached: dict[str, Any] | None = get_analysis_cache(cache_key, status_file)
    if cached is not None:
        logger.debug("Abstract cache hit for: %s", title)
        return cached.get("abstract", "")

    logger.info("Fetching abstract from Semantic Scholar: %s", title)
    try:
        abstract = _query_semantic_scholar(title)
    except Exception as exc:
        logger.warning("Abstract fetch failed for %r: %s", title, exc)
        return ""

    set_analysis_cache(cache_key, {"abstract": abstract}, status_file)
    logger.debug("Abstract cached for: %s", title)
    return abstract


def _query_semantic_scholar(title: str) -> str:
    """Query Semantic Scholar Graph API and return the best-match abstract.

    Args:
        title: Paper title to search.

    Returns:
        Abstract string from the top result, or empty string if none found.
    """
    params = {
        "query": title,
        "fields": _FIELDS,
        "limit": 1,
    }
    with httpx.Client(timeout=_REQUEST_TIMEOUT) as client:
        response = client.get(_SEMANTIC_SCHOLAR_URL, params=params)
        response.raise_for_status()

    data = response.json()
    papers = data.get("data", [])
    if not papers:
        logger.debug("No Semantic Scholar results for: %s", title)
        return ""

    top = papers[0]
    abstract = top.get("abstract") or ""
    if abstract:
        year = top.get("year", "")
        venue = top.get("venue", "")
        meta = f"[{venue}, {year}]" if venue and year else f"[{year}]" if year else ""
        logger.info("Abstract fetched %s: %d chars", meta, len(abstract))
    else:
        logger.debug("Top result has no abstract for: %s", title)

    return abstract
