"""Projects router — project list, detail, smart index, graph-linked items."""

import logging
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_vault_path_str
from api.routers.graph import _get_graph_data

from utils.graph_engine import get_project_context
from utils.smart_matcher import build_smart_project_index, get_graph_linked_items
from utils.vault_parser import parse_projects

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["projects"])

_URL_RE = re.compile(r"https?://\S+")


def _clean_discovery_source(raw: str) -> str:
    """Strip markdown, URLs, and 'Link:' labels from a source string."""
    text = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", raw)
    text = re.sub(r"\[\[(.+?)(?:\|.+?)?\]\]", r"\1", text)
    text = _URL_RE.sub("", text)
    text = re.sub(r"\bLink:\s*", "", text)
    text = re.sub(r"\s*\|\s*$", "", text).strip()
    return text


def _to_project_item(item: dict[str, Any]) -> dict[str, Any]:
    """Map smart_matcher item → frontend ProjectItem contract.

    smart_matcher returns: name, source_type, source, status, match_type, confidence, ...
    Frontend expects: title, type, discovery_source, relevance_score, status, source
    """
    return {
        "title": item.get("name", ""),
        "type": item.get("source_type", "method"),
        "source": item.get("source", ""),
        "status": item.get("status", ""),
        "discovery_source": _clean_discovery_source(item.get("source", "")),
        "relevance_score": round(item.get("confidence", 0) * 100)
        if item.get("confidence") is not None
        else None,
    }


@router.get("/projects")
def list_projects(
    vault_path: str = Depends(get_vault_path_str),
) -> list[dict[str, Any]]:
    """List all projects from the vault."""
    from pathlib import Path

    return parse_projects(Path(vault_path))


@router.get("/projects/{name}")
def get_project(
    name: str,
    vault_path: str = Depends(get_vault_path_str),
) -> dict[str, Any]:
    """Get a single project by name."""
    from pathlib import Path

    projects = parse_projects(Path(vault_path))
    for project in projects:
        if project["name"] == name:
            return project
    raise HTTPException(status_code=404, detail=f"Project '{name}' not found")


@router.get("/project-index/{project}")
def get_project_index(
    project: str,
    vault_path: str = Depends(get_vault_path_str),
) -> list[dict[str, Any]]:
    """Get smart-matched items for a project (Tier 1 + Tier 2)."""
    index = build_smart_project_index(vault_path)
    return [_to_project_item(item) for item in index.get(project, [])]


@router.get("/project-index/{project}/graph")
def get_project_graph_items(
    project: str,
    vault_path: str = Depends(get_vault_path_str),
) -> list[dict[str, Any]]:
    """Get graph-linked items for a project (Tier 1 + 2 + 3)."""
    index = build_smart_project_index(vault_path)
    linked_items = index.get(project, [])

    # Build graph context for Tier 3 discovery (uses cached graph data)
    data = _get_graph_data(vault_path)
    G = data["graph"]
    if G.number_of_nodes() == 0:
        return [
            _strip_frozensets(item)
            for item in get_graph_linked_items(project, linked_items, index, None)
        ]

    graph_ctx = get_project_context(G, data["metrics"], data["communities"], project)

    items = get_graph_linked_items(project, linked_items, index, graph_ctx)
    return [_strip_frozensets(item) for item in items]


def _strip_frozensets(item: dict[str, Any]) -> dict[str, Any]:
    """Convert any frozenset values in an item dict to sorted lists."""
    result = {}
    for key, val in item.items():
        if isinstance(val, frozenset):
            result[key] = sorted(val)
        else:
            result[key] = val
    return result
