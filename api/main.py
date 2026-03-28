"""FastAPI application factory for the Research Intelligence Dashboard API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure src/ is on sys.path before any utils imports
import api.deps  # noqa: F401
from api.routers import (
    analysis,
    content,
    graph,
    ingestion,
    linker,
    projects,
    research,
    status,
    workbench,
)
from api import ws


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance with CORS and all routers.
    """
    app = FastAPI(
        title="Research Intelligence Dashboard API",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    # CORS — locked to localhost:3000 (Next.js dev server)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers — read-only
    app.include_router(projects.router)
    app.include_router(content.router)
    app.include_router(graph.router)
    app.include_router(workbench.router)

    # Register routers — mutations
    app.include_router(status.router)
    app.include_router(analysis.router)
    app.include_router(research.router)
    app.include_router(ingestion.router)
    app.include_router(linker.router)

    # WebSocket
    app.include_router(ws.router)

    return app


app = create_app()
