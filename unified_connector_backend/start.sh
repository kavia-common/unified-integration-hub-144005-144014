#!/usr/bin/env bash
# PUBLIC_INTERFACE
# Start script for Unified Connector Backend.
# Ensures the FastAPI app runs on 0.0.0.0:3001 by default so orchestrators detect readiness.
set -euo pipefail

export HOST="${HOST:-0.0.0.0}"
export PORT="${PORT:-3001}"
export LOG_LEVEL="${LOG_LEVEL:-info}"
# RELOAD may be set externally; default to false for containerized runs
export RELOAD="${RELOAD:-false}"

echo "[start.sh] Launching uvicorn app.asgi:app on ${HOST}:${PORT} (reload=${RELOAD}, log_level=${LOG_LEVEL})"
exec uvicorn app.asgi:app --host "${HOST}" --port "${PORT}" --log-level "${LOG_LEVEL}"
