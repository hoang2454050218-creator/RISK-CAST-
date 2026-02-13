"""
Security Module.

Provides:
1. API Key Authentication
2. Rate Limiting
3. Request Validation
4. Security Headers

Design Principles:
- Defense in depth
- Fail secure
- Principle of least privilege
"""

from typing import Optional
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import secrets
import time

from fastapi import Request, HTTPException, Depends, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


# ============================================================================
# API KEY AUTHENTICATION
# ============================================================================


class APIKey(BaseModel):
    """API Key model."""

    key_id: str = Field(description="Public key identifier")
    key_hash: str = Field(description="Hashed secret key")
    customer_id: Optional[str] = Field(default=None, description="Associated customer")
    name: str = Field(description="Key name/description")
    scopes: list[str] = Field(default_factory=list, description="Allowed scopes")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(default=None)
    last_used_at: Optional[datetime] = Field(default=None)
    rate_limit: int = Field(default=100, description="Requests per minute")


class AuthContext(BaseModel):
    """Authentication context for request."""

    api_key: APIKey
    customer_id: Optional[str]
    scopes: list[str]


# API Key header definition
api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="API Key for authentication",
)


# PRODUCTION: API keys are stored in database
# This in-memory dict is ONLY for development/bootstrap keys
# Production code should use validate_api_key_from_db()
_bootstrap_keys: dict[str, APIKey] = {}


def hash_api_key(key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key.

    Returns:
        Tuple of (key_id, secret_key)
        The secret_key should only be shown once!
    """
    key_id = f"rk_{secrets.token_hex(8)}"
    secret_key = secrets.token_urlsafe(32)
    return key_id, secret_key


def create_api_key(
    name: str,
    customer_id: Optional[str] = None,
    scopes: Optional[list[str]] = None,
    expires_days: Optional[int] = None,
    rate_limit: int = 100,
) -> tuple[str, str, APIKey]:
    """
    Create and store a new API key (bootstrap/development only).

    For production, use PostgresAPIKeyRepository.create() instead.
    This function stores keys in memory - they will be lost on restart!

    Args:
        name: Key name/description
        customer_id: Associated customer
        scopes: Allowed scopes
        expires_days: Days until expiration
        rate_limit: Requests per minute

    Returns:
        Tuple of (key_id, secret_key, api_key_model)
    """
    key_id, secret_key = generate_api_key()

    # Create full key for hashing (key_id.secret)
    full_key = f"{key_id}.{secret_key}"
    key_hash = hash_api_key(full_key)

    expires_at = None
    if expires_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_days)

    api_key = APIKey(
        key_id=key_id,
        key_hash=key_hash,
        customer_id=customer_id,
        name=name,
        scopes=scopes or ["read"],
        expires_at=expires_at,
        rate_limit=rate_limit,
    )

    # Store in bootstrap keys (development/testing only)
    _bootstrap_keys[key_id] = api_key

    logger.info(
        "bootstrap_api_key_created",
        key_id=key_id,
        name=name,
        customer_id=customer_id,
        scopes=scopes,
    )

    return key_id, secret_key, api_key


def validate_api_key(key: str) -> Optional[APIKey]:
    """
    Validate an API key (sync version for bootstrap keys).

    This checks bootstrap/development keys stored in memory.
    For production with database keys, use validate_api_key_async().

    Args:
        key: Full API key (key_id.secret)

    Returns:
        APIKey if valid, None otherwise
    """
    if not key or "." not in key:
        return None

    parts = key.split(".", 1)
    if len(parts) != 2:
        return None

    key_id = parts[0]

    # Look up in bootstrap keys
    api_key = _bootstrap_keys.get(key_id)
    if not api_key:
        return None

    # Check if active
    if not api_key.is_active:
        return None

    # Check expiration
    if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
        return None

    # Verify hash
    key_hash = hash_api_key(key)
    if not secrets.compare_digest(key_hash, api_key.key_hash):
        return None

    # Update last used
    api_key.last_used_at = datetime.utcnow()

    return api_key


async def validate_api_key_from_db(key: str, session) -> Optional[APIKey]:
    """
    Validate an API key from database (production).

    This is the production method that checks keys stored in PostgreSQL.

    Args:
        key: Full API key (key_id.secret)
        session: Database session

    Returns:
        APIKey if valid, None otherwise
    """
    from app.db.repositories.api_keys import PostgresAPIKeyRepository
    
    if not key:
        return None
    
    # First check bootstrap keys (for development)
    bootstrap_key = validate_api_key(key)
    if bootstrap_key:
        return bootstrap_key
    
    # Then check database
    try:
        repo = PostgresAPIKeyRepository(session)
        db_key = await repo.validate(key)
        
        if db_key:
            # Convert to our APIKey model
            return APIKey(
                key_id=db_key.key_id,
                key_hash=db_key.key_hash,
                customer_id=db_key.owner_id,
                name=db_key.name,
                scopes=db_key.scopes,
                is_active=db_key.is_active,
                created_at=db_key.created_at,
                expires_at=db_key.expires_at,
                last_used_at=db_key.last_used_at,
                rate_limit=db_key.rate_limit_per_minute,
            )
    except Exception as e:
        logger.warning("database_key_validation_failed", error=str(e))
    
    return None


def revoke_api_key(key_id: str) -> bool:
    """Revoke a bootstrap API key (sync, in-memory only)."""
    if key_id in _bootstrap_keys:
        _bootstrap_keys[key_id].is_active = False
        logger.info("bootstrap_api_key_revoked", key_id=key_id)
        return True
    return False


async def revoke_api_key_in_db(key_id: str, session) -> bool:
    """Revoke an API key in database (production)."""
    from app.db.repositories.api_keys import PostgresAPIKeyRepository
    
    try:
        repo = PostgresAPIKeyRepository(session)
        result = await repo.deactivate(key_id)
        if result:
            logger.info("api_key_revoked_in_db", key_id=key_id)
        return result
    except Exception as e:
        logger.error("api_key_revoke_failed", key_id=key_id, error=str(e))
        return False


# ============================================================================
# RATE LIMITING
# ============================================================================


class RateLimiter:
    """
    Token bucket rate limiter.

    Allows burst traffic while enforcing average rate.
    """

    def __init__(
        self,
        rate: int = 100,  # Requests per minute
        burst: int = 20,  # Max burst size
    ):
        self.rate = rate
        self.burst = burst
        self.tokens: dict[str, float] = {}  # key -> tokens
        self.last_update: dict[str, float] = {}  # key -> timestamp

    def _refill(self, key: str) -> float:
        """Refill tokens based on elapsed time."""
        now = time.time()
        last = self.last_update.get(key, now)
        elapsed = now - last

        # Add tokens based on rate (per second)
        tokens_per_second = self.rate / 60.0
        new_tokens = elapsed * tokens_per_second

        current = self.tokens.get(key, self.burst)
        self.tokens[key] = min(self.burst, current + new_tokens)
        self.last_update[key] = now

        return self.tokens[key]

    def allow(self, key: str, cost: int = 1) -> bool:
        """
        Check if request is allowed.

        Args:
            key: Rate limit key (e.g., IP or API key)
            cost: Token cost for this request

        Returns:
            True if allowed, False if rate limited
        """
        tokens = self._refill(key)

        if tokens >= cost:
            self.tokens[key] = tokens - cost
            return True
        return False

    def get_remaining(self, key: str) -> int:
        """Get remaining tokens for a key."""
        self._refill(key)
        return int(self.tokens.get(key, self.burst))

    def get_reset_time(self, key: str) -> int:
        """Get seconds until tokens fully reset."""
        tokens = self.tokens.get(key, self.burst)
        missing = self.burst - tokens
        if missing <= 0:
            return 0
        tokens_per_second = self.rate / 60.0
        return int(missing / tokens_per_second) + 1


# Global rate limiter
_rate_limiter = RateLimiter()


def get_rate_limit_key(request: Request, api_key: Optional[APIKey]) -> str:
    """Get rate limit key from request."""
    if api_key:
        return f"key:{api_key.key_id}"

    # Fall back to IP
    client_ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    return f"ip:{client_ip}"


# ============================================================================
# FASTAPI DEPENDENCIES
# ============================================================================


async def get_api_key(
    api_key: Optional[str] = Depends(api_key_header),
) -> Optional[APIKey]:
    """
    Dependency to extract and validate API key.

    Returns None if no key provided (for optional auth).
    """
    if not api_key:
        return None

    validated = validate_api_key(api_key)
    if not validated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return validated


async def require_api_key(
    api_key: Optional[APIKey] = Depends(get_api_key),
) -> APIKey:
    """
    Dependency that requires a valid API key.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key


def require_scope(scope: str):
    """
    Dependency factory that requires a specific scope.

    Usage:
        @app.get("/admin", dependencies=[Depends(require_scope("admin"))])
    """
    async def check_scope(
        api_key: APIKey = Depends(require_api_key),
    ):
        if scope not in api_key.scopes and "*" not in api_key.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Scope '{scope}' required",
            )
        return api_key

    return check_scope


