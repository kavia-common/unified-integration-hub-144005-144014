from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from src.core.response import normalize_upstream_error


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

    async def search_issues(self, jql: str, start_at: int = 0, max_results: int = 50) -> Dict[str, Any]:
        """Search issues using JQL with pagination."""
        url = self._url("/rest/api/3/search")
        params = {"jql": jql, "startAt": start_at, "maxResults": max_results}
        async with httpx.AsyncClient(timeout=self.timeout, headers=self._headers()) as client:
            resp = await client.get(url, params=params)
            if resp.status_code >= 400:
                return normalize_upstream_error(resp.status_code, resp.text, headers=resp.headers, default_message="Jira search failed")
            data = resp.json()
            issues: List[Dict[str, Any]] = data.get("issues", [])
            total = data.get("total")
            start_at_out = data.get("startAt", start_at)
            max_results_out = data.get("maxResults", max_results)
            return {"status": "ok", "data": {"issues": issues, "paging": {"total": total, "startAt": start_at_out, "maxResults": max_results_out}}, "meta": {}}

    async def list_projects(self, start_at: int = 0, max_results: int = 50) -> Dict[str, Any]:
        """List projects visible to the user with pagination."""
        url = self._url("/rest/api/3/project/search")
        params = {"startAt": start_at, "maxResults": max_results}
        async with httpx.AsyncClient(timeout=self.timeout, headers=self._headers()) as client:
            resp = await client.get(url, params=params)
            if resp.status_code >= 400:
                return normalize_upstream_error(resp.status_code, resp.text, headers=resp.headers, default_message="Jira projects listing failed")
            data = resp.json()
            values = data.get("values", [])
            total = data.get("total", None)
            start_at_out = data.get("startAt", start_at)
            max_results_out = data.get("maxResults", max_results)
            return {"status": "ok", "data": {"projects": values, "paging": {"total": total, "startAt": start_at_out, "maxResults": max_results_out}}, "meta": {}}

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
                return normalize_upstream_error(resp.status_code, resp.text, headers=resp.headers, default_message="Jira create issue failed")
            return {"status": "ok", "data": {"issue": resp.json()}, "meta": {}}
