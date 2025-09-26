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

Container/preview entrypoint
- A Procfile is provided: `web: bash start.sh`
- The start script binds to 0.0.0.0:${PORT:-3001} to satisfy orchestrator health checks.

- The server starts at http://localhost:3001
- API docs: http://localhost:3001/docs
- OpenAPI JSON: http://localhost:3001/openapi.json

## Health

- `GET /` -> `{ "message": "Unified Connector Backend is running." }`
- `GET /health` -> `{ "status": "ok" }`

## Environment Variables

- `PORT` (default: 3001)
- `HOST` (default: 0.0.0.0)
- `RELOAD` (default: false)
- `LOG_LEVEL` (default: info)
