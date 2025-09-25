from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx


class JiraClient:
    """Jira Cloud REST API client using Atlassian platform with Bearer access token.

    Notes:
    - Uses https://api.atlassian.com/ex/jira/{cloudid}/rest/api/3 endpoints.
    - Requires caller to supply cloud_id (site identifier) for the tenant context.
    """

    def __init__(self, access_token: str, cloud_id: str, base_url: str | None = None, timeout: float = 20.0):
        self.base_url = base_url or "https://api.atlassian.com"
        self.access_token = access_token
        self.cloud_id = cloud_id
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _url(self, path: str) -> str:
        # Jira REST v3 base for cloud
        return f"{self.base_url}/ex/jira/{self.cloud_id}{path}"

    async def search_issues(self, jql: str) -> Dict[str, Any]:
        """Search issues using JQL."""
        url = self._url("/rest/api/3/search")
        params = {"jql": jql}
        async with httpx.AsyncClient(timeout=self.timeout, headers=self._headers()) as client:
            resp = await client.get(url, params=params)
            if resp.status_code >= 400:
                return {"ok": False, "status": resp.status_code, "error": "jira_search_failed", "details": resp.text}
            data = resp.json()
            issues: List[Dict[str, Any]] = data.get("issues", [])
            return {"ok": True, "issues": issues}

    async def list_projects(self) -> Dict[str, Any]:
        """List projects visible to the user."""
        url = self._url("/rest/api/3/project/search")
        async with httpx.AsyncClient(timeout=self.timeout, headers=self._headers()) as client:
            resp = await client.get(url)
            if resp.status_code >= 400:
                return {"ok": False, "status": resp.status_code, "error": "jira_projects_failed", "details": resp.text}
            data = resp.json()
            values = data.get("values", [])
            return {"ok": True, "projects": values}

    async def create_issue(self, project_key: str, summary: str, issuetype: str = "Task", description: Optional[str] = None) -> Dict[str, Any]:
        """Create a Jira issue in the specified project."""
        url = self._url("/rest/api/3/issue")
        payload: Dict[str, Any] = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "issuetype": {"name": issuetype},
            }
        }
        if description:
            payload["fields"]["description"] = description  # Basic text; advanced doc format out of scope here
        async with httpx.AsyncClient(timeout=self.timeout, headers=self._headers()) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code >= 400:
                return {"ok": False, "status": resp.status_code, "error": "jira_create_issue_failed", "details": resp.text}
            return {"ok": True, "issue": resp.json()}
