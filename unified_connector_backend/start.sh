#!/usr/bin/env bash
# PUBLIC_INTERFACE
# Start script for Unified Connector Backend.
# CHANGE NOTE: Default port updated to 3002 (was 3001).
# Ensures the FastAPI app runs on 0.0.0.0:3002 by default so orchestrators detect readiness.
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
export PORT="${PORT:-3002}"
export LOG_LEVEL="${LOG_LEVEL:-info}"
# RELOAD may be set externally; default to false for containerized runs
export RELOAD="${RELOAD:-false}"

# Expose PYTHONPATH explicitly to include current directory, aiding module import resolution in CI/container envs.
export PYTHONPATH="${PYTHONPATH:-${SCRIPT_DIR}}"

echo "[start.sh] Working directory: $(pwd)"
echo "[start.sh] HOST=${HOST} PORT=${PORT} RELOAD=${RELOAD} LOG_LEVEL=${LOG_LEVEL}"
echo "[start.sh] PYTHONPATH=${PYTHONPATH}"
echo "[start.sh] Launching Python module runner: python -m app.server"
# Use the Python module runner which internally calls uvicorn with the configured app and loads .env
exec python -m app.server
