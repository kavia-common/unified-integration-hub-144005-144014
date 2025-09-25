from __future__ import annotations

from typing import Any, Dict, List


def map_issue(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Map raw Jira issue to normalized structure.

    Normalized entity fields:
    - id: string
    - key: string
    - title: from fields.summary
    - type: issue type name
    - status: workflow status name
    """
    fields = raw.get("fields") or {}
    issuetype = (fields.get("issuetype") or {}).get("name")
    status = (fields.get("status") or {}).get("name")
    return {
        "id": raw.get("id"),
        "key": raw.get("key"),
        "title": fields.get("summary"),
        "type": issuetype,
        "status": status,
    }


def map_project(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Map raw Jira project to normalized structure."""
    return {
        "id": raw.get("id"),
        "key": raw.get("key"),
        "name": raw.get("name"),
    }


# PUBLIC_INTERFACE
def normalize_search_issues(raw_issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize Jira search issues response into unified schema:
    { status: 'ok', data: { items: [...], paging: { total?, next? } } }
    """
    items = [map_issue(x) for x in raw_issues]
    data = {"items": items, "paging": {}}
    return {"status": "ok", "data": data, "meta": {}}


# PUBLIC_INTERFACE
def normalize_create_issue(raw_issue: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize Jira create issue response into unified schema:
    { status: 'ok', data: { id, key } }
    """
    return {
        "status": "ok",
        "data": {
            "id": raw_issue.get("id"),
            "key": raw_issue.get("key"),
        },
        "meta": {},
    }
