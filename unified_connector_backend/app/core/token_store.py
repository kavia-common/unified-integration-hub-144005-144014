# PUBLIC_INTERFACE
"""
Thread-safe in-memory token/connection store.

- Per-tenant, per-connector storage.
- Optional AES-GCM encryption via ENCRYPTION_KEY.
- No persistence; ephemeral only.
"""
from __future__ import annotations

import threading
import time
from typing import Dict, Optional, Any

from pydantic import BaseModel, Field

from .security import encrypt_blob, decrypt_blob


class _Entry(BaseModel):
    connector_id: str
    tenant_id: str
    # encrypted credentials bytes
    data: bytes
    status: str = "connected"
    last_refreshed: float = Field(default_factory=lambda: time.time())


class _MemoryStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        # key = (tenant_id, connector_id)
        self._store: Dict[tuple[str, str], _Entry] = {}

    def set(self, tenant_id: str, connector_id: str, credentials: Dict[str, Any]) -> None:
        blob = encrypt_blob(str(credentials).encode("utf-8"))
        with self._lock:
            self._store[(tenant_id, connector_id)] = _Entry(
                connector_id=connector_id,
                tenant_id=tenant_id,
                data=blob,
                status="connected",
                last_refreshed=time.time(),
            )

    def get(self, tenant_id: str, connector_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            entry = self._store.get((tenant_id, connector_id))
            if not entry:
                return None
            raw = decrypt_blob(entry.data).decode("utf-8")
            # credentials were stringified dict; eval safely by literal_eval
            import ast
            return ast.literal_eval(raw)

    def delete(self, tenant_id: str, connector_id: str) -> bool:
        with self._lock:
            return self._store.pop((tenant_id, connector_id), None) is not None

    def status(self, tenant_id: str, connector_id: str) -> Optional[str]:
        with self._lock:
            entry = self._store.get((tenant_id, connector_id))
            return entry.status if entry else None

    def list_connectors_for_tenant(self, tenant_id: str) -> Dict[str, str]:
        with self._lock:
            return {cid: e.status for (t, cid), e in self._store.items() if t == tenant_id}


_store = _MemoryStore()


# PUBLIC_INTERFACE
def token_store() -> _MemoryStore:
    """Return the singleton in-memory token store."""
    return _store
