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

# If PORT resolves to 3001, print a diagnostic warning so platform logs are clear.
if [ "${PORT}" = "3001" ]; then
  echo "[start.sh][WARN] PORT is set to 3001 by the environment. Backend will bind to 3001."
  echo "[start.sh][WARN] If your preview/deploy expects 3002, set PORT=3002 or update the platform health check/port mapping."
fi

echo "[start.sh] Launching Python module runner: python -m app.server"
# Use the Python module runner which internally calls uvicorn with the configured app and loads .env
exec python -m app.server
