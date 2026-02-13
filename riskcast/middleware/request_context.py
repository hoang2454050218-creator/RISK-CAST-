"""
Request Context Middleware.

Adds:
- Unique request_id to every request (for log correlation)
- Request timing (X-Response-Time header)
- Structured request/response logging

The request_id is:
1. Read from X-Request-ID header (if provided by upstream proxy)
2. Generated as UUID4 if not provided
3. Returned in X-Request-ID response header
4. Injected into structlog context for all log messages
"""

import time
import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Adds request_id and timing to every request.

    Placed AFTER error handler, BEFORE tenant middleware.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        # Bind to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        # Time the request
        start = time.perf_counter()

        response = await call_next(request)

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        # Add headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{elapsed_ms}ms"

        # Log request completion
        logger.info(
            "request_completed",
            status=response.status_code,
            elapsed_ms=elapsed_ms,
        )

        return response
