from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar
from typing import Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Context variables to carry across the request lifecycle
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
tenant_id_ctx: ContextVar[str] = ContextVar("tenant_id", default="public")
route_ctx: ContextVar[str] = ContextVar("route", default="-")

# In-memory basic counters/gauges (simple, process-local) for quick metrics
_METRICS: Dict[str, float] = {
    "requests_total": 0.0,
    "requests_errors_total": 0.0,
    "search_requests_total": 0.0,
    "search_latency_ms_sum": 0.0,
    "token_refresh_total": 0.0,
}

def metrics_snapshot() -> Dict[str, float]:
    """Return a shallow copy of current metrics."""
    return dict(_METRICS)

# PUBLIC_INTERFACE
def increment_metric(name: str, inc: float = 1.0) -> None:
    """Increment a named metric counter by inc."""
    _METRICS[name] = _METRICS.get(name, 0.0) + inc

# PUBLIC_INTERFACE
def observe_latency(name: str, ms: float) -> None:
    """Accumulate latency in milliseconds for a given metric name (e.g., search_latency_ms_sum)."""
    _METRICS[name] = _METRICS.get(name, 0.0) + ms

def get_current_request_id() -> str:
    return request_id_ctx.get()

def get_current_tenant_id() -> str:
    return tenant_id_ctx.get()

def mask_secret_value(value: Optional[str], keep: int = 4) -> Optional[str]:
    """Mask a secret for safe logging. Keep last N chars."""
    if value is None:
        return None
    try:
        v = str(value)
        if len(v) <= keep:
            return "*" * len(v)
        return "*" * (len(v) - keep) + v[-keep:]
    except Exception:
        return "***"

class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware to attach a correlation/request ID, tenant id and emit structured logs + metrics."""

    def __init__(self, app, tenant_header_name: str = "X-Tenant-ID", logger: Optional[logging.Logger] = None):
        super().__init__(app)
        self.tenant_header_name = tenant_header_name
        self.logger = logger or logging.getLogger(__name__)

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request_id_ctx.set(rid)
        # Tenant header handling is case-insensitive; starlette exposes .headers dict-like
        tid = request.headers.get(self.tenant_header_name) or tenant_id_ctx.get()
        tenant_id_ctx.set(tid)
        # best-effort route path template after resolution
        route_template = "-"
        try:
            route_template = request.scope.get("route").path  # type: ignore[attr-defined]
        except Exception:
            pass
        route_ctx.set(route_template)

        increment_metric("requests_total", 1.0)

        # Log request start (structured)
        self.logger.info(
            "request_start",
            extra={
                "request_id": rid,
                "tenant_id": tid,
                "method": request.method,
                "path": request.url.path,
                "route": route_template,
                "client": request.client.host if request.client else None,
            },
        )
        try:
            response: Response = await call_next(request)
            status = response.status_code
            if status >= 400:
                increment_metric("requests_errors_total", 1.0)
            return response
        except Exception as ex:
            increment_metric("requests_errors_total", 1.0)
            # Log exception without leaking potential secrets
            self.logger.exception(
                "request_error",
                extra={
                    "request_id": rid,
                    "tenant_id": tid,
                    "route": route_template,
                    "error": str(ex),
                },
            )
            raise
        finally:
            dur_ms = (time.perf_counter() - start) * 1000.0
            self.logger.info(
                "request_end",
                extra={
                    "request_id": rid,
                    "tenant_id": tid,
                    "route": route_template,
                    "duration_ms": round(dur_ms, 2),
                },
            )

# PUBLIC_INTERFACE
def get_structured_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a structured logger that adds correlation attributes through logging Filters."""
    logger = logging.getLogger(name or __name__)
    if not any(isinstance(f, _ContextFilter) for f in logger.filters):
        logger.addFilter(_ContextFilter())
    return logger

class _ContextFilter(logging.Filter):
    """Inject request context (request_id, tenant_id, route) into records."""
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.request_id = request_id_ctx.get()
            record.tenant_id = tenant_id_ctx.get()
            record.route = route_ctx.get()
        except Exception:
            record.request_id = "-"
            record.tenant_id = "public"
            record.route = "-"
        return True
