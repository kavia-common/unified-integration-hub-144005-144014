# PUBLIC_INTERFACE
"""
Jira connector (demo). Implements BaseConnector methods with mocked vendor calls
while exercising token storage and normalization.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List

from .base import BaseConnector, NormalizedItem, CreateResult
from ..core.token_store import token_store


class JiraConnector(BaseConnector):
    id = "jira"
    display_name = "Jira"
    supports_oauth = True
    required_scopes: List[str] = ["read:jira-work", "write:jira-work"]

    def get_oauth_authorize_url(self, tenant_id: str, state: str) -> Dict[str, str]:
        # In a real implementation, craft Atlassian OAuth URL with scopes.
        return {"authorize_url": f"https://auth.atlassian.com/authorize?client_id=dummy&state={state}", "state": state}

    def exchange_code_for_tokens(self, tenant_id: str, code: str, state: str) -> Dict[str, Any]:
        # Mock exchange: store fake tokens
        creds = {
            "access_token": f"jira_at_{int(time.time())}",
            "refresh_token": "jira_rt_mock",
            "token_expires_at": int(time.time()) + 3600,
            "site_url": "https://example.atlassian.net",
            "scopes": self.required_scopes,
        }
        token_store().set(tenant_id, self.id, creds)
        return {"status": "connected"}

    def validate_pat(self, tenant_id: str, credentials: Dict[str, Any]) -> bool:
        # For demo, require api_token and email
        if not credentials.get("api_token") or not credentials.get("email"):
            return False
        token_store().set(tenant_id, self.id, {
            "pat": "set",
            "email": credentials["email"],
            "site_url": credentials.get("site_url", "https://example.atlassian.net"),
            "scopes": ["basic"],
        })
        return True

    def search(self, tenant_id: str, query: str, resource: str, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        # Mock data
        items = [
            NormalizedItem(id=f"JIRA-00{i}", title=f"Issue about {query} #{i}", url=f"https://example.atlassian.net/browse/JIRA-00{i}", type="issue")
            for i in range((page - 1) * per_page + 1, page * per_page + 1)
        ]
        return {"items": [i.model_dump() for i in items], "page": page, "per_page": per_page}

    def create(self, tenant_id: str, resource: str, payload: Dict[str, Any]) -> CreateResult:
        key = payload.get("project_key", "DEMO") + "-123"
        itm = NormalizedItem(id=key, title=payload.get("summary", "New Issue"), url=f"https://example.atlassian.net/browse/{key}", type="issue")
        return CreateResult(item=itm)

    def list_collections(self, tenant_id: str, resource: str) -> Dict[str, Any]:
        # e.g., list projects
        projects = [{"key": "DEMO", "name": "Demo Project"}, {"key": "APP", "name": "App Project"}]
        return {"projects": projects}


jira_connector = JiraConnector()
