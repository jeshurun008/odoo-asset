from typing import Any, Dict, Optional
from app.exceptions.base import AppException


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=404,
            details=details
        )


class ConflictException(AppException):
    def __init__(self, message: str = "Resource conflict occurred", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=409,
            details=details
        )


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Unauthorized access", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=401,
            details=details
        )


class ForbiddenException(AppException):
    def __init__(self, message: str = "Forbidden operation", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=403,
            details=details
        )


class ValidationException(AppException):
    def __init__(self, message: str = "Validation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details=details
        )


class LockedException(AppException):
    """Exception raised when an account is temporarily or permanently locked."""
    def __init__(self, message: str = "Account is locked", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="ACCOUNT_LOCKED",
            status_code=423,
            details=details
        )


class InternalException(AppException):
    def __init__(self, message: str = "Internal server error occurred", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="INTERNAL_ERROR",
            status_code=500,
            details=details
        )
