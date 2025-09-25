from __future__ import annotations

from typing import Any, Dict, List


def map_page(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Map raw Confluence page to normalized structure.

    Normalized entity fields:
    - id: string
    - title: string
    - spaceKey: string (if present)
    - status: current/draft/etc.
    """
    return {
        "id": raw.get("id") or raw.get("uuid"),
        "title": raw.get("title"),
        "spaceKey": (raw.get("space") or {}).get("key"),
        "status": raw.get("status"),
    }


def map_space(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Map raw Confluence space to normalized structure."""
    return {
        "id": raw.get("id"),
        "key": raw.get("key"),
        "name": raw.get("name"),
    }


# PUBLIC_INTERFACE
def normalize_search_pages(raw_pages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize Confluence search pages result to unified schema:
    { status: 'ok', data: { items: [...] } }
    """
    items = [map_page(x) for x in raw_pages]
    return {"status": "ok", "data": {"items": items, "paging": {}}, "meta": {}}


# PUBLIC_INTERFACE
def normalize_create_page(raw_page: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize Confluence create page response to unified schema:
    { status: 'ok', data: { id, title } }
    """
    return {"status": "ok", "data": {"id": raw_page.get("id"), "title": raw_page.get("title")}, "meta": {}}
