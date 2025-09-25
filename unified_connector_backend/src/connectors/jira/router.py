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
from .client import JiraClient

logger = get_logger(__name__)
router = APIRouter()


class JiraConnector(BaseConnector):
    id = "jira"
    name = "Jira"

    def __init__(self, tenant_id: str):
        super().__init__(tenant_id)
        self.settings = get_settings()
        self.collection = tenant_collection(tenant_id, "connectors")
        self.token_store = TokenStore(tenant_id)

    def get_public_info(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name}

    async def oauth_login(self, redirect_to: Optional[str] = None) -> OAuthLoginResponse:
        """Build Atlassian authorization URL with PKCE and CSRF state and persist ephemeral state."""
        client_id = self.settings.oauth.JIRA_CLIENT_ID or ""
        redirect_uri = self.settings.oauth.JIRA_REDIRECT_URI or (redirect_to or "")
        scopes = ["read:jira-user", "read:jira-work", "offline_access"]
        pkce = generate_pkce()
        state = generate_csrf_state(self.tenant_id, self.id)

        # store ephemeral auth session (state + code_verifier) in tenant collection
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

        client_id = self.settings.oauth.JIRA_CLIENT_ID or ""
        client_secret = self.settings.oauth.JIRA_CLIENT_SECRET  # optional for PKCE-only apps
        redirect_uri = self.settings.oauth.JIRA_REDIRECT_URI or ""

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
                # Do not log token payloads or codes
                logger.error("Atlassian code exchange failed with status %s", resp.status_code)
                return {"ok": False, "error": "exchange_failed", "status": resp.status_code}
            data = resp.json()

        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        scope = data.get("scope")
        expires_in = int(data.get("expires_in", 3600))
        expires_at = compute_expiry(expires_in)

        # persist encrypted
        self.token_store.save_tokens(
            connector_id=self.id,
            name=self.name,
            access_token=access_token,
            refresh_token=refresh_token,
            scope=scope,
            expires_at=expires_at,
        )

        # cleanup auth session
        self.collection.delete_one({"_id": f"oauth_session::{self.id}"})

        return {"ok": True, "message": "OAuth linked"}

    async def search(self, query: str) -> SearchResponse:
        # Ensure we have a valid token (auto-refresh if needed)
        access = await self.token_store.ensure_valid_token_atlassian(
            connector_id=self.id,
            name=self.name,
            client_id=self.settings.oauth.JIRA_CLIENT_ID or "",
            client_secret=self.settings.oauth.JIRA_CLIENT_SECRET,
            refresh_token=None,
            redirect_uri=self.settings.oauth.JIRA_REDIRECT_URI or "",
        )
        client = JiraClient(access_token=access)
        data = await client.search_issues(jql=query)
        return SearchResponse(results=data.get("issues", []))

    async def connect(self):
        # Simple connectivity check via token retrieval
        access = await self.token_store.ensure_valid_token_atlassian(
            connector_id=self.id,
            name=self.name,
            client_id=self.settings.oauth.JIRA_CLIENT_ID or "",
            client_secret=self.settings.oauth.JIRA_CLIENT_SECRET,
            refresh_token=None,
            redirect_uri=self.settings.oauth.JIRA_REDIRECT_URI or "",
        )
        return {"ok": bool(access)}

    async def disconnect(self):
        self.collection.delete_one({"_id": self.id})
        self.collection.delete_one({"_id": f"oauth_session::{self.id}"})
        return {"ok": True, "message": "Disconnected"}


def get_router() -> APIRouter:
    """Return Jira-specific router if needed (currently none, placeholder)."""
    return router


def factory(tenant_id: str) -> JiraConnector:
    return JiraConnector(tenant_id)
