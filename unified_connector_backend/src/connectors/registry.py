from __future__ import annotations

from typing import Callable, Dict, List, Optional, Any

from fastapi import APIRouter, Depends, FastAPI, Query
from pydantic import BaseModel, Field
import json

from src.core.tenants import get_tenant_id
from src.connectors.base import BaseConnector, SearchParams
from src.core.response import ok, validation_error
from src.core.db import tenant_collection
from src.core.observability import increment_metric, observe_latency
from src.core.api_models import (
    ConnectorListSuccess,
    OAuthLoginSuccess,
    GenericItemsSuccess,
    ConnectDisconnectSuccess,
)
import time


class ConnectorInfo(BaseModel):
    id: str = Field(..., description="Connector id")
    name: str = Field(..., description="Connector name")
    tags: List[str] = Field(default_factory=list, description="Tags/categories")


class ConnectorStatus(BaseModel):
    """Per-tenant connection status fields surfaced on GET /connectors."""
    connected: bool = Field(..., description="True if connector is linked/configured for this tenant")
    last_refreshed: Optional[str] = Field(default=None, description="ISO timestamp when tokens/connection were last refreshed or linked")
    last_error: Optional[str] = Field(default=None, description="Last error message observed for this connector, if any")
    scopes: List[str] = Field(default_factory=list, description="Active scopes/permissions granted for this connection")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional connector metadata (e.g., cloud_id or extra configuration)")


class ConnectorListItem(BaseModel):
    id: str = Field(..., description="Connector id")
    name: str = Field(..., description="Connector name")
    tags: List[str] = Field(default_factory=list, description="Tags/categories")
    status: ConnectorStatus = Field(..., description="Per-tenant connection status")


ConnectorFactory = Callable[[str], BaseConnector]


def _derive_status_from_doc(doc: Dict[str, Any] | None) -> ConnectorStatus:
    """Map a stored connector document to ConnectorStatus."""
    if not doc:
        return ConnectorStatus(
            connected=False,
            last_refreshed=None,
            last_error=None,
            scopes=[],
            metadata={},
        )
    meta = (doc.get("meta") or {})
    oauth = (meta.get("oauth") or {})
    # Determine connected
    connected = (meta.get("status") == "linked") or bool(oauth.get("access_token"))
    # Best-effort timestamps: prefer expires_at presence as indicator of recent link; otherwise last_sync_at
    last_refreshed_val = meta.get("last_sync_at") or oauth.get("expires_at")
    last_refreshed = None
    if last_refreshed_val:
        try:
            # If it's already a datetime, FastAPI/Pydantic will convert; if string, keep as string
            last_refreshed = str(last_refreshed_val)
        except Exception:
            last_refreshed = None
    scope_str = oauth.get("scope") or ""
    scopes = [s for s in scope_str.split(" ") if s] if isinstance(scope_str, str) else []
    last_error = (meta.get("last_error") or None)
    metadata = (meta.get("extra") or {})
    return ConnectorStatus(
        connected=connected,
        last_refreshed=last_refreshed,
        last_error=last_error,
        scopes=scopes,
        metadata=metadata,
    )


