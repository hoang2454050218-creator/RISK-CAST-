"""Authentication & Authorization for RISKCAST.

Provides:
- API Key authentication
- Customer-scoped authorization
- Rate limiting support
- Multi-tenancy isolation
"""

import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Annotated
from functools import wraps

import structlog
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.common.exceptions import (
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
)

logger = structlog.get_logger(__name__)

# Security headers
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


# ============================================================================
# MODELS
# ============================================================================


class APIKey(BaseModel):
    """API Key model."""

    key_id: str = Field(description="Unique key identifier")
    key_hash: str = Field(description="SHA-256 hash of the key")
    owner_id: str = Field(description="Customer ID that owns this key")
    owner_type: str = Field(default="customer", description="Owner type")
    name: str = Field(description="Human-readable name")
    scopes: list[str] = Field(default_factory=list, description="Allowed scopes")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(default=None)
    last_used_at: Optional[datetime] = Field(default=None)
    rate_limit_per_minute: int = Field(default=60)
    metadata: dict = Field(default_factory=dict)


class AuthContext(BaseModel):
    """Authentication context for a request."""

    api_key: APIKey
    customer_id: str
    scopes: list[str]
    request_id: Optional[str] = None
    is_admin: bool = False


# ============================================================================
# SCOPES
# ============================================================================


class Scopes:
    """API Key scopes."""

    # Read scopes
    READ_DECISIONS = "decisions:read"
    READ_CUSTOMERS = "customers:read"
    READ_SIGNALS = "signals:read"
    READ_ALERTS = "alerts:read"

    # Write scopes
    WRITE_DECISIONS = "decisions:write"
    WRITE_CUSTOMERS = "customers:write"
    WRITE_ALERTS = "alerts:write"

    # Special scopes
    LEGAL_DECISIONS = "decisions:legal"  # Access to legal-level justifications

    # Admin scopes
    ADMIN = "admin"
    ADMIN_READ = "admin:read"
    ADMIN_WRITE = "admin:write"

    # Convenience groups
    ALL_READ = [READ_DECISIONS, READ_CUSTOMERS, READ_SIGNALS, READ_ALERTS]
    ALL_WRITE = [WRITE_DECISIONS, WRITE_CUSTOMERS, WRITE_ALERTS]
    ALL = ALL_READ + ALL_WRITE


# ============================================================================
# API KEY STORE (In production, use database)
# ============================================================================


class APIKeyStore:
    """
    API Key storage and validation.

    MVP: In-memory store with hashed keys.
    Production: Use PostgreSQL with proper indexing.
    """

    def __init__(self):
        self._keys: dict[str, APIKey] = {}  # key_hash -> APIKey
        self._by_owner: dict[str, list[str]] = {}  # owner_id -> [key_hashes]
        self._rate_limits: dict[str, list[float]] = {}  # key_hash -> [timestamps]

    def create_key(
        self,
        owner_id: str,
        name: str,
        scopes: list[str],
        expires_in_days: Optional[int] = None,
        rate_limit_per_minute: int = 60,
    ) -> tuple[str, APIKey]:
        """
        Create a new API key.

        Returns:
            Tuple of (raw_key, APIKey) - raw_key is only shown once!
        """
        # Generate secure random key
        raw_key = f"rc_{secrets.token_urlsafe(32)}"
        key_hash = self._hash_key(raw_key)
        key_id = f"key_{secrets.token_urlsafe(8)}"

        # Create APIKey
        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            owner_id=owner_id,
            name=name,
            scopes=scopes,
            expires_at=(
                datetime.utcnow() + timedelta(days=expires_in_days)
                if expires_in_days
                else None
            ),
            rate_limit_per_minute=rate_limit_per_minute,
        )

        # Store
        self._keys[key_hash] = api_key
        if owner_id not in self._by_owner:
            self._by_owner[owner_id] = []
        self._by_owner[owner_id].append(key_hash)

        logger.info(
            "api_key_created",
            key_id=key_id,
            owner_id=owner_id,
            scopes=scopes,
        )

        return raw_key, api_key

    def validate_key(self, raw_key: str) -> Optional[APIKey]:
        """Validate an API key and return the APIKey if valid."""
        key_hash = self._hash_key(raw_key)
        api_key = self._keys.get(key_hash)

        if not api_key:
            return None

        # Check if active
        if not api_key.is_active:
            logger.warning("api_key_inactive", key_id=api_key.key_id)
            return None

        # Check expiration
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            logger.warning("api_key_expired", key_id=api_key.key_id)
            return None

        # Update last used
        api_key.last_used_at = datetime.utcnow()

        return api_key

    def check_rate_limit(self, api_key: APIKey) -> bool:
        """
        Check if the API key is within rate limits.

        Returns True if allowed, raises RateLimitError if not.
        """
        now = time.time()
        window_start = now - 60  # 1 minute window

        # Get timestamps for this key
        timestamps = self._rate_limits.get(api_key.key_hash, [])

        # Filter to current window
        timestamps = [t for t in timestamps if t > window_start]

        # Check limit
        if len(timestamps) >= api_key.rate_limit_per_minute:
            # Calculate retry after
            oldest = min(timestamps)
            retry_after = int(60 - (now - oldest)) + 1
            raise RateLimitError(retry_after=retry_after)

        # Add current timestamp
        timestamps.append(now)
        self._rate_limits[api_key.key_hash] = timestamps

        return True

    def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        for key_hash, api_key in self._keys.items():
            if api_key.key_id == key_id:
                api_key.is_active = False
                logger.info("api_key_revoked", key_id=key_id)
                return True
        return False

    def get_keys_for_owner(self, owner_id: str) -> list[APIKey]:
        """Get all API keys for an owner."""
        key_hashes = self._by_owner.get(owner_id, [])
        return [self._keys[h] for h in key_hashes if h in self._keys]

    def _hash_key(self, raw_key: str) -> str:
        """Hash an API key."""
        return hashlib.sha256(raw_key.encode()).hexdigest()


