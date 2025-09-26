import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers.connectors import router as connectors_router
from .routers.docs import router as docs_router
from .utils.openapi import get_openapi_config

def get_allowed_origins():
    origins = os.getenv("ALLOWED_ORIGINS", "*")
    return [o.strip() for o in origins.split(",") if o.strip()]

app = FastAPI(**get_openapi_config())

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(connectors_router, prefix="/api", tags=["Connectors"])
app.include_router(docs_router, prefix="/api", tags=["System"])

# PUBLIC_INTERFACE
@app.get("/api/health", tags=["System"], summary="Health check", description="Returns service health and version.")
def health():
    """Service health endpoint."""
    return {"status": "ok", "version": os.getenv("APP_VERSION", "0.1.0")}
