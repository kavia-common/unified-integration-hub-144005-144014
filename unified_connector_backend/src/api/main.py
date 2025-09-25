from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.core.settings import get_settings
from src.core.logging import get_logger
from src.core.response import ok
from src.core.api_models import SuccessResponse
from src.connectors.registry import ConnectorRegistry
from src.connectors.jira.router import factory as jira_factory, get_router as jira_router
from src.connectors.confluence.router import factory as confluence_factory, get_router as confluence_router
from src.core.observability import RequestContextMiddleware, metrics_snapshot

settings = get_settings()
logger = get_logger(__name__)

openapi_tags = [
    {"name": "Connectors", "description": "Common endpoints for all connectors"},
    {"name": "Jira", "description": "Jira connector specific endpoints"},
    {"name": "Confluence", "description": "Confluence connector specific endpoints"},
]

app = FastAPI(
    title=settings.api.API_TITLE,
    description=settings.api.API_DESCRIPTION,
    version=settings.api.API_VERSION,
    openapi_tags=openapi_tags,
    contact={"name": "Unified Connector Team"},
    terms_of_service="https://example.com/terms",
    license_info={"name": "Apache-2.0"},
)

# CORS: allow configured origins/methods/headers; defaults are permissive but can be tightened via env
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.api.CORS_ALLOW_METHODS,
    allow_headers=settings.api.CORS_ALLOW_HEADERS,
)

# Correlation ID / request context middleware
app.add_middleware(RequestContextMiddleware, tenant_header_name=settings.tenant.TENANT_HEADER_NAME, logger=logger)


class HealthData(BaseModel):
    message: str = Field(..., description="Health status message")
    env: str = Field(..., description="Environment name")

# PUBLIC_INTERFACE
@app.get(
    "/",
    summary="Health Check",
    description="Health check endpoint that returns service status and environment.",
    tags=["Connectors"],
    response_model=SuccessResponse[HealthData],  # type: ignore[type-arg]
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {"status": "ok", "data": {"message": "Healthy", "env": "development"}, "meta": {}}
                }
            },
        }
    },
)
def health_check():
    """Health check endpoint that returns service status and environment."""
    return ok({"message": "Healthy", "env": settings.tenant.ENV})

class MetricsData(BaseModel):
    """Metric snapshot key/value map."""
    __root__: dict = Field(default_factory=dict, description="Metric name to value mapping")

# PUBLIC_INTERFACE
@app.get(
    "/_metrics",
    summary="Metrics (basic)",
    description="Basic in-process counters and accumulators for observability.",
    tags=["Connectors"],
    response_model=SuccessResponse[dict],  # type: ignore[type-arg]
    responses={
        200: {
            "description": "Metrics snapshot",
            "content": {"application/json": {"example": {"status": "ok", "data": {"requests_total": 10.0}, "meta": {}}}},
        }
    },
)
def metrics():
    """Return basic service metrics (process-local) for quick visibility."""
    return ok(metrics_snapshot())

# WebSocket usage helper (if future real-time features are added)
# PUBLIC_INTERFACE
@app.get(
    "/_websocket-docs",
    summary="WebSocket usage help",
    description="This project may expose WebSocket endpoints in the future. Connect using standard ws(s):// URL and include X-Tenant-ID header where applicable.",
    tags=["Connectors"],
    response_model=SuccessResponse[dict],  # type: ignore[type-arg]
)
def websocket_help():
    """Provide guidance for connecting to WebSocket endpoints in this API."""
    return ok({"message": "No active WebSocket endpoints. Use REST endpoints documented in OpenAPI."})

# Initialize registry and register connectors
registry = ConnectorRegistry()
registry.register("jira", "Jira", factory=jira_factory, router=jira_router(), tags=["SaaS"])
registry.register("confluence", "Confluence", factory=confluence_factory, router=confluence_router(), tags=["SaaS"])

# Mount all connector endpoints
registry.mount_all(app, prefix="/connectors")
