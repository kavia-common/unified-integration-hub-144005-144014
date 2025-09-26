# PUBLIC_INTERFACE
"""
Base connector interface and common models.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol
from pydantic import BaseModel, Field


# PUBLIC_INTERFACE
class NormalizedItem(BaseModel):
    """Unified search/create item format across connectors."""
    id: str = Field(..., description="Connector-specific unique identifier")
    title: str = Field(..., description="Display title / summary")
    url: str = Field(..., description="Link to the item on the vendor system")
    type: str = Field(..., description="Type, e.g., 'issue' or 'page'")
    subtitle: Optional[str] = Field(default=None, description="Optional subtitle")


# PUBLIC_INTERFACE
class CreateResult(BaseModel):
    """Unified create result format."""
    item: NormalizedItem


# PUBLIC_INTERFACE
class BaseConnector(Protocol):
    """Protocol every connector must follow."""

    id: str
    display_name: str
    supports_oauth: bool
    required_scopes: List[str]

    # PUBLIC_INTERFACE
    def get_oauth_authorize_url(self, tenant_id: str, state: str) -> Dict[str, str]:
        """Return an authorization URL to initiate OAuth flow."""
        ...

    # PUBLIC_INTERFACE
    def exchange_code_for_tokens(self, tenant_id: str, code: str, state: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens and store credentials."""
        ...

    # PUBLIC_INTERFACE
    def validate_pat(self, tenant_id: str, credentials: Dict[str, Any]) -> bool:
        """Validate PAT/API key credentials and store if valid."""
        ...

    # PUBLIC_INTERFACE
    def search(self, tenant_id: str, query: str, resource: str, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Search vendor items and return normalized items."""
        ...

    # PUBLIC_INTERFACE
    def create(self, tenant_id: str, resource: str, payload: Dict[str, Any]) -> CreateResult:
        """Create a vendor resource and return normalized result."""
        ...

    # PUBLIC_INTERFACE
    def list_collections(self, tenant_id: str, resource: str) -> Dict[str, Any]:
        """List supporting collections like projects/spaces."""
        ...
