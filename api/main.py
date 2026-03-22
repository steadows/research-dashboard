"""FastAPI application factory for the Research Intelligence Dashboard API."""

from fastapi import FastAPI

# Ensure src/ is on sys.path before any utils imports
import api.deps  # noqa: F401


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance.
    """
    app = FastAPI(
        title="Research Intelligence Dashboard API",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    return app


app = create_app()
