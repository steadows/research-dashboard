"""Claude API client — Anthropic SDK wrapper with LLM trace logging.

Provides quick (Haiku) and deep (Sonnet) analysis with caching via
status_tracker. Implements LLM trace logging per the streamlit-llm-trace
protocol.
"""

import hashlib
import logging
import os
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import Any

import anthropic

from utils.paper_fetcher import fetch_paper_context
from utils.prompt_builder import build_deep_prompt, build_quick_prompt
from utils.status_tracker import get_analysis_cache, set_analysis_cache

logger = logging.getLogger(__name__)

# Dedicated LLM trace logger — propagate=False prevents bleed-through
_llm_trace_log = logging.getLogger("llm_trace")
_llm_trace_log.propagate = False

# Model constants
_HAIKU_MODEL = "claude-haiku-4-5-20251001"
_SONNET_MODEL = "claude-sonnet-4-6"

# Cost estimates per 1M tokens (USD)
_COST_PER_1M: dict[str, dict[str, float]] = {
    _HAIKU_MODEL: {"input": 1.00, "output": 5.00},
    _SONNET_MODEL: {"input": 3.00, "output": 15.00},
}


@lru_cache(maxsize=1)
def _get_client() -> anthropic.Anthropic:
    """Create and return a cached Anthropic client.

    The client is cached to reuse the HTTP connection pool across calls.

    Raises:
        ValueError: If ANTHROPIC_API_KEY env var is empty or missing.

    Returns:
        Configured Anthropic client instance.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key.strip():
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable is empty or missing. "
            "Set it to your Anthropic API key."
        )
    return anthropic.Anthropic(api_key=api_key)


def _build_cache_key(item_name: str, project_name: str, analysis_type: str) -> str:
    """Build a deterministic cache key from item, project, and type.

    Args:
        item_name: Name of the item being analyzed.
        project_name: Name of the project context.
        analysis_type: 'quick' or 'deep'.

    Returns:
        SHA-256 hex digest cache key.
    """
    raw = f"{item_name}:{project_name}:{analysis_type}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate API call cost in USD.

    Args:
        model: Model identifier string.
        input_tokens: Number of input tokens.
        output_tokens: Number of output tokens.

    Returns:
        Estimated cost in USD.
    """
    rates = _COST_PER_1M.get(model, {"input": 3.0, "output": 15.0})
    return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000


def _is_trace_enabled() -> bool:
    """Check if LLM trace logging is enabled via LLM_TRACE env var."""
    return os.environ.get("LLM_TRACE", "0") == "1"


def _log_pre_call(prompt: str, model: str) -> None:
    """Log prompt before API call (only when LLM_TRACE=1).

    Args:
        prompt: The full prompt being sent.
        model: The model being called.
    """
    if _is_trace_enabled():
        _llm_trace_log.debug("LLM prompt [model=%s]:\n%s", model, prompt)


def _log_post_call(
    model: str, input_tokens: int, output_tokens: int, cost: float
) -> None:
    """Log response metadata after API call.

    Args:
        model: Model used.
        input_tokens: Input token count.
        output_tokens: Output token count.
        cost: Estimated cost in USD.
    """
    _llm_trace_log.info(
        "LLM response [model=%s] tokens_in=%d tokens_out=%d cost=$%.4f",
        model,
        input_tokens,
        output_tokens,
        cost,
    )


def _log_error(prompt: str, error: Exception) -> None:
    """Log error with prompt context (prompt only when LLM_TRACE=1).

    Args:
        prompt: The prompt that caused the error.
        error: The exception that occurred.
    """
    if _is_trace_enabled():
        _llm_trace_log.warning(
            "LLM error [%s]: %s\nPrompt was:\n%s",
            type(error).__name__,
            error,
            prompt,
        )
    else:
        _llm_trace_log.warning(
            "LLM error [%s]: %s",
            type(error).__name__,
            error,
        )


def _call_api(prompt: str, model: str, max_tokens: int = 1024) -> dict[str, Any]:
    """Call the Anthropic API with trace logging.

    Args:
        prompt: User prompt string.
        model: Model identifier.
        max_tokens: Maximum response tokens.

    Returns:
        Dict with 'response', 'model', 'input_tokens', 'output_tokens', 'cost'.

    Raises:
        anthropic.APIError: On API failure (after logging).
    """
    client = _get_client()
    _log_pre_call(prompt, model)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:
        _log_error(prompt, exc)
        logger.warning("Claude API call failed [model=%s]: %s", model, exc)
        raise

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = _estimate_cost(model, input_tokens, output_tokens)

    _log_post_call(model, input_tokens, output_tokens, cost)

    return {
        "response": response.content[0].text,
        "model": response.model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost": cost,
    }


