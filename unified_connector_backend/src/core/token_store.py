from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any, Tuple

import httpx

from src.core.db import tenant_collection, upsert_by_id
from src.core.logging import get_logger
from src.core.models import OAuthState
from src.core.security import encrypt_secret, decrypt_secret, compute_expiry, is_expired
from src.core.settings import get_settings

logger = get_logger(__name__)


class TokenStore:
    """Manages encrypted storage and refresh of OAuth tokens per tenant + connector."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.collection = tenant_collection(tenant_id, "connectors")
        self.settings = get_settings()

    # PUBLIC_INTERFACE
    def save_tokens(
        self,
        connector_id: str,
        name: str,
        access_token: str,
        refresh_token: Optional[str],
        scope: Optional[str],
        expires_at: Optional[datetime],
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Upsert connector metadata with encrypted tokens."""
        payload = {
            "_id": connector_id,
            "id": connector_id,
            "name": name,
            "tenant_id": self.tenant_id,
            "meta": {
                "status": "linked",
                "oauth": {
                    "access_token": encrypt_secret(access_token) if access_token else None,
                    "refresh_token": encrypt_secret(refresh_token) if refresh_token else None,
                    "expires_at": expires_at,
                    "scope": scope,
                },
                "extra": extra or {},
            },
        }
        upsert_by_id(self.collection, _id=connector_id, payload=payload)

    # PUBLIC_INTERFACE
    def get_tokens(self, connector_id: str) -> Optional[OAuthState]:
        """Fetch encrypted tokens for connector and return as OAuthState (still encrypted)."""
        doc = self.collection.find_one({"_id": connector_id})
        if not doc:
            return None
        meta = (doc.get("meta") or {})
        oauth = (meta.get("oauth") or {})
        return OAuthState(
            access_token=oauth.get("access_token"),
            refresh_token=oauth.get("refresh_token"),
            expires_at=oauth.get("expires_at"),
            scope=oauth.get("scope"),
        )

    # PUBLIC_INTERFACE
    def get_decrypted_access(self, connector_id: str) -> Tuple[Optional[str], Optional[str], Optional[datetime]]:
        """Return decrypted access_token, refresh_token and expiry."""
        st = self.get_tokens(connector_id)
        if not st:
            return None, None, None
        return decrypt_secret(st.access_token), decrypt_secret(st.refresh_token), st.expires_at

    # PUBLIC_INTERFACE
    async def ensure_valid_token_atlassian(
        self,
        connector_id: str,
        name: str,
        client_id: str,
        client_secret: Optional[str],
        refresh_token: Optional[str],
        redirect_uri: str,
    ) -> Optional[str]:
        """Refresh Atlassian access token if expired, and persist back. Returns current access token or None."""
        access_token, rt, expires_at = self.get_decrypted_access(connector_id)
        if access_token and not is_expired(expires_at):
            return access_token

        # If expired and no refresh_token, cannot refresh
        refresh_tok = refresh_token or rt
        if not refresh_tok:
            return None

        token_url = "https://auth.atlassian.com/oauth/token"
        data = {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "refresh_token": refresh_tok,
        }
        if client_secret:
            data["client_secret"] = client_secret
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(token_url, json=data)
            if resp.status_code >= 400:
                logger.error("Atlassian refresh failed with status %s", resp.status_code)
                return None
            payload = resp.json()
            new_access = payload.get("access_token")
            new_refresh = payload.get("refresh_token", refresh_tok)  # sometimes rotated
            expires_in = payload.get("expires_in", 3600)
            scope = payload.get("scope")
            expires_at = compute_expiry(int(expires_in))
            # Save updated tokens
            self.save_tokens(
                connector_id=connector_id,
                name=name,
                access_token=new_access,
                refresh_token=new_refresh,
                scope=scope,
                expires_at=expires_at,
            )
            return new_access
