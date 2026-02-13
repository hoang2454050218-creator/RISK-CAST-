"""
Auth API routes — register and login.

Uses bcrypt directly (passlib has compatibility issues with bcrypt 5.x).
Includes brute force protection and security audit logging.
"""

import asyncio
import uuid

import bcrypt
import structlog
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from riskcast.auth.jwt import create_access_token
from riskcast.auth.schemas import LoginRequest, RegisterRequest, TokenResponse
from riskcast.db.engine import get_session_factory
from riskcast.db.models import Company, User
from riskcast.middleware.brute_force import get_brute_force_protection

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, respecting X-Forwarded-For."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, request: Request):
    """Register a new company and its first admin user."""
    factory = get_session_factory()
    async with factory() as session:
        # Create company
        company = Company(
            name=body.company_name,
            slug=body.company_slug,
            industry=body.industry,
        )
        session.add(company)

        try:
            await session.flush()
        except IntegrityError:
            await session.rollback()
            raise HTTPException(status_code=409, detail="Company slug already exists")

        # Create admin user
        user = User(
            company_id=company.id,
            email=body.email,
            password_hash=hash_password(body.password),
            name=body.name,
            role="admin",
        )
        session.add(user)

        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise HTTPException(status_code=409, detail="Email already registered")

        await session.refresh(company)
        await session.refresh(user)

        token = create_access_token(
            user_id=str(user.id),
            company_id=str(company.id),
            email=user.email,
            role=user.role,
        )

        logger.info("user_registered", user_id=str(user.id), company_id=str(company.id))

        # Audit log
        _log_auth_event("register", str(user.id), str(company.id), request)

        return TokenResponse(
            access_token=token,
            user_id=str(user.id),
            company_id=str(company.id),
            email=user.email,
            role=user.role,
            name=user.name,
        )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request):
    """Authenticate user and return JWT. Protected by brute force detection."""
    ip = _get_client_ip(request)
    bf = get_brute_force_protection()

    # Check brute force lockout
    allowed, reason, retry_after = bf.check_allowed(ip, body.email)
    if not allowed:
        logger.warning("login_blocked", ip=ip, email=body.email, reason=reason)
        raise HTTPException(
            status_code=429,
            detail=reason,
            headers={"Retry-After": str(retry_after)},
        )

    # Progressive delay
    delay = bf.get_progressive_delay(ip)
    if delay > 0:
        await asyncio.sleep(delay)

    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(User).where(User.email == body.email)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(body.password, user.password_hash):
            bf.record_failure(ip, body.email)
            _log_auth_event("login_failed", None, None, request, email=body.email)
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Success — clear brute force counters
        bf.record_success(ip, body.email)

        from datetime import datetime, timezone
        user.last_login_at = datetime.utcnow()
        await session.commit()
        await session.refresh(user)

        token = create_access_token(
            user_id=str(user.id),
            company_id=str(user.company_id),
            email=user.email,
            role=user.role,
        )

        logger.info("user_logged_in", user_id=str(user.id))
        _log_auth_event("login", str(user.id), str(user.company_id), request)

        return TokenResponse(
            access_token=token,
            user_id=str(user.id),
            company_id=str(user.company_id),
            email=user.email,
            role=user.role,
            name=user.name,
        )


def _log_auth_event(
    action: str,
    user_id: str | None,
    company_id: str | None,
    request: Request,
    email: str | None = None,
) -> None:
    """Fire-and-forget security audit log for auth events."""
    try:
        import asyncio
        from riskcast.services.security_audit import log_security_event

        ip = _get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")[:500]

        asyncio.create_task(
            log_security_event(
                action=action,
                user_id=uuid.UUID(user_id) if user_id else None,
                company_id=uuid.UUID(company_id) if company_id else None,
                ip_address=ip,
                user_agent=user_agent,
                request_method=request.method,
                request_path=request.url.path,
                details={"email": email} if email and action == "login_failed" else None,
            )
        )
    except Exception:
        # Audit logging should never break the auth flow
        logger.warning("audit_log_failed", action=action, exc_info=True)
