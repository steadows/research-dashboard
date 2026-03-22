"""Pydantic request/response models for FastAPI mutation endpoints."""

from pydantic import BaseModel, Field


class StatusUpdateRequest(BaseModel):
    """Request body for POST/PATCH /api/status/{key}."""

    status: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="New status value (e.g. 'new', 'reviewed', 'skipped').",
    )


class AnalyzeRequest(BaseModel):
    """Request body for POST /api/analyze (quick Haiku analysis)."""

    item: dict = Field(..., description="Item dict with at least 'name'.")
    project: dict = Field(..., description="Project dict with at least 'name'.")
    graph_context: dict | None = Field(
        default=None,
        description="Optional graph context for vault network intelligence.",
    )


class WorkbenchAddRequest(BaseModel):
    """Request body for POST /api/workbench."""

    item: dict = Field(..., description="Full item dict snapshot (tool or method).")
    previous_status: str = Field(
        default="new",
        max_length=50,
        description="The item's status before being sent to workbench.",
    )


class WorkbenchUpdateRequest(BaseModel):
    """Request body for PATCH /api/workbench/{key}."""

    updates: dict = Field(
        ...,
        description="Dict of fields to merge into the workbench entry.",
    )


class IngestionRequest(BaseModel):
    """Request body for POST /api/instagram/refresh."""

    username: str = Field(
        ...,
        min_length=1,
        max_length=30,
        pattern=r"^[A-Za-z0-9._]+$",
        description="Instagram username to ingest from.",
    )
    days: int = Field(
        default=14,
        ge=1,
        le=90,
        description="Only include posts from the last N days.",
    )


class BlogDraftRequest(BaseModel):
    """Request body for POST /api/blog-queue/draft."""

    item: dict = Field(
        ...,
        description="Blog item dict with at least 'name', optionally 'hook', 'tags'.",
    )


class SummarizeInstagramRequest(BaseModel):
    """Request body for POST /api/summarize/instagram."""

    post: dict = Field(
        ...,
        description="Instagram post dict with transcript, key_points, name, account.",
    )
