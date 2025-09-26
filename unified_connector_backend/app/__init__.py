# PUBLIC_INTERFACE
"""
Unified Connector Backend application package.

This package contains:
- main: FastAPI app instance with health endpoints
- asgi: ASGI entrypoint exposing `app` for uvicorn/gunicorn
- server: Python module runner to start uvicorn with environment configuration
"""

# Re-export FastAPI app for convenience so 'uvicorn app:app' also works if used.
try:
    from .main import app  # noqa: F401
except Exception:
    # Do not raise at import time for package import; asgi.py has explicit diagnostics.
    app = None  # type: ignore
