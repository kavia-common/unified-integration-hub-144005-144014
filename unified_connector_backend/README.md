# Unified Connector Backend (FastAPI)

Features:
- Modular connectors registry (Jira, Confluence).
- OAuth 2.0 flows for Atlassian.
- MongoDB persistence with encrypted tokens.
- Normalized search/create endpoints.
- OpenAPI at /openapi.json.

Quickstart:
1) Create .env from .env.example and fill in Atlassian OAuth info.
2) Install deps: pip install -r requirements.txt
3) Run: uvicorn unified_connector_backend.app.main:app --reload --host 0.0.0.0 --port 8000

Key endpoints:
- GET /connectors
- GET /connectors/jira/oauth/login
- GET /connectors/jira/search?q=...
- POST /connectors/jira/issues
- GET /connectors/confluence/oauth/login
- GET /connectors/confluence/search?q=...
- POST /connectors/confluence/pages
