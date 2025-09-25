from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


ConnectorType = Literal["jira", "confluence"]


class OAuthState(BaseModel):
    access_token: Optional[str] = Field(default=None, description="Encrypted access token")
    refresh_token: Optional[str] = Field(default=None, description="Encrypted refresh token")
    expires_at: Optional[datetime] = Field(default=None, description="Token expiry timestamp")
    scope: Optional[str] = Field(default=None, description="Granted scope string")


class ConnectorMeta(BaseModel):
    oauth: OAuthState = Field(default_factory=OAuthState)
    last_sync_at: Optional[datetime] = Field(default=None)
    status: Literal["not_configured", "linked", "error"] = Field(default="not_configured")
    extra: Dict[str, Any] = Field(default_factory=dict)


class ConnectorRecord(BaseModel):
    id: str = Field(..., description="Connector id (e.g., 'jira', 'confluence')")
    type: ConnectorType = Field(..., description="Connector type")
    name: str = Field(..., description="Human readable name")
    tenant_id: str = Field(..., description="Tenant scope")
    meta: ConnectorMeta = Field(default_factory=ConnectorMeta)
