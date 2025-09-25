from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class OAuthLoginResponse(BaseModel):
    auth_url: str = Field(..., description="URL to redirect user to start OAuth flow")
    state: Optional[str] = Field(default=None, description="Opaque state value to validate callback")


class SearchResponse(BaseModel):
    results: list[dict] = Field(default_factory=list, description="Results returned from connector search")


class Paging(BaseModel):
    page: int = Field(1, description="Current page number (1-based)")
    per_page: int = Field(10, description="Items per page")
    total: Optional[int] = Field(default=None, description="Total number of items if known")
    next_page: Optional[int] = Field(default=None, description="Next page number if available")
    prev_page: Optional[int] = Field(default=None, description="Previous page number if available")


class SearchParams(BaseModel):
    """Normalized search parameters accepted by all connectors."""
    q: str = Field(..., description="Free text query")
    resource_type: Optional[str] = Field(default=None, description="Filter by resource type (e.g., 'issues','projects','pages','spaces')")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Connector-specific filter map (e.g., projectKey, spaceKey)")
    page: int = Field(1, ge=1, description="Page number (1-based)")
    per_page: int = Field(10, ge=1, le=100, description="Items per page (max 100)")


# PUBLIC_INTERFACE
class BaseConnector(ABC):
    """Abstract base class for all connectors."""

    id: str
    name: str

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    # PUBLIC_INTERFACE
    @abstractmethod
    def get_public_info(self) -> Dict[str, Any]:
        """Return public descriptor info: id, name, status hints."""
        raise NotImplementedError

    # PUBLIC_INTERFACE
    @abstractmethod
    async def oauth_login(self, redirect_to: Optional[str] = None) -> OAuthLoginResponse:
        """Start OAuth flow for the connector and return the authorization URL."""
        raise NotImplementedError

    # PUBLIC_INTERFACE
    @abstractmethod
    async def oauth_callback(self, code: str, state: Optional[str]) -> Dict[str, Any]:
        """Complete OAuth by exchanging code for tokens. Store securely in tenant storage."""
        raise NotImplementedError

    # PUBLIC_INTERFACE
    @abstractmethod
    async def search(self, params: SearchParams) -> Dict[str, Any]:
        """Search within the connector's data domain and return normalized paginated payload:
        { status:'ok', data:{ items:[...], paging:{ page, per_page, total?, next_page?, prev_page? } }, meta:{...}}
        """
        raise NotImplementedError

    # PUBLIC_INTERFACE
    @abstractmethod
    async def connect(self) -> Dict[str, Any]:
        """Establish connection using stored credentials/config."""
        raise NotImplementedError

    # PUBLIC_INTERFACE
    @abstractmethod
    async def disconnect(self) -> Dict[str, Any]:
        """Remove token/config and disconnect."""
        raise NotImplementedError
