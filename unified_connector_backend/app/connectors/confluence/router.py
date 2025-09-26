from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from ...connectors.base import BaseConnector
from .client import build_authorize_url, exchange_code_for_tokens, search_pages, create_page, CONF_SCOPES
from ...connectors.registry import register
from ...utils.errors import http_error

router = APIRouter()

def get_tenant_id():
    return "demo-tenant"

class OAuthLoginResponse(BaseModel):
    authorize_url: str
    state: str

# PUBLIC_INTERFACE
@router.get("/oauth/login", response_model=OAuthLoginResponse, tags=["oauth"], summary="Start Confluence OAuth")
async def oauth_login(tenant_id: str = Depends(get_tenant_id), return_url: bool = True):
    """Build and return the Confluence OAuth authorization URL."""
    state = f"{tenant_id}-state"
    data = await build_authorize_url(state)
    return OAuthLoginResponse(**data)

# PUBLIC_INTERFACE
@router.get("/oauth/callback", tags=["oauth"], summary="Confluence OAuth callback")
async def oauth_callback(state: str, code: str, tenant_id: str = Depends(get_tenant_id)):
    """Handle OAuth callback for Confluence."""
    if not state or tenant_id not in state:
        http_error("CSRF", "Invalid state", 400)
    data = await exchange_code_for_tokens(tenant_id, code)
    return data

class SearchResponse(BaseModel):
    items: list[dict] = Field(default_factory=list)

# PUBLIC_INTERFACE
@router.get("/search", response_model=SearchResponse, tags=["confluence"], summary="Search Confluence pages")
async def search(q: str = Query(..., alias="q"), resource: str = "page", page: int = 1, per_page: int = 20, tenant_id: str = Depends(get_tenant_id)):
    """Search Confluence pages and return normalized items."""
    if resource != "page":
        http_error("VALIDATION", "Unsupported resource", 400)
    res = await search_pages(tenant_id, q, page, per_page)
    return {"items": res.get("items", [])}

class CreatePageBody(BaseModel):
    space_key: str
    title: str
    body: str | None = ""

# PUBLIC_INTERFACE
@router.post("/pages", tags=["confluence"], summary="Create Confluence page")
async def create_page_route(body: CreatePageBody, tenant_id: str = Depends(get_tenant_id)):
    """Create a Confluence page with minimal fields."""
    res = await create_page(tenant_id, body.model_dump())
    if res.get("status") == "error":
        http_error(res["code"], res.get("message", "Error"), 400)
    return res

class ConfluenceConnector(BaseConnector):
    id = "confluence"
    display_name = "Confluence"
    supports_oauth = True
    required_scopes = CONF_SCOPES

    async def oauth_authorize_url(self, tenant_id: str, state: str):
        return await build_authorize_url(state)

    async def oauth_exchange(self, tenant_id: str, code: str, state: str):
        return await exchange_code_for_tokens(tenant_id, code)

    async def search(self, tenant_id: str, query: str, resource: str, page: int = 1, per_page: int = 20):
        if resource != "page":
            return {"items": []}
        return await search_pages(tenant_id, query, page, per_page)

    async def create(self, tenant_id: str, resource: str, payload: dict):
        if resource != "page":
            return {"status": "error", "code": "VALIDATION", "message": "Unsupported resource"}
        return await create_page(tenant_id, payload)

register(ConfluenceConnector(), router)
