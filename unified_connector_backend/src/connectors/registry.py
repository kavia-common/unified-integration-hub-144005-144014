from __future__ import annotations

from typing import Callable, Dict, List, Optional

from fastapi import APIRouter, Depends, FastAPI
from pydantic import BaseModel, Field

from src.core.tenants import get_tenant_id
from src.connectors.base import BaseConnector
from src.core.response import ok, validation_error


class ConnectorInfo(BaseModel):
    id: str = Field(..., description="Connector id")
    name: str = Field(..., description="Connector name")
    tags: List[str] = Field(default_factory=list, description="Tags/categories")


ConnectorFactory = Callable[[str], BaseConnector]


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

    # PUBLIC_INTERFACE
    def mount_all(self, app: FastAPI, prefix: str = "/connectors"):
        """Mount all connector routers onto the FastAPI app under a unified prefix and inject common endpoints."""
        router = APIRouter(prefix=prefix, tags=["Connectors"])

        @router.get("", summary="List connectors", description="List all available connectors")
        def list_connectors():
            return ok([c.model_dump() for c in self.list_public()])

        @router.get("/{connector_id}/oauth/login", summary="Start OAuth", description="Return OAuth authorization URL for a connector")
        async def oauth_login(connector_id: str, tenant_id: str = Depends(get_tenant_id), redirect_to: Optional[str] = None):
            factory = self.get_factory(connector_id)
            connector = factory(tenant_id)
            resp = await connector.oauth_login(redirect_to=redirect_to)
            return ok(resp.model_dump())

        @router.get("/{connector_id}/oauth/callback", summary="OAuth callback", description="Complete OAuth flow and store credentials")
        async def oauth_callback(connector_id: str, code: str, state: Optional[str] = None, tenant_id: str = Depends(get_tenant_id)):
            if not code:
                return validation_error("Missing OAuth code")
            factory = self.get_factory(connector_id)
            connector = factory(tenant_id)
            return await connector.oauth_callback(code=code, state=state)

        @router.get("/{connector_id}/search", summary="Search", description="Search data in the connector (stub)")
        async def search(connector_id: str, q: str, tenant_id: str = Depends(get_tenant_id)):
            if not q:
                return validation_error("Missing search query")
            factory = self.get_factory(connector_id)
            connector = factory(tenant_id)
            # Since base connectors return SearchResponse with results list, wrap in standardized "ok"
            sr = await connector.search(q)
            return ok({"items": sr.results, "paging": {}}, meta={"connector": connector_id})

        @router.post("/{connector_id}/connect", summary="Connect", description="Connect using stored credentials (stub)")
        async def connect(connector_id: str, tenant_id: str = Depends(get_tenant_id)):
            factory = self.get_factory(connector_id)
            connector = factory(tenant_id)
            return await connector.connect()

        @router.post("/{connector_id}/disconnect", summary="Disconnect", description="Disconnect and remove credentials (stub)")
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
