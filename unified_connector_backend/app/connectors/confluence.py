import os
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, Any, List

import httpx
from .base import BaseConnector, OAuthAuthorize, NormalizedItem, CreateResult
from ..db.mongo import upsert_connection, get_connection
from ..security.crypto import encrypt_str, decrypt_str

CONF_AUTH_URL = "https://auth.atlassian.com/authorize"
CONF_TOKEN_URL = "https://auth.atlassian.com/oauth/token"
CONF_API_ROOT = "https://api.atlassian.com/ex/confluence"

def _client_id():
    return os.getenv("CONFLUENCE_CLIENT_ID", "")

def _client_secret():
    return os.getenv("CONFLUENCE_CLIENT_SECRET", "")

def _redirect_uri():
    return os.getenv("CONFLUENCE_REDIRECTION_URI", "")

SCOPES = [
    "read:confluence-content.summary",
    "read:confluence-space.summary",
    "write:confluence-content",
    "offline_access",
]

class ConfluenceConnector(BaseConnector):
    id = "confluence"
    display_name = "Confluence"
    supports_oauth = True
    required_scopes = SCOPES

    # PUBLIC_INTERFACE
    async def get_oauth_authorize_url(self, tenant_id: str, state: str) -> OAuthAuthorize:
        params = {
            "audience": "api.atlassian.com",
            "client_id": _client_id(),
            "scope": " ".join(SCOPES),
            "redirect_uri": _redirect_uri(),
            "state": state,
            "response_type": "code",
            "prompt": "consent",
        }
        url = f"{CONF_AUTH_URL}?{urllib.parse.urlencode(params)}"
        return OAuthAuthorize(authorize_url=url, state=state)

    # PUBLIC_INTERFACE
    async def exchange_code_for_tokens(self, tenant_id: str, code: str, state: str) -> Dict[str, Any]:
        data = {
            "grant_type": "authorization_code",
            "client_id": _client_id(),
            "client_secret": _client_secret(),
            "code": code,
            "redirect_uri": _redirect_uri(),
        }
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.post(CONF_TOKEN_URL, json=data)
            res.raise_for_status()
            tok = res.json()
        access_token = tok.get("access_token")
        refresh_token = tok.get("refresh_token")
        expires_in = tok.get("expires_in", 3600)
        token_expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat() + "Z"
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
        }

    # PUBLIC_INTERFACE
    async def search(self, tenant_id: str, query: str, resource: str, page: int = 1, per_page: int = 20):
        auth = await self._get_auth(tenant_id)
        access_token = auth["access_token"]
        async with httpx.AsyncClient(timeout=20) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            res = await client.get("https://api.atlassian.com/oauth/token/accessible-resources", headers=headers)
            res.raise_for_status()
            resources = res.json()
        if not resources:
            return {"items": []}
        cloud_id = resources[0]["id"]
        # Confluence CQL search
        url = f"{CONF_API_ROOT}/{cloud_id}/wiki/rest/api/search"
        params = {"cql": f'text ~ "{query}"', "limit": per_page, "start": (page - 1) * per_page}
        async with httpx.AsyncClient(timeout=20) as client:
            headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
            res = await client.get(url, headers=headers, params=params)
            res.raise_for_status()
            data = res.json()
        items: List[NormalizedItem] = []
        for r in data.get("results", []):
            title = r.get("title") or r.get("content", {}).get("title") or "Untitled"
            content_id = r.get("content", {}).get("id") or r.get("id")
            url = f"{resources[0]['url']}/wiki/spaces/{r.get('space', {}).get('key','')}/pages/{content_id}"
            items.append(NormalizedItem(id=str(content_id), title=title, url=url, type="page", subtitle=r.get("space", {}).get("name")))
        return {"items": items}

    # PUBLIC_INTERFACE
    async def create(self, tenant_id: str, resource: str, payload: Dict[str, Any]) -> CreateResult:
        """Create a Confluence page: payload { space_key, title, body }"""
        auth = await self._get_auth(tenant_id)
        access_token = auth["access_token"]
        async with httpx.AsyncClient(timeout=20) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            res = await client.get("https://api.atlassian.com/oauth/token/accessible-resources", headers=headers)
            res.raise_for_status()
            resources = res.json()
        if not resources:
            raise ValueError("No accessible Confluence cloud")
        cloud_id = resources[0]["id"]
        url = f"{CONF_API_ROOT}/{cloud_id}/wiki/rest/api/content"
        body = {
            "type": "page",
            "title": payload["title"],
            "space": {"key": payload["space_key"]},
            "body": {
                "storage": {
                    "value": payload.get("body", ""),
                    "representation": "storage",
                }
            },
        }
        async with httpx.AsyncClient(timeout=20) as client:
            headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
            res = await client.post(url, headers=headers, json=body)
            res.raise_for_status()
            created = res.json()
        page_id = created.get("id")
        page_url = f"{resources[0]['url']}/wiki/spaces/{payload['space_key']}/pages/{page_id}"
        return CreateResult(id=str(page_id), title=payload["title"], url=page_url, type="page")

    # PUBLIC_INTERFACE
    async def list_supporting(self, tenant_id: str, resource: str):
        """List spaces"""
        if resource != "spaces":
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
        url = f"{CONF_API_ROOT}/{cloud_id}/wiki/rest/api/space"
        async with httpx.AsyncClient(timeout=20) as client:
            headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
            res = await client.get(url, headers=headers, params={"limit": 100})
            res.raise_for_status()
            data = res.json()
        return [{"key": s["key"], "name": s["name"]} for s in data.get("results", [])]
