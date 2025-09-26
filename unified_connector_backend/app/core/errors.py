# PUBLIC_INTERFACE
"""
Error types and unified error response models.
"""
from __future__ import annotations

from fastapi import HTTPException, status
from pydantic import BaseModel, Field


# PUBLIC_INTERFACE
class ErrorResponse(BaseModel):
    """Standard error envelope with a stable code."""
    status: str = Field(default="error", description="Always 'error'")
    code: str = Field(..., description="Stable error code")
    message: str = Field(..., description="Human readable error message")
    retry_after: int | None = Field(default=None, description="Optional retry-after seconds")


class ErrorCode:
    VALIDATION = "VALIDATION"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    RATE_LIMITED = "RATE_LIMITED"
    CONFLICT = "CONFLICT"
    INTERNAL = "INTERNAL"


# PUBLIC_INTERFACE
def http_error(status_code: int, code: str, message: str, retry_after: int | None = None) -> HTTPException:
    """Create HTTPException with a unified error response body."""
    return HTTPException(
        status_code=status_code,
        detail=ErrorResponse(status="error", code=code, message=message, retry_after=retry_after).model_dump(),
    )
