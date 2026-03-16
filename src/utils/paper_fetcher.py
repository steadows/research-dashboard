"""Paper fetcher — retrieves paper context from Semantic Scholar by title.

Uses the free Semantic Scholar Graph API (no key required).
Fetches abstract, metadata, and full text (via open-access PDF or arXiv HTML).
Falls back gracefully on any failure so callers are never blocked.

Paper cache is stored in ~/.research-dashboard/paper-cache/ as separate files
(NOT in status.json) to avoid degrading status tracker performance.
"""

import hashlib
import io
import json
import logging
import re
import tempfile
from pathlib import Path
from typing import Any, TypedDict

import httpx

from utils.status_tracker import get_analysis_cache, set_analysis_cache

logger = logging.getLogger(__name__)

_SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
_FIELDS = "abstract,openAccessPdf,externalIds,year,venue,authors"
_ABSTRACT_ONLY_FIELDS = "abstract,year,venue,authors"
_CACHE_TYPE = "paper_abstract_v1"
_REQUEST_TIMEOUT = 10.0  # seconds
_FULL_TEXT_CAP = 30_000  # chars (~7.5K tokens)

_DEFAULT_CACHE_DIR = Path.home() / ".research-dashboard" / "paper-cache"


class PaperContext(TypedDict):
    """Typed dict for unified paper context."""

    abstract: str
    full_text: str
    full_text_source: str  # "pdf" | "arxiv_html" | "abstract_only" | ""
    year: str
    venue: str
    authors: list[str]
    fetch_state: str  # "not_fetched" | "not_found" | "failed" | "abstract_only" | "pdf" | "arxiv_html"
    error: str  # short error summary, empty on success


def _empty_context(fetch_state: str = "not_fetched", error: str = "") -> PaperContext:
    """Return an empty PaperContext with the given state."""
    return PaperContext(
        abstract="",
        full_text="",
        full_text_source="",
        year="",
        venue="",
        authors=[],
        fetch_state=fetch_state,
        error=error,
    )


# ---------------------------------------------------------------------------
# Paper cache (separate file-based cache, NOT status.json)
# ---------------------------------------------------------------------------


def _paper_cache_key(title: str) -> str:
    """Build a deterministic cache key from normalised title."""
    raw = title.strip().lower()
    return hashlib.sha256(raw.encode()).hexdigest()


def _read_paper_cache(
    cache_key: str, cache_dir: Path = _DEFAULT_CACHE_DIR
) -> PaperContext | None:
    """Read cached paper context from disk.

    Args:
        cache_key: SHA-256 hex digest key.
        cache_dir: Directory containing paper cache files.

    Returns:
        PaperContext dict if cached, None on miss.
    """
    meta_file = cache_dir / f"{cache_key}.json"
    if not meta_file.is_file():
        return None

    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    # Load full text from separate .txt file if it exists
    text_file = cache_dir / f"{cache_key}.txt"
    full_text = ""
    if text_file.is_file():
        try:
            full_text = text_file.read_text(encoding="utf-8")
        except OSError:
            pass

    return PaperContext(
        abstract=meta.get("abstract", ""),
        full_text=full_text,
        full_text_source=meta.get("full_text_source", ""),
        year=str(meta.get("year", "")),
        venue=meta.get("venue", ""),
        authors=meta.get("authors", []),
        fetch_state=meta.get("fetch_state", "not_fetched"),
        error=meta.get("error", ""),
    )


