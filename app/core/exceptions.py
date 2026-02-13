"""
Custom exceptions for RISKCAST.

Provides structured error handling with recovery hints and error codes.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import traceback


class ErrorCode(str, Enum):
    """Standard error codes for RISKCAST."""
    # General errors (1xxx)
    UNKNOWN_ERROR = "E1000"
    VALIDATION_ERROR = "E1001"
    CONFIGURATION_ERROR = "E1002"
    TIMEOUT_ERROR = "E1003"
    
    # Data errors (2xxx)
    DATA_NOT_FOUND = "E2000"
    DATA_INVALID = "E2001"
    DATA_STALE = "E2002"
    DATA_CORRUPT = "E2003"
    
    # Security errors (3xxx)
    AUTHENTICATION_ERROR = "E3000"
    AUTHORIZATION_ERROR = "E3001"
    ENCRYPTION_ERROR = "E3002"
    KEY_MANAGEMENT_ERROR = "E3003"
    
    # Service errors (4xxx)
    SERVICE_UNAVAILABLE = "E4000"
    SERVICE_TIMEOUT = "E4001"
    RATE_LIMITED = "E4002"
    UPSTREAM_ERROR = "E4003"
    
    # Decision errors (5xxx)
    DECISION_ERROR = "E5000"
    NO_EXPOSURE = "E5001"
    INVALID_ACTION = "E5002"
    CONFIDENCE_TOO_LOW = "E5003"
    
    # Signal errors (6xxx)
    SIGNAL_ERROR = "E6000"
    SIGNAL_VALIDATION_FAILED = "E6001"
    SOURCE_UNTRUSTED = "E6002"
    SIGNAL_EXPIRED = "E6003"


@dataclass
class RecoveryHint:
    """A hint for recovering from an error."""
    action: str
    description: str
    auto_retry: bool = False
    retry_delay_seconds: int = 0
    requires_human: bool = False


@dataclass
class ErrorContext:
    """Context information for an error."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    user_id: Optional[str] = None
    customer_id: Optional[str] = None
    request_id: Optional[str] = None
    service_name: str = "riskcast"
    additional: Dict[str, Any] = field(default_factory=dict)


class RiskCastError(Exception):
    """
    Base exception for RISKCAST.
    
    All custom exceptions should inherit from this class.
    """
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        recovery_hint: Optional[RecoveryHint] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.recovery_hint = recovery_hint
        self.context = context or ErrorContext()
        self.cause = cause
        self.stack_trace = traceback.format_exc() if cause else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/API responses."""
        result = {
            "error_code": self.error_code.value,
            "message": self.message,
            "timestamp": self.context.timestamp.isoformat(),
        }
        
        if self.recovery_hint:
            result["recovery"] = {
                "action": self.recovery_hint.action,
                "description": self.recovery_hint.description,
                "auto_retry": self.recovery_hint.auto_retry,
            }
        
        if self.context.trace_id:
            result["trace_id"] = self.context.trace_id
        
        return result
    
    def __str__(self) -> str:
        return f"[{self.error_code.value}] {self.message}"


class ValidationError(RiskCastError):
    """Error raised when validation fails."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            recovery_hint=RecoveryHint(
                action="fix_input",
                description="Check and fix the invalid input field",
            ),
            **kwargs,
        )
        self.field = field
        self.value = value


class ConfigurationError(RiskCastError):
    """Error raised when configuration is invalid."""
    
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.CONFIGURATION_ERROR,
            recovery_hint=RecoveryHint(
                action="check_config",
                description="Review configuration settings",
                requires_human=True,
            ),
            **kwargs,
        )
        self.config_key = config_key


class DataNotFoundError(RiskCastError):
    """Error raised when requested data is not found."""
    
    def __init__(self, message: str, resource_type: str = "", resource_id: str = "", **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.DATA_NOT_FOUND,
            recovery_hint=RecoveryHint(
                action="verify_id",
                description="Verify the resource ID exists",
            ),
            **kwargs,
        )
        self.resource_type = resource_type
        self.resource_id = resource_id


