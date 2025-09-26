import os
from dotenv import load_dotenv
import uvicorn

# PUBLIC_INTERFACE
def main():
    """Entry point to start the FastAPI server with environment-based configuration.

    Notes:
    - Binds to HOST:PORT where HOST defaults to 0.0.0.0 and PORT defaults to 3002.
    - Reads environment variables from a local .env if present:
        HOST, PORT, LOG_LEVEL, RELOAD
    - Signals: start.sh uses `exec python -m app.server` so SIGINT/SIGTERM are
      delivered to the uvicorn process, enabling graceful shutdown.
    - Troubleshooting:
        * If startup fails with "address already in use", either free the port or set PORT to a different value.
        * Verify required deps: fastapi, uvicorn, pydantic, python-dotenv.
        * You can run `uvicorn app.asgi:app --host 0.0.0.0 --port 3002` directly to isolate uvicorn issues.

    CHANGE NOTE:
    Default port updated from 3001 to 3002 to align with project configuration. Override via environment variable PORT if needed.
    """
    # Print requested message on server start
    print("Hello Hi 1!")
    # Load environment variables from .env if present (no hardcoding of secrets)
    load_dotenv()

    def _bool_env(name: str, default: bool = False) -> bool:
        val = os.getenv(name)
        if val is None:
            return default
        return val.strip().lower() in {"1", "true", "yes", "on"}

    # Default to container port 3002 to satisfy orchestrator checks
    port = int(os.getenv("PORT", "3002"))
    host = os.getenv("HOST", "0.0.0.0")
    log_level = os.getenv("LOG_LEVEL", "info")
    reload = _bool_env("RELOAD", False)

    # Informative startup print (visible in container logs)
    print(f"[server] Starting Unified Connector Backend on {host}:{port} (reload={reload}, log_level={log_level})")
    if port == 3001:
        # Extra diagnostic to help detect platform/preview misconfiguration expecting different port
        print("[server][WARN] PORT resolved to 3001. If your platform expects 3002, set PORT=3002 or update preview/deploy health checks.")

    # Start uvicorn pointing to FastAPI app
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )

if __name__ == "__main__":
    main()
