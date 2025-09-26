"""
Server entrypoint and ASGI app exposure for Unified Connector Backend.

This module serves two purposes:
1) ASGI export: Exposes `app` so you can run:
       uvicorn app.server:app --host 0.0.0.0 --port 3001
2) Module runner: Provides `main()` so you can run:
       python -m app.server
   which loads environment variables and starts uvicorn with the configured host/port.
"""

import os
import sys
from dotenv import load_dotenv
import uvicorn

print('Hello Hi 3!')

# Import the FastAPI app from app.main and expose it at module level for ASGI servers.
try:
    from app.main import app  # noqa: F401
except Exception as import_err:
    # Provide helpful diagnostics if import fails so container logs show context
    print(f"[server] Failed to import FastAPI app from app.main: {import_err}")
    print(f"[server] CWD={os.getcwd()} PYTHONPATH={os.environ.get('PYTHONPATH')} sys.path[0:3]={sys.path[0:3]}")
    raise


# PUBLIC_INTERFACE
def main():
    """Entry point to start the FastAPI server with environment-based configuration."""
    # Load environment variables from .env if present (no hardcoding of secrets)
    load_dotenv()

    def _bool_env(name: str, default: bool = False) -> bool:
        val = os.getenv(name)
        if val is None:
            return default
        return val.strip().lower() in {"1", "true", "yes", "on"}

    # Default to container port 3001 to satisfy orchestrator checks
    port = int(os.getenv("PORT", "3001"))
    host = os.getenv("HOST", "0.0.0.0")
    log_level = os.getenv("LOG_LEVEL", "info")
    reload = _bool_env("RELOAD", False)

    # Informative startup print (visible in container logs)
    print(f"[server] Starting Unified Connector Backend on {host}:{port} (reload={reload}, log_level={log_level})")

    # Start uvicorn pointing to the already-imported FastAPI app object
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )


if __name__ == "__main__":
    main()
