"""
Server shim under interfaces/ so that the command:
    uvicorn app.server:app
works even if the working directory is unified_connector_backend/interfaces.

It forwards imports to the backend's src package and exposes `app`.
It also provides a main() entrypoint for 'python -m app.server'.
"""
from __future__ import annotations

import os
import sys
from dotenv import load_dotenv

# Compute paths relative to this file to reach the backend src directory
_THIS_DIR = os.path.dirname(__file__)
_INTERFACES_DIR = os.path.abspath(os.path.join(_THIS_DIR, os.pardir))
_BACKEND_ROOT = os.path.abspath(os.path.join(_INTERFACES_DIR, os.pardir))
_BACKEND_SRC = os.path.join(_BACKEND_ROOT, "src")

# Ensure backend src is importable
if _BACKEND_SRC not in sys.path:
    sys.path.insert(0, _BACKEND_SRC)

# Import the FastAPI app from the backend src package
try:
    from unified_connector_backend.app import app as _fastapi_app  # type: ignore
except Exception as src_import_err:  # pragma: no cover
    # Fallback: try backend compatibility layer (app.main) if needed
    try:
        if _BACKEND_ROOT not in sys.path:
            sys.path.insert(0, _BACKEND_ROOT)
        from app.main import app as _fastapi_app  # type: ignore
    except Exception as compat_err:  # pragma: no cover
        print(f"[interfaces app.server] Failed to import FastAPI app from src: {src_import_err}")
        print(f"[interfaces app.server] Fallback import also failed: {compat_err}")
        raise

# Expose the FastAPI app for uvicorn
app = _fastapi_app


# PUBLIC_INTERFACE
def main() -> None:
    """Start the Unified Connector Backend using uvicorn with environment configuration."""
    load_dotenv()

    def _bool_env(name: str, default: bool = False) -> bool:
        val = os.getenv(name)
        if val is None:
            return default
        return val.strip().lower() in {"1", "true", "yes", "on"}

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "3001"))
    log_level = os.getenv("LOG_LEVEL", "info")
    reload = _bool_env("RELOAD", False)

    import uvicorn
    print(f"[interfaces app.server] Starting Unified Connector Backend on {host}:{port} (reload={reload}, log_level={log_level})")
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )


if __name__ == "__main__":
    main()
