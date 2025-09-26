print('Hello Hi 1!')
import os
from dotenv import load_dotenv
import uvicorn

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
