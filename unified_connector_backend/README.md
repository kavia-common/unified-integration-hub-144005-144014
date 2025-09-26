# Unified Connector Backend

FastAPI backend for Unified Connector Platform.

This repository has been refactored to use a conventional `src/` layout and `interfaces/` folder for OpenAPI.

## Structure

- src/
  - unified_connector_backend/
    - __init__.py
    - app.py               # FastAPI app factory and routing composition
    - config.py            # Environment and CORS configuration helpers
    - routes/
      - __init__.py
      - health.py          # Root and health endpoints
      - integrations.py    # Jira and Confluence test/config endpoints
    - utils/
      - __init__.py
      - http_client.py     # Minimal HTTP client helpers
      - atlassian.py       # Basic auth test helpers for Atlassian cloud
  - run.py                 # Module runner (loads .env and starts uvicorn)
- interfaces/
  - openapi.json           # OpenAPI schema (can be exported at runtime)
- app/
  - __init__.py            # Backwards-compatible shim
  - asgi.py                # ASGI entrypoint (importing from src package)
  - main.py                # Backwards-compatible shim mapping to new app
  - server.py              # Backwards-compatible module runner
  - requirements.txt
- requirements.txt
- start.sh (optional in containers)

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

# Option C: new src runner (recommended for development)
python -m unified_connector_backend.run
```

Container/preview entrypoint
- A Procfile may use: `web: bash start.sh`
- The start script binds to 0.0.0.0:${PORT:-3001} to satisfy orchestrator health checks.

- The server starts at http://localhost:3001
- API docs: http://localhost:3001/docs
- OpenAPI JSON: http://localhost:3001/openapi.json

## Health

- `GET /` -> `{ "message": "Unified Connector Backend is running." }`
- `GET /health` -> `{ "status": "ok" }`
- `GET /docs-status` -> `{ "ok": true }`

## New Integration Endpoints

- `POST /api/integrations/jira`
- `POST /api/integrations/confluence`

Body:
```json
{
  "baseUrl": "https://your-domain.atlassian.net",
  "email_or_username": "you@example.com",
  "apiToken": "atlassian_api_token"
}
```

Behavior:
- Credentials are stored in-memory (for development). Do not use this in production without secure storage and encryption.
- The server performs a basic authentication check against the vendor API and returns:
  - 200: `{ "success": true, "message": "Connection successful." }`
  - 400: `{ "detail": "<reason>" }`

## CORS

CORS is enabled for all origins by default for development. In production, restrict origins by setting an environment variable and updating the middleware:

- Suggested env var: `ALLOWED_ORIGINS` (comma-separated list), not currently required.
- Frontend should call these endpoints from the configured backend URL.

## Environment Variables

- `PORT` (default: 3001)
- `HOST` (default: 0.0.0.0)
- `RELOAD` (default: false)
- `LOG_LEVEL` (default: info)
- `ALLOWED_ORIGINS` (optional, comma-separated)
