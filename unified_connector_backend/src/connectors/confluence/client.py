from __future__ import annotations

from typing import Any, Dict


class ConfluenceClient:
    """Minimal Confluence client (stub)."""

    def __init__(self, base_url: str | None = None, access_token: str | None = None):
        self.base_url = base_url or "https://api.atlassian.com"
        self.access_token = access_token

    async def search_pages(self, query: str) -> Dict[str, Any]:
        # Stub implementation
        return {"pages": [], "query": query}
