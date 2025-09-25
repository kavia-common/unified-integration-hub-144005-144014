from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union


# PUBLIC_INTERFACE
def ok(data: Dict[str, Any] | List[Any] | Any, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Produce a standardized success payload.
    Use "status": "ok" and include a top-level "data" wrapper to align with a unified interface.
    """
    return {
        "status": "ok",
        "data": data,
        "meta": meta or {},
    }


# PUBLIC_INTERFACE
def error_payload(
    code: str,
    message: str,
    retry_after: Optional[Union[int, float]] = None,
    details: Optional[Dict[str, Any]] = None,
    http_status: Optional[int] = None,
) -> Dict[str, Any]:
    """Produce a standardized error payload.

    - status: always "error"
    - code: machine-readable error code (e.g., AUTH_REQUIRED, RATE_LIMITED, VALIDATION_ERROR, UPSTREAM_ERROR)
    - message: human-readable message
    - retry_after: optional seconds to wait (if rate limited)
    - details: optional structured extra info (safe; should not include secrets)
    - http_status: optional http status observed from upstream (for debugging/observability)
    """
    payload: Dict[str, Any] = {
        "status": "error",
        "code": code,
        "message": message,
    }
    if retry_after is not None:
        payload["retry_after"] = retry_after
    if details:
        payload["details"] = details
    if http_status is not None:
        payload["http_status"] = http_status
    return payload


def _is_rate_limited(status_code: Optional[int], headers: Dict[str, Any] | None = None) -> Tuple[bool, Optional[float]]:
    if status_code == 429:
        retry_after_header = None
        if headers:
            # Handle common header keys
            for k in ("retry-after", "Retry-After", "x-rate-limit-reset", "X-Rate-Limit-Reset"):
                if k in headers:
                    retry_after_header = headers[k]
                    break
        try:
            if retry_after_header is None:
                return True, None
            # May be seconds or unix timestamp; we assume seconds if convertible to float
            return True, float(retry_after_header)
        except Exception:
            return True, None
    return False, None


# PUBLIC_INTERFACE
def normalize_upstream_error(
    upstream_status: Optional[int],
    upstream_text: Optional[str],
    headers: Optional[Dict[str, Any]] = None,
    default_message: str = "Upstream service error",
) -> Dict[str, Any]:
    """Normalize upstream HTTP error into standard error payload."""
    # Handle token/authorization errors
    if upstream_status in (401, 403):
        return error_payload(code="AUTH_FAILED", message="Authorization with upstream service failed.", http_status=upstream_status)
    # Handle rate limiting
    limited, retry_after = _is_rate_limited(upstream_status, headers)
    if limited:
        return error_payload(code="RATE_LIMITED", message="Rate limit reached. Please retry later.", retry_after=retry_after, http_status=upstream_status)
    # Generic upstream error
    return error_payload(code="UPSTREAM_ERROR", message=default_message, details={"upstream": upstream_text or ""}, http_status=upstream_status)


# PUBLIC_INTERFACE
def validation_error(message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return standardized validation error payload."""
    return error_payload(code="VALIDATION_ERROR", message=message, details=details or {})


# PUBLIC_INTERFACE
def auth_required_error(message: str = "Authentication required to perform this operation.") -> Dict[str, Any]:
    """Return standardized auth required error payload."""
    return error_payload(code="AUTH_REQUIRED", message=message)


# PUBLIC_INTERFACE
def config_required_error(message: str = "Connector is not fully configured for this tenant.") -> Dict[str, Any]:
    """Return standardized configuration required error payload."""
    return error_payload(code="CONFIG_REQUIRED", message=message)
