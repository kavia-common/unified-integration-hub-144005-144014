import logging
import os
from typing import Optional

_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


def _configure_root_logger(level: str) -> logging.Logger:
    logger = logging.getLogger()
    if not logger.handlers:
        handler = logging.StreamHandler()
        fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


root_logger = _configure_root_logger(_LOG_LEVEL)


# PUBLIC_INTERFACE
def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a module logger configured with the global format and level."""
    return logging.getLogger(name or __name__)
