from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypedDict

class NormalizedItem(TypedDict, total=False):
    id: str
    title: str
    url: str
    type: str
    subtitle: str

class BaseConnector(ABC):
    id: str
    display_name: str
    supports_oauth: bool = True
    required_scopes: List[str] = []

    # PUBLIC_INTERFACE
    @abstractmethod
    async def oauth_authorize_url(self, tenant_id: str, state: str) -> Dict[str, Any]:
        """Return provider authorization URL and additional data."""

    # PUBLIC_INTERFACE
    @abstractmethod
    async def oauth_exchange(self, tenant_id: str, code: str, state: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens and persist connection."""

    # PUBLIC_INTERFACE
    @abstractmethod
    async def search(self, tenant_id: str, query: str, resource: str, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Search resources and return normalized items."""

    # PUBLIC_INTERFACE
    @abstractmethod
    async def create(self, tenant_id: str, resource: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a resource and return a normalized summary."""

    # PUBLIC_INTERFACE
    async def list_options(self, tenant_id: str, resource: str) -> Dict[str, Any]:
        """List helper options like projects/spaces."""
        return {"items": []}

    # PUBLIC_INTERFACE
    async def disconnect(self, tenant_id: str) -> Dict[str, Any]:
        """Revoke and delete connection."""
        return {"status": "ok"}
