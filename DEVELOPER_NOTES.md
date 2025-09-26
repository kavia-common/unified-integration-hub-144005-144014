# Developer Notes — Backend install path

If you are installing Python dependencies or starting the backend from the repository root, ensure you point pip to the backend's requirements file:

Correct path:
    pip install -r unified_connector_backend/requirements.txt

From within the backend directory (cd unified_connector_backend):
    pip install -r requirements.txt

Typical start (from backend directory):
    uvicorn app.asgi:app --host 0.0.0.0 --port 3002
or
    python -m app.server

The backend is located at:
    unified-integration-hub-144005-144014/unified_connector_backend
