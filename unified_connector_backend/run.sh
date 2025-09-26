#!/usr/bin/env bash
set -euo pipefail
export APP_VERSION=${APP_VERSION:-0.1.0}
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --reload
