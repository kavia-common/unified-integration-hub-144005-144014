# PUBLIC_INTERFACE
"""
Top-level 'app' package wrapper for CI/preview import resolution.

Purpose:
- Allow 'uvicorn app.server:app' to work when the working directory is the
  workspace root (one level above unified_connector_backend).
- Dynamically loads the actual FastAPI app defined in
  unified_connector_backend/app/main.py, avoiding duplication.

Note:
- The real application code lives under 'unified_connector_backend/app'.
- Containerized runs should continue using the module runner inside that folder
  (e.g., 'python -m app.server' from within unified_connector_backend).
"""
