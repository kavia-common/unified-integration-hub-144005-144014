#!/usr/bin/env bash
# Simple start script for local/dev environments.
# Usage:
#   bash start.sh
# Ensures .env is loaded (if present) and runs uvicorn using the app.server module.

set -euo pipefail

if [ -f ".env" ]; then
  # load .env without exporting comments
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

export HOST="${HOST:-0.0.0.0}"
export PORT="${PORT:-3001}"
export LOG_LEVEL="${LOG_LEVEL:-info}"
export RELOAD="${RELOAD:-false}"

echo "[start] Starting Unified Connector Backend on ${HOST}:${PORT} (reload=${RELOAD}, log_level=${LOG_LEVEL})"
python -m app.server
