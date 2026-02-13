"""
Application Exceptions Module.

Centralized exception definitions with:
- Structured error responses
- HTTP status code mapping
- Error codes for client handling
- Detailed error information
"""

from typing import Optional, Dict, Any
from enum import Enum
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# ERROR CODES
# ============================================================================


class ErrorCode(str, Enum):
    """Application error codes."""
    
    # General errors (1xxx)
    INTERNAL_ERROR = "E1000"
    VALIDATION_ERROR = "E1001"
    NOT_FOUND = "E1002"
    CONFLICT = "E1003"
    
    # Authentication errors (2xxx)
    UNAUTHORIZED = "E2000"
    INVALID_API_KEY = "E2001"
    EXPIRED_API_KEY = "E2002"
    INSUFFICIENT_SCOPE = "E2003"
    
    # Rate limiting errors (3xxx)
    RATE_LIMIT_EXCEEDED = "E3000"
    QUOTA_EXCEEDED = "E3001"
    
    # Resource errors (4xxx)
    CUSTOMER_NOT_FOUND = "E4000"
    SHIPMENT_NOT_FOUND = "E4001"
    DECISION_NOT_FOUND = "E4002"
    NO_EXPOSURE = "E4003"
    
    # External service errors (5xxx)
    EXTERNAL_SERVICE_ERROR = "E5000"
    CIRCUIT_BREAKER_OPEN = "E5001"
    TIMEOUT_ERROR = "E5002"
    SERVICE_UNAVAILABLE = "E5003"
    
    # Data errors (6xxx)
    INVALID_DATA = "E6000"
    DATA_INTEGRITY_ERROR = "E6001"
    ENCRYPTION_ERROR = "E6002"


# ============================================================================
# ERROR RESPONSE MODEL
# ============================================================================


class ErrorDetail(BaseModel):
    """Detailed error information."""
    
    code: str
    message: str
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """
    Standard error response.
    
    All API errors return this unified format for consistency.
    """
    
    error: ErrorDetail
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    timestamp: Optional[str] = None
    documentation_url: Optional[str] = Field(
        default="https://docs.riskcast.io/errors",
        description="Link to error documentation",
    )
    trace_id: Optional[str] = Field(
        default=None,
        description="Distributed trace ID for debugging",
    )


# ============================================================================
# BASE EXCEPTION
# ============================================================================


class RiskCastError(Exception):
    """Base exception for RISKCAST application."""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        field: Optional[str] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        self.field = field
        super().__init__(message)
    
    def to_response(self, request_id: Optional[str] = None) -> ErrorResponse:
        """Convert to error response."""
        from datetime import datetime
        
        return ErrorResponse(
            error=ErrorDetail(
                code=self.code.value,
                message=self.message,
                field=self.field,
                details=self.details,
            ),
            request_id=request_id,
            timestamp=datetime.utcnow().isoformat(),
        )


# ============================================================================
# SPECIFIC EXCEPTIONS
# ============================================================================


