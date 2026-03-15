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
