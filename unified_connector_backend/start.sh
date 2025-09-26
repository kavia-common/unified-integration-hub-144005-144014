#!/usr/bin/env bash
# PUBLIC_INTERFACE
# Start script for Unified Connector Backend.
# Ensures the FastAPI app runs on 0.0.0.0:3001 by default so orchestrators detect readiness.
set -euo pipefail

# Always run from the directory where this script resides so that 'app' package is importable.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Load .env if present to avoid hardcoding and to respect environment configuration
if [ -f ".env" ]; then
  # shellcheck disable=SC1091
  set -a
  . ./.env
  set +a
fi

export HOST="${HOST:-0.0.0.0}"
export PORT="${PORT:-3001}"
export LOG_LEVEL="${LOG_LEVEL:-info}"
# RELOAD may be set externally; default to false for containerized runs
export RELOAD="${RELOAD:-false}"

# Expose PYTHONPATH explicitly to include current directory, aiding uvicorn import resolution in some CI environments.
export PYTHONPATH="${PYTHONPATH:-${SCRIPT_DIR}}"

echo "[start.sh] Working directory: $(pwd)"
echo "[start.sh] PYTHONPATH=${PYTHONPATH}"
echo "[start.sh] Launching uvicorn app.asgi:app on ${HOST}:${PORT} (reload=${RELOAD}, log_level=${LOG_LEVEL})"
exec uvicorn app.asgi:app --host "${HOST}" --port "${PORT}" --log-level "${LOG_LEVEL}"
