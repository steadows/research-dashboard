"""Paper fetcher — retrieves paper context from Semantic Scholar + OpenAlex.

Primary: Semantic Scholar Graph API (supports optional API key via
SEMANTIC_SCHOLAR_API_KEY env var for higher rate limits).
Fallback: OpenAlex API (free, no key, generous rate limits).
Full text: open-access PDF or arXiv HTML.

Falls back gracefully on any failure so callers are never blocked.

Paper cache is stored in ~/.research-dashboard/paper-cache/ as separate files
(NOT in status.json) to avoid degrading status tracker performance.
"""

import hashlib
import io
import json
import logging
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, TypedDict

import httpx

from utils.status_tracker import get_analysis_cache, set_analysis_cache

logger = logging.getLogger(__name__)

_SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
_OPENALEX_SEARCH_URL = "https://api.openalex.org/works"
_FIELDS = "abstract,openAccessPdf,externalIds,year,venue,authors"
_ABSTRACT_ONLY_FIELDS = "abstract,year,venue,authors"
_CACHE_TYPE = "paper_abstract_v1"
_REQUEST_TIMEOUT = 10.0  # seconds
_FULL_TEXT_CAP = 30_000  # chars (~7.5K tokens)
_RETRY_ATTEMPTS = 3
_RETRY_BACKOFF_BASE = 3.0  # seconds — exponential: 3, 6, 12
_FAILED_CACHE_COOLDOWN = 300  # seconds — don't re-fetch failed papers for 5 min

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


def _read_paper_cache_timestamp(
    cache_key: str, cache_dir: Path = _DEFAULT_CACHE_DIR
) -> float | None:
    """Read the cached_at timestamp from a paper cache file.

    Args:
        cache_key: SHA-256 hex digest key.
        cache_dir: Directory containing paper cache files.

    Returns:
        Unix timestamp float, or None if missing/unreadable.
    """
    meta_file = cache_dir / f"{cache_key}.json"
    if not meta_file.is_file():
        return None
    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        return meta.get("cached_at")
    except (json.JSONDecodeError, OSError):
        return None


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
        "cached_at": time.time(),
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

    # Check file cache — serve hits, but retry "failed" entries after cooldown
    cached = _read_paper_cache(cache_key, cache_dir)
    if cached is not None:
        if cached["fetch_state"] != "failed":
            logger.debug("Paper cache hit for: %s", title)
            return cached
        # For failed entries, check if cooldown has elapsed
        cached_at = _read_paper_cache_timestamp(cache_key, cache_dir)
        if cached_at and (time.time() - cached_at) < _FAILED_CACHE_COOLDOWN:
            logger.debug(
                "Paper cache cooldown active for: %s (retry in %ds)",
                title,
                int(_FAILED_CACHE_COOLDOWN - (time.time() - cached_at)),
            )
            return cached

    logger.info("Fetching paper context from Semantic Scholar: %s", title)

    try:
        return _fetch_and_cache_paper(title, cache_key, cache_dir)
    except Exception as exc:
        logger.warning("Paper context fetch failed for %r: %s", title, exc)
        context = _empty_context(fetch_state="failed", error=str(exc))
        _write_paper_cache(cache_key, context, cache_dir)
        return context


