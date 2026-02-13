"""
FastAPI Middleware Stack.

Provides:
1. Request ID generation and propagation
2. Request/Response logging
3. Error handling
4. Performance tracking
5. Security headers
6. Correlation ID management
"""

import time
import uuid
from typing import Callable, Optional
from contextvars import ContextVar

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from app.core.config import settings
from app.common.exceptions import RiskCastError
from app.common.metrics import record_http_request

logger = structlog.get_logger(__name__)

# Context variables for request-scoped data
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
customer_id_var: ContextVar[Optional[str]] = ContextVar("customer_id", default=None)


def get_request_id() -> Optional[str]:
    """Get current request ID from context."""
    return request_id_var.get()


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context."""
    return correlation_id_var.get()


def get_customer_id() -> Optional[str]:
    """Get current customer ID from context."""
    return customer_id_var.get()


# ============================================================================
# REQUEST ID MIDDLEWARE
# ============================================================================


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Adds unique request ID to every request.
    
    - Generates X-Request-ID if not provided
    - Propagates X-Correlation-ID for distributed tracing
    - Makes IDs available via context variables
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = f"req_{uuid.uuid4().hex[:16]}"
        
        # Get or propagate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = f"corr_{uuid.uuid4().hex[:16]}"
        
        # Set context variables
        request_id_var.set(request_id)
        correlation_id_var.set(correlation_id)
        
        # Store in request state for handlers
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        
        # Process request
        response = await call_next(request)
        
        # Add IDs to response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response


# ============================================================================
# LOGGING MIDDLEWARE
# ============================================================================


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs all requests with timing and context.
    
    Includes:
    - Request method, path, status
    - Response time
    - Request/Correlation IDs
    - Client IP (with privacy consideration)
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Get IDs from context
        request_id = get_request_id()
        correlation_id = get_correlation_id()
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Log request
        logger.info(
            "request_started",
            request_id=request_id,
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
            client_ip=self._mask_ip(client_ip),
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Log response
        logger.info(
            "request_completed",
            request_id=request_id,
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        
        # Record metrics
        record_http_request(
            method=request.method,
            endpoint=self._normalize_path(request.url.path),
            status_code=response.status_code,
            duration=duration_ms / 1000,
        )
        
        # Add timing header
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check X-Forwarded-For for proxied requests
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Fall back to direct connection
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _mask_ip(self, ip: str) -> str:
        """Mask IP for privacy (keep first two octets)."""
        if ip == "unknown":
            return ip
        
        parts = ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.*.*"
        
        return ip[:8] + "***"
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path for metrics (replace IDs with placeholders)."""
        parts = path.split("/")
        normalized = []
        
        for part in parts:
            # Replace UUIDs and common ID patterns
            if len(part) > 20 or (len(part) > 0 and part[0].isdigit()):
                normalized.append("{id}")
            elif part.startswith("dec_") or part.startswith("cust_"):
                normalized.append("{id}")
            else:
                normalized.append(part)
        
        return "/".join(normalized)


# ============================================================================
# ERROR HANDLING MIDDLEWARE
# ============================================================================


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Global error handler with structured error responses.
    
    Converts all exceptions to consistent JSON format:
    {
        "error": "error_code",
        "message": "Human readable message",
        "details": {...},
        "request_id": "req_xxx",
        "documentation_url": "https://..."
    }
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except RiskCastError as e:
            return self._handle_riskcast_error(e)
        except Exception as e:
            return self._handle_unexpected_error(e)
    
    def _handle_riskcast_error(self, error: RiskCastError) -> JSONResponse:
        """Handle known RISKCAST errors."""
        request_id = get_request_id()
        
        # Map error codes to HTTP status
        status_map = {
            "not_found": 404,
            "validation_error": 400,
            "authentication_error": 401,
            "authorization_error": 403,
            "conflict": 409,
            "rate_limit_exceeded": 429,
            "external_service_error": 503,
            "no_exposure": 422,
            "insufficient_data": 422,
            "decision_expired": 410,
        }
        
        status_code = status_map.get(error.code, 500)
        
        logger.warning(
            "request_error",
            request_id=request_id,
            error_code=error.code,
            message=error.message,
            details=error.details,
        )
        
        return JSONResponse(
            status_code=status_code,
            content={
                "error": error.code,
                "message": error.message,
                "details": error.details,
                "request_id": request_id,
                "documentation_url": f"https://docs.riskcast.io/errors/{error.code}",
            },
        )
    
    def _handle_unexpected_error(self, error: Exception) -> JSONResponse:
        """Handle unexpected errors."""
        request_id = get_request_id()
        
        logger.error(
            "unexpected_error",
            request_id=request_id,
            error_type=type(error).__name__,
            error=str(error),
            exc_info=True,
        )
        
        # Don't expose internal errors in production
        if settings.is_production:
            message = "An unexpected error occurred"
            details = {}
        else:
            message = str(error)
            details = {"type": type(error).__name__}
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": message,
                "details": details,
                "request_id": request_id,
                "documentation_url": "https://docs.riskcast.io/errors/internal_error",
            },
        )


