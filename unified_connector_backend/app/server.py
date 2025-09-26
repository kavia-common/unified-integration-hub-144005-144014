import os
from dotenv import load_dotenv
import uvicorn

# Load environment variables from .env if present (no hardcoding of secrets)
load_dotenv()

def _bool_env(name: str, default: bool = False) -> bool:
    """Parse boolean environment variables safely."""
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}

if __name__ == "__main__":
    # Default to container port 3001 to satisfy orchestrator checks
    port = int(os.getenv("PORT", "3001"))
    host = os.getenv("HOST", "0.0.0.0")

    # Informative startup print (visible in container logs)
    print(f"Starting Unified Connector Backend on {host}:{port} (reload={_bool_env('RELOAD', False)})")

    # Start uvicorn pointing to FastAPI app
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=_bool_env("RELOAD", False),
        log_level=os.getenv("LOG_LEVEL", "info"),
    )
