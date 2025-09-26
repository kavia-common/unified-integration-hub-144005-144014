# PUBLIC_INTERFACE
"""
Structured logging helpers for the service.

- Avoids logging secrets.
- Adds request_id and tenant_id context.
"""
from __future__ import annotations

import json
import sys
import time
from typing import Any, Dict, Optional


def _mask_secret(value: Any) -> Any:
    if value is None:
        return None
    text = str(value)
    if len(text) <= 6:
        return "***"
    return f"{text[:2]}***{text[-2:]}"


def log(level: str, message: str, *, request_id: Optional[str] = None, tenant_id: Optional[str] = None, **kwargs: Any) -> None:
    record: Dict[str, Any] = {
        "ts": round(time.time(), 3),
        "level": level.lower(),
        "msg": message,
    }
    if request_id:
        record["request_id"] = request_id
    if tenant_id:
        record["tenant_id"] = tenant_id

    # Never log tokens/credentials plainly; mask some common fields if provided.
    sensitive_keys = {"token", "access_token", "refresh_token", "apiToken", "password", "secret", "authorization"}
    for k, v in list(kwargs.items()):
        if k in sensitive_keys:
            record[k] = _mask_secret(v)
        else:
            record[k] = v
    sys.stdout.write(json.dumps(record) + "\n")
    sys.stdout.flush()


# PUBLIC_INTERFACE
def info(message: str, **kwargs: Any) -> None:
    """Info level structured log."""
    log("INFO", message, **kwargs)


# PUBLIC_INTERFACE
def warning(message: str, **kwargs: Any) -> None:
    """Warning level structured log."""
    log("WARN", message, **kwargs)


# PUBLIC_INTERFACE
def error(message: str, **kwargs: Any) -> None:
    """Error level structured log."""
    log("ERROR", message, **kwargs)
