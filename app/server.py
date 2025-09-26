"""
Top-level server entrypoint wrapper for Unified Connector Backend.

This module exposes `app` to support running:
    uvicorn app.server:app

It dynamically loads the actual FastAPI app object from:
    unified_connector_backend/app/main.py

This file exists primarily for CI/preview environments where the working
directory is the workspace root (one level above `unified_connector_backend`).
For containerized runs, the backend uses its own runner in
`unified_connector_backend/app/server.py`.
"""

import os
import sys
import importlib.util
from typing import Any

# Resolve path to the backend's main.py
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_WORKSPACE_ROOT = os.path.dirname(_THIS_DIR)
_BACKEND_DIR = os.path.join(_WORKSPACE_ROOT, "unified_connector_backend")
_BACKEND_MAIN_PATH = os.path.join(_BACKEND_DIR, "app", "main.py")


def _load_backend_main_module() -> Any:
    """
    Load the backend's app.main module from file location to avoid
    package name collisions with this top-level 'app' wrapper.
    """
    if not os.path.exists(_BACKEND_MAIN_PATH):
        raise RuntimeError(
            f"Backend main.py not found at: {_BACKEND_MAIN_PATH}. "
            "Ensure the repository layout is intact."
        )
    spec = importlib.util.spec_from_file_location("backend_app_main", _BACKEND_MAIN_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to create import spec for backend_app_main")
    module = importlib.util.module_from_spec(spec)
    sys.modules["backend_app_main"] = module
    spec.loader.exec_module(module)
    return module


# Load the actual FastAPI app object from the backend module
_backend_main = _load_backend_main_module()
app = getattr(_backend_main, "app", None)
if app is None:
    raise RuntimeError(
        "Failed to load FastAPI 'app' from backend module. "
        "Verify unified_connector_backend/app/main.py defines 'app'."
    )


# PUBLIC_INTERFACE
def main() -> None:
    """
    Optional: Run the server directly from the workspace root.

    This method mirrors the container behavior by launching uvicorn with the
    loaded FastAPI app. It respects HOST/PORT/LOG_LEVEL/RELOAD environment variables.
    """
    import uvicorn  # local import to avoid dependency at import time

    def _bool_env(name: str, default: bool = False) -> bool:
        val = os.getenv(name)
        if val is None:
            return default
        return val.strip().lower() in {"1", "true", "yes", "on"}

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "3001"))
    log_level = os.getenv("LOG_LEVEL", "info")
    reload = _bool_env("RELOAD", False)

    print(f"[top-level server] Starting Unified Connector Backend on {host}:{port} (reload={reload}, log_level={log_level})")
    uvicorn.run(app, host=host, port=port, reload=reload, log_level=log_level)


if __name__ == "__main__":
    main()
