# Unified Connector Backend

FastAPI backend for a modular connectors platform with tenant isolation, unified APIs, and ephemeral credential storage.

Key features:
- Modular connectors with a registry (Jira, Confluence included).
- Thread-safe in-memory token/connection store.
- Optional AES-GCM encryption for stored credentials via ENCRYPTION_KEY.
- Unified response envelopes and stable error codes.
- Tenant isolation via X-Tenant-Id header.
- Structured logging (no secrets are logged).
- Basic unit and integration tests.

## Project Structure

app/
- api/
  - models.py
  - routes/
    - connectors.py
    - connections.py
- connectors/
  - base.py
  - registry.py
  - jira.py
  - confluence.py
- core/
  - settings.py
  - security.py
  - token_store.py
  - tenancy.py
  - errors.py
  - logging.py
  - retry.py
- asgi.py
- main.py
- server.py
tests/
- test_registry_and_mapping.py
- test_oauth_callback.py

## Setup

1. Create and populate a `.env` (if needed). Do not commit secrets.
2. Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Run locally

Default port is 3001 (configurable via `PORT`).

```bash
# Option A: module runner (loads .env)
python -m app.server

# Option B: uvicorn directly (explicit)
uvicorn app.asgi:app --host 0.0.0.0 --port 3001

# Option C: start script (recommended for containers/preview)
bash start.sh
```

- The server starts at http://localhost:3001
- API docs: http://localhost:3001/docs
- OpenAPI JSON: http://localhost:3001/openapi.json

## Health

- GET / -> `{ "message": "Unified Connector Backend is running." }`
- GET /health -> `{ "status": "ok" }`

## Unified API (selected)

Headers: `X-Tenant-Id: <tenant>`

- GET /api/connectors
- GET /api/connectors/{id}/oauth/login
- GET /api/connectors/{id}/oauth/callback?code=...&state=...
- POST /api/connectors/{id}/pat/validate
- GET /api/connectors/{id}/search?q=...&resource=issue|page&page=1&per_page=20
- POST /api/connectors/jira/issues
- POST /api/connectors/confluence/pages
- GET /api/connectors/jira/projects
- GET /api/connectors/confluence/spaces
- DELETE /api/connectors/{id}/connection
- GET /api/connections

All responses use unified envelopes:
```json
{ "status": "ok", "data": { ... } }
```
Errors:
```json
{ "status": "error", "code": "VALIDATION", "message": "..." }
```

## Security & Storage

- All credentials are stored in-memory only, per-tenant, never persisted.
- Optional encryption at rest (in memory) via AES-GCM if `ENCRYPTION_KEY` is set.
- No secrets are logged; logs are structured JSON.

## Environment Variables

See `.env.example` for full list. Common:
- PORT (default: 3001)
- HOST (default: 0.0.0.0)
- LOG_LEVEL (default: info)
- ALLOWED_ORIGINS (default: *)
- ENCRYPTION_KEY (optional; enables AES-GCM encryption)
- JIRA_CLIENT_ID / JIRA_CLIENT_SECRET / JIRA_REDIRECTION_URI (optional demo)
- CONFLUENCE_CLIENT_ID / CONFLUENCE_CLIENT_SECRET / CONFLUENCE_REDIRECTION_URI (optional demo)

## Limitations

- Vendor calls are mocked for the demo; replace with real client integrations.
- Tokens are ephemeral and cleared on process restart.
- No database connections present by design for this demo.
