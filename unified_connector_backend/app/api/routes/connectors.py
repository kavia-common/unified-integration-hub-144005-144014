# PUBLIC_INTERFACE
"""
Connectors endpoints:
- GET /api/connectors
- GET /api/connectors/{id}/oauth/login
- GET /api/connectors/{id}/oauth/callback
- POST /api/connectors/{id}/pat/validate
- GET /api/connectors/{id}/search
- POST /api/connectors/jira/issues
- POST /api/connectors/confluence/pages
- GET /api/connectors/jira/projects
- GET /api/connectors/confluence/spaces
- DELETE /api/connectors/{id}/connection
"""
from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, Query
from typing import Optional

from ...core.tenancy import tenant_dep, TenantContext
from ...core.errors import http_error, ErrorCode
from ...core.logging import info
from ...core.token_store import token_store
from ...connectors.registry import connectors_registry
from ...api.models import (
    Envelope,
    OAuthStartResponse,
    PatCredentials,
    SearchResponse,
    CreateJiraIssueRequest,
    CreateConfluencePageRequest,
)

router = APIRouter(prefix="/api/connectors", tags=["connectors"])


@router.get("", summary="List available connectors", response_model=Envelope)
def list_connectors(tenant: TenantContext = Depends(tenant_dep)):
    """Return registered connectors with connection status for the tenant."""
    reg = connectors_registry()
    items = reg.list()
    # augment with connection status
    statuses = token_store().list_connectors_for_tenant(tenant.tenant_id)
    for it in items:
        it["status"] = statuses.get(it["id"], "disconnected")
    info("Listed connectors", tenant_id=tenant.tenant_id)
    return Envelope(data=items)


@router.get("/{connector_id}/oauth/login", summary="Start OAuth flow", response_model=OAuthStartResponse)
def oauth_login(connector_id: str, tenant: TenantContext = Depends(tenant_dep), return_url: Optional[bool] = Query(default=True)):
    """Return the vendor authorize URL for redirection."""
    conn = connectors_registry().get(connector_id)
    if not conn:
        raise http_error(404, ErrorCode.NOT_FOUND, "Connector not found")
    state = str(uuid.uuid4())
    res = conn.get_oauth_authorize_url(tenant.tenant_id, state)
    return OAuthStartResponse(**res)


@router.get("/{connector_id}/oauth/callback", summary="OAuth callback", response_model=Envelope)
def oauth_callback(connector_id: str, code: str, state: str, tenant: TenantContext = Depends(tenant_dep)):
    """Callback to exchange code for tokens and store credentials."""
    conn = connectors_registry().get(connector_id)
    if not conn:
        raise http_error(404, ErrorCode.NOT_FOUND, "Connector not found")
    result = conn.exchange_code_for_tokens(tenant.tenant_id, code, state)
    return Envelope(data=result)


@router.post("/{connector_id}/pat/validate", summary="Validate PAT/API key", response_model=Envelope)
def pat_validate(connector_id: str, body: PatCredentials, tenant: TenantContext = Depends(tenant_dep)):
    """Validate PAT/API key credentials and store if valid."""
    conn = connectors_registry().get(connector_id)
    if not conn:
        raise http_error(404, ErrorCode.NOT_FOUND, "Connector not found")
    ok = conn.validate_pat(tenant.tenant_id, body.model_dump())
    if not ok:
        raise http_error(400, ErrorCode.VALIDATION, "Invalid credentials")
    return Envelope(data={"status": "connected"})


@router.get("/{connector_id}/search", summary="Search items", response_model=SearchResponse)
def search_items(
    connector_id: str,
    q: str = Query(..., alias="q", description="Search query"),
    resource: str = Query(..., description="Resource type, e.g., issue|page"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    tenant: TenantContext = Depends(tenant_dep),
):
    """Search normalized items for the connector."""
    conn = connectors_registry().get(connector_id)
    if not conn:
        raise http_error(404, ErrorCode.NOT_FOUND, "Connector not found")
    return conn.search(tenant.tenant_id, q, resource, page=page, per_page=per_page)  # type: ignore[return-value]


@router.post("/jira/issues", summary="Create Jira issue", response_model=Envelope)
def create_jira_issue(body: CreateJiraIssueRequest, tenant: TenantContext = Depends(tenant_dep)):
    """Create a Jira issue with normalized result."""
    conn = connectors_registry().get("jira")
    if not conn:
        raise http_error(404, ErrorCode.NOT_FOUND, "Connector not found")
    res = conn.create(tenant.tenant_id, "issue", body.model_dump())
    return Envelope(data=res.model_dump())


@router.post("/confluence/pages", summary="Create Confluence page", response_model=Envelope)
def create_confluence_page(body: CreateConfluencePageRequest, tenant: TenantContext = Depends(tenant_dep)):
    """Create a Confluence page with normalized result."""
    conn = connectors_registry().get("confluence")
    if not conn:
        raise http_error(404, ErrorCode.NOT_FOUND, "Connector not found")
    res = conn.create(tenant.tenant_id, "page", body.model_dump())
    return Envelope(data=res.model_dump())


@router.get("/jira/projects", summary="List Jira projects", response_model=Envelope)
def list_jira_projects(tenant: TenantContext = Depends(tenant_dep)):
    """List Jira projects."""
    conn = connectors_registry().get("jira")
    if not conn:
        raise http_error(404, ErrorCode.NOT_FOUND, "Connector not found")
    data = conn.list_collections(tenant.tenant_id, "projects")
    return Envelope(data=data)


@router.get("/confluence/spaces", summary="List Confluence spaces", response_model=Envelope)
def list_confluence_spaces(tenant: TenantContext = Depends(tenant_dep)):
    """List Confluence spaces."""
    conn = connectors_registry().get("confluence")
    if not conn:
        raise http_error(404, ErrorCode.NOT_FOUND, "Connector not found")
    data = conn.list_collections(tenant.tenant_id, "spaces")
    return Envelope(data=data)


@router.delete("/{connector_id}/connection", summary="Delete connection", response_model=Envelope)
def delete_connection(connector_id: str, tenant: TenantContext = Depends(tenant_dep)):
    """Delete stored credentials for a connector."""
    deleted = token_store().delete(tenant.tenant_id, connector_id)
    if not deleted:
        raise http_error(404, ErrorCode.NOT_FOUND, "No active connection found")
    return Envelope(data={"deleted": True})