# Global store instance
_api_key_store: Optional[APIKeyStore] = None


def get_api_key_store() -> APIKeyStore:
    """Get the API key store singleton."""
    global _api_key_store
    if _api_key_store is None:
        _api_key_store = APIKeyStore()
        # Create default admin key for development
        _create_default_keys(_api_key_store)
    return _api_key_store


def _create_default_keys(store: APIKeyStore) -> None:
    """Create default API keys for development."""
    import os

    if os.getenv("ENVIRONMENT", "development") == "development":
        # Create a random test key (logged for manual use)
        raw_key, api_key = store.create_key(
            owner_id="test_customer",
            name="Development Key",
            scopes=Scopes.ALL,
            rate_limit_per_minute=1000,
        )
        logger.info(
            "default_api_key_created",
            key_id=api_key.key_id,
            raw_key=raw_key,  # Only log in development!
        )

        # Create a KNOWN dev key for frontend/scripts/testing
        # This key is deterministic so frontend and scripts can use it
        known_key = os.getenv("RISKCAST_DEV_API_KEY", "riskcast-dev-key-2026")
        known_hash = store._hash_key(known_key)
        known_api_key = APIKey(
            key_id="key_dev_known",
            key_hash=known_hash,
            owner_id="dev_admin",
            name="Known Development Key",
            scopes=Scopes.ALL + [Scopes.ADMIN, Scopes.ADMIN_READ, Scopes.ADMIN_WRITE],
            rate_limit_per_minute=10000,
        )
        store._keys[known_hash] = known_api_key
        if "dev_admin" not in store._by_owner:
            store._by_owner["dev_admin"] = []
        store._by_owner["dev_admin"].append(known_hash)
        logger.info(
            "known_dev_key_registered",
            key_id="key_dev_known",
            hint="Use X-API-Key: riskcast-dev-key-2026",
        )


# ============================================================================
# AUTHENTICATION DEPENDENCIES
# ============================================================================


async def get_api_key(
    api_key_header: Annotated[Optional[str], Depends(API_KEY_HEADER)],
    request: Request,
) -> APIKey:
    """
    Validate API key from header.

    Raises:
        AuthenticationError: If key is missing or invalid
    """
    if not api_key_header:
        raise AuthenticationError(
            message="API key required",
            reason="missing_key",
        )

    store = get_api_key_store()
    api_key = store.validate_key(api_key_header)

    if not api_key:
        raise AuthenticationError(
            message="Invalid API key",
            reason="invalid_key",
        )

    # Check rate limit
    store.check_rate_limit(api_key)

    # Store in request state
    request.state.api_key = api_key
    request.state.customer_id = api_key.owner_id

    return api_key


async def get_auth_context(
    api_key: Annotated[APIKey, Depends(get_api_key)],
    request: Request,
) -> AuthContext:
    """Get full authentication context."""
    return AuthContext(
        api_key=api_key,
        customer_id=api_key.owner_id,
        scopes=api_key.scopes,
        request_id=getattr(request.state, "request_id", None),
        is_admin=Scopes.ADMIN in api_key.scopes,
    )


def require_scope(*required_scopes: str):
    """
    Dependency that requires specific scopes.

    Usage:
        @router.get("/admin")
        async def admin_endpoint(
            auth: AuthContext = Depends(require_scope(Scopes.ADMIN))
        ):
            ...
    """

    async def scope_checker(
        auth: Annotated[AuthContext, Depends(get_auth_context)],
    ) -> AuthContext:
        # Admin has all scopes
        if auth.is_admin:
            return auth

        # Check if any required scope is present
        if not any(scope in auth.scopes for scope in required_scopes):
            raise AuthorizationError(
                message=f"Required scope: {' or '.join(required_scopes)}",
                required_scope=required_scopes[0],
            )

        return auth

    return scope_checker