def _analyze_item(
    item: dict,
    project: dict,
    status_file: Path,
    analysis_type: str,
    model: str,
    max_tokens: int,
    prompt_fn: Callable[[dict, dict], str],
) -> dict[str, Any]:
    """Shared analysis logic — cache check, API call, cache write.

    Args:
        item: Item dict with at least 'name'.
        project: Project dict with at least 'name'.
        status_file: Path to status JSON for caching.
        analysis_type: 'quick' or 'deep'.
        model: Model identifier to use.
        max_tokens: Maximum response tokens.
        prompt_fn: Function to build the prompt.

    Returns:
        Analysis result dict.
    """
    cache_key = _build_cache_key(item["name"], project["name"], analysis_type)

    cached = get_analysis_cache(cache_key, status_file)
    if cached is not None:
        logger.debug(
            "Cache hit for %s analysis: %s + %s",
            analysis_type,
            item["name"],
            project["name"],
        )
        return cached

    logger.info(
        "%s analysis requested: %s for project %s",
        analysis_type.capitalize(),
        item["name"],
        project["name"],
    )
    prompt = prompt_fn(item, project)
    result = _call_api(prompt, model, max_tokens)

    set_analysis_cache(cache_key, result, status_file)
    logger.info(
        "Cached %s analysis: %s + %s", analysis_type, item["name"], project["name"]
    )

    return result


def call_haiku_json(prompt: str, max_tokens: int = 600) -> str:
    """Call Haiku for structured JSON extraction.

    Args:
        prompt: User prompt expecting JSON response.
        max_tokens: Maximum response tokens.

    Returns:
        Raw response text (caller parses JSON).
    """
    result = _call_api(prompt, model=_HAIKU_MODEL, max_tokens=max_tokens)
    return result["response"]


def analyze_item_quick(
    item: dict,
    project: dict,
    status_file: Path,
) -> dict[str, Any]:
    """Run quick relevance analysis using Haiku.

    Checks cache first. On miss, builds prompt, calls API, and caches result.

    Args:
        item: Item dict with at least 'name'.
        project: Project dict with at least 'name'.
        status_file: Path to status JSON for caching.

    Returns:
        Analysis result dict.
    """
    return _analyze_item(
        item, project, status_file, "quick", _HAIKU_MODEL, 1024, build_quick_prompt
    )


def summarize_paper(
    item: dict,
    status_file: Path = Path.home() / ".research-dashboard" / "status.json",
) -> str:
    """Return a 2–3 sentence plain-English summary of the paper/article.

    Uses Haiku with caching. Returns empty string on failure.

    Args:
        item: Blog item dict with name, hook, source fields.
        status_file: Path to status JSON for caching.

    Returns:
        Plain-text summary string, or empty string on error.
    """
    cache_key = _build_cache_key(item["name"], "", "paper_summary_v3")
    cached = get_analysis_cache(cache_key, status_file)
    if cached is not None:
        return cached.get("response", "")

    title = item.get("name", "")
    hook = item.get("hook", "")
    source = item.get("source paper") or item.get("source", "")
    tags = item.get("tags", "")
    projects = item.get("projects", [])

    # Enrich with paper abstract from Semantic Scholar
    paper_ctx = fetch_paper_context(source)
    abstract = paper_ctx.get("abstract", "")
    abstract_block = (
        f"Abstract: {abstract}" if abstract else "Abstract: (not available)"
    )

    # Connected projects
    projects_line = f"Connected Projects: {', '.join(projects)}" if projects else ""

    prompt = f"""\
<context>
A blogger is skimming a reading list and needs to quickly decide if a paper is worth their time.

Title: {title}
Hook: {hook}
Source: {source}
{abstract_block}
Tags: {tags}
{projects_line}
</context>

<objective>
Summarise what this paper is about in plain, everyday English. Cover: what problem it solves, \
what they actually did, and what they found.
</objective>

<style>
Short sentences. Simple words. No academic language, no jargon. If you must use a technical \
term, immediately explain it in plain English in the same sentence. Write like you're explaining \
it to a smart friend over coffee, not writing a paper review.
</style>

<tone>
Casual and clear.
</tone>

<audience>
Someone technical who is skimming quickly and wants the core idea in under 10 seconds.
</audience>

<response>
2–3 short sentences. Plain prose, no bullet points. No opener like "This paper..." or \
"The authors..." — jump straight to the idea.
</response>"""

    try:
        result = _call_api(prompt, _HAIKU_MODEL, max_tokens=200)
        set_analysis_cache(cache_key, result, status_file)
        return result.get("response", "")
    except Exception as exc:
        logger.warning("summarize_paper failed for %s: %s", title, exc)
        return ""