def _write_paper_cache(
    cache_key: str, context: PaperContext, cache_dir: Path = _DEFAULT_CACHE_DIR
) -> None:
    """Write paper context to disk cache atomically.

    Args:
        cache_key: SHA-256 hex digest key.
        context: PaperContext to persist.
        cache_dir: Directory for paper cache files.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Write metadata (everything except full_text)
    meta = {
        "abstract": context["abstract"],
        "full_text_source": context["full_text_source"],
        "year": context["year"],
        "venue": context["venue"],
        "authors": context["authors"],
        "fetch_state": context["fetch_state"],
        "error": context["error"],
    }

    meta_file = cache_dir / f"{cache_key}.json"
    fd, tmp_path = tempfile.mkstemp(dir=str(cache_dir), suffix=".tmp")
    try:
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(meta, f)
        Path(tmp_path).replace(meta_file)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise

    # Write full text to separate file if non-empty
    if context["full_text"]:
        text_file = cache_dir / f"{cache_key}.txt"
        fd2, tmp_path2 = tempfile.mkstemp(dir=str(cache_dir), suffix=".tmp")
        try:
            with open(fd2, "w", encoding="utf-8") as f:
                f.write(context["full_text"])
            Path(tmp_path2).replace(text_file)
        except Exception:
            Path(tmp_path2).unlink(missing_ok=True)
            raise


def get_cached_paper_context(
    title: str, cache_dir: Path = _DEFAULT_CACHE_DIR
) -> PaperContext | None:
    """Passive cache inspection — returns cached context or None without triggering fetch.

    This is safe to call on the render path. No network calls.

    Args:
        title: Paper title to look up.
        cache_dir: Directory containing paper cache files.

    Returns:
        PaperContext if cached, None if not yet fetched.
    """
    if not title or not title.strip():
        return None
    cache_key = _paper_cache_key(title)
    return _read_paper_cache(cache_key, cache_dir)


# ---------------------------------------------------------------------------
# Full text extraction helpers
# ---------------------------------------------------------------------------


def _extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using pypdf.

    Prefers semantic section extraction (Introduction, Conclusion, Discussion,
    Results). Falls back to sequential text if section extraction yields < 500 chars.

    Args:
        pdf_bytes: Raw PDF file bytes.

    Returns:
        Extracted text, capped at _FULL_TEXT_CAP characters.
    """
    try:
        import pypdf

        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        # Extract all pages (bounded to prevent huge PDFs)
        pages_text = []
        for page in reader.pages[:50]:
            text = page.extract_text()
            if text:
                pages_text.append(text)

        full = "\n\n".join(pages_text)

        # Try semantic section extraction
        section_pattern = re.compile(
            r"(?:^|\n)((?:Introduction|Conclusion|Discussion|Results|Abstract)"
            r"[^\n]*)\n(.*?)(?=\n(?:Introduction|Conclusion|Discussion|Results"
            r"|References|Bibliography|Acknowledgment)[^\n]*\n|\Z)",
            re.DOTALL | re.IGNORECASE,
        )
        sections = section_pattern.findall(full)
        if sections:
            semantic = "\n\n".join(
                f"{header.strip()}\n{body.strip()}" for header, body in sections
            )
            if len(semantic) >= 500:
                return semantic[:_FULL_TEXT_CAP]

        return full[:_FULL_TEXT_CAP]
    except Exception as exc:
        logger.warning("PDF text extraction failed: %s", exc)
        return ""


def _extract_text_from_arxiv_html(html_content: str) -> str:
    """Extract text from arXiv HTML page by stripping tags.

    Args:
        html_content: Raw HTML string from arXiv.

    Returns:
        Plain text, capped at _FULL_TEXT_CAP characters.
    """
    # Strip HTML tags
    text = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text[:_FULL_TEXT_CAP]


# ---------------------------------------------------------------------------
# Unified paper context fetcher
# ---------------------------------------------------------------------------


def fetch_paper_context(
    title: str, cache_dir: Path = _DEFAULT_CACHE_DIR
) -> PaperContext:
    """Fetch all available context for a paper title. Single Semantic Scholar lookup.

    Checks paper-cache directory first. On miss, queries Semantic Scholar,
    attempts full text extraction (PDF → arXiv HTML → abstract only),
    caches result, and returns.

    Never raises — returns PaperContext with fetch_state indicating outcome.

    Args:
        title: Paper title to look up.
        cache_dir: Directory for paper cache files.

    Returns:
        PaperContext with all available fields populated.
    """
    if not title or not title.strip():
        return _empty_context(fetch_state="not_found")

    cache_key = _paper_cache_key(title)

    # Check file cache
    cached = _read_paper_cache(cache_key, cache_dir)
    if cached is not None:
        logger.debug("Paper cache hit for: %s", title)
        return cached

    logger.info("Fetching paper context from Semantic Scholar: %s", title)

    try:
        return _fetch_and_cache_paper(title, cache_key, cache_dir)
    except Exception as exc:
        logger.warning("Paper context fetch failed for %r: %s", title, exc)
        context = _empty_context(fetch_state="failed", error=str(exc))
        _write_paper_cache(cache_key, context, cache_dir)
        return context


