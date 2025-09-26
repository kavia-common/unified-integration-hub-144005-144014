from typing import Dict, Any
import httpx
from ...repositories.connections_repo import get_connection, upsert_connection
from ...models.connection import Connection, Credentials
from ...core.config import settings
from datetime import datetime, timedelta

ATL_TOKEN_URL = "https://auth.atlassian.com/oauth/token"
ATL_AUTH_URL = "https://auth.atlassian.com/authorize"
CLOUD_API = "https://api.atlassian.com"

JIRA_SCOPES = [
    "read:jira-user",
    "read:jira-work",
    "write:jira-work",
    "offline_access",
]

def _headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json", "Content-Type": "application/json"}

async def build_authorize_url(state: str) -> Dict[str, Any]:
    params = {
        "audience": "api.atlassian.com",
        "client_id": settings.JIRA_CLIENT_ID,
        "scope": " ".join(JIRA_SCOPES),
        "redirect_uri": str(settings.JIRA_REDIRECT_URI),
        "state": state,
        "response_type": "code",
        "prompt": "consent",
    }
    from urllib.parse import urlencode
    return {"authorize_url": f"{ATL_AUTH_URL}?{urlencode(params)}", "state": state}

async def exchange_code_for_tokens(tenant_id: str, code: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            ATL_TOKEN_URL,
            json={
                "grant_type": "authorization_code",
                "client_id": settings.JIRA_CLIENT_ID,
                "client_secret": settings.JIRA_CLIENT_SECRET,
                "code": code,
                "redirect_uri": str(settings.JIRA_REDIRECT_URI),
            },
        )
        resp.raise_for_status()
        data = resp.json()
    access_token = data["access_token"]
    refresh_token = data.get("refresh_token")
    expires_in = int(data.get("expires_in", 3600))
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    # Discover cloud id
    async with httpx.AsyncClient(timeout=20, headers=_headers(access_token)) as client:
        res = await client.get(f"{CLOUD_API}/oauth/token/accessible-resources")
        res.raise_for_status()
        resources = res.json()
    site_url = resources[0]["url"] if resources else None
    conn = Connection(
        tenant_id=tenant_id,
        connector_id="jira",
        credentials=Credentials(
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=expires_at,
            site_url=site_url,
            scopes=JIRA_SCOPES,
        ),
        metadata={"connected": True},
        refreshed_at=datetime.utcnow(),
    )
    await upsert_connection(conn)
    return {"status": "ok", "connected": True}

async def search_issues(tenant_id: str, query: str, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
    conn = await get_connection(tenant_id, "jira")
    if not conn or not conn.credentials.access_token:
        return {"items": []}
    token = conn.credentials.access_token
    # JQL search
    start_at = (page - 1) * per_page
    async with httpx.AsyncClient(timeout=20, headers=_headers(token)) as client:
        # Need cloud id
        res_cloud = await client.get(f"{CLOUD_API}/oauth/token/accessible-resources")
        res_cloud.raise_for_status()
        cloud_id = res_cloud.json()[0]["id"]
        res = await client.get(
            f"{CLOUD_API}/ex/jira/{cloud_id}/rest/api/3/search",
            params={"jql": query, "startAt": start_at, "maxResults": per_page, "fields": "summary"},
        )
        res.raise_for_status()
        data = res.json()
    items = []
    base_url = conn.credentials.site_url or ""
    for issue in data.get("issues", []):
        key = issue["key"]
        title = issue["fields"].get("summary", key)
        items.append({"id": key, "title": title, "url": f"{base_url}/browse/{key}", "type": "issue"})
    return {"items": items}

async def create_issue(tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    conn = await get_connection(tenant_id, "jira")
    if not conn or not conn.credentials.access_token:
        return {"status": "error", "code": "NOT_CONNECTED", "message": "Jira not connected"}
    token = conn.credentials.access_token
    async with httpx.AsyncClient(timeout=20, headers=_headers(token)) as client:
        res_cloud = await client.get(f"{CLOUD_API}/oauth/token/accessible-resources")
        res_cloud.raise_for_status()
        cloud_id = res_cloud.json()[0]["id"]
        res = await client.post(
            f"{CLOUD_API}/ex/jira/{cloud_id}/rest/api/3/issue",
            json={
                "fields": {
                    "project": {"key": payload["project_key"]},
                    "summary": payload["summary"],
                    "issuetype": {"name": payload.get("issue_type", "Task")},
                    "description": payload.get("description", ""),
                }
            },
        )
        res.raise_for_status()
        data = res.json()
    key = data.get("key")
    base_url = conn.credentials.site_url or ""
    return {"id": key, "title": payload["summary"], "url": f"{base_url}/browse/{key}", "type": "issue"}