def _request_with_retry(
    client: httpx.Client,
    url: str,
    params: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """GET request with exponential backoff on 429 rate-limit responses.

    Args:
        client: Active httpx client.
        url: Request URL.
        params: Query parameters.
        headers: Optional request headers (e.g. API key).

    Returns:
        Successful httpx.Response.

    Raises:
        httpx.HTTPStatusError: On non-429 errors or after all retries exhausted.
    """
    for attempt in range(_RETRY_ATTEMPTS):
        response = client.get(url, params=params, headers=headers or {})
        if response.status_code != 429:
            response.raise_for_status()
            return response

        # Respect Retry-After header if present, otherwise use exponential backoff
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                wait = min(float(retry_after), 30.0)  # cap at 30s
            except ValueError:
                wait = _RETRY_BACKOFF_BASE * (2**attempt)
        else:
            wait = _RETRY_BACKOFF_BASE * (2**attempt)

        logger.warning(
            "Semantic Scholar 429 rate limit — retrying in %.0fs (attempt %d/%d)",
            wait,
            attempt + 1,
            _RETRY_ATTEMPTS,
        )
        time.sleep(wait)

    # Final attempt — let it raise naturally if still 429
    response = client.get(url, params=params, headers=headers or {})
    response.raise_for_status()
    return response


def _get_semantic_scholar_headers() -> dict[str, str]:
    """Build request headers, including API key if configured.

    Set SEMANTIC_SCHOLAR_API_KEY env var for higher rate limits (100 req/sec).
    Free keys available at https://www.semanticscholar.org/product/api#api-key
    """
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
    if api_key:
        return {"x-api-key": api_key}
    return {}


def _fetch_from_semantic_scholar(
    title: str, client: httpx.Client
) -> dict[str, Any] | None:
    """Query Semantic Scholar and return the top paper dict, or None on failure.

    Args:
        title: Paper title to search.
        client: Active httpx client.

    Returns:
        Top paper dict from Semantic Scholar, or None if rate-limited/no results.
    """
    params = {"query": title, "fields": _FIELDS, "limit": 1}
    headers = _get_semantic_scholar_headers()
    try:
        response = _request_with_retry(
            client, _SEMANTIC_SCHOLAR_URL, params, headers=headers
        )
        data = response.json()
        papers = data.get("data", [])
        return papers[0] if papers else None
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:
            logger.warning("Semantic Scholar rate-limited, falling back to OpenAlex")
            return None
        raise


def _fetch_from_openalex(title: str, client: httpx.Client) -> dict[str, Any] | None:
    """Query OpenAlex as fallback and return a Semantic Scholar-shaped paper dict.

    OpenAlex is free with no API key and generous rate limits (10 req/sec polite,
    100K/day). We reshape the response to match the Semantic Scholar format so
    downstream code is unaffected.

    Args:
        title: Paper title to search.
        client: Active httpx client.

    Returns:
        Paper dict shaped like Semantic Scholar output, or None on failure.
    """
    params = {
        "search": title,
        "per_page": 1,
        "select": "title,doi,publication_year,primary_location,authorships,"
        "open_access,abstract_inverted_index",
    }
    # Polite pool: include mailto for better rate limits
    headers = {"User-Agent": "ResearchDashboard/1.0 (mailto:polite@example.com)"}
    try:
        response = client.get(
            _OPENALEX_SEARCH_URL,
            params=params,
            headers=headers,
            timeout=_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        if not results:
            return None

        work = results[0]
        return _openalex_to_paper_dict(work)
    except Exception as exc:
        logger.warning("OpenAlex fallback failed: %s", exc)
        return None


def _openalex_to_paper_dict(work: dict[str, Any]) -> dict[str, Any]:
    """Convert an OpenAlex work object to Semantic Scholar paper dict format.

    Args:
        work: OpenAlex work dict.

    Returns:
        Dict matching the Semantic Scholar paper shape used downstream.
    """
    # Reconstruct abstract from inverted index
    abstract = _reconstruct_abstract(work.get("abstract_inverted_index"))

    # Extract authors
    authors = [
        {"name": a.get("author", {}).get("display_name", "")}
        for a in (work.get("authorships") or [])
    ]

    # Extract venue from primary location
    primary = work.get("primary_location") or {}
    source = primary.get("source") or {}
    venue = source.get("display_name") or ""

    # Open access PDF
    oa = work.get("open_access") or {}
    oa_url = oa.get("oa_url") or ""
    open_access_pdf = {"url": oa_url} if oa_url else None

    # External IDs (for arXiv fallback)
    doi = work.get("doi") or ""
    external_ids = {}
    if doi:
        external_ids["DOI"] = doi.replace("https://doi.org/", "")
    # Check if arXiv by looking at the primary location
    if primary.get("source", {}).get("display_name", "").lower() == "arxiv":
        # Extract arXiv ID from doi or landing_page_url
        landing = primary.get("landing_page_url") or ""
        arxiv_match = re.search(r"arxiv\.org/abs/(\d+\.\d+)", landing)
        if arxiv_match:
            external_ids["ArXiv"] = arxiv_match.group(1)

    return {
        "abstract": abstract,
        "year": work.get("publication_year"),
        "venue": venue,
        "authors": authors,
        "openAccessPdf": open_access_pdf,
        "externalIds": external_ids,
    }


def _reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    """Reconstruct abstract text from OpenAlex inverted index format.

    Args:
        inverted_index: Dict mapping words to their position indices.

    Returns:
        Reconstructed abstract string, or empty string if unavailable.
    """
    if not inverted_index:
        return ""
    # Build position → word mapping
    positions: list[tuple[int, str]] = []
    for word, indices in inverted_index.items():
        for idx in indices:
            positions.append((idx, word))
    positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in positions)


def _fetch_and_cache_paper(title: str, cache_key: str, cache_dir: Path) -> PaperContext:
    """Fetch paper metadata: Semantic Scholar first, OpenAlex fallback on 429.

    Args:
        title: Paper title to search.
        cache_key: Pre-computed cache key.
        cache_dir: Cache directory.

    Returns:
        Populated PaperContext.
    """
    with httpx.Client(timeout=_REQUEST_TIMEOUT) as client:
        # Try Semantic Scholar first
        top = _fetch_from_semantic_scholar(title, client)

        # Fallback to OpenAlex if Semantic Scholar failed (rate limit) or no results
        source_api = "semantic_scholar"
        if top is None:
            top = _fetch_from_openalex(title, client)
            source_api = "openalex"

        if not top:
            logger.debug("No results from any API for: %s", title)
            context = _empty_context(fetch_state="not_found")
            _write_paper_cache(cache_key, context, cache_dir)
            return context

        logger.info("Paper metadata from %s: %s", source_api, title)

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
    headers = _get_semantic_scholar_headers()
    with httpx.Client(timeout=_REQUEST_TIMEOUT) as client:
        response = _request_with_retry(
            client, _SEMANTIC_SCHOLAR_URL, params, headers=headers
        )

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
