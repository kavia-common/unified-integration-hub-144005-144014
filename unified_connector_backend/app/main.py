# PUBLIC_INTERFACE
"""
Backwards-compatible FastAPI app exposure.

This module imports the app from the new src/ package structure so that existing
commands like `uvicorn app.asgi:app` and `python -m app.server` continue to work.
"""
from unified_connector_backend.app import app  # re-export FastAPI app instance
