from typing import List
import os


# PUBLIC_INTERFACE
def get_allowed_origins() -> List[str]:
    """Return allowed CORS origins from ALLOWED_ORIGINS env var (comma-separated) or ['*'] if not set."""
    _allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "").strip()
    return ["*"] if not _allowed_origins_env else [o.strip() for o in _allowed_origins_env.split(",") if o.strip()]


def env_bool(name: str, default: bool = False) -> bool:
    """Read a boolean environment variable with sensible defaults."""
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def get_host() -> str:
    """Get bind host, defaulting to 0.0.0.0 for container environments."""
    return os.getenv("HOST", "0.0.0.0")


def get_port() -> int:
    """Get server port, default 3001."""
    try:
        return int(os.getenv("PORT", "3001"))
    except ValueError:
        return 3001


def get_log_level() -> str:
    """Get uvicorn log level, default 'info'."""
    return os.getenv("LOG_LEVEL", "info")
