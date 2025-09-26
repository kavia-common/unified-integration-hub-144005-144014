from typing import Dict, List, Tuple
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from ..utils.atlassian import test_atlassian_basic

router = APIRouter(prefix="", tags=["integrations"])

# In-memory storage for credentials (placeholder for future DB)
_INTEGRATION_STORE: Dict[str, Dict[str, str]] = {}


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


def _store_connection(kind: str, req: IntegrationConfigRequest, ok: bool, msg: str) -> None:
    """Store connection status in-memory (dev only)."""
    _INTEGRATION_STORE[kind] = {
        "baseUrl": str(req.baseUrl),
        "email_or_username": req.email_or_username,
        "apiToken": req.apiToken,
        "status": "connected" if ok else "error",
        "last_message": msg,
    }


@router.post(
    "/api/integrations/jira",
    response_model=IntegrationTestResponse,
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
    ok, msg = test_atlassian_basic(str(payload.baseUrl), payload.email_or_username, payload.apiToken, service="jira")
    _store_connection("jira", payload, ok, msg)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return IntegrationTestResponse(success=True, message=msg)


@router.post(
    "/api/integrations/confluence",
    response_model=IntegrationTestResponse,
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
    ok, msg = test_atlassian_basic(str(payload.baseUrl), payload.email_or_username, payload.apiToken, service="confluence")
    _store_connection("confluence", payload, ok, msg)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return IntegrationTestResponse(success=True, message=msg)
