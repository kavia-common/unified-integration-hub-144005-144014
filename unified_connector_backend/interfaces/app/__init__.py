# PUBLIC_INTERFACE
"""
Local app package shim under interfaces/ to ensure 'uvicorn app.server:app'
works when the working directory is this folder. This forwards to the backend's
FastAPI app located in src/unified_connector_backend/app.py.
"""
