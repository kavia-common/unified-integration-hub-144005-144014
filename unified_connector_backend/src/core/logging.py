import logging
import os
import json
from typing import Optional

from .observability import get_structured_logger

_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
_LOG_FORMAT = os.getenv("LOG_FORMAT", "json").lower()  # 'json' or 'plain'


class JsonFormatter(logging.Formatter):
    """Emit logs as single-line JSON with common fields and context (request_id, tenant, route)."""

    def format(self, record: logging.LogRecord) -> str:
        base = {
            "ts": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            # Context fields added by filter (see observability._ContextFilter)
            "request_id": getattr(record, "request_id", "-"),
            "tenant_id": getattr(record, "tenant_id", "public"),
            "route": getattr(record, "route", "-"),
        }
        # Include extras if present (avoid non-serializable)
        for key, val in record.__dict__.items():
            if key in ("msg", "args", "exc_info", "exc_text", "stack_info", "stacklevel", "levelno", "levelname",
                       "msecs", "relativeCreated", "created", "thread", "threadName", "processName", "process",
                       "pathname", "filename", "module", "lineno", "funcName", "name"):
                continue
            # do not include duplicates of context fields
            if key in ("request_id", "tenant_id", "route"):
                continue
            try:
                json.dumps({key: val})
                base[key] = val
            except Exception:
                base[key] = str(val)
        if record.exc_info:
            base["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(base, separators=(",", ":"))

def _configure_root_logger(level: str) -> logging.Logger:
    logger = logging.getLogger()
    if not logger.handlers:
        handler = logging.StreamHandler()
        if _LOG_FORMAT == "json":
            handler.setFormatter(JsonFormatter())
        else:
            fmt = "%(asctime)s | %(levelname)s | %(name)s | [%(request_id)s %(tenant_id)s %(route)s] %(message)s"
            handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


root_logger = _configure_root_logger(_LOG_LEVEL)


# PUBLIC_INTERFACE
def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a module logger configured with the global format and level."""
    # Attach context filter to the child logger for structured context
    return get_structured_logger(name or __name__)
