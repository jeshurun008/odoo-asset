from typing import Any, Dict, Generic, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success envelope wrapping any schema type T."""
    status: str = Field(default="success")
    data: T
    meta: Optional[Dict[str, Any]] = None


class ErrorPayload(BaseModel):
    """Details concerning an error event."""
    code: str
    message: str
    correlation_id: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standard error envelope wrapping the payload details."""
    status: str = Field(default="error")
    error: ErrorPayload
