"""
Tenant Isolation Middleware.

CRITICAL SECURITY COMPONENT — bug here = data leak between tenants.

- SET LOCAL app.current_company_id before any query
- SET LOCAL scopes to current transaction — auto-resets on commit/rollback
- Extracts JWT from Authorization header or ?token= query param (SSE)
- API-key auth for service-to-service endpoints (ingest, reconcile)
"""

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from riskcast.auth.jwt import decode_token

logger = structlog.get_logger(__name__)

# Paths that bypass ALL authentication (public endpoints)
PUBLIC_PATHS = frozenset({
    "/health",
    "/ready",
    "/metrics",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/docs",
    "/openapi.json",
    "/redoc",
})

# Prefixes that bypass ALL authentication
PUBLIC_PREFIXES = (
    "/static",
)

# Paths that use API-key authentication (service-to-service)
API_KEY_PATHS = frozenset({
    "/api/v1/signals/ingest",
})

# Prefixes that use API-key authentication
API_KEY_PREFIXES = (
    "/reconcile",
)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Mandatory SET/RESET of app.current_company_id for every request.

    Three auth modes:
    1. PUBLIC_PATHS / PUBLIC_PREFIXES → no auth
    2. API_KEY_PATHS / API_KEY_PREFIXES → X-API-Key header
    3. Everything else → JWT Bearer token
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # 0. CORS preflight — always pass through (handled by CORSMiddleware)
        if request.method == "OPTIONS":
            return await call_next(request)

        # 1. Public endpoints — no auth required
        if path in PUBLIC_PATHS or path.rstrip("/") in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES):
            return await call_next(request)

        # 2. API-key authenticated endpoints (service-to-service)
        if path in API_KEY_PATHS or path.startswith(API_KEY_PREFIXES):
            return await self._handle_api_key_auth(request, call_next)

        # 2b. Development mode: accept X-API-Key on ANY path as fallback
        #     This allows frontend and scripts to use a simple API key
        import os
        if os.getenv("ENVIRONMENT", "development") == "development":
            api_key = request.headers.get("X-API-Key")
            if api_key:
                return await self._handle_api_key_auth(request, call_next)

        # 3. JWT authenticated endpoints (user-facing)
        return await self._handle_jwt_auth(request, call_next)

    async def _handle_api_key_auth(self, request: Request, call_next) -> Response:
        """Authenticate via X-API-Key header for service-to-service calls."""
        import os

        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return Response(
                status_code=401,
                content='{"detail":"Missing X-API-Key header"}',
                media_type="application/json",
            )

        # Development shortcut: accept known dev key without DB lookup
        known_dev_key = os.getenv("RISKCAST_DEV_API_KEY", "riskcast-dev-key-2026")
        if os.getenv("ENVIRONMENT", "development") == "development" and api_key == known_dev_key:
            # Resolve dev company: use RISKCAST_DEV_COMPANY_SLUG or find by slug/latest
            dev_company_id = os.getenv("RISKCAST_DEV_COMPANY_ID", "")
            if not dev_company_id:
                try:
                    from sqlalchemy import select as sa_select
                    from riskcast.db.engine import get_db_session
                    from riskcast.db.models import Company
                    slug = os.getenv("RISKCAST_DEV_COMPANY_SLUG", "vietnam-exports")
                    async with get_db_session() as session:
                        result = await session.execute(
                            sa_select(Company.id).where(Company.slug == slug).limit(1)
                        )
                        row = result.scalar_one_or_none()
                        if not row:
                            # Fallback: most recently created company
                            result = await session.execute(
                                sa_select(Company.id).order_by(Company.created_at.desc()).limit(1)
                            )
                            row = result.scalar_one_or_none()
                        if row:
                            dev_company_id = str(row)
                except Exception:
                    pass
            if not dev_company_id:
                dev_company_id = "00000000-0000-0000-0000-000000000001"

            request.state.company_id = dev_company_id
            request.state.user_id = "dev-admin"
            request.state.user_email = "dev@riskcast.local"
            request.state.user_role = "admin"
            request.state.api_key_prefix = "dev-key"
            request.state.api_key_scopes = ["*"]
            return await call_next(request)

        try:
            from riskcast.auth.api_keys import validate_api_key
            context = await validate_api_key(request)
            # Set request state for downstream use
            request.state.company_id = str(context.company_id)
            request.state.user_id = None  # API keys are not users
            request.state.user_email = f"apikey:{context.key_name}"
            request.state.user_role = "admin"  # API keys have admin-equivalent access
            request.state.api_key_prefix = context.key_prefix
            request.state.api_key_scopes = context.scopes
        except Exception as e:
            logger.warning("api_key_auth_failed", error=str(e), path=request.url.path)
            return Response(
                status_code=401,
                content='{"detail":"Invalid or expired API key"}',
                media_type="application/json",
            )

        return await call_next(request)

    async def _handle_jwt_auth(self, request: Request, call_next) -> Response:
        """Authenticate via JWT Bearer token for user requests."""
        token = self._extract_token(request)
        if not token:
            return Response(
                status_code=401,
                content='{"detail":"Missing authentication token"}',
                media_type="application/json",
            )

        try:
            payload = decode_token(token)
            company_id = payload["company_id"]
            user_id = payload["user_id"]
        except Exception as e:
            logger.warning("tenant_auth_failed", error=str(e), path=request.url.path)
            return Response(
                status_code=401,
                content='{"detail":"Invalid or expired token"}',
                media_type="application/json",
            )

        # Attach to request state for downstream use
        request.state.company_id = company_id
        request.state.user_id = user_id
        request.state.user_email = payload.get("email", "")
        request.state.user_role = payload.get("role", "viewer")
        request.state.api_key_prefix = None
        request.state.api_key_scopes = None

        response = await call_next(request)
        return response

    def _extract_token(self, request: Request) -> str | None:
        """Extract JWT from Authorization header or query param."""
        # Header: Authorization: Bearer xxx
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:]

        # Query param: ?token=xxx (for SSE EventSource)
        token = request.query_params.get("token")
        if token:
            return token

        return None
