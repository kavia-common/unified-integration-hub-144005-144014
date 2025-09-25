from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.connectors.base import BaseConnector, OAuthLoginResponse, SearchResponse
from src.core.db import tenant_collection
from src.core.logging import get_logger
from src.core.security import generate_csrf_state, generate_pkce, verify_csrf_state, compute_expiry
from src.core.settings import get_settings
from src.core.token_store import TokenStore
from src.core.tenants import get_tenant_id
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

        # Discover accessible resources to determine cloud ID for Jira
        cloud_id = None
        try:
            async with httpx.AsyncClient(timeout=20.0, headers={"Authorization": f"Bearer {access_token}"}) as c2:
                r2 = await c2.get("https://api.atlassian.com/oauth/token/accessible-resources")
                if r2.status_code < 400:
                    resources = r2.json()
                    # pick first Jira resource
                    for res in resources:
                        if res.get("scopes") and any("jira" in s for s in res.get("scopes", [])):
                            cloud_id = res.get("id")
                            break
                    # fallback: if first entry has 'id'
                    if not cloud_id and resources:
                        cloud_id = resources[0].get("id")
        except Exception:
            logger.warning("Failed to fetch Atlassian accessible resources; proceeding without cloud_id")

        # persist encrypted with extra meta
        extra_meta = {"cloud_id": cloud_id} if cloud_id else {}
        self.token_store.save_tokens(
            connector_id=self.id,
            name=self.name,
            access_token=access_token,
            refresh_token=refresh_token,
            scope=scope,
            expires_at=expires_at,
            extra=extra_meta,
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


class JiraIssueCreate(BaseModel):
    project_key: str = Field(..., description="Project key (e.g., ABC)")
    summary: str = Field(..., description="Issue summary/title")
    issuetype: str = Field(default="Task", description="Issue type name")
    description: Optional[str] = Field(default=None, description="Optional issue description")


def _get_token_and_cloud_id(connector: "JiraConnector") -> tuple[Optional[str], Optional[str]]:
    # get decrypted tokens and meta
    state = connector.token_store.get_tokens(connector.id)
    if not state:
        return None, None
    access_token, _, expires_at = connector.token_store.get_decrypted_access(connector.id)
    # fetch meta.extra.cloud_id from raw connector doc
    doc = connector.collection.find_one({"_id": connector.id}) or {}
    meta = (doc.get("meta") or {})
    extra = (meta.get("extra") or {})
    cloud_id = extra.get("cloud_id")
    return access_token, cloud_id


def get_router() -> APIRouter:
    """Jira-specific endpoints: projects listing and issue creation."""

    @router.get(
        "/jira/projects",
        summary="List Jira projects",
        description="List Jira projects visible to the authorized user.",
        tags=["Jira"],
        responses={200: {"description": "Projects list"}, 401: {"description": "Unauthorized"}, 502: {"description": "Upstream error"}},
    )
    async def list_projects(tenant_id: str = Depends(get_tenant_id)):
        connector = JiraConnector(tenant_id)
        # ensure a valid token (attempt refresh if needed)
        access = await connector.token_store.ensure_valid_token_atlassian(
            connector_id=connector.id,
            name=connector.name,
            client_id=connector.settings.oauth.JIRA_CLIENT_ID or "",
            client_secret=connector.settings.oauth.JIRA_CLIENT_SECRET,
            refresh_token=None,
            redirect_uri=connector.settings.oauth.JIRA_REDIRECT_URI or "",
        )
        if not access:
            return {"ok": False, "error": "unauthorized", "code": "AUTH_REQUIRED"}
        # find cloud_id
        _, cloud_id = _get_token_and_cloud_id(connector)
        if not cloud_id:
            return {"ok": False, "error": "missing_cloud_id", "code": "CONFIG_REQUIRED"}
        client = JiraClient(access_token=access, cloud_id=cloud_id)
        data = await client.list_projects()
        if not data.get("ok"):
            return {"ok": False, "error": data.get("error"), "code": "UPSTREAM_ERROR", "status": data.get("status")}
        return {"ok": True, "projects": data.get("projects", [])}

    @router.post(
        "/jira/issues",
        summary="Create Jira issue",
        description="Create a Jira issue using the authorized user's token.",
        tags=["Jira"],
        responses={200: {"description": "Issue created"}, 400: {"description": "Bad Request"}, 401: {"description": "Unauthorized"}, 502: {"description": "Upstream error"}},
    )
    async def create_issue(payload: JiraIssueCreate, tenant_id: str = Depends(get_tenant_id)):
        connector = JiraConnector(tenant_id)
        access = await connector.token_store.ensure_valid_token_atlassian(
            connector_id=connector.id,
            name=connector.name,
            client_id=connector.settings.oauth.JIRA_CLIENT_ID or "",
            client_secret=connector.settings.oauth.JIRA_CLIENT_SECRET,
            refresh_token=None,
            redirect_uri=connector.settings.oauth.JIRA_REDIRECT_URI or "",
        )
        if not access:
            return {"ok": False, "error": "unauthorized", "code": "AUTH_REQUIRED"}
        _, cloud_id = _get_token_and_cloud_id(connector)
        if not cloud_id:
            return {"ok": False, "error": "missing_cloud_id", "code": "CONFIG_REQUIRED"}
        client = JiraClient(access_token=access, cloud_id=cloud_id)
        resp = await client.create_issue(
            project_key=payload.project_key,
            summary=payload.summary,
            issuetype=payload.issuetype,
            description=payload.description,
        )
        if not resp.get("ok"):
            return {"ok": False, "error": resp.get("error"), "code": "UPSTREAM_ERROR", "status": resp.get("status")}
        return {"ok": True, "issue": resp.get("issue")}
    return router


def factory(tenant_id: str) -> JiraConnector:
    return JiraConnector(tenant_id)