# ============================================================================
# SECURITY HEADERS MIDDLEWARE
# ============================================================================


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all responses.
    
    Headers:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security: max-age=31536000
    - Content-Security-Policy: default-src 'self'
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: geolocation=(), microphone=()
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS only in production
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # CSP - adjust based on your needs
        csp = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
        response.headers["Content-Security-Policy"] = csp
        
        return response


# ============================================================================
# RATE LIMITING MIDDLEWARE (Fixed version)
# ============================================================================


class RateLimitState:
    """Shared state for rate limiting across requests."""
    
    def __init__(self):
        self.tokens: dict[str, float] = {}
        self.last_update: dict[str, float] = {}


# Global rate limit state (shared across requests)
_rate_limit_state = RateLimitState()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Token bucket rate limiter middleware.
    
    FIXED: Uses shared state instead of creating new instance per request.
    """
    
    def __init__(self, app, rate: int = 100, burst: int = 20):
        super().__init__(app)
        self.rate = rate  # Requests per minute
        self.burst = burst
        self.state = _rate_limit_state
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/ready", "/metrics"]:
            return await call_next(request)
        
        # Get rate limit key
        key = self._get_key(request)
        
        # Check rate limit
        allowed, remaining, reset_time = self._check_rate_limit(key)
        
        if not allowed:
            logger.warning(
                "rate_limit_exceeded",
                request_id=get_request_id(),
                key=key,
                reset_seconds=reset_time,
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests",
                    "details": {
                        "retry_after_seconds": reset_time,
                    },
                    "request_id": get_request_id(),
                },
                headers={
                    "X-RateLimit-Limit": str(self.rate),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time),
                },
            )
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.rate)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
    
    def _get_key(self, request: Request) -> str:
        """Get rate limit key from request."""
        # Try API key first
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"key:{api_key[:16]}"
        
        # Fall back to IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        elif request.client:
            ip = request.client.host
        else:
            ip = "unknown"
        
        return f"ip:{ip}"
    
    def _check_rate_limit(self, key: str) -> tuple[bool, int, int]:
        """
        Check if request is allowed.
        
        Returns:
            (allowed, remaining_tokens, seconds_until_reset)
        """
        now = time.time()
        
        # Refill tokens
        last_update = self.state.last_update.get(key, now)
        elapsed = now - last_update
        tokens_per_second = self.rate / 60.0
        new_tokens = elapsed * tokens_per_second
        
        current = self.state.tokens.get(key, self.burst)
        current = min(self.burst, current + new_tokens)
        
        self.state.last_update[key] = now
        
        # Check if allowed
        if current >= 1:
            self.state.tokens[key] = current - 1
            remaining = int(current - 1)
            return True, remaining, 0
        
        # Not allowed - calculate reset time
        self.state.tokens[key] = current
        tokens_needed = 1 - current
        reset_time = int(tokens_needed / tokens_per_second) + 1
        
        return False, 0, reset_time


# ============================================================================
# SETUP FUNCTION
# ============================================================================


def setup_middleware(app: FastAPI) -> None:
    """
    Setup all middleware in correct order.
    
    Order matters! Middleware is applied bottom-to-top:
    - First added = outermost (runs first for request, last for response)
    """
    # Error handling (outermost - catches all errors)
    app.add_middleware(ErrorHandlingMiddleware)
    
    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Rate limiting
    app.add_middleware(
        RateLimitMiddleware,
        rate=settings.rate_limit_per_minute if hasattr(settings, 'rate_limit_per_minute') else 100,
        burst=20,
    )
    
    # Logging (after rate limit so we log rejected requests too)
    app.add_middleware(LoggingMiddleware)
    
    # Request ID (innermost - sets context for all other middleware)
    app.add_middleware(RequestIdMiddleware)
    
    logger.info("middleware_configured")
