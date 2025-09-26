# PUBLIC_INTERFACE
from fastapi import FastAPI
from pydantic import BaseModel, Field

# Initialize FastAPI app with metadata for docs
app = FastAPI(
    title="Unified Connector Backend",
    description="API backend that handles integration logic with JIRA, Confluence, and manages connector configurations.",
    version="0.1.0",
    openapi_tags=[
        {"name": "health", "description": "Health and readiness endpoints"},
        {"name": "root", "description": "Root information"},
    ],
)

# PUBLIC_INTERFACE
class HealthResponse(BaseModel):
    """Response model for health checks."""
    status: str = Field(..., description="Overall service status string, e.g. 'ok' or 'error'.")


@app.get("/", tags=["root"], summary="Root", description="Root endpoint to verify API is running.")
def read_root():
    """Return a simple greeting to confirm the API is live."""
    return {"message": "Unified Connector Backend is running."}


@app.get("/health", response_model=HealthResponse, tags=["health"], summary="Liveness probe", description="Simple liveness check endpoint.")
def health():
    """Return liveness status for health checks."""
    return HealthResponse(status="ok")
