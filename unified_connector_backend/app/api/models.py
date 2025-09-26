# PUBLIC_INTERFACE
"""
Shared API models: unified response envelopes and requests.
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


# PUBLIC_INTERFACE
class Envelope(BaseModel):
    """Standard success response envelope."""
    status: str = Field(default="ok")
    data: Any = Field(default=None)


# PUBLIC_INTERFACE
class OAuthStartResponse(BaseModel):
    """OAuth start response."""
    authorize_url: str = Field(..., description="URL to redirect the user to")
    state: str = Field(..., description="Opaque state included in callback")


# PUBLIC_INTERFACE
class PatCredentials(BaseModel):
    """PAT/API token credentials for connectors."""
    site_url: Optional[str] = Field(default=None, description="Base site URL")
    email: str = Field(..., description="Account email/username where applicable")
    api_token: str = Field(..., description="Personal Access Token or API Key (never logged)")


# PUBLIC_INTERFACE
class SearchResponse(BaseModel):
    """Normalized search results."""
    items: List[Dict[str, Any]]
    page: int
    per_page: int


# PUBLIC_INTERFACE
class CreateJiraIssueRequest(BaseModel):
    """Payload for creating a Jira issue."""
    project_key: str = Field(..., description="Project key, e.g., DEMO")
    summary: str = Field(..., description="Issue summary/title")
    description: Optional[str] = Field(default=None, description="Issue description")


# PUBLIC_INTERFACE
class CreateConfluencePageRequest(BaseModel):
    """Payload for creating a Confluence page."""
    space_key: str = Field(..., description="Space key, e.g., SPACE")
    title: str = Field(..., description="Page title")
    body: Optional[str] = Field(default=None, description="Page body content (simplified)")
