# PUBLIC_INTERFACE
"""
Integration test for OAuth callback (mocked).
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_oauth_flow_mock():
    # Start
    r = client.get("/api/connectors/jira/oauth/login", headers={"X-Tenant-Id": "t2"})
    assert r.status_code == 200
    payload = r.json()
    assert "authorize_url" in payload and "state" in payload

    # Callback
    r2 = client.get(
        "/api/connectors/jira/oauth/callback",
        headers={"X-Tenant-Id": "t2"},
        params={"code": "dummycode", "state": payload["state"]},
    )
    assert r2.status_code == 200
    assert r2.json()["data"]["status"] == "connected"

    # Connection should now appear
    r3 = client.get("/api/connections", headers={"X-Tenant-Id": "t2"})
    assert r3.status_code == 200
    ids = [c["connector_id"] for c in r3.json()["data"]]
    assert "jira" in ids
