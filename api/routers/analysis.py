"""Analysis router — Claude API quick/deep analysis endpoints."""

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from api.models import AnalyzeRequest
from utils.claude_client import analyze_item_deep, analyze_item_quick

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analyze", tags=["analysis"])

_STATUS_FILE = Path.home() / ".research-dashboard" / "status.json"


def _to_frontend(result: dict[str, Any]) -> dict[str, Any]:
    """Map internal analysis result to the frontend AnalysisResult contract.

    Args:
        result: Raw result from claude_client with 'response', 'input_tokens', etc.

    Returns:
        Frontend-shaped dict with 'analysis', 'tokens_used', 'cached'.
    """
    return {
        "analysis": result.get("response", ""),
        "model": result.get("model", ""),
        "tokens_used": result.get("input_tokens", 0) + result.get("output_tokens", 0),
        "cached": False,
        # Also pass through raw fields for clients that expect them
        "response": result.get("response", ""),
        "input_tokens": result.get("input_tokens", 0),
        "output_tokens": result.get("output_tokens", 0),
        "cost": result.get("cost", 0.0),
    }


@router.post("")
def analyze_quick(body: AnalyzeRequest) -> dict[str, Any]:
    """Run quick relevance analysis using Haiku.

    Args:
        body: Request with item, project, and optional graph_context.

    Returns:
        Analysis result dict with response, model, tokens, cost.
    """
    result = analyze_item_quick(
        body.item,
        body.project,
        _STATUS_FILE,
        graph_context=body.graph_context,
    )
    return _to_frontend(result)


@router.post("/deep")
def analyze_deep(body: AnalyzeRequest) -> dict[str, Any]:
    """Run deep analysis using Sonnet.

    Args:
        body: Request with item, project, and optional graph_context.

    Returns:
        Analysis result dict with response, model, tokens, cost.
    """
    result = analyze_item_deep(
        body.item,
        body.project,
        _STATUS_FILE,
        graph_context=body.graph_context,
    )
    return _to_frontend(result)
