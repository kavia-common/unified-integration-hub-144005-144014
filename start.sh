#!/usr/bin/env bash
set -euo pipefail

# Create and activate venv
python3 -m venv .venv
. .venv/bin/activate

# Install using workspace-level requirements shim
pip install -r requirements.txt

# Start backend using compatibility entrypoint
exec uvicorn unified_connector_backend/app.server:app --host 0.0.0.0 --port "${PORT:-3001}"
