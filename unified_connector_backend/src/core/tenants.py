from __future__ import annotations

from fastapi import Header

from src.core.settings import get_settings


# PUBLIC_INTERFACE
def get_tenant_id(x_tenant_id: str | None = Header(default=None, alias=None)) -> str:
    """Resolve tenant ID from X-Tenant-ID header; falls back to default if missing."""
    settings = get_settings()
    # We set alias None to capture raw header; use configured header name if future override
    tenant_id = x_tenant_id or settings.tenant.DEFAULT_TENANT_ID
    return tenant_id