async def check_rate_limit(
    request: Request,
    api_key: Optional[APIKey] = Depends(get_api_key),
):
    """
    Dependency to check rate limit.
    
    FIXED: Now uses global rate limiter instance instead of creating new one each request.
    """
    key = get_rate_limit_key(request, api_key)

    # Use API key's rate limit if available
    rate_limit = api_key.rate_limit if api_key else 60

    # FIXED: Use global rate limiter, not new instance per request!
    # The global limiter tracks state across all requests
    if not _rate_limiter.allow(key):
        remaining = _rate_limiter.get_remaining(key)
        reset_time = _rate_limiter.get_reset_time(key)

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(rate_limit),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset_time),
                "Retry-After": str(reset_time),
            },
        )


# ============================================================================
# MIDDLEWARE
# ============================================================================


def add_security_headers(request: Request, response):
    """Add security headers to response."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response


# ============================================================================
# INITIALIZATION
# ============================================================================


def init_default_api_keys():
    """Initialize default API keys for development."""
    if settings.environment == "development":
        # Create a development key
        key_id, secret, _ = create_api_key(
            name="Development Key",
            scopes=["*"],
            rate_limit=1000,
        )
        # SECURITY FIX: Never log the full API key!
        # Only log the key_id prefix for reference
        logger.info(
            "development_api_key_created",
            key_id=key_id,
            hint="Check console output or env var for the secret",
        )
        # Print to console ONLY in development (not logged to files)
        print(f"\n{'='*60}")
        print(f"DEVELOPMENT API KEY (use this for testing):")
        print(f"  {key_id}.{secret}")
        print(f"{'='*60}\n")


def get_auth_context(api_key: APIKey) -> AuthContext:
    """Build auth context from API key."""
    return AuthContext(
        api_key=api_key,
        customer_id=api_key.customer_id,
        scopes=api_key.scopes,
    )
