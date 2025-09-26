# PUBLIC_INTERFACE
"""
Connections endpoints (container-level operations, comments, webhooks).

For MVP demo, these endpoints return stubbed data with unified envelopes.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from ...core.tenancy import tenant_dep, TenantContext
from ...api.models import Envelope

router = APIRouter(prefix="/api/connections", tags=["connections"])


@router.get("", summary="List active connections", response_model=Envelope)
def list_connections(tenant: TenantContext = Depends(tenant_dep)):
    """Return active connections for the tenant (from in-memory store)."""
    from ...core.token_store import token_store
    statuses = token_store().list_connectors_for_tenant(tenant.tenant_id)
    data = [{"connector_id": cid, "status": status} for cid, status in statuses.items()]
    return Envelope(data=data)


@router.post("/{connector_id}/webhooks", summary="Register webhook (stub)", response_model=Envelope)
def register_webhook(connector_id: str, tenant: TenantContext = Depends(tenant_dep)):
    """Register a webhook for a connector (stubbed)."""
    return Envelope(data={"registered": True})


@router.delete("/{connector_id}/webhooks/{webhook_id}", summary="Delete webhook (stub)", response_model=Envelope)
def delete_webhook(connector_id: str, webhook_id: str, tenant: TenantContext = Depends(tenant_dep)):
    """Delete a webhook (stubbed)."""
    return Envelope(data={"deleted": True})


@router.post("/{connector_id}/items/{item_id}/comments", summary="Add comment to item (stub)", response_model=Envelope)
def add_comment(connector_id: str, item_id: str, tenant: TenantContext = Depends(tenant_dep)):
    """Add a comment to an item (stubbed)."""
    return Envelope(data={"commented": True})
