# PUBLIC_INTERFACE
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, HttpUrl
from typing import Dict, Optional, List
import base64
import http.client
from urllib.parse import urlparse
import os

# In-memory storage for credentials (placeholder for future DB)
_INTEGRATION_STORE: Dict[str, Dict[str, str]] = {}

# Initialize FastAPI app with metadata for docs
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

# Enable CORS for frontend requests; origins can be refined via env later
_allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "").strip()
allowed_origins: List[str] = ["*"] if not _allowed_origins_env else [o.strip() for o in _allowed_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # In production, restrict via ALLOWED_ORIGINS env
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PUBLIC_INTERFACE
class HealthResponse(BaseModel):
    """Response model for health checks."""
    status: str = Field(..., description="Overall service status string, e.g. 'ok' or 'error'.")

# PUBLIC_INTERFACE
class IntegrationConfigRequest(BaseModel):
    """Incoming config for Jira/Confluence integration."""
    baseUrl: HttpUrl = Field(..., description="Base URL of the service, e.g. https://your-domain.atlassian.net")
    email_or_username: str = Field(..., description="Email (for Atlassian) or username as required by the service")
    apiToken: str = Field(..., description="API token or personal access token")

# PUBLIC_INTERFACE
class IntegrationTestResponse(BaseModel):
    """Response indicating the result of a test connection."""
    success: bool = Field(..., description="True if the test connection succeeded, else False")
    message: str = Field(..., description="Human-friendly message about the test result")

def _basic_auth_header(username: str, token: str) -> str:
    """Build a Basic authorization header value for Atlassian APIs."""
    raw = f"{username}:{token}".encode("utf-8")
    encoded = base64.b64encode(raw).decode("ascii")
    return f"Basic {encoded}"

def _http_get(host: str, path: str, scheme: str, headers: Dict[str, str]) -> int:
    """Perform a simple HTTP GET using http.client to avoid external deps; return status code."""
    conn = None
    try:
        if scheme == "https":
            conn = http.client.HTTPSConnection(host, timeout=10)
        else:
            conn = http.client.HTTPConnection(host, timeout=10)
        conn.request("GET", path, headers=headers)
        resp = conn.getresponse()
        # read and close to free sockets
        resp.read()
        return resp.status
    finally:
        if conn:
            conn.close()

def _test_atlassian_basic(base_url: str, username: str, api_token: str, service: str) -> (bool, str):
    """
    Perform a minimal Basic Auth test against Atlassian Jira/Confluence Cloud.
    Jira test endpoint: /rest/api/3/myself
    Confluence test endpoint: /wiki/rest/api/space?limit=1 (common on cloud is /wiki prefix)
    """
    parsed = urlparse(base_url)
    scheme = parsed.scheme or "https"
    host = parsed.netloc
    # Normalize path prefix (Jira typically root; Confluence often uses /wiki)
    prefix = parsed.path.rstrip("/")
    auth = _basic_auth_header(username, api_token)

    if service == "jira":
        path = f"{prefix}/rest/api/3/myself"
    else:
        # Try common Confluence cloud path; users may provide either https://site.atlassian.net or https://site.atlassian.net/wiki
        # We'll attempt with provided prefix first, then fallback to '/wiki'
        path = f"{prefix}/rest/api/space?limit=1" if prefix.endswith("/wiki") else f"{prefix}/wiki/rest/api/space?limit=1"

    headers = {
        "Authorization": auth,
        "Accept": "application/json",
        "User-Agent": "UnifiedConnector/0.1",
    }

    try:
        status = _http_get(host, path, scheme, headers)
        if status in (200, 201):
            return True, "Connection successful."
        elif status == 401:
            return False, "Authentication failed (401). Check email/username and API token."
        elif status == 403:
            return False, "Access forbidden (403). The token may lack required scopes."
        elif status == 404:
            return False, "Endpoint not found (404). Verify the baseUrl (ensure correct site and product path)."
        else:
            return False, f"Unexpected response status: {status}"
    except Exception as e:
        return False, f"Connection error: {e}"

@app.on_event("startup")
async def _on_startup() -> None:
    """Log a message on startup to help diagnose readiness issues."""
    host = os.getenv("HOST", "0.0.0.0")
    port = os.getenv("PORT", "3001")
    print(f"[main] FastAPI app startup complete. Listening on {host}:{port}")

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

# PUBLIC_INTERFACE
@app.post(
    "/api/integrations/jira",
    response_model=IntegrationTestResponse,
    tags=["integrations"],
    summary="Configure and test Jira integration",
    description="""
Stores the provided Jira credentials in-memory and performs a basic authentication test against Jira Cloud.

Request body:
- baseUrl: Full Jira base URL (e.g., https://your-domain.atlassian.net)
- email_or_username: Atlassian account email
- apiToken: API token generated from your Atlassian account

Returns 200 on success with a message, or 400 on failure with details.
""",
    responses={
        200: {"description": "Jira connection successful"},
        400: {"description": "Jira connection failed"},
    },
)
def configure_jira(payload: IntegrationConfigRequest):
    """Configure Jira credentials and attempt a test API call to validate authentication."""
    ok, msg = _test_atlassian_basic(str(payload.baseUrl), payload.email_or_username, payload.apiToken, service="jira")
    # Store regardless; in real system consider only storing after success or marking status
    _INTEGRATION_STORE["jira"] = {
        "baseUrl": str(payload.baseUrl),
        "email_or_username": payload.email_or_username,
        "apiToken": payload.apiToken,  # Note: Do not log; consider encryption at rest for persistence.
        "status": "connected" if ok else "error",
        "last_message": msg,
    }
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return IntegrationTestResponse(success=True, message=msg)

# PUBLIC_INTERFACE
@app.post(
    "/api/integrations/confluence",
    response_model=IntegrationTestResponse,
    tags=["integrations"],
    summary="Configure and test Confluence integration",
    description="""
Stores the provided Confluence credentials in-memory and performs a basic authentication test against Confluence Cloud.

Request body:
- baseUrl: Full Confluence base URL (e.g., https://your-domain.atlassian.net or https://your-domain.atlassian.net/wiki)
- email_or_username: Atlassian account email
- apiToken: API token generated from your Atlassian account

Returns 200 on success with a message, or 400 on failure with details.
""",
    responses={
        200: {"description": "Confluence connection successful"},
        400: {"description": "Confluence connection failed"},
    },
)
def configure_confluence(payload: IntegrationConfigRequest):
    """Configure Confluence credentials and attempt a test API call to validate authentication."""
    ok, msg = _test_atlassian_basic(str(payload.baseUrl), payload.email_or_username, payload.apiToken, service="confluence")
    _INTEGRATION_STORE["confluence"] = {
        "baseUrl": str(payload.baseUrl),
        "email_or_username": payload.email_or_username,
        "apiToken": payload.apiToken,
        "status": "connected" if ok else "error",
        "last_message": msg,
    }
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return IntegrationTestResponse(success=True, message=msg)
