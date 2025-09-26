from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from ...connectors.base import BaseConnector
from .client import build_authorize_url, exchange_code_for_tokens, search_issues, create_issue, JIRA_SCOPES
from ...connectors.registry import register
from ...utils.errors import http_error

router = APIRouter()

def get_tenant_id():
    return "demo-tenant"

class OAuthLoginResponse(BaseModel):
    authorize_url: str = Field(..., description="Provider authorization URL")
    state: str = Field(..., description="Opaque state value")

# PUBLIC_INTERFACE
@router.get("/oauth/login", response_model=OAuthLoginResponse, summary="Start Jira OAuth", tags=["oauth"])
async def oauth_login(tenant_id: str = Depends(get_tenant_id), return_url: bool = True):
    """Build and return the Jira OAuth authorization URL."""
    state = f"{tenant_id}-state"
    data = await build_authorize_url(state)
    return OAuthLoginResponse(**data)

# PUBLIC_INTERFACE
@router.get("/oauth/callback", summary="Jira OAuth callback", tags=["oauth"])
async def oauth_callback(state: str, code: str, tenant_id: str = Depends(get_tenant_id)):
    """Handle OAuth callback, exchange code for tokens, and persist connection."""
    if not state or tenant_id not in state:
        http_error("CSRF", "Invalid state", 400)
    data = await exchange_code_for_tokens(tenant_id, code)
    return data

class SearchResponse(BaseModel):
    items: list[dict] = Field(default_factory=list)

# PUBLIC_INTERFACE
@router.get("/search", response_model=SearchResponse, summary="Search Jira issues", tags=["jira"])
async def search(q: str = Query(..., alias="q"), resource: str = "issue", page: int = 1, per_page: int = 20, tenant_id: str = Depends(get_tenant_id)):
    """Search issues by JQL and return normalized items."""
    if resource != "issue":
        http_error("VALIDATION", "Unsupported resource", 400)
    res = await search_issues(tenant_id, q, page, per_page)
    return {"items": res.get("items", [])}

class CreateIssueBody(BaseModel):
    project_key: str
    summary: str
    description: str | None = None
    issue_type: str | None = "Task"

# PUBLIC_INTERFACE
@router.post("/issues", summary="Create Jira issue", tags=["jira"])
async def create_issue_route(body: CreateIssueBody, tenant_id: str = Depends(get_tenant_id)):
    """Create a Jira issue with minimal fields and return normalized summary."""
    res = await create_issue(tenant_id, body.model_dump())
    if res.get("status") == "error":
        http_error(res["code"], res.get("message", "Error"), 400)
    return res

class JiraConnector(BaseConnector):
    id = "jira"
    display_name = "Jira"
    supports_oauth = True
    required_scopes = JIRA_SCOPES

    async def oauth_authorize_url(self, tenant_id: str, state: str):
        return await build_authorize_url(state)

    async def oauth_exchange(self, tenant_id: str, code: str, state: str):
        return await exchange_code_for_tokens(tenant_id, code)

    async def search(self, tenant_id: str, query: str, resource: str, page: int = 1, per_page: int = 20):
        if resource != "issue":
            return {"items": []}
        return await search_issues(tenant_id, query, page, per_page)

    async def create(self, tenant_id: str, resource: str, payload: dict):
        if resource != "issue":
            return {"status": "error", "code": "VALIDATION", "message": "Unsupported resource"}
        return await create_issue(tenant_id, payload)

# register connector and router at import time
register(JiraConnector(), router)
