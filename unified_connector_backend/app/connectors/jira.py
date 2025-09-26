import os
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, Any, List

import httpx
from pydantic import BaseModel, Field

from .base import BaseConnector, OAuthAuthorize, NormalizedItem, CreateResult
from ..db.mongo import upsert_connection, get_connection
from ..security.crypto import encrypt_str, decrypt_str

JIRA_AUTH_URL = "https://auth.atlassian.com/authorize"
JIRA_TOKEN_URL = "https://auth.atlassian.com/oauth/token"
JIRA_API_BASE = "https://api.atlassian.com/ex/jira"

def _client_id():
    return os.getenv("JIRA_CLIENT_ID", "")

def _client_secret():
    return os.getenv("JIRA_CLIENT_SECRET", "")

def _redirect_uri():
    return os.getenv("JIRA_REDIRECTION_URI", "")

SCOPES = [
    "read:jira-user",
    "read:jira-work",
    "write:jira-work",
    "offline_access",
]

class JiraConnector(BaseConnector):
    id = "jira"
    display_name = "Jira"
    supports_oauth = True
    required_scopes = SCOPES

    # PUBLIC_INTERFACE
    async def get_oauth_authorize_url(self, tenant_id: str, state: str) -> OAuthAuthorize:
        """Compose Atlassian OAuth 2.0 authorize URL."""
        params = {
            "audience": "api.atlassian.com",
            "client_id": _client_id(),
            "scope": " ".join(SCOPES),
            "redirect_uri": _redirect_uri(),
            "state": state,
            "response_type": "code",
            "prompt": "consent",
        }
        url = f"{JIRA_AUTH_URL}?{urllib.parse.urlencode(params)}"
        return OAuthAuthorize(authorize_url=url, state=state)

    # PUBLIC_INTERFACE
    async def exchange_code_for_tokens(self, tenant_id: str, code: str, state: str) -> Dict[str, Any]:
        """Exchange auth code for tokens and store credentials in Mongo."""
        data = {
            "grant_type": "authorization_code",
            "client_id": _client_id(),
            "client_secret": _client_secret(),
            "code": code,
            "redirect_uri": _redirect_uri(),
        }
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.post(JIRA_TOKEN_URL, json=data)
            res.raise_for_status()
            tok = res.json()
        access_token = tok.get("access_token")
        refresh_token = tok.get("refresh_token")
        expires_in = tok.get("expires_in", 3600)
        token_expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat() + "Z"

        # For MVP we cannot derive cloudid/site here; clients must provide or we discover on first call
        credentials = {
            "access_token": encrypt_str(access_token),
            "refresh_token": encrypt_str(refresh_token) if refresh_token else None,
            "token_expires_at": token_expires_at,
            "scopes": tok.get("scope", "").split(" "),
        }
        await upsert_connection(tenant_id, self.id, credentials, metadata={"status": "connected"})
        return {"status": "ok"}

    async def _get_auth(self, tenant_id: str) -> Dict[str, Any]:
        conn = await get_connection(tenant_id, self.id)
        if not conn or not conn.get("credentials"):
            raise ValueError("No credentials")
        creds = conn["credentials"]
        return {
            "access_token": decrypt_str(creds["access_token"]),
            "refresh_token": decrypt_str(creds["refresh_token"]) if creds.get("refresh_token") else None,
            "token_expires_at": creds.get("token_expires_at"),
            "cloud_id": creds.get("cloud_id"),  # optional
        }

    # PUBLIC_INTERFACE
    async def search(self, tenant_id: str, query: str, resource: str, page: int = 1, per_page: int = 20):
        """Search Jira issues using JQL text query across accessible projects."""
        auth = await self._get_auth(tenant_id)
        access_token = auth["access_token"]

        # Discover cloud ids
        async with httpx.AsyncClient(timeout=20) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            res = await client.get("https://api.atlassian.com/oauth/token/accessible-resources", headers=headers)
            res.raise_for_status()
            resources = res.json()
        if not resources:
            return {"items": []}
        cloud_id = resources[0]["id"]

        jql = f'text ~ "{query}" ORDER BY updated DESC'
        search_url = f"{JIRA_API_BASE}/{cloud_id}/rest/api/3/search"
        params = {"jql": jql, "startAt": (page - 1) * per_page, "maxResults": per_page}
        async with httpx.AsyncClient(timeout=20) as client:
            headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
            res = await client.get(search_url, headers=headers, params=params)
            res.raise_for_status()
            data = res.json()
        items: List[NormalizedItem] = []
        for issue in data.get("issues", []):
            key = issue["key"]
            fields = issue.get("fields", {})
            title = fields.get("summary", key)
            url = f"https://id.atlassian.com/login?continue=https%3A%2F%2F{resources[0]['url'].replace('https://', '')}%2Fbrowse%2F{key}"
            items.append(NormalizedItem(id=key, title=title, url=url, type="issue", subtitle=fields.get("status", {}).get("name")))
        return {"items": items}

    # PUBLIC_INTERFACE
    async def create(self, tenant_id: str, resource: str, payload: Dict[str, Any]) -> CreateResult:
        """Create a Jira issue: payload { project_key, summary, description? }"""
        auth = await self._get_auth(tenant_id)
        access_token = auth["access_token"]

        async with httpx.AsyncClient(timeout=20) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            res = await client.get("https://api.atlassian.com/oauth/token/accessible-resources", headers=headers)
            res.raise_for_status()
            resources = res.json()
        if not resources:
            raise ValueError("No accessible Jira cloud")
        cloud_id = resources[0]["id"]

        issue_url = f"{JIRA_API_BASE}/{cloud_id}/rest/api/3/issue"
        body = {
            "fields": {
                "project": {"key": payload["project_key"]},
                "summary": payload["summary"],
                "issuetype": {"name": "Task"},
            }
        }
        if payload.get("description"):
            body["fields"]["description"] = payload["description"]
        async with httpx.AsyncClient(timeout=20) as client:
            headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
            res = await client.post(issue_url, headers=headers, json=body)
            res.raise_for_status()
            created = res.json()
        key = created.get("key") or created.get("id")
        url = f"{resources[0]['url']}/browse/{key}"
        return CreateResult(id=key, title=payload["summary"], url=url, type="issue")

    # PUBLIC_INTERFACE
    async def list_supporting(self, tenant_id: str, resource: str):
        """List supporting resources like projects."""
        if resource != "projects":
            return []
        auth = await self._get_auth(tenant_id)
        access_token = auth["access_token"]

        async with httpx.AsyncClient(timeout=20) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            res = await client.get("https://api.atlassian.com/oauth/token/accessible-resources", headers=headers)
            res.raise_for_status()
            resources = res.json()
        if not resources:
            return []
        cloud_id = resources[0]["id"]
        projects_url = f"{JIRA_API_BASE}/{cloud_id}/rest/api/3/project/search"
        async with httpx.AsyncClient(timeout=20) as client:
            headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
            res = await client.get(projects_url, headers=headers)
            res.raise_for_status()
            data = res.json()
        return [{"key": p["key"], "name": p["name"]} for p in data.get("values", [])]
