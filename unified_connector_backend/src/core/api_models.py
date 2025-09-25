from __future__ import annotations

from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Paging(BaseModel):
    """Standard pagination model used by list/search endpoints."""
    page: int = Field(1, description="Current page number (1-based)")
    per_page: int = Field(10, description="Items per page")
    total: Optional[int] = Field(default=None, description="Total items if known")
    next_page: Optional[int] = Field(default=None, description="Next page number if available")
    prev_page: Optional[int] = Field(default=None, description="Previous page number if available")
    # Some Atlassian APIs use cursor; include optional field for connectors that surface cursors
    next_cursor: Optional[str] = Field(default=None, description="Opaque cursor for fetching next page, if provided by upstream")


class ErrorResponse(BaseModel):
    """Standardized error payload for all endpoints."""
    status: str = Field("error", description="Error status, always 'error'")
    code: str = Field(..., description="Machine-readable error code (e.g., AUTH_REQUIRED, VALIDATION_ERROR, UPSTREAM_ERROR)")
    message: str = Field(..., description="Human-readable description of the error")
    retry_after: Optional[float] = Field(default=None, description="Seconds to wait before retrying (for rate limiting)")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional structured, safe-to-log error details")
    http_status: Optional[int] = Field(default=None, description="HTTP status observed from upstream or local decision")


class OAuthLogin(BaseModel):
    """Response body for starting OAuth flow."""
    auth_url: str = Field(..., description="URL to redirect user to start OAuth flow")
    state: Optional[str] = Field(default=None, description="Opaque state value to validate callback")


class ConnectorStatusModel(BaseModel):
    """Status details for a connector on GET /connectors."""
    connected: bool = Field(..., description="True if connector is linked/configured for this tenant")
    last_refreshed: Optional[str] = Field(default=None, description="ISO timestamp when tokens/connection were last refreshed or linked")
    last_error: Optional[str] = Field(default=None, description="Last error message observed for this connector, if any")
    scopes: List[str] = Field(default_factory=list, description="Active scopes/permissions granted for this connection")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional connector metadata (e.g., cloud_id)")


class ConnectorListItemModel(BaseModel):
    """Connector descriptor merged with per-tenant status."""
    id: str = Field(..., description="Connector id")
    name: str = Field(..., description="Connector name")
    tags: List[str] = Field(default_factory=list, description="Tags/categories")
    status: ConnectorStatusModel = Field(..., description="Per-tenant connection status")


class JiraIssueCreateModel(BaseModel):
    """Payload to create a Jira issue."""
    project_key: str = Field(..., description="Project key (e.g., ABC)")
    summary: str = Field(..., description="Issue summary/title")
    issuetype: str = Field(default="Task", description="Issue type name")
    description: Optional[str] = Field(default=None, description="Optional issue description")


class ConfluenceCreatePageModel(BaseModel):
    """Payload to create a Confluence page."""
    space_key: str = Field(..., description="Confluence space key")
    title: str = Field(..., description="Page title")
    body: str = Field(..., description="Page body in storage representation")


class JiraIssueCreated(BaseModel):
    """Minimal normalized response when an issue is created."""
    id: Optional[str] = Field(default=None, description="Created issue id")
    key: Optional[str] = Field(default=None, description="Created issue key")


class ConfluencePageCreated(BaseModel):
    """Minimal normalized response when a page is created."""
    id: Optional[str] = Field(default=None, description="Created page id")
    title: Optional[str] = Field(default=None, description="Created page title")


class NormalizedItems(BaseModel, Generic[T]):
    """Normalized list wrapper with paging."""
    items: List[T] = Field(default_factory=list, description="List of items")
    paging: Paging = Field(default_factory=Paging, description="Paging metadata")


class SuccessResponse(BaseModel, Generic[T]):
    """Standardized success payload wrapper."""
    status: str = Field("ok", description="Success status, always 'ok'")
    data: T = Field(..., description="Response data")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata associated with the response")


# Convenience alias types for commonly returned shapes

class OAuthLoginSuccess(SuccessResponse[OAuthLogin]):  # type: ignore[type-arg]
    pass


class ConnectDisconnectResult(BaseModel):
    connected: Optional[bool] = Field(default=None, description="True if connector is connected")
    disconnected: Optional[bool] = Field(default=None, description="True if connector is disconnected")
    message: Optional[str] = Field(default=None, description="Informational message (e.g., 'OAuth linked')")


class ConnectDisconnectSuccess(SuccessResponse[ConnectDisconnectResult]):  # type: ignore[type-arg]
    pass


class ConnectorListSuccess(SuccessResponse[List[ConnectorListItemModel]]):  # type: ignore[type-arg]
    pass


class GenericItemsSuccess(SuccessResponse[NormalizedItems[Dict[str, Any]]]):  # type: ignore[type-arg]
    pass


class JiraIssueCreateSuccess(SuccessResponse[JiraIssueCreated]):  # type: ignore[type-arg]
    pass


class ConfluencePageCreateSuccess(SuccessResponse[ConfluencePageCreated]):  # type: ignore[type-arg]
    pass
