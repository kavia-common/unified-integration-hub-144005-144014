from __future__ import annotations

from typing import Any, Dict

import httpx


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

    async def search_pages(self, query: str) -> Dict[str, Any]:
        url = self._url("/wiki/api/v2/pages")
        params = {"q": query}
        async with httpx.AsyncClient(timeout=self.timeout, headers=self._headers()) as client:
            resp = await client.get(url, params=params)
            if resp.status_code >= 400:
                return {"ok": False, "status": resp.status_code, "error": "conf_search_failed", "details": resp.text}
            data = resp.json()
            return {"ok": True, "pages": data.get("results", [])}

    async def list_spaces(self) -> Dict[str, Any]:
        url = self._url("/wiki/api/v2/spaces")
        async with httpx.AsyncClient(timeout=self.timeout, headers=self._headers()) as client:
            resp = await client.get(url)
            if resp.status_code >= 400:
                return {"ok": False, "status": resp.status_code, "error": "conf_spaces_failed", "details": resp.text}
            data = resp.json()
            return {"ok": True, "spaces": data.get("results", [])}

    async def create_page(self, space_key: str, title: str, body: str) -> Dict[str, Any]:
        """Create a Confluence page in the specified space (v2 API)."""
        url = self._url("/wiki/api/v2/pages")
        payload = {
            "spaceId": None,  # v2 API supports space by ID; here we use legacy v2 that also accepts spaceKey in bodyProperties
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
                return {"ok": False, "status": resp.status_code, "error": "conf_create_page_failed", "details": resp.text}
            return {"ok": True, "page": resp.json()}
