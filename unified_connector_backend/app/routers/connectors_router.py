from fastapi import APIRouter, Depends, Query
from ..connectors.registry import list_connectors, get_connector
from pydantic import BaseModel, Field

router = APIRouter()

def get_tenant_id():
    # In production, derive from auth/session headers. For now, accept a header or default demo.
    # This is kept simple for scaffolding.
    return "demo-tenant"

class ConnectorsListResponse(BaseModel):
    items: list[dict] = Field(..., description="Registered connectors")

# PUBLIC_INTERFACE
@router.get("", response_model=ConnectorsListResponse, summary="List registered connectors", tags=["connectors"])
def connectors_list():
    """Return registered connectors with metadata."""
    return {"items": list_connectors()}

class SearchResponse(BaseModel):
    items: list[dict] = Field(..., description="Normalized items")
    page: int = 1
    per_page: int = 20

# PUBLIC_INTERFACE
@router.get("/{connector_id}/search", response_model=SearchResponse, summary="Search resources", tags=["connectors"])
async def generic_search(connector_id: str, q: str = Query(..., alias="q"), resource: str = "issue", page: int = 1, per_page: int = 20, tenant_id: str = Depends(get_tenant_id)):
    """Proxy to connector search and return normalized list."""
    connector = get_connector(connector_id)
    if not connector:
        return {"items": [], "page": page, "per_page": per_page}
    data = await connector.search(tenant_id, q, resource, page, per_page)
    return {"items": data.get("items", []), "page": page, "per_page": per_page}
