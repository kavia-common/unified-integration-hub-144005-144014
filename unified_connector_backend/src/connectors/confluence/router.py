from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter

from src.connectors.base import BaseConnector, OAuthLoginResponse, SearchResponse
from src.core.db import tenant_collection, upsert_by_id
from src.core.settings import get_settings
from src.core.logging import get_logger
from .client import ConfluenceClient

logger = get_logger(__name__)
router = APIRouter()


class ConfluenceConnector(BaseConnector):
    id = "confluence"
    name = "Confluence"

    def __init__(self, tenant_id: str):
        super().__init__(tenant_id)
        self.settings = get_settings()
        self.collection = tenant_collection(tenant_id, "connectors")

    def get_public_info(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name}

    async def oauth_login(self, redirect_to: Optional[str] = None) -> OAuthLoginResponse:
        redirect_uri = self.settings.oauth.CONFLUENCE_REDIRECT_URI or (redirect_to or "")
        auth_url = f"https://auth.atlassian.com/authorize?client_id={self.settings.oauth.CONFLUENCE_CLIENT_ID or ''}&redirect_uri={redirect_uri}&response_type=code&scope=read%3Aconfluence-content.summary"
        return OAuthLoginResponse(auth_url=auth_url, state=None)

    async def oauth_callback(self, code: str, state: Optional[str]):
        upsert_by_id(
            self.collection,
            _id=self.id,
            payload={
                "_id": self.id,
                "id": self.id,
                "name": self.name,
                "tenant_id": self.tenant_id,
                "meta": {
                    "status": "linked",
                    "oauth": {"access_token": "encrypted::dummy", "refresh_token": "encrypted::dummy", "scope": "read:confluence-content.summary"},
                },
            },
        )
        return {"ok": True, "message": "OAuth linked (stub)"}

    async def search(self, query: str) -> SearchResponse:
        client = ConfluenceClient(access_token=None)
        data = await client.search_pages(query=query)
        return SearchResponse(results=data.get("pages", []))

    async def connect(self):
        return {"ok": True, "message": "Connected (stub)"}

    async def disconnect(self):
        self.collection.delete_one({"_id": self.id})
        return {"ok": True, "message": "Disconnected (stub)"}


def get_router() -> APIRouter:
    return router


def factory(tenant_id: str) -> ConfluenceConnector:
    return ConfluenceConnector(tenant_id)
