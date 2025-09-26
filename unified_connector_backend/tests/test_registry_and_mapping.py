# PUBLIC_INTERFACE
"""
Unit tests for connector registry and normalized mapping.
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_connectors_requires_tenant():
    r = client.get("/api/connectors")
    assert r.status_code == 422  # missing header

    r = client.get("/api/connectors", headers={"X-Tenant-Id": "t1"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert any(x["id"] == "jira" for x in data)
    assert any(x["id"] == "confluence" for x in data)


def test_jira_create_issue_normalized():
    body = {"project_key": "DEMO", "summary": "Test Issue", "description": "Body"}
    r = client.post("/api/connectors/jira/issues", headers={"X-Tenant-Id": "t1"}, json=body)
    assert r.status_code == 200
    item = r.json()["data"]["item"]
    assert item["type"] == "issue"
    assert item["id"].startswith("DEMO-")
