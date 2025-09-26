# unified-integration-hub-144005-144014

This workspace contains:
- unified_connector_backend/ → FastAPI backend (primary Python project)

For convenience, a root-level requirements.txt is provided and delegates to:
- unified_connector_backend/requirements.txt

Typical usage from repo root:
- python3 -m venv .venv && . .venv/bin/activate
- pip install -r requirements.txt
- uvicorn unified_connector_backend/app.server:app --host 0.0.0.0 --port 3001

Alternatively, use the helper scripts:
- bash unified-integration-hub-144005-144014/dev_start_backend.sh
- bash unified-integration-hub-144005-144014/unified_connector_backend/dev_start.sh
