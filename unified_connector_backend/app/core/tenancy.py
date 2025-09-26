# PUBLIC_INTERFACE
"""
Tenant context utilities and FastAPI dependency to enforce multi-tenancy via X-Tenant-Id header.
"""
from __future__ import annotations

from fastapi import Header, Depends
from pydantic import BaseModel, Field
from .settings import get_settings


# PUBLIC_INTERFACE
class TenantContext(BaseModel):
    """Represents the request's tenant context."""
    tenant_id: str = Field(..., description="Tenant identifier (from X-Tenant-Id header)")


# PUBLIC_INTERFACE
def tenant_dep(x_tenant_id: str = Header(..., alias="X-Tenant-Id")) -> TenantContext:
    """FastAPI dependency to extract tenant id or reject request."""
    settings = get_settings()
    # Additional validation could be added here. For now, just require non-empty.
    if not x_tenant_id or not x_tenant_id.strip():
        # Raising here will be captured by FastAPI and returned as validation error.
        from .errors import http_error, ErrorCode
        raise http_error(400, ErrorCode.VALIDATION, f"Missing or empty {settings.tenant_header} header")
    return TenantContext(tenant_id=x_tenant_id.strip())
