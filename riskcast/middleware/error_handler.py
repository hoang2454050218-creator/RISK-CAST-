"""
Global Error Handler Middleware.

Catches all unhandled exceptions and returns structured JSON responses.
NEVER leaks stack traces, DB errors, or internal details to clients.
Every error gets a unique error_id for correlation with server logs.
"""

import traceback
import uuid

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from riskcast.config import settings

logger = structlog.get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Outermost middleware — catches everything.

    Returns structured error responses:
    {
      "error": "human-readable message",
      "error_id": "uuid for log correlation",
      "status": 500
    }

    NEVER includes: stack traces, exception types, DB errors, internal paths.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            response = await call_next(request)
            return response

        except Exception as exc:
            error_id = str(uuid.uuid4())

            # Log full traceback server-side with error_id for correlation
            logger.error(
                "unhandled_exception",
                error_id=error_id,
                path=request.url.path,
                method=request.method,
                error=str(exc),
                traceback=traceback.format_exc(),
            )

            # Client-facing response — GENERIC message only
            status_code = getattr(exc, "status_code", 500)

            body: dict = {
                "error": "An internal error occurred. Please try again later.",
                "error_id": error_id,
                "status": status_code,
            }

            # In debug mode, add type hint ONLY (not full traceback)
            if settings.debug:
                body["debug_hint"] = type(exc).__name__

            return JSONResponse(status_code=status_code, content=body)
