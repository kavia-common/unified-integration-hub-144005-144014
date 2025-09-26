"""
Module runner to start the FastAPI server using the src/ package structure.

Usage:
    python -m unified_connector_backend.run
"""
import os
from dotenv import load_dotenv
import uvicorn
from .app import app
from .config import get_host, get_port, get_log_level, env_bool


# PUBLIC_INTERFACE
def main():
    """Entry point to start the FastAPI server with environment-based configuration."""
    load_dotenv()
    host = get_host()
    port = get_port()
    log_level = get_log_level()
    reload = env_bool("RELOAD", False)

    print(f"[server] Starting Unified Connector Backend on {host}:{port} (reload={reload}, log_level={log_level})")
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )


if __name__ == "__main__":
    main()