def require_customer_access(customer_id_param: str = "customer_id"):
    """
    Dependency that requires access to a specific customer.

    Validates that the authenticated user can access the customer_id
    in the request path or query parameters.

    Usage:
        @router.get("/customers/{customer_id}")
        async def get_customer(
            customer_id: str,
            auth: AuthContext = Depends(require_customer_access()),
        ):
            ...
    """

    async def customer_checker(
        auth: Annotated[AuthContext, Depends(get_auth_context)],
        request: Request,
    ) -> AuthContext:
        # Admin can access any customer
        if auth.is_admin:
            return auth

        # Get customer_id from path or query
        customer_id = (
            request.path_params.get(customer_id_param)
            or request.query_params.get(customer_id_param)
        )

        if not customer_id:
            # No customer_id specified, allow
            return auth

        # Check if user can access this customer
        if customer_id != auth.customer_id:
            raise AuthorizationError(
                message=f"Cannot access customer {customer_id}",
            )

        return auth

    return customer_checker


# ============================================================================
# OPTIONAL AUTH (for endpoints that work with or without auth)
# ============================================================================


async def get_optional_auth(
    api_key_header: Annotated[Optional[str], Depends(API_KEY_HEADER)],
    request: Request,
) -> Optional[AuthContext]:
    """
    Get auth context if API key is provided, None otherwise.

    Use for endpoints that have different behavior for authenticated
    vs anonymous users.
    """
    if not api_key_header:
        return None

    try:
        api_key = await get_api_key(api_key_header, request)
        return AuthContext(
            api_key=api_key,
            customer_id=api_key.owner_id,
            scopes=api_key.scopes,
            request_id=getattr(request.state, "request_id", None),
            is_admin=Scopes.ADMIN in api_key.scopes,
        )
    except AuthenticationError:
        return None


# ============================================================================
# IDEMPOTENCY
# ============================================================================


class IdempotencyStore:
    """
    Store for idempotency keys.

    Tracks processed requests to prevent duplicate operations.
    """

    def __init__(self, ttl_seconds: int = 86400):  # 24 hours
        self._store: dict[str, dict] = {}  # key -> {response, timestamp}
        self._ttl = ttl_seconds

    def check_and_set(
        self,
        idempotency_key: str,
        customer_id: str,
    ) -> Optional[dict]:
        """
        Check if request was already processed.

        Returns:
            Previous response if exists, None if new request
        """
        full_key = f"{customer_id}:{idempotency_key}"

        # Clean expired entries
        self._cleanup()

        # Check if exists
        if full_key in self._store:
            entry = self._store[full_key]
            logger.info(
                "idempotency_hit",
                idempotency_key=idempotency_key,
                customer_id=customer_id,
            )
            return entry.get("response")

        # Mark as processing
        self._store[full_key] = {
            "response": None,
            "timestamp": time.time(),
            "status": "processing",
        }

        return None

    def set_response(
        self,
        idempotency_key: str,
        customer_id: str,
        response: dict,
    ) -> None:
        """Store the response for an idempotency key."""
        full_key = f"{customer_id}:{idempotency_key}"
        self._store[full_key] = {
            "response": response,
            "timestamp": time.time(),
            "status": "completed",
        }

    def _cleanup(self) -> None:
        """Remove expired entries."""
        now = time.time()
        expired = [
            k
            for k, v in self._store.items()
            if now - v["timestamp"] > self._ttl
        ]
        for k in expired:
            del self._store[k]


# Global idempotency store
_idempotency_store: Optional[IdempotencyStore] = None


def get_idempotency_store() -> IdempotencyStore:
    """Get the idempotency store singleton."""
    global _idempotency_store
    if _idempotency_store is None:
        _idempotency_store = IdempotencyStore()
    return _idempotency_store


async def check_idempotency(
    idempotency_key: Annotated[Optional[str], Header(alias="X-Idempotency-Key")] = None,
    auth: Annotated[AuthContext, Depends(get_auth_context)] = None,
) -> Optional[str]:
    """
    Check idempotency key if provided.

    Returns the key if new request, raises HTTPException if duplicate.
    """
    if not idempotency_key:
        return None

    store = get_idempotency_store()
    previous = store.check_and_set(idempotency_key, auth.customer_id)

    if previous:
        from fastapi.responses import JSONResponse

        raise HTTPException(
            status_code=200,  # Return same response
            detail=previous,
        )

    return idempotency_key