class ValidationError(RiskCastError):
    """Validation error."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            field=field,
            details=details,
        )


class NotFoundError(RiskCastError):
    """Resource not found error."""
    
    def __init__(
        self,
        resource: str,
        identifier: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=f"{resource} not found: {identifier}",
            code=ErrorCode.NOT_FOUND,
            status_code=404,
            details={"resource": resource, "identifier": identifier, **(details or {})},
        )


class CustomerNotFoundError(RiskCastError):
    """Customer not found error."""
    
    def __init__(self, customer_id: str):
        super().__init__(
            message=f"Customer not found: {customer_id}",
            code=ErrorCode.CUSTOMER_NOT_FOUND,
            status_code=404,
            details={"customer_id": customer_id},
        )


class ShipmentNotFoundError(RiskCastError):
    """Shipment not found error."""
    
    def __init__(self, shipment_id: str):
        super().__init__(
            message=f"Shipment not found: {shipment_id}",
            code=ErrorCode.SHIPMENT_NOT_FOUND,
            status_code=404,
            details={"shipment_id": shipment_id},
        )


class DecisionNotFoundError(RiskCastError):
    """Decision not found error."""
    
    def __init__(self, decision_id: str):
        super().__init__(
            message=f"Decision not found: {decision_id}",
            code=ErrorCode.DECISION_NOT_FOUND,
            status_code=404,
            details={"decision_id": decision_id},
        )


class NoExposureError(RiskCastError):
    """Customer has no affected shipments."""
    
    def __init__(self, customer_id: str, chokepoint: str):
        super().__init__(
            message=f"Customer {customer_id} has no exposure to {chokepoint}",
            code=ErrorCode.NO_EXPOSURE,
            status_code=404,
            details={"customer_id": customer_id, "chokepoint": chokepoint},
        )


class InsufficientDataError(RiskCastError):
    """Insufficient data to make a decision."""
    
    def __init__(
        self,
        message: str = "Insufficient data for decision",
        missing_fields: Optional[list] = None,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            details={"missing_fields": missing_fields or []},
        )


class AuthenticationError(RiskCastError):
    """Authentication error."""
    
    def __init__(
        self,
        message: str = "Authentication required",
        code: ErrorCode = ErrorCode.UNAUTHORIZED,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=401,
            details=details,
        )


class InvalidAPIKeyError(AuthenticationError):
    """Invalid API key error."""
    
    def __init__(self):
        super().__init__(
            message="Invalid or missing API key",
            code=ErrorCode.INVALID_API_KEY,
        )


class ExpiredAPIKeyError(AuthenticationError):
    """Expired API key error."""
    
    def __init__(self, key_id: str):
        super().__init__(
            message="API key has expired",
            code=ErrorCode.EXPIRED_API_KEY,
            details={"key_id": key_id},
        )


class InsufficientScopeError(RiskCastError):
    """Insufficient scope/permissions error."""
    
    def __init__(self, required_scope: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Insufficient permissions. Required scope: {required_scope}",
            code=ErrorCode.INSUFFICIENT_SCOPE,
            status_code=403,
            details={"required_scope": required_scope, **(details or {})},
        )


class AuthorizationError(RiskCastError):
    """Authorization error (403 Forbidden)."""
    
    def __init__(
        self,
        message: str = "Access denied",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.INSUFFICIENT_SCOPE,
            status_code=403,
            details=details,
        )


class RateLimitError(RiskCastError):
    """Rate limit exceeded error."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            status_code=429,
            details=details,
        )


class QuotaExceededError(RiskCastError):
    """Quota exceeded error."""
    
    def __init__(self, quota_type: str, limit: int):
        super().__init__(
            message=f"{quota_type} quota exceeded. Limit: {limit}",
            code=ErrorCode.QUOTA_EXCEEDED,
            status_code=429,
            details={"quota_type": quota_type, "limit": limit},
        )


class ExternalServiceError(RiskCastError):
    """External service error."""
    
    def __init__(
        self,
        service: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=f"External service error ({service}): {message}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            status_code=502,
            details={"service": service, **(details or {})},
        )


class CircuitBreakerOpenError(RiskCastError):
    """Circuit breaker is open."""
    
    def __init__(self, service: str, retry_after_seconds: Optional[int] = None):
        details = {"service": service}
        if retry_after_seconds:
            details["retry_after_seconds"] = retry_after_seconds
        
        super().__init__(
            message=f"Service {service} is temporarily unavailable",
            code=ErrorCode.CIRCUIT_BREAKER_OPEN,
            status_code=503,
            details=details,
        )


class TimeoutError(RiskCastError):
    """Operation timeout error."""
    
    def __init__(self, operation: str, timeout_seconds: float):
        super().__init__(
            message=f"Operation {operation} timed out after {timeout_seconds}s",
            code=ErrorCode.TIMEOUT_ERROR,
            status_code=504,
            details={"operation": operation, "timeout_seconds": timeout_seconds},
        )


class DataIntegrityError(RiskCastError):
    """Data integrity error."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=ErrorCode.DATA_INTEGRITY_ERROR,
            status_code=500,
            details=details,
        )


class EncryptionError(RiskCastError):
    """Encryption/decryption error."""
    
    def __init__(self, operation: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Encryption error during {operation}",
            code=ErrorCode.ENCRYPTION_ERROR,
            status_code=500,
            details={"operation": operation, **(details or {})},
        )


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================


async def riskcast_exception_handler(
    request: Request,
    exc: RiskCastError,
) -> JSONResponse:
    """Handle RiskCastError exceptions."""
    request_id = getattr(request.state, "request_id", None)
    
    logger.error(
        "riskcast_error",
        error_code=exc.code.value,
        message=exc.message,
        status_code=exc.status_code,
        request_id=request_id,
        details=exc.details,
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_response(request_id).model_dump(),
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle generic exceptions."""
    request_id = getattr(request.state, "request_id", None)
    
    logger.exception(
        "unhandled_exception",
        error=str(exc),
        request_id=request_id,
    )
    
    error = RiskCastError(
        message="An internal error occurred",
        code=ErrorCode.INTERNAL_ERROR,
        status_code=500,
    )
    
    return JSONResponse(
        status_code=500,
        content=error.to_response(request_id).model_dump(),
    )


def register_exception_handlers(app):
    """Register exception handlers with FastAPI app."""
    app.add_exception_handler(RiskCastError, riskcast_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
