from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


# PUBLIC_INTERFACE
class HealthResponse(BaseModel):
    """Response model for health checks."""
    status: str = Field(..., description="Overall service status string, e.g. 'ok' or 'error'.")


@router.get("/", tags=["root"], summary="Root", description="Root endpoint to verify API is running.")
def read_root():
    """Return a simple greeting to confirm the API is live."""
    return {"message": "Unified Connector Backend is running."}


@router.get("/health", response_model=HealthResponse, tags=["health"], summary="Liveness probe", description="Simple liveness check endpoint.")
def health():
    """Return liveness status for health checks."""
    return HealthResponse(status="ok")


# PUBLIC_INTERFACE
@router.get(
    "/docs-status",
    tags=["health"],
    summary="Docs readiness",
    description="Returns a minimal status to confirm OpenAPI schema is available and app is responsive.",
    responses={200: {"description": "Docs status OK"}}
)
def docs_status():
    """Simple endpoint to validate documentation readiness without opening Swagger UI."""
    return {"ok": True}
