from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class Credentials(BaseModel):
    access_token: Optional[str] = Field(default=None, description="Encrypted access token")
    refresh_token: Optional[str] = Field(default=None, description="Encrypted refresh token")
    token_expires_at: Optional[datetime] = Field(default=None, description="Expiry time")
    site_url: Optional[str] = Field(default=None, description="Vendor site/cloud URL")
    scopes: Optional[list[str]] = Field(default=None, description="Granted scopes")

class Connection(BaseModel):
    tenant_id: str = Field(..., description="Tenant identifier")
    connector_id: str = Field(..., description="Connector ID, e.g., 'jira', 'confluence'")
    credentials: Credentials = Field(default_factory=Credentials)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    refreshed_at: Optional[datetime] = None
    last_error: Optional[str] = None
