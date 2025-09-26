import os
import secrets
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..connectors.registry import make_connectors_router, get_connector, get_tenant, TenantContext, list_connectors
from ..connectors.jira import JiraConnector
from ..connectors.confluence import ConfluenceConnector
from ..db.mongo import delete_connection

# Instantiate and register connectors once.
JIRA = JiraConnector()
CONFLUENCE = ConfluenceConnector()

router = APIRouter()
router.include_router(make_connectors_router())

# Simple in-memory state store for MVP; replace with Redis in prod
STATE_STORE: Dict[str, str] = {}

class OAuthLoginResponse(BaseModel):
    authorize_url: str = Field(..., description="URL to redirect user for provider OAuth")
    state: str = Field(..., description="CSRF state")

# PUBLIC_INTERFACE
@router.get("/connectors/{connector_id}/oauth/login", response_model=OAuthLoginResponse, summary="Start OAuth login", description="Begins OAuth flow for a connector and returns the provider authorize URL.")
async def oauth_login(connector_id: str, return_url: Optional[str] = Query(None), tenant: TenantContext = Depends(get_tenant)):
    """Start OAuth flow by creating a CSRF state and composing provider URL."""
    try:
        connector = get_connector(connector_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Connector not found")
    if not connector.supports_oauth:
        raise HTTPException(status_code=400, detail="Connector does not support OAuth")
    state = secrets.token_urlsafe(24)
    # Store mapping tenant->state
    STATE_STORE[state] = tenant.tenant_id
    auth = await connector.get_oauth_authorize_url(tenant.tenant_id, state)
    return OAuthLoginResponse(authorize_url=auth.authorize_url, state=state)

class OAuthCallbackResponse(BaseModel):
    status: str = "ok"

# PUBLIC_INTERFACE
@router.get("/connectors/{connector_id}/oauth/callback", response_model=OAuthCallbackResponse, summary="OAuth callback", description="Handles provider callback with code/state and stores credentials.")
async def oauth_callback(connector_id: str, code: str = Query(...), state: str = Query(...)):
    """Process provider callback: validate state, exchange code."""
    tenant_id = STATE_STORE.pop(state, None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Invalid state")
    try:
        connector = get_connector(connector_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Connector not found")
    await connector.exchange_code_for_tokens(tenant_id, code, state)
    return OAuthCallbackResponse()

class SearchResponse(BaseModel):
    items: List[Dict[str, Any]]

# PUBLIC_INTERFACE
@router.get("/connectors/{connector_id}/search", response_model=SearchResponse, summary="Search", description="Normalized search for resources.")
async def search(connector_id: str, q: str = Query(..., description="Query string"), resource: str = Query(..., description="Resource type"), page: int = 1, per_page: int = 20, tenant: TenantContext = Depends(get_tenant)):
    """Search resources for a connector with normalized results."""
    try:
        connector = get_connector(connector_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Connector not found")
    try:
        return await connector.search(tenant.tenant_id, q, resource, page, per_page)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class JiraCreateIssue(BaseModel):
    project_key: str = Field(..., description="Jira project key")
    summary: str = Field(..., description="Issue summary")
    description: Optional[str] = Field(None, description="Issue description")

class ConfluenceCreatePage(BaseModel):
    space_key: str = Field(..., description="Confluence space key")
    title: str = Field(..., description="Page title")
    body: Optional[str] = Field("", description="Page body (storage)")

# PUBLIC_INTERFACE
@router.post("/connectors/jira/issues", summary="Create Jira issue", description="Create a Jira issue with normalized response.")
async def create_jira_issue(payload: JiraCreateIssue, tenant: TenantContext = Depends(get_tenant)):
    connector = JIRA
    try:
        res = await connector.create(tenant.tenant_id, "issue", payload.dict())
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# PUBLIC_INTERFACE
@router.post("/connectors/confluence/pages", summary="Create Confluence page", description="Create a Confluence page with normalized response.")
async def create_conf_page(payload: ConfluenceCreatePage, tenant: TenantContext = Depends(get_tenant)):
    connector = CONFLUENCE
    try:
        res = await connector.create(tenant.tenant_id, "page", payload.dict())
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# PUBLIC_INTERFACE
@router.get("/connectors/jira/projects", summary="List Jira projects", description="Supporting list for Jira projects.")
async def list_jira_projects(tenant: TenantContext = Depends(get_tenant)):
    try:
        return await JIRA.list_supporting(tenant.tenant_id, "projects")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# PUBLIC_INTERFACE
@router.get("/connectors/confluence/spaces", summary="List Confluence spaces", description="Supporting list for Confluence spaces.")
async def list_conf_spaces(tenant: TenantContext = Depends(get_tenant)):
    try:
        return await CONFLUENCE.list_supporting(tenant.tenant_id, "spaces")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# PUBLIC_INTERFACE
@router.delete("/connectors/{connector_id}/connection", summary="Delete connection", description="Revoke and remove stored credentials for a connector.")
async def delete_conn(connector_id: str, tenant: TenantContext = Depends(get_tenant)):
    try:
        get_connector(connector_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Connector not found")
    await delete_connection(tenant.tenant_id, connector_id)
    return {"status": "ok"}