def summarize_tool(
    tool: dict,
    status_file: Path = Path.home() / ".research-dashboard" / "status.json",
) -> str:
    """Return a 2–3 sentence plain-English summary of what a tool does and why it matters.

    Uses Haiku with caching. Returns empty string on failure.

    Args:
        tool: Tool item dict with name, category, source, what_it_does fields.
        status_file: Path to status JSON for caching.

    Returns:
        Plain-text summary string, or empty string on error.
    """
    cache_key = _build_cache_key(tool["name"], "", "tool_summary_v2")
    cached = get_analysis_cache(cache_key, status_file)
    if cached is not None:
        return cached.get("response", "")

    name = tool.get("name", "")
    category = tool.get("category", "")
    source = tool.get("source", "")
    what_it_does = tool.get("what it does", "")
    projects = tool.get("projects", [])
    projects_line = f"Connected Projects: {', '.join(projects)}" if projects else ""

    prompt = f"""\
<context>
A developer is scanning a tools radar and needs to quickly understand what a tool does
and whether it's worth investigating.

Tool name: {name}
Category: {category}
Source: {source}
Description: {what_it_does}
{projects_line}
</context>

<objective>
Explain what this tool does and why a developer might care about it.
</objective>

<style>
Plain English. Short sentences. No marketing language, no jargon without explanation.
If a technical term is needed, explain it in the same sentence.
Write like you're telling a smart colleague about a tool you just discovered.
</style>

<tone>
Practical and direct. Skip the hype.
</tone>

<audience>
A developer who wants to know what the tool actually does in 10 seconds.
</audience>

<response>
2–3 short sentences. Plain prose, no bullet points.
No opener like "This tool..." — jump straight to what it does.
</response>"""

    try:
        result = _call_api(prompt, _HAIKU_MODEL, max_tokens=200)
        set_analysis_cache(cache_key, result, status_file)
        return result.get("response", "")
    except Exception as exc:
        logger.warning("summarize_tool failed for %s: %s", name, exc)
        return ""


def analyze_blog_potential(
    item: dict,
    status_file: Path = Path.home() / ".research-dashboard" / "status.json",
) -> dict[str, Any]:
    """Analyze blog post potential using Haiku with caching.

    Args:
        item: Blog item dict with name, hook, source, tags fields.
        status_file: Path to status JSON for caching.

    Returns:
        Analysis result dict with 'response', model, token, cost fields.
    """
    cache_key = _build_cache_key(item["name"], "", "blog_potential_v2")
    cached = get_analysis_cache(cache_key, status_file)
    if cached is not None:
        return cached

    title = item.get("name", "")
    hook = item.get("hook", "")
    source = item.get("source paper") or item.get("source", "")
    tags = item.get("tags", "")
    projects = item.get("projects", [])

    # Enrich with paper abstract
    paper_ctx = fetch_paper_context(source)
    abstract = paper_ctx.get("abstract", "")
    abstract_block = (
        f"Abstract: {abstract}" if abstract else "Abstract: (not available)"
    )
    projects_line = f"Connected Projects: {', '.join(projects)}" if projects else ""

    prompt = f"""\
<context>
You are helping a technical blogger decide whether to invest time writing a post based on \
a research paper or industry article.

Title: {title}
Hook: {hook}
Source: {source}
{abstract_block}
Tags: {tags}
{projects_line}
</context>

<objective>
Assess the blog post potential of this idea across four dimensions: target audience, \
unique angle, timeliness, and writing effort.
</objective>

<style>
Terse, one-line answers per dimension. No elaboration beyond what is requested.
</style>

<tone>
Direct and opinionated. Make a call — don't hedge.
</tone>

<audience>
The author themselves — this is a personal decision-making tool, not a pitch to an editor.
</audience>

<response>
Exactly 4 lines, plain text only, no markdown:
AUDIENCE: [one sentence — who specifically gets the most value from this post]
ANGLE: [one sentence — what makes this take distinct from existing content on the topic]
WHY NOW: [one sentence — why this is timely or strategically relevant right now]
EFFORT: [Low / Medium / High — with a one-phrase reason]
</response>"""

    result = _call_api(prompt, _HAIKU_MODEL, max_tokens=300)
    set_analysis_cache(cache_key, result, status_file)
    return result


