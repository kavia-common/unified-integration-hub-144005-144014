from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends

from src.connectors.base import BaseConnector, OAuthLoginResponse, SearchParams
from src.core.db import tenant_collection
from src.core.logging import get_logger
from src.core.security import generate_csrf_state, generate_pkce, verify_csrf_state, compute_expiry
from src.core.settings import get_settings
from src.core.token_store import TokenStore
from src.core.tenants import get_tenant_id
from src.core.response import ok, auth_required_error, config_required_error, normalize_upstream_error, validation_error
from src.core.api_models import (
    GenericItemsSuccess,
    ConfluenceCreatePageModel,
    ConfluencePageCreateSuccess,
)
from .client import ConfluenceClient
from .mapping import normalize_create_page, normalize_search_pages

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
            return validation_error("Invalid OAuth state")

        sess = self.collection.find_one({"_id": f"oauth_session::{self.id}"}) or {}
        stored_state = sess.get("state")
        code_verifier = sess.get("code_verifier")
        if not stored_state or stored_state != state or not code_verifier:
            return validation_error("OAuth state mismatch")

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
                return normalize_upstream_error(resp.status_code, resp.text, headers=resp.headers, default_message="OAuth code exchange failed")
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
        return ok({"message": "OAuth linked"})

    async def search(self, params: SearchParams) -> Dict[str, Any]:
        """Search Confluence pages by query with pagination.
        Supports cursor-based pagination via params.filters['cursor'] if provided by a previous response.
        """
        # Ensure valid token
        access = await self.token_store.ensure_valid_token_atlassian(
            connector_id=self.id,
            name=self.name,
            client_id=self.settings.oauth.CONFLUENCE_CLIENT_ID or "",
            client_secret=self.settings.oauth.CONFLUENCE_CLIENT_SECRET,
            refresh_token=None,
            redirect_uri=self.settings.oauth.CONFLUENCE_REDIRECT_URI or "",
        )
        if not access:
            return auth_required_error()
        # Require cloud id
        doc = self.collection.find_one({"_id": self.id}) or {}
        meta = (doc.get("meta") or {})
        extra = (meta.get("extra") or {})
        cloud_id = extra.get("cloud_id")
        if not cloud_id:
            return config_required_error("Missing Confluence cloud_id for this tenant.")

        # Use upstream cursor if provided in filters
        cursor = None
        try:
            if params.filters and isinstance(params.filters, dict):
                cursor = params.filters.get("cursor")
        except Exception:
            cursor = None

        client = ConfluenceClient(access_token=access, cloud_id=cloud_id)
        resp = await client.search_pages(query=params.q, limit=params.per_page, cursor=cursor)
        if resp.get("status") == "error":
            return resp
        body = resp.get("data") or {}
        pages = body.get("pages", []) or body.get("results", [])
        next_cursor = (body.get("paging") or {}).get("next_cursor") or None
        # Normalize response into unified items/paging; expose next_cursor for clients via paging.next_cursor
        return normalize_search_pages(pages, page=params.page, per_page=params.per_page, next_cursor=next_cursor)

    async def connect(self):
        access = await self.token_store.ensure_valid_token_atlassian(
            connector_id=self.id,
            name=self.name,
            client_id=self.settings.oauth.CONFLUENCE_CLIENT_ID or "",
            client_secret=self.settings.oauth.CONFLUENCE_CLIENT_SECRET,
            refresh_token=None,
            redirect_uri=self.settings.oauth.CONFLUENCE_REDIRECT_URI or "",
        )
        return ok({"connected": bool(access)})

    async def disconnect(self):
        self.collection.delete_one({"_id": self.id})
        self.collection.delete_one({"_id": f"oauth_session::{self.id}"})
        return ok({"disconnected": True})


# Use shared ConfluenceCreatePageModel from core.api_models


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
        response_model=GenericItemsSuccess,  # type: ignore[type-arg]
        responses={
            200: {"description": "Spaces list", "content": {"application/json": {"example": {"status": "ok", "data": {"items": [{"id": "42", "key": "ENG", "name": "Engineering"}], "paging": {"page": 1, "per_page": 10}}, "meta": {"source": "confluence"}}}}},
            401: {"description": "Unauthorized"},
            502: {"description": "Upstream error"},
        },
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
            return auth_required_error()
        cloud_id = _get_cloud_id(connector)
        if not cloud_id:
            return config_required_error("Missing Confluence cloud_id for this tenant.")
        client = ConfluenceClient(access_token=access, cloud_id=cloud_id)
        data = await client.list_spaces()
        if data.get("status") == "error":
            return data
        spaces = (data.get("data") or {}).get("spaces", [])
        return ok({"items": [s for s in spaces]}, meta={"source": "confluence"})

    @router.post(
        "/confluence/pages",
        summary="Create Confluence page",
        description="Create a Confluence page in a space.",
        tags=["Confluence"],
        response_model=ConfluencePageCreateSuccess,  # type: ignore[type-arg]
        responses={
            200: {"description": "Page created", "content": {"application/json": {"example": {"status": "ok", "data": {"id": "12345", "title": "New Page"}, "meta": {}}}}},
            401: {"description": "Unauthorized"},
            400: {"description": "Bad Request"},
            502: {"description": "Upstream error"},
        },
    )
    async def create_page(payload: ConfluenceCreatePageModel, tenant_id: str = Depends(get_tenant_id)):
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
            return auth_required_error()
        cloud_id = _get_cloud_id(connector)
        if not cloud_id:
            return config_required_error("Missing Confluence cloud_id for this tenant.")
        client = ConfluenceClient(access_token=access, cloud_id=cloud_id)
        resp = await client.create_page(space_key=payload.space_key, title=payload.title, body=payload.body)
        if resp.get("status") == "error":
            return resp
        page_raw = (resp.get("data") or {}).get("page") or {}
        return normalize_create_page(page_raw)
    return router


def factory(tenant_id: str) -> ConfluenceConnector:
    return ConfluenceConnector(tenant_id)
