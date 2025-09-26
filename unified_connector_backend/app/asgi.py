# PUBLIC_INTERFACE
# Provide defensive import with explicit error log to aid startup diagnostics.
import os
import sys
try:
    from app.main import app  # noqa: F401
except Exception as import_err:
    # Printing ensures the error is visible in container logs if import fails.
    # Re-raise so the process exits and orchestrator reports failure explicitly.
    print(f"[asgi] Failed to import FastAPI app from app.main: {import_err}")
    print(f"[asgi] CWD={os.getcwd()} PYTHONPATH={os.environ.get('PYTHONPATH')} sys.path[0:3]={sys.path[0:3]}")
    raise

"""
ASGI application entrypoint.

This exposes `app` for ASGI servers like uvicorn or gunicorn to import directly, binding to the configured host/port:
    uvicorn app.asgi:app --host 0.0.0.0 --port 3001

Notes:
- The FastAPI application defines:
  - GET /          -> simple root message
  - GET /health    -> readiness/liveness probe returning {"status":"ok"}
- If startup fails, logs printed here include CWD and PYTHONPATH to diagnose import resolution issues.
"""
