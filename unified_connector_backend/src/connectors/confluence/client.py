from __future__ import annotations

from typing import Any, Dict

import httpx

from src.core.response import normalize_upstream_error


class ConfluenceClient:
    """Confluence Cloud REST API client using Atlassian platform with Bearer access token."""

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
        # Confluence REST base
        return f"{self.base_url}/ex/confluence/{self.cloud_id}{path}"

    async def search_pages(self, query: str, limit: int = 25, cursor: str | None = None) -> Dict[str, Any]:
        """Search pages (v2 API does not support complex query; use title contains via q and pagination)."""
        url = self._url("/wiki/api/v2/pages")
        params: Dict[str, Any] = {"q": query, "limit": limit}
        if cursor:
            params["cursor"] = cursor
        async with httpx.AsyncClient(timeout=self.timeout, headers=self._headers()) as client:
            resp = await client.get(url, params=params)
            if resp.status_code >= 400:
                return normalize_upstream_error(resp.status_code, resp.text, headers=resp.headers, default_message="Confluence search failed")
            data = resp.json()
            results = data.get("results", [])
            next_cursor = (data.get("_links") or {}).get("next")
            return {"status": "ok", "data": {"pages": results, "paging": {"next_cursor": next_cursor}}, "meta": {}}

    async def list_spaces(self, limit: int = 25, cursor: str | None = None) -> Dict[str, Any]:
        url = self._url("/wiki/api/v2/spaces")
        params: Dict[str, Any] = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        async with httpx.AsyncClient(timeout=self.timeout, headers=self._headers()) as client:
            resp = await client.get(url, params=params)
            if resp.status_code >= 400:
                return normalize_upstream_error(resp.status_code, resp.text, headers=resp.headers, default_message="Confluence spaces list failed")
            data = resp.json()
            results = data.get("results", [])
            next_cursor = (data.get("_links") or {}).get("next")
            return {"status": "ok", "data": {"spaces": results, "paging": {"next_cursor": next_cursor}}, "meta": {}}

    async def create_page(self, space_key: str, title: str, body: str) -> Dict[str, Any]:
        """Create a Confluence page in the specified space (v2 API)."""
        url = self._url("/wiki/api/v2/pages")
        payload = {
            "spaceId": None,
            "status": "current",
            "title": title,
            "body": {
                "storage": {
                    "value": body,
                    "representation": "storage",
                }
            },
            "space": {"key": space_key},
        }
        async with httpx.AsyncClient(timeout=self.timeout, headers=self._headers()) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code >= 400:
                return normalize_upstream_error(resp.status_code, resp.text, headers=resp.headers, default_message="Confluence create page failed")
            return {"status": "ok", "data": {"page": resp.json()}, "meta": {}}
