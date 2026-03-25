"""
Standard API response envelope.
Every endpoint returns this format for consistent frontend integration.

Success: {"success": true, "message": "...", "data": {...}, "error": null}
Error:   {"success": false, "message": "...", "data": null, "error": {"code": "...", "details": ...}}
"""

from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable error code")
    details: Optional[Any] = Field(None, description="Additional error context")


class ApiResponse(BaseModel, Generic[T]):
    """Standard response wrapper for all API endpoints."""
    success: bool
    message: str
    data: Optional[T] = None
    error: Optional[ErrorDetail] = None


def success_response(
    data: Any = None,
    message: str = "Request successful",
    status_code: int = 200,
) -> dict:
    """Build a success response dict (used inside route handlers)."""
    return {
        "success": True,
        "message": message,
        "data": data,
        "error": None,
    }


def error_response(
    message: str,
    code: str = "UNKNOWN_ERROR",
    details: Any = None,
) -> dict:
    """Build an error response dict (used inside exception handlers)."""
    return {
        "success": False,
        "message": message,
        "data": None,
        "error": {"code": code, "details": details},
    }