class ConnectorRegistry:
    """In-memory registry of available connectors."""

    def __init__(self):
        self._connectors: Dict[str, Dict[str, object]] = {}

    # PUBLIC_INTERFACE
    def register(self, connector_id: str, name: str, factory: ConnectorFactory, router: Optional[APIRouter] = None, tags: Optional[List[str]] = None):
        """Register a connector with a factory and optional APIRouter."""
        self._connectors[connector_id] = {
            "id": connector_id,
            "name": name,
            "factory": factory,
            "router": router,
            "tags": tags or [],
        }

    # PUBLIC_INTERFACE
    def get_factory(self, connector_id: str) -> ConnectorFactory:
        """Get the factory for a connector id."""
        item = self._connectors.get(connector_id)
        if not item:
            raise KeyError(f"Connector '{connector_id}' not registered")
        return item["factory"]  # type: ignore[return-value]

    # PUBLIC_INTERFACE
    def list_public(self) -> List[ConnectorInfo]:
        """List public info about registered connectors."""
        return [ConnectorInfo(id=v["id"], name=v["name"], tags=v.get("tags", [])) for v in self._connectors.values()]  # type: ignore[call-arg]

    def _list_with_status(self, tenant_id: str) -> List[ConnectorListItem]:
        """Return connectors enriched with per-tenant connection status."""
        # Read all relevant connector docs for this tenant once
        col = tenant_collection(tenant_id, "connectors")
        stored_docs = {doc.get("_id"): doc for doc in col.find({}, {"_id": 1, "meta": 1})}
        items: List[ConnectorListItem] = []
        for v in self._connectors.values():
            cid = v["id"]  # type: ignore[index]
            status = _derive_status_from_doc(stored_docs.get(cid))
            items.append(
                ConnectorListItem(
                    id=cid,  # type: ignore[arg-type]
                    name=v["name"],  # type: ignore[arg-type]
                    tags=v.get("tags", []),  # type: ignore[arg-type]
                    status=status,
                )
            )
        return items

    # PUBLIC_INTERFACE
    def mount_all(self, app: FastAPI, prefix: str = "/connectors"):
        """Mount all connector routers onto the FastAPI app under a unified prefix and inject common endpoints."""
        router = APIRouter(prefix=prefix, tags=["Connectors"])

        @router.get(
            "",
            summary="List connectors",
            description="List all connectors merged with per-tenant connection status from stored records.",
            response_model=ConnectorListSuccess,  # type: ignore[type-arg]
            responses={
                200: {
                    "description": "Connectors listed",
                    "content": {
                        "application/json": {
                            "example": {
                                "status": "ok",
                                "data": [
                                    {
                                        "id": "jira",
                                        "name": "Jira",
                                        "tags": ["SaaS"],
                                        "status": {"connected": False, "last_refreshed": None, "last_error": None, "scopes": [], "metadata": {}},
                                    }
                                ],
                                "meta": {},
                            }
                        }
                    },
                },
                422: {"description": "Validation Error"},
            },
        )
        def list_connectors(tenant_id: str = Depends(get_tenant_id)):
            enriched = [c.model_dump() for c in self._list_with_status(tenant_id)]
            return ok(enriched)

        @router.get(
            "/{connector_id}/oauth/login",
            summary="Start OAuth",
            description="Return OAuth authorization URL for a connector",
            response_model=OAuthLoginSuccess,  # type: ignore[type-arg]
            responses={
                200: {
                    "description": "Authorization URL created",
                    "content": {
                        "application/json": {
                            "example": {
                                "status": "ok",
                                "data": {"auth_url": "https://auth.atlassian.com/authorize?...",
                                         "state": "eyJhbGciOiJI..."},
                                "meta": {},
                            }
                        }
                    },
                }
            },
        )
        async def oauth_login(connector_id: str, tenant_id: str = Depends(get_tenant_id), redirect_to: Optional[str] = None):
            factory = self.get_factory(connector_id)
            connector = factory(tenant_id)
            resp = await connector.oauth_login(redirect_to=redirect_to)
            return ok(resp.model_dump())

        @router.get(
            "/{connector_id}/oauth/callback",
            summary="OAuth callback",
            description="Complete OAuth flow and store credentials",
            response_model=ConnectDisconnectSuccess,  # type: ignore[type-arg]
            responses={
                200: {"description": "OAuth completed", "content": {"application/json": {"example": {"status": "ok", "data": {"message": "OAuth linked"}, "meta": {}}}}},
                400: {"description": "Validation error"},
            },
        )
        async def oauth_callback(connector_id: str, code: str, state: Optional[str] = None, tenant_id: str = Depends(get_tenant_id)):
            if not code:
                return validation_error("Missing OAuth code")
            factory = self.get_factory(connector_id)
            connector = factory(tenant_id)
            return await connector.oauth_callback(code=code, state=state)

        @router.get(
            "/{connector_id}/search",
            summary="Search",
            description="Search data in the connector with pagination and filtering",
            response_model=GenericItemsSuccess,  # type: ignore[type-arg]
            responses={
                200: {
                    "description": "Search results",
                    "content": {
                        "application/json": {
                            "example": {
                                "status": "ok",
                                "data": {"items": [{"id": "123", "title": "Example"}], "paging": {"page": 1, "per_page": 10, "total": 1, "next_page": None, "prev_page": None}},
                                "meta": {},
                            }
                        }
                    },
                }
            },
        )
        async def search(
            connector_id: str,
            q: str = Query(..., description="Search query"),
            tenant_id: str = Depends(get_tenant_id),
            resource_type: Optional[str] = Query(default=None, description="Filter by resource type (e.g., issues, pages)"),
            page: int = Query(1, ge=1, description="Page number (1-based)"),
            per_page: int = Query(10, ge=1, le=100, description="Items per page"),
            filters: Optional[str] = Query(default=None, description="JSON object string of additional filters"),
        ):
            if not q:
                return validation_error("Missing search query")
            factory = self.get_factory(connector_id)
            connector = factory(tenant_id)
            # Parse filters JSON if provided
            filters_obj: Dict[str, Any] = {}
            if filters:
                try:
                    parsed = json.loads(filters)
                    if isinstance(parsed, dict):
                        filters_obj = parsed
                    else:
                        return validation_error("filters must be a JSON object")
                except Exception:
                    return validation_error("filters must be valid JSON")
            params = SearchParams(q=q, resource_type=resource_type, page=page, per_page=per_page, filters=filters_obj)
            # Delegate to connector for normalized response with timing
            increment_metric("search_requests_total", 1.0)
            _t0 = time.perf_counter()
            res = await connector.search(params)
            _elapsed_ms = (time.perf_counter() - _t0) * 1000.0
            observe_latency("search_latency_ms_sum", _elapsed_ms)
            return res

        @router.post(
            "/{connector_id}/connect",
            summary="Connect",
            description="Connect using stored credentials (stub)",
            response_model=ConnectDisconnectSuccess,  # type: ignore[type-arg]
            responses={200: {"description": "Connected status"}, 401: {"description": "Unauthorized"}},
        )
        async def connect(connector_id: str, tenant_id: str = Depends(get_tenant_id)):
            factory = self.get_factory(connector_id)
            connector = factory(tenant_id)
            return await connector.connect()

        @router.post(
            "/{connector_id}/disconnect",
            summary="Disconnect",
            description="Disconnect and remove credentials (stub)",
            response_model=ConnectDisconnectSuccess,  # type: ignore[type-arg]
            responses={200: {"description": "Disconnected"}},
        )
        async def disconnect(connector_id: str, tenant_id: str = Depends(get_tenant_id)):
            factory = self.get_factory(connector_id)
            connector = factory(tenant_id)
            return await connector.disconnect()

        app.include_router(router)

        # Mount sub-routers for connector-specific endpoints if provided
        for item in self._connectors.values():
            sub_router: Optional[APIRouter] = item.get("router")  # type: ignore[assignment]
            if sub_router is not None:
                app.include_router(sub_router, prefix=f"{prefix}/{item['id']}", tags=[item["name"]])
