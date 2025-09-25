from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter

from src.connectors.base import BaseConnector, OAuthLoginResponse, SearchResponse
from src.core.db import tenant_collection
from src.core.logging import get_logger
from src.core.security import generate_csrf_state, generate_pkce, verify_csrf_state, compute_expiry
from src.core.settings import get_settings
from src.core.token_store import TokenStore
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
        self.token_store = TokenStore(tenant_id)

    def get_public_info(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name}

    async def oauth_login(self, redirect_to: Optional[str] = None) -> OAuthLoginResponse:
        """Build Atlassian authorization URL with PKCE and CSRF state and persist ephemeral state."""
        client_id = self.settings.oauth.CONFLUENCE_CLIENT_ID or ""
        redirect_uri = self.settings.oauth.CONFLUENCE_REDIRECT_URI or (redirect_to or "")
        scopes = ["read:confluence-content.summary", "read:confluence-user", "offline_access"]
        pkce = generate_pkce()
        state = generate_csrf_state(self.tenant_id, self.id)

        self.collection.update_one(
            {"_id": f"oauth_session::{self.id}"},
            {"$set": {"_id": f"oauth_session::{self.id}", "state": state, "code_verifier": pkce.verifier, "created_at": datetime.utcnow()}},
            upsert=True,
        )

        params = {
            "audience": "api.atlassian.com",
            "client_id": client_id,
            "scope": " ".join(scopes),
            "redirect_uri": redirect_uri,
            "state": state,
            "response_type": "code",
            "prompt": "consent",
            "code_challenge": pkce.challenge,
            "code_challenge_method": pkce.method,
        }
        auth_url = f"https://auth.atlassian.com/authorize?{urlencode(params)}"
        return OAuthLoginResponse(auth_url=auth_url, state=state)

    async def oauth_callback(self, code: str, state: Optional[str]):
        """Exchange authorization code for tokens and persist encrypted secrets. Do not log secrets."""
        if not state or not verify_csrf_state(state):
            return {"ok": False, "error": "invalid_state"}

        sess = self.collection.find_one({"_id": f"oauth_session::{self.id}"}) or {}
        stored_state = sess.get("state")
        code_verifier = sess.get("code_verifier")
        if not stored_state or stored_state != state or not code_verifier:
            return {"ok": False, "error": "state_mismatch"}

        client_id = self.settings.oauth.CONFLUENCE_CLIENT_ID or ""
        client_secret = self.settings.oauth.CONFLUENCE_CLIENT_SECRET
        redirect_uri = self.settings.oauth.CONFLUENCE_REDIRECT_URI or ""

        token_url = "https://auth.atlassian.com/oauth/token"
        payload = {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        }
        if client_secret:
            payload["client_secret"] = client_secret

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(token_url, json=payload)
            if resp.status_code >= 400:
                logger.error("Atlassian code exchange failed with status %s", resp.status_code)
                return {"ok": False, "error": "exchange_failed", "status": resp.status_code}
            data = resp.json()

        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        scope = data.get("scope")
        expires_in = int(data.get("expires_in", 3600))
        expires_at = compute_expiry(expires_in)

        # Discover accessible resources to get cloud id (Confluence)
        cloud_id = None
        try:
            async with httpx.AsyncClient(timeout=20.0, headers={"Authorization": f"Bearer {access_token}"}) as c2:
                r2 = await c2.get("https://api.atlassian.com/oauth/token/accessible-resources")
                if r2.status_code < 400:
                    resources = r2.json()
                    for res in resources:
                        if res.get("scopes") and any("confluence" in s for s in res.get("scopes", [])):
                            cloud_id = res.get("id")
                            break
                    if not cloud_id and resources:
                        cloud_id = resources[0].get("id")
        except Exception:
            logger.warning("Failed to fetch Atlassian accessible resources for Confluence")

        self.token_store.save_tokens(
            connector_id=self.id,
            name=self.name,
            access_token=access_token,
            refresh_token=refresh_token,
            scope=scope,
            expires_at=expires_at,
            extra={"cloud_id": cloud_id} if cloud_id else {},
        )

        self.collection.delete_one({"_id": f"oauth_session::{self.id}"})
        return {"ok": True, "message": "OAuth linked"}

    async def search(self, query: str) -> SearchResponse:
        access = await self.token_store.ensure_valid_token_atlassian(
            connector_id=self.id,
            name=self.name,
            client_id=self.settings.oauth.CONFLUENCE_CLIENT_ID or "",
            client_secret=self.settings.oauth.CONFLUENCE_CLIENT_SECRET,
            refresh_token=None,
            redirect_uri=self.settings.oauth.CONFLUENCE_REDIRECT_URI or "",
        )
        client = ConfluenceClient(access_token=access)
        data = await client.search_pages(query=query)
        return SearchResponse(results=data.get("pages", []))

    async def connect(self):
        access = await self.token_store.ensure_valid_token_atlassian(
            connector_id=self.id,
            name=self.name,
            client_id=self.settings.oauth.CONFLUENCE_CLIENT_ID or "",
            client_secret=self.settings.oauth.CONFLUENCE_CLIENT_SECRET,
            refresh_token=None,
            redirect_uri=self.settings.oauth.CONFLUENCE_REDIRECT_URI or "",
        )
        return {"ok": bool(access)}

    async def disconnect(self):
        self.collection.delete_one({"_id": self.id})
        self.collection.delete_one({"_id": f"oauth_session::{self.id}"})
        return {"ok": True, "message": "Disconnected"}


