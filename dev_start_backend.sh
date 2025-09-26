#!/usr/bin/env bash
# Convenience script to run backend from repo root in CI.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR/unified_connector_backend"

python3 -m venv .venv
. .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

exec uvicorn app.server:app --host 0.0.0.0 --port "${PORT:-3001}"
