from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .core.mongodb import connect_to_mongo, close_mongo_connection
from .core.logging import configure_logging
from .routers import connectors_router
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="Unified Connector Backend",
    description="Modular connectors API for Jira, Confluence and more.",
    version="1.0.0",
    openapi_tags=[
        {"name": "connectors", "description": "Unified connectors registry and operations"},
        {"name": "oauth", "description": "OAuth authorization flows per connector"},
        {"name": "jira", "description": "Jira connector endpoints"},
        {"name": "confluence", "description": "Confluence connector endpoints"},
        {"name": "ws", "description": "WebSocket usage info"},
    ],
)

# CORS for local dev and configurable origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

configure_logging()

@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()
    # ensure connectors are registered and routers mounted
    from .connectors.registry import mount_all_connectors
    mount_all_connectors(app)

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()

# Mount core router
app.include_router(connectors_router.router, prefix="/connectors", tags=["connectors"])

# PUBLIC_INTERFACE
@app.get("/docs/websocket", tags=["ws"], summary="WebSocket usage help")
def websocket_help():
    """Provide WebSocket usage documentation and endpoint info."""
    return {
        "message": "This API currently focuses on REST for connectors. No WebSocket endpoints are exposed for connectors in this version.",
    }

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