class EncryptionError(RiskCastError):
    """Error raised when encryption/decryption fails."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.ENCRYPTION_ERROR,
            recovery_hint=RecoveryHint(
                action="check_keys",
                description="Verify encryption keys are properly configured",
                requires_human=True,
            ),
            **kwargs,
        )


class KeyManagementError(RiskCastError):
    """Error raised for key management issues."""
    
    def __init__(self, message: str, key_name: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.KEY_MANAGEMENT_ERROR,
            recovery_hint=RecoveryHint(
                action="configure_keys",
                description="Set required encryption keys in environment",
                requires_human=True,
            ),
            **kwargs,
        )
        self.key_name = key_name


class ServiceUnavailableError(RiskCastError):
    """Error raised when a service is unavailable."""
    
    def __init__(self, message: str, service_name: str = "", **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
            recovery_hint=RecoveryHint(
                action="retry",
                description="Retry the request after a delay",
                auto_retry=True,
                retry_delay_seconds=30,
            ),
            **kwargs,
        )
        self.service_name = service_name


class RateLimitedError(RiskCastError):
    """Error raised when rate limited."""
    
    def __init__(self, message: str, retry_after_seconds: int = 60, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.RATE_LIMITED,
            recovery_hint=RecoveryHint(
                action="wait_and_retry",
                description=f"Wait {retry_after_seconds} seconds and retry",
                auto_retry=True,
                retry_delay_seconds=retry_after_seconds,
            ),
            **kwargs,
        )
        self.retry_after_seconds = retry_after_seconds


class DecisionError(RiskCastError):
    """Error raised during decision generation."""
    
    def __init__(self, message: str, decision_id: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.DECISION_ERROR,
            **kwargs,
        )
        self.decision_id = decision_id


class NoExposureError(RiskCastError):
    """Error raised when customer has no affected shipments."""
    
    def __init__(self, message: str = "No affected shipments found", **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.NO_EXPOSURE,
            recovery_hint=RecoveryHint(
                action="verify_shipments",
                description="Verify customer has active shipments on affected routes",
            ),
            **kwargs,
        )


class SignalError(RiskCastError):
    """Error raised during signal processing."""
    
    def __init__(self, message: str, signal_id: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.SIGNAL_ERROR,
            **kwargs,
        )
        self.signal_id = signal_id


class SignalValidationError(SignalError):
    """Error raised when signal validation fails."""
    
    def __init__(
        self,
        message: str,
        validation_errors: Optional[List[str]] = None,
        **kwargs,
    ):
        kwargs.setdefault("error_code", ErrorCode.SIGNAL_VALIDATION_FAILED)
        super().__init__(message=message, **kwargs)
        self.validation_errors = validation_errors or []


class TimeoutError(RiskCastError):
    """Error raised when an operation times out."""
    
    def __init__(self, message: str, timeout_seconds: float = 0, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.TIMEOUT_ERROR,
            recovery_hint=RecoveryHint(
                action="retry_with_longer_timeout",
                description="Retry with increased timeout",
                auto_retry=True,
                retry_delay_seconds=5,
            ),
            **kwargs,
        )
        self.timeout_seconds = timeout_seconds


# Error handler helper
def handle_error(error: Exception, context: Optional[ErrorContext] = None) -> RiskCastError:
    """
    Convert any exception to a RiskCastError.
    
    Args:
        error: The exception to handle
        context: Optional error context
        
    Returns:
        RiskCastError instance
    """
    if isinstance(error, RiskCastError):
        if context:
            error.context = context
        return error
    
    # Wrap unknown exceptions
    return RiskCastError(
        message=str(error),
        error_code=ErrorCode.UNKNOWN_ERROR,
        context=context,
        cause=error,
    )
