# PUBLIC_INTERFACE
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List
import os

from .core.settings import get_settings
from .api.routes.connectors import router as connectors_router
from .api.routes.connections import router as connections_router
from .connectors.registry import connectors_registry
from .connectors.jira import jira_connector
from .connectors.confluence import confluence_connector

# Initialize FastAPI app with metadata for docs
app = FastAPI(
    title="Unified Connector Backend",
    description=(
        "API backend that handles integration logic with JIRA and Confluence. "
        "Includes health endpoints and unified connectors APIs."
    ),
    version="1.0.0",
    openapi_tags=[
        {"name": "health", "description": "Health and readiness endpoints"},
        {"name": "root", "description": "Root information"},
        {"name": "connectors", "description": "Unified connector endpoints"},
        {"name": "connections", "description": "Tenant-scoped connections and webhooks"},
    ],
)

# Enable CORS for frontend requests
settings = get_settings()
allowed_origins: List[str] = settings.cors_allowed_origins or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# PUBLIC_INTERFACE
class HealthResponse(BaseModel):
    """Response model for health checks."""
    status: str = Field(..., description="Overall service status string, e.g. 'ok' or 'error'.")


@app.on_event("startup")
async def _on_startup() -> None:
    """Register connectors and log startup message."""
    reg = connectors_registry()
    # register built-in connectors
    try:
        reg.register(jira_connector)
    except Exception:
        pass
    try:
        reg.register(confluence_connector)
    except Exception:
        pass
    print(f"[main] FastAPI app startup complete. Listening on {settings.host}:{settings.port}. Connectors: {[c['id'] for c in reg.list()]}")

@app.get("/", tags=["root"], summary="Root", description="Root endpoint to verify API is running.")
def read_root():
    """Return a simple greeting to confirm the API is live."""
    return {"message": "Unified Connector Backend is running."}

@app.get("/health", response_model=HealthResponse, tags=["health"], summary="Liveness probe", description="Simple liveness check endpoint.")
def health():
    """Return liveness status for health checks."""
    return HealthResponse(status="ok")

# PUBLIC_INTERFACE
@app.get(
    "/docs-status",
    tags=["health"],
    summary="Docs readiness",
    description="Returns a minimal status to confirm OpenAPI schema is available and app is responsive.",
    responses={200: {"description": "Docs status OK"}}
)
def docs_status():
    """Simple endpoint to validate documentation readiness without opening Swagger UI."""
    return {"ok": True}

# Mount API routers
app.include_router(connectors_router)
app.include_router(connections_router)
