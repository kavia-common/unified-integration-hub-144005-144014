from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Query

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
    JiraIssueCreateModel,
    JiraIssueCreateSuccess,
)
from .client import JiraClient
from .mapping import normalize_create_issue, normalize_search_issues

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
                logger.error("Atlassian code exchange failed with status %s", resp.status_code)
                return normalize_upstream_error(resp.status_code, resp.text, headers=resp.headers, default_message="OAuth code exchange failed")
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
                    for res in resources:
                        if res.get("scopes") and any("jira" in s for s in res.get("scopes", [])):
                            cloud_id = res.get("id")
                            break
                    if not cloud_id and resources:
                        cloud_id = resources[0].get("id")
        except Exception:
            logger.warning("Failed to fetch Atlassian accessible resources; proceeding without cloud_id")

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
        # Ensure token
        access = await self.token_store.ensure_valid_token_atlassian(
            connector_id=self.id,
            name=self.name,
            client_id=self.settings.oauth.JIRA_CLIENT_ID or "",
            client_secret=self.settings.oauth.JIRA_CLIENT_SECRET,
            refresh_token=None,
            redirect_uri=self.settings.oauth.JIRA_REDIRECT_URI or "",
        )
        if not access:
            return auth_required_error()
        # Need cloud id
        doc = self.collection.find_one({"_id": self.id}) or {}
        meta = (doc.get("meta") or {})
        extra = (meta.get("extra") or {})
        cloud_id = extra.get("cloud_id")
        if not cloud_id:
            return config_required_error("Missing Jira cloud_id for this tenant.")
        client = JiraClient(access_token=access, cloud_id=cloud_id)

        # Build JQL using q + filters
        jql_parts = []
        if params.q:
            # Basic contains on summary or description
            term = params.q.replace('"', '\\"')
            jql_parts.append(f'text ~ "{term}"')
        f = params.filters or {}
        if f.get("projectKey"):
            jql_parts.append(f'project = "{f.get("projectKey")}"')
        if f.get("type"):
            jql_parts.append(f'issuetype = "{f.get("type")}"')
        if f.get("status"):
            jql_parts.append(f'status = "{f.get("status")}"')
        jql = " AND ".join(jql_parts) if jql_parts else ""

        start_at = (params.page - 1) * params.per_page
        jr = await client.search_issues(jql=jql, start_at=start_at, max_results=params.per_page)
        if jr.get("status") == "error":
            return jr
        data = jr.get("data") or {}
        issues = data.get("issues", [])
        paging_raw = data.get("paging", {}) or {}
        total = paging_raw.get("total")
        return normalize_search_issues(issues, total=total, page=params.page, per_page=params.per_page)

    async def connect(self):
        access = await self.token_store.ensure_valid_token_atlassian(
            connector_id=self.id,
            name=self.name,
            client_id=self.settings.oauth.JIRA_CLIENT_ID or "",
            client_secret=self.settings.oauth.JIRA_CLIENT_SECRET,
            refresh_token=None,
            redirect_uri=self.settings.oauth.JIRA_REDIRECT_URI or "",
        )
        return ok({"connected": bool(access)})

    async def disconnect(self):
        self.collection.delete_one({"_id": self.id})
        self.collection.delete_one({"_id": f"oauth_session::{self.id}"})
        return ok({"disconnected": True})


# Use shared JiraIssueCreateModel from core.api_models


def _get_token_and_cloud_id(connector: "JiraConnector") -> tuple[Optional[str], Optional[str]]:
    state = connector.token_store.get_tokens(connector.id)
    if not state:
        return None, None
    access_token, _, _ = connector.token_store.get_decrypted_access(connector.id)
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
        response_model=GenericItemsSuccess,  # type: ignore[type-arg]
        responses={
            200: {"description": "Projects list", "content": {"application/json": {"example": {"status": "ok", "data": {"items": [{"id": "10000", "key": "ABC", "name": "Example"}], "paging": {"page": 1, "per_page": 50, "total": 1}}, "meta": {"source": "jira"}}}}},
            401: {"description": "Unauthorized"},
            502: {"description": "Upstream error"},
        },
    )
    async def list_projects(tenant_id: str = Depends(get_tenant_id), page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=100)):
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
            return auth_required_error()
        _, cloud_id = _get_token_and_cloud_id(connector)
        if not cloud_id:
            return config_required_error("Missing Jira cloud_id for this tenant.")
        client = JiraClient(access_token=access, cloud_id=cloud_id)
        start_at = (page - 1) * per_page
        data = await client.list_projects(start_at=start_at, max_results=per_page)
        if data.get("status") == "error":
            return data
        body = data.get("data") or {}
        projects = body.get("projects", [])
        paging_raw = body.get("paging", {}) or {}
        total = paging_raw.get("total")
        # Map simple normalized structure with paging
        next_page = page + 1 if total is not None and page * per_page < total else None
        prev_page = page - 1 if page > 1 else None
        return ok({"items": [p for p in projects], "paging": {"page": page, "per_page": per_page, "total": total, "next_page": next_page, "prev_page": prev_page}}, meta={"source": "jira"})

    @router.post(
        "/jira/issues",
        summary="Create Jira issue",
        description="Create a Jira issue using the authorized user's token.",
        tags=["Jira"],
        response_model=JiraIssueCreateSuccess,  # type: ignore[type-arg]
        responses={
            200: {"description": "Issue created", "content": {"application/json": {"example": {"status": "ok", "data": {"id": "10001", "key": "ABC-1"}, "meta": {}}}}},
            400: {"description": "Bad Request"},
            401: {"description": "Unauthorized"},
            502: {"description": "Upstream error"},
        },
    )
    async def create_issue(payload: JiraIssueCreateModel, tenant_id: str = Depends(get_tenant_id)):
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
            return auth_required_error()
        _, cloud_id = _get_token_and_cloud_id(connector)
        if not cloud_id:
            return config_required_error("Missing Jira cloud_id for this tenant.")
        client = JiraClient(access_token=access, cloud_id=cloud_id)
        resp = await client.create_issue(
            project_key=payload.project_key,
            summary=payload.summary,
            issuetype=payload.issuetype,
            description=payload.description,
        )
        if resp.get("status") == "error":
            return resp
        issue_raw = (resp.get("data") or {}).get("issue") or {}
        return normalize_create_issue(issue_raw)
    return router


def factory(tenant_id: str) -> JiraConnector:
    return JiraConnector(tenant_id)
