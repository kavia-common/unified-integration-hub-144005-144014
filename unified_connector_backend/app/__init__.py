# PUBLIC_INTERFACE
"""
Unified Connector Backend application package.

This package contains:
- main: FastAPI app instance with health endpoints
- asgi: ASGI entrypoint exposing `app` for uvicorn/gunicorn
- server: Python module runner to start uvicorn with environment configuration
"""
