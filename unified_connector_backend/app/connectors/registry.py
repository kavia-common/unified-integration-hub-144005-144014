from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from .base import BaseConnector, NormalizedItem, CreateResult
from pydantic import BaseModel, Field

_registry: Dict[str, BaseConnector] = {}

# PUBLIC_INTERFACE
def register(connector: BaseConnector):
    """Register a connector in the in-memory registry."""
    _registry[connector.id] = connector

# PUBLIC_INTERFACE
def list_connectors() -> List[Dict]:
    """Return connector definitions."""
    return [
        {
            "id": c.id,
            "display_name": c.display_name,
            "supports_oauth": c.supports_oauth,
            "required_scopes": c.required_scopes,
        }
        for c in _registry.values()
    ]

# PUBLIC_INTERFACE
def get_connector(id: str) -> BaseConnector:
    """Get a registered connector instance by id."""
    if id not in _registry:
        raise KeyError(id)
    return _registry[id]

class TenantContext(BaseModel):
    tenant_id: str = Field(..., description="Tenant identifier")

def get_tenant(tenant_id: Optional[str] = Query(None, description="Tenant id for multi-tenant scoping")) -> TenantContext:
    if not tenant_id:
        # For MVP we allow a default; production must enforce auth/tenant
        tenant_id = "demo-tenant"
    return TenantContext(tenant_id=tenant_id)

def make_connectors_router() -> APIRouter:
    router = APIRouter()

    @router.get("/connectors", summary="List connectors", description="Lists available connectors and basic info.", response_model=List[Dict])
    async def list_all(_tenant: TenantContext = Depends(get_tenant)):
        return list_connectors()

    return router