def deep_read_paper(
    item: dict,
    status_file: Path = Path.home() / ".research-dashboard" / "status.json",
) -> str:
    """Return a 2–3 paragraph rich synthesis of the paper for an ML practitioner.

    Uses Sonnet with caching. Returns empty string on failure.

    Args:
        item: Blog item dict with name, hook, source, tags fields.
        status_file: Path to status JSON for caching.

    Returns:
        Multi-paragraph synthesis string, or empty string on error.
    """
    cache_key = _build_cache_key(item["name"], "", "paper_deep_read_v2")
    cached = get_analysis_cache(cache_key, status_file)
    if cached is not None:
        return cached.get("response", "")

    title = item.get("name", "")
    hook = item.get("hook", "")
    source = item.get("source paper") or item.get("source", "")
    tags = item.get("tags", "")

    # Fetch full paper context (abstract + full text if available)
    paper_ctx = fetch_paper_context(source)
    full_text = paper_ctx.get("full_text", "")
    abstract = paper_ctx.get("abstract", "")

    if full_text:
        content_block = f"Paper Content:\n{full_text}"
    elif abstract:
        content_block = f"Abstract: {abstract}"
    else:
        content_block = "Abstract: (not available)"

    prompt = f"""\
<context>
An ML practitioner is deciding whether to write a blog post about this research paper.
They want a thorough but readable synthesis — not an academic summary, but the kind of
breakdown a smart colleague would give over lunch.

Title: {title}
Hook: {hook}
Source: {source}
{content_block}
Tags: {tags}
</context>

<objective>
Write a 2–3 paragraph deep synthesis covering:
1. What problem this solves and why it matters now
2. The core method or idea — what they actually did (include key results if known)
3. Limitations, open questions, and what an ML practitioner should take away
</objective>

<style>
Plain English. Short paragraphs. Active voice. No academic hedging.
If a technical term is needed, explain it in the same sentence using an analogy.
Write like a senior engineer explaining to an interested non-specialist.
</style>

<tone>
Engaged and direct. Confident about what matters, honest about gaps.
</tone>

<audience>
An ML practitioner who has heard of the topic but hasn't read the paper.
They want to understand what's new and whether it changes anything they should do.
</audience>

<response>
2–3 short paragraphs. Plain prose only — no headers, no bullet points, no lists.
No opener like "This paper..." — start with the core idea immediately.
</response>"""

    try:
        result = _call_api(prompt, _SONNET_MODEL, max_tokens=600)
        set_analysis_cache(cache_key, result, status_file)
        return result.get("response", "")
    except Exception as exc:
        logger.warning("deep_read_paper failed for %s: %s", title, exc)
        return ""


