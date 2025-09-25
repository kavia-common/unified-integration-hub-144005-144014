from __future__ import annotations

from typing import Any, Dict


def map_page(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Map raw Confluence page to normalized structure (stub)."""
    return {
        "id": raw.get("id") or raw.get("uuid"),
        "title": raw.get("title"),
        "spaceKey": ((raw.get("space") or {}).get("key")),
        "status": raw.get("status"),
        "raw": raw,
    }


def map_space(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Map raw Confluence space to normalized structure (stub)."""
    return {
        "id": raw.get("id"),
        "key": raw.get("key"),
        "name": raw.get("name"),
        "raw": raw,
    }
