import pytest
from httpx import AsyncClient
from unified_connector_backend.app.main import app

@pytest.mark.asyncio
async def test_list_connectors():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.get("/connectors")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    ids = {c["id"] for c in data["items"]}
    assert "jira" in ids and "confluence" in ids

@pytest.mark.asyncio
async def test_jira_oauth_login_url_shape():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.get("/connectors/jira/oauth/login")
    assert res.status_code == 200
    d = res.json()
    assert "authorize_url" in d and "state" in d

@pytest.mark.asyncio
async def test_search_generic_proxy_empty_without_connection(monkeypatch):
    # Without connection, search should return empty items gracefully
    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.get("/connectors/jira/search", params={"q": "project = TEST"})
    assert res.status_code == 200
    assert "items" in res.json()
