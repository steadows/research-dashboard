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


@router.post("")
def analyze_quick(body: AnalyzeRequest) -> dict[str, Any]:
    """Run quick relevance analysis using Haiku.

    Args:
        body: Request with item, project, and optional graph_context.

    Returns:
        Analysis result dict with response, model, tokens, cost.
    """
    return analyze_item_quick(
        body.item,
        body.project,
        _STATUS_FILE,
        graph_context=body.graph_context,
    )


@router.post("/deep")
def analyze_deep(body: AnalyzeRequest) -> dict[str, Any]:
    """Run deep analysis using Sonnet.

    Args:
        body: Request with item, project, and optional graph_context.

    Returns:
        Analysis result dict with response, model, tokens, cost.
    """
    return analyze_item_deep(
        body.item,
        body.project,
        _STATUS_FILE,
        graph_context=body.graph_context,
    )