from fastapi import Depends
from pydantic import BaseModel, Field
from src.core.tenants import get_tenant_id


class CreatePagePayload(BaseModel):
    space_key: str = Field(..., description="Confluence space key")
    title: str = Field(..., description="Page title")
    body: str = Field(..., description="Page body in storage representation")


def _get_cloud_id(connector: "ConfluenceConnector") -> Optional[str]:
    doc = connector.collection.find_one({"_id": connector.id}) or {}
    meta = (doc.get("meta") or {})
    extra = (meta.get("extra") or {})
    return extra.get("cloud_id")


def get_router() -> APIRouter:
    @router.get(
        "/confluence/spaces",
        summary="List Confluence spaces",
        description="List Confluence spaces accessible to the user.",
        tags=["Confluence"],
        responses={200: {"description": "Spaces list"}, 401: {"description": "Unauthorized"}, 502: {"description": "Upstream error"}},
    )
    async def list_spaces(tenant_id: str = Depends(get_tenant_id)):
        connector = ConfluenceConnector(tenant_id)
        access = await connector.token_store.ensure_valid_token_atlassian(
            connector_id=connector.id,
            name=connector.name,
            client_id=connector.settings.oauth.CONFLUENCE_CLIENT_ID or "",
            client_secret=connector.settings.oauth.CONFLUENCE_CLIENT_SECRET,
            refresh_token=None,
            redirect_uri=connector.settings.oauth.CONFLUENCE_REDIRECT_URI or "",
        )
        if not access:
            return {"ok": False, "error": "unauthorized", "code": "AUTH_REQUIRED"}
        cloud_id = _get_cloud_id(connector)
        if not cloud_id:
            return {"ok": False, "error": "missing_cloud_id", "code": "CONFIG_REQUIRED"}
        client = ConfluenceClient(access_token=access, cloud_id=cloud_id)
        data = await client.list_spaces()
        if not data.get("ok"):
            return {"ok": False, "error": data.get("error"), "code": "UPSTREAM_ERROR", "status": data.get("status")}
        return {"ok": True, "spaces": data.get("spaces", [])}

    @router.post(
        "/confluence/pages",
        summary="Create Confluence page",
        description="Create a Confluence page in a space.",
        tags=["Confluence"],
        responses={200: {"description": "Page created"}, 401: {"description": "Unauthorized"}, 400: {"description": "Bad Request"}, 502: {"description": "Upstream error"}},
    )
    async def create_page(payload: CreatePagePayload, tenant_id: str = Depends(get_tenant_id)):
        connector = ConfluenceConnector(tenant_id)
        access = await connector.token_store.ensure_valid_token_atlassian(
            connector_id=connector.id,
            name=connector.name,
            client_id=connector.settings.oauth.CONFLUENCE_CLIENT_ID or "",
            client_secret=connector.settings.oauth.CONFLUENCE_CLIENT_SECRET,
            refresh_token=None,
            redirect_uri=connector.settings.oauth.CONFLUENCE_REDIRECT_URI or "",
        )
        if not access:
            return {"ok": False, "error": "unauthorized", "code": "AUTH_REQUIRED"}
        cloud_id = _get_cloud_id(connector)
        if not cloud_id:
            return {"ok": False, "error": "missing_cloud_id", "code": "CONFIG_REQUIRED"}
        client = ConfluenceClient(access_token=access, cloud_id=cloud_id)
        resp = await client.create_page(space_key=payload.space_key, title=payload.title, body=payload.body)
        if not resp.get("ok"):
            return {"ok": False, "error": resp.get("error"), "code": "UPSTREAM_ERROR", "status": resp.get("status")}
        return {"ok": True, "page": resp.get("page")}
    return router


def factory(tenant_id: str) -> ConfluenceConnector:
    return ConfluenceConnector(tenant_id)
