# PUBLIC_INTERFACE
from app.main import app  # noqa: F401

"""
ASGI application entrypoint.

This exposes `app` for ASGI servers like uvicorn or gunicorn to import directly:
    uvicorn app.asgi:app --host 0.0.0.0 --port 3001

Notes:
- The FastAPI application defines:
  - GET /          -> simple root message
  - GET /health    -> readiness/liveness probe returning {"status":"ok"}
"""
