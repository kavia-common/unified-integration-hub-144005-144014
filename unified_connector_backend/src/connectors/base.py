from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class OAuthLoginResponse(BaseModel):
    auth_url: str = Field(..., description="URL to redirect user to start OAuth flow")
    state: Optional[str] = Field(default=None, description="Opaque state value to validate callback")


class SearchResponse(BaseModel):
    results: list[dict] = Field(default_factory=list, description="Results returned from connector search")


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
    async def search(self, query: str) -> SearchResponse:
        """Search within the connector's data domain (stub)."""
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
