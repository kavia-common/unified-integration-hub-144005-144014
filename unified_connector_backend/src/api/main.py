from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.settings import get_settings
from src.core.logging import get_logger
from src.core.response import ok
from src.connectors.registry import ConnectorRegistry
from src.connectors.jira.router import factory as jira_factory, get_router as jira_router
from src.connectors.confluence.router import factory as confluence_factory, get_router as confluence_router

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
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.api.CORS_ALLOW_METHODS,
    allow_headers=settings.api.CORS_ALLOW_HEADERS,
)


@app.get("/", summary="Health Check", tags=["Connectors"])
def health_check():
    """Health check endpoint that returns service status and environment."""
    return ok({"message": "Healthy", "env": settings.tenant.ENV})


# Initialize registry and register connectors
registry = ConnectorRegistry()
registry.register("jira", "Jira", factory=jira_factory, router=jira_router(), tags=["SaaS"])
registry.register("confluence", "Confluence", factory=confluence_factory, router=confluence_router(), tags=["SaaS"])

# Mount all connector endpoints
registry.mount_all(app, prefix="/connectors")
