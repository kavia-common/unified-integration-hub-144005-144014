# Unified Connector Backend

FastAPI backend for Unified Connector Platform.

## Setup

1. Create and populate a `.env` (if needed). Do not commit secrets.
2. Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Troubleshooting: Startup fails or port not ready
- Ensure Python dependencies are installed from requirements.txt. A missing FastAPI package will prevent the server from starting.
- Quick check:

```bash
python - <<'PY'
import importlib
for m in ['fastapi','uvicorn','pydantic','dotenv']:
    try:
        importlib.import_module(m)
        print(m, 'OK')
    except Exception as e:
        print(m, 'MISSING', e)
PY
```

- If any are missing, run:

```bash
pip install -r requirements.txt
```

Port/health check mismatch (3001 vs 3002)
- The backend honors the PORT environment variable. Default is 3002 if PORT is not set.
- Many preview/deploy platforms inject PORT (often PORT=3001). In that case, the server will bind to that injected value.
- If your orchestrator or preview health check expects the service on 3002 while PORT=3001, it will appear as "backend failed to start" even though it is running on 3001.
- Resolution options (choose one):
  1) Set PORT=3002 in the platform/container environment so the server binds to 3002.
  2) Update the platform’s health check and port mapping to use the injected PORT value (e.g., 3001).
  3) If the platform requires a specific port, remove conflicting overrides and let the platform-provided PORT take precedence.
- Diagnostics:
  - start.sh and server.py will log the resolved HOST and PORT at startup.
  - If PORT resolves to 3001 a [WARN] line is printed to highlight possible health check mismatches.

## Run locally

Default port is 3002 (configurable via `PORT`).

```bash
# Option A: module runner (loads .env)
python -m app.server

# Option B: uvicorn directly (explicit)
uvicorn app.asgi:app --host 0.0.0.0 --port 3002

# Option C: start script (recommended for containers/preview)
bash start.sh
```

Container/preview entrypoint
- A Procfile is provided: `web: bash start.sh`
- The start script binds to 0.0.0.0:${PORT:-3002} to satisfy orchestrator health checks.

- The server starts at http://localhost:3002
- API docs: http://localhost:3002/docs
- OpenAPI JSON: http://localhost:3002/openapi.json

CHANGE NOTE:
- The backend default port has been updated from 3001 to 3002. Override via environment variable `PORT` as needed.

## Health

- `GET /` -> `{ "message": "Unified Connector Backend is running." }`
- `GET /health` -> `{ "status": "ok" }`

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

- `PORT` (default: 3002) — The app binds to this port. If your platform injects `PORT`, that value will be used.
- `HOST` (default: 0.0.0.0)
- `RELOAD` (default: false)
- `LOG_LEVEL` (default: info)
- `ALLOWED_ORIGINS` (optional, comma-separated) — for CORS. Leave empty in development to allow all origins.
- See `.env.example` for a sample configuration. Do not commit secrets.
