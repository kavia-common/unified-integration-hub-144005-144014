from __future__ import annotations

from typing import Any, Dict


def map_issue(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Map raw Jira issue to normalized structure (stub)."""
    return {
        "id": raw.get("id"),
        "key": raw.get("key"),
        "summary": ((raw.get("fields") or {}).get("summary")),
        "issuetype": (((raw.get("fields") or {}).get("issuetype") or {}).get("name")),
        "status": (((raw.get("fields") or {}).get("status") or {}).get("name")),
        "raw": raw,
    }


def map_project(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Map raw Jira project to normalized structure (stub)."""
    return {
        "id": raw.get("id"),
        "key": raw.get("key"),
        "name": raw.get("name"),
        "raw": raw,
    }