def generate_blog_draft(
    item: dict,
    status_file: Path = Path.home() / ".research-dashboard" / "status.json",
) -> str:
    """Generate a ~1000 word blog post body using Sonnet.

    Returns raw MDX body only (no frontmatter). Uses caching.
    Returns empty string on failure.

    Args:
        item: Blog item dict with name, hook, source, tags fields.
        status_file: Path to status JSON for caching.

    Returns:
        Raw MDX body string, or empty string on error.
    """
    cache_key = _build_cache_key(item["name"], "", "blog_draft_v2")
    cached = get_analysis_cache(cache_key, status_file)
    if cached is not None:
        return cached.get("response", "")

    title = item.get("name", "")
    hook = item.get("hook", "")
    source = item.get("source paper") or item.get("source", "")
    tags = item.get("tags", "")

    # Fetch full paper context
    paper_ctx = fetch_paper_context(source)
    full_text = paper_ctx.get("full_text", "")
    abstract = paper_ctx.get("abstract", "")

    if full_text:
        content_block = f"Paper Content:\n{full_text}"
    elif abstract:
        content_block = f"Abstract: {abstract}"
    else:
        content_block = "Abstract: (not available)"

    prompt = f"""\
<context>
A technical blogger is writing a post for their personal blog. The audience is smart,
curious people who are NOT ML specialists — they're product managers, engineers in
adjacent fields, entrepreneurs, or curious generalists who follow AI developments.

Title: {title}
Hook: {hook}
Source: {source}
{content_block}
Tags: {tags}
</context>

<objective>
Write a complete blog post body of approximately 900–1100 words.
Cover: what the problem is (with a relatable analogy), what was done and why it's clever,
what the results show, and what readers should take away or watch for.
</objective>

<style>
Write for a smart, curious reader who is NOT an ML specialist.
Use analogies. Avoid jargon — if a technical term must appear, explain it in the same sentence.
Short paragraphs (2–4 sentences). Active voice throughout.
Use markdown headers (## and ###) to break the post into readable sections.
</style>

<tone>
Curious, direct, and honest. Enthusiastic about interesting ideas without being hype-y.
Acknowledge what we don't know yet.
</tone>

<audience>
Non-specialist but technically literate readers who follow AI/ML news and want to understand
what actually matters and why.
</audience>

<response>
Raw MDX body only — no YAML frontmatter, no title heading at the top.
Start directly with a compelling opening paragraph (no "Introduction" header).
Use ## and ### markdown headers for sections.
End with a brief "What this means" or "Why it matters" section.
Approximately 900–1100 words.
</response>"""

    try:
        result = _call_api(prompt, _SONNET_MODEL, max_tokens=2000)
        set_analysis_cache(cache_key, result, status_file)
        return result.get("response", "")
    except Exception as exc:
        logger.warning("generate_blog_draft failed for %s: %s", title, exc)
        return ""


def generate_linkedin_post(
    item: dict,
    draft_excerpt: str,
    status_file: Path = Path.home() / ".research-dashboard" / "status.json",
) -> str:
    """Generate a 3–4 sentence LinkedIn announcement for a blog post.

    Uses Haiku with caching. Returns empty string on failure.

    Args:
        item: Blog item dict with name, hook fields.
        draft_excerpt: First ~200 chars of the blog draft for context.
        status_file: Path to status JSON for caching.

    Returns:
        LinkedIn post string, or empty string on error.
    """
    # Hash full draft body for cache key — not truncated excerpt
    draft_hash = hashlib.sha256(draft_excerpt.encode()).hexdigest()[:16]
    cache_key = _build_cache_key(item["name"], draft_hash, "linkedin_post_v2")
    cached = get_analysis_cache(cache_key, status_file)
    if cached is not None:
        return cached.get("response", "")

    title = item.get("name", "")
    hook = item.get("hook", "")

    prompt = f"""\
<context>
A technical blogger just published a new post and wants to announce it on LinkedIn.

Post title: {title}
Post hook: {hook}
Draft body: {draft_excerpt}
</context>

<objective>
Write a short LinkedIn announcement for this blog post.
</objective>

<style>
Conversational and authentic — not corporate, not hype-y.
No hashtag spam. At most 2 relevant hashtags at the end.
No "Excited to share" or "Thrilled to announce" openers.
</style>

<tone>
Warm, direct, and genuine. Like a smart colleague sharing something they found interesting.
</tone>

<audience>
LinkedIn connections who follow AI/ML topics — a mix of practitioners, managers, and curious generalists.
</audience>

<response>
3–4 sentences. Plain text. End with 1–2 hashtags on a new line.
No bullet points. No em-dashes as lists.
</response>"""

    try:
        result = _call_api(prompt, _HAIKU_MODEL, max_tokens=300)
        set_analysis_cache(cache_key, result, status_file)
        return result.get("response", "")
    except Exception as exc:
        logger.warning("generate_linkedin_post failed for %s: %s", title, exc)
        return ""


def analyze_item_deep(
    item: dict,
    project: dict,
    status_file: Path,
) -> dict[str, Any]:
    """Run deep analysis using Sonnet.

    Checks cache first. On miss, builds prompt, calls API, and caches result.

    Args:
        item: Item dict with at least 'name'.
        project: Project dict with at least 'name'.
        status_file: Path to status JSON for caching.

    Returns:
        Analysis result dict.
    """
    return _analyze_item(
        item, project, status_file, "deep", _SONNET_MODEL, 2048, build_deep_prompt
    )
