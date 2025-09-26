# PUBLIC_INTERFACE
"""
Confluence connector (demo). Implements BaseConnector with mocked calls.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List

from .base import BaseConnector, NormalizedItem, CreateResult
from ..core.token_store import token_store


class ConfluenceConnector(BaseConnector):
    id = "confluence"
    display_name = "Confluence"
    supports_oauth = True
    required_scopes: List[str] = ["read:confluence-content", "write:confluence-content"]

    def get_oauth_authorize_url(self, tenant_id: str, state: str) -> Dict[str, str]:
        return {"authorize_url": f"https://auth.atlassian.com/authorize?client_id=dummy_conf&state={state}", "state": state}

    def exchange_code_for_tokens(self, tenant_id: str, code: str, state: str) -> Dict[str, Any]:
        creds = {
            "access_token": f"conf_at_{int(time.time())}",
            "refresh_token": "conf_rt_mock",
            "token_expires_at": int(time.time()) + 3600,
            "site_url": "https://example.atlassian.net/wiki",
            "scopes": self.required_scopes,
        }
        token_store().set(tenant_id, self.id, creds)
        return {"status": "connected"}

    def validate_pat(self, tenant_id: str, credentials: Dict[str, Any]) -> bool:
        if not credentials.get("api_token") or not credentials.get("email"):
            return False
        token_store().set(tenant_id, self.id, {
            "pat": "set",
            "email": credentials["email"],
            "site_url": credentials.get("site_url", "https://example.atlassian.net/wiki"),
            "scopes": ["basic"],
        })
        return True

    def search(self, tenant_id: str, query: str, resource: str, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        items = [
            NormalizedItem(id=f"PAGE-{i}", title=f"Page about {query} #{i}", url=f"https://example.atlassian.net/wiki/spaces/SPACE/pages/{i}", type="page")
            for i in range((page - 1) * per_page + 1, page * per_page + 1)
        ]
        return {"items": [i.model_dump() for i in items], "page": page, "per_page": per_page}

    def create(self, tenant_id: str, resource: str, payload: Dict[str, Any]) -> CreateResult:
        page_id = "123456"
        itm = NormalizedItem(id=page_id, title=payload.get("title", "New Page"), url=f"https://example.atlassian.net/wiki/pages/{page_id}", type="page")
        return CreateResult(item=itm)

    def list_collections(self, tenant_id: str, resource: str) -> Dict[str, Any]:
        spaces = [{"key": "SPACE", "name": "Space A"}, {"key": "DOCS", "name": "Docs Space"}]
        return {"spaces": spaces}


confluence_connector = ConfluenceConnector()
