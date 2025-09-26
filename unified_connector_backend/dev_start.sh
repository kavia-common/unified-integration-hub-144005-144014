#!/usr/bin/env bash
# Helper script to create venv, install dependencies, and start uvicorn from the correct working directory.
# Usage: bash unified-integration-hub-144005-144014/unified_connector_backend/dev_start.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

python3 -m venv .venv
. .venv/bin/activate

# Install using the container-level requirements.txt (this file exists relative to SCRIPT_DIR)
pip install --upgrade pip
pip install -r requirements.txt

# Run uvicorn using the asgi app path
exec uvicorn app.server:app --host 0.0.0.0 --port "${PORT:-3001}"