def _fetch_and_cache_paper(title: str, cache_key: str, cache_dir: Path) -> PaperContext:
    """Execute Semantic Scholar query and full text extraction pipeline.

    Args:
        title: Paper title to search.
        cache_key: Pre-computed cache key.
        cache_dir: Cache directory.

    Returns:
        Populated PaperContext.
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
            context = _empty_context(fetch_state="not_found")
            _write_paper_cache(cache_key, context, cache_dir)
            return context

        top = papers[0]
        abstract = top.get("abstract") or ""
        year = str(top.get("year") or "")
        venue = top.get("venue") or ""
        authors = [a.get("name", "") for a in (top.get("authors") or [])]

        # Try full text extraction pipeline
        full_text, full_text_source, fetch_state = _try_full_text_extraction(
            top, client
        )

    # Apply full text cap
    if full_text and len(full_text) > _FULL_TEXT_CAP:
        full_text = full_text[:_FULL_TEXT_CAP]

    # If no full text but we have abstract, mark as abstract_only
    if not full_text and abstract:
        fetch_state = "abstract_only"
        full_text_source = "abstract_only"

    context = PaperContext(
        abstract=abstract,
        full_text=full_text,
        full_text_source=full_text_source,
        year=year,
        venue=venue,
        authors=authors,
        fetch_state=fetch_state,
        error="",
    )

    _write_paper_cache(cache_key, context, cache_dir)
    logger.info(
        "Paper context cached [state=%s, text=%d chars]: %s",
        fetch_state,
        len(full_text),
        title,
    )
    return context


def _try_full_text_extraction(
    paper: dict[str, Any], client: httpx.Client
) -> tuple[str, str, str]:
    """Attempt to extract full text from open-access sources.

    Pipeline: PDF → arXiv HTML → empty.

    Args:
        paper: Semantic Scholar paper dict.
        client: Active httpx client for follow-up requests.

    Returns:
        Tuple of (full_text, full_text_source, fetch_state).
    """
    # 1. PDF path
    open_access = paper.get("openAccessPdf")
    if open_access and open_access.get("url"):
        try:
            pdf_url = open_access["url"]
            logger.debug("Fetching PDF: %s", pdf_url)
            pdf_response = client.get(pdf_url, timeout=30.0)
            pdf_response.raise_for_status()
            text = _extract_text_from_pdf(pdf_response.content)
            if text:
                logger.info("PDF text extracted: %d chars", len(text))
                return text, "pdf", "pdf"
        except Exception as exc:
            logger.warning("PDF extraction failed, trying arXiv: %s", exc)

    # 2. arXiv HTML path
    external_ids = paper.get("externalIds") or {}
    arxiv_id = external_ids.get("ArXiv")
    if arxiv_id:
        try:
            arxiv_url = f"https://arxiv.org/html/{arxiv_id}"
            logger.debug("Fetching arXiv HTML: %s", arxiv_url)
            html_response = client.get(arxiv_url, timeout=30.0)
            html_response.raise_for_status()
            text = _extract_text_from_arxiv_html(html_response.text)
            if text:
                logger.info("arXiv HTML text extracted: %d chars", len(text))
                return text, "arxiv_html", "arxiv_html"
        except Exception as exc:
            logger.warning("arXiv HTML extraction failed: %s", exc)

    # 3. No full text available
    return "", "", "not_found"


# ---------------------------------------------------------------------------
# Legacy abstract-only API (kept for backward compatibility)
# ---------------------------------------------------------------------------


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
        "fields": _ABSTRACT_ONLY_FIELDS,
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
