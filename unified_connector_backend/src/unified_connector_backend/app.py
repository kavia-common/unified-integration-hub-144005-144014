# PUBLIC_INTERFACE
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_allowed_origins
from .routes.health import router as health_router
from .routes.integrations import router as integrations_router


# PUBLIC_INTERFACE
def create_app() -> FastAPI:
    """Create and configure the FastAPI app instance with CORS and routers."""
    app = FastAPI(
        title="Unified Connector Backend",
        description=(
            "API backend that handles integration logic with JIRA, Confluence, and manages connector configurations. "
            "Includes health endpoints and integration configuration/testing for development."
        ),
        version="0.1.0",
        openapi_tags=[
            {"name": "health", "description": "Health and readiness endpoints"},
            {"name": "root", "description": "Root information"},
            {"name": "integrations", "description": "Configure and test third-party integrations like Jira and Confluence."},
        ],
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_allowed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include modular routers
    app.include_router(health_router)
    app.include_router(integrations_router)

    # Startup logging
    @app.on_event("startup")
    async def _on_startup() -> None:
        """Log a message on startup to help diagnose readiness issues."""
        import os
        host = os.getenv("HOST", "0.0.0.0")
        port = os.getenv("PORT", "3001")
        print(f"[main] FastAPI app startup complete. Listening on {host}:{port}")

    return app


# Expose app for ASGI import if this module is used directly.
app = create_app()
