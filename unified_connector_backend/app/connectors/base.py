from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class NormalizedItem(BaseModel):
    id: str = Field(..., description="Stable id/key")
    title: str = Field(..., description="Human-readable title")
    url: Optional[str] = Field(None, description="Direct URL to the resource")
    type: str = Field(..., description="Resource type")
    subtitle: Optional[str] = Field(None, description="Additional context")

class CreateResult(BaseModel):
    id: str = Field(..., description="Created resource id/key")
    title: str = Field(..., description="Title")
    url: Optional[str] = Field(None, description="Direct URL")
    type: str = Field(..., description="Resource type")

class ConnectorError(BaseModel):
    status: str = "error"
    code: str
    message: str
    retry_after: Optional[int] = None

class OAuthAuthorize(BaseModel):
    authorize_url: str
    state: str

class BaseConnector:
    id: str
    display_name: str
    supports_oauth: bool = True
    required_scopes: List[str] = []

    # PUBLIC_INTERFACE
    async def get_oauth_authorize_url(self, tenant_id: str, state: str) -> OAuthAuthorize:
        """Return provider authorization URL and state."""
        raise NotImplementedError

    # PUBLIC_INTERFACE
    async def exchange_code_for_tokens(self, tenant_id: str, code: str, state: str) -> Dict[str, Any]:
        """Exchange auth code for tokens and store credentials."""
        raise NotImplementedError

    # PUBLIC_INTERFACE
    async def search(self, tenant_id: str, query: str, resource: str, page: int = 1, per_page: int = 20) -> Dict[str, List[NormalizedItem]]:
        """Perform normalized search."""
        raise NotImplementedError

    # PUBLIC_INTERFACE
    async def create(self, tenant_id: str, resource: str, payload: Dict[str, Any]) -> CreateResult:
        """Create a resource normalized result."""
        raise NotImplementedError

    # PUBLIC_INTERFACE
    async def list_supporting(self, tenant_id: str, resource: str) -> List[Dict[str, Any]]:
        """Support paths like Jira projects, Confluence spaces."""
        raise NotImplementedError
