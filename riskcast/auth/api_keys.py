"""
API Key Authentication for Service-to-Service Communication.

Keys stored as SHA-256 hashes in DB — NEVER plaintext.
Supports:
- Multiple active keys per company (key rotation without downtime)
- Scoped access (signals:ingest, reconcile:run, etc.)
- Expiration dates
- Rate limiting per key
- Last-used tracking
"""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.engine import get_db_session

logger = structlog.get_logger(__name__)

API_KEY_PREFIX = "rc_live_"
API_KEY_BYTE_LENGTH = 32


@dataclass(frozen=True)
class APIKeyContext:
    """Context extracted from a valid API key."""

    company_id: uuid.UUID
    key_name: str
    key_prefix: str
    scopes: list[str]


def generate_api_key() -> tuple[str, str, str]:
    """
    Generate a new API key.

    Returns: (full_key, key_hash, key_prefix)
    The full key is shown ONCE to the user. After that, only prefix + hash are stored.
    """
    random_part = secrets.token_hex(API_KEY_BYTE_LENGTH)
    full_key = f"{API_KEY_PREFIX}{random_part}"
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    key_prefix = full_key[:16]
    return full_key, key_hash, key_prefix


def hash_api_key(key: str) -> str:
    """Hash an API key using SHA-256."""
    return hashlib.sha256(key.encode()).hexdigest()


async def validate_api_key(request: Request) -> APIKeyContext:
    """
    Validate an API key from the X-API-Key header.

    Steps:
    1. Extract key from header
    2. Hash the provided key
    3. Lookup in v2_api_keys WHERE is_active=True AND not expired
    4. Return APIKeyContext with company_id, name, scopes

    Raises HTTPException 401 if invalid.
    """
    key = request.headers.get("X-API-Key")
    if not key:
        raise HTTPException(
            status_code=401,
            detail={"error": "missing_api_key", "message": "X-API-Key header required"},
        )

    key_hash_value = hash_api_key(key)

    from riskcast.db.models import APIKey

    async with get_db_session() as session:
        now = datetime.utcnow()
        result = await session.execute(
            select(APIKey).where(
                APIKey.key_hash == key_hash_value,
                APIKey.is_active.is_(True),
            )
        )
        api_key = result.scalar_one_or_none()

        if api_key is None:
            logger.warning(
                "api_key_rejected",
                key_prefix=key[:16] if len(key) >= 16 else key,
                reason="not_found_or_inactive",
            )
            raise HTTPException(
                status_code=401,
                detail={"error": "invalid_api_key", "message": "Invalid or inactive API key"},
            )

        # Check expiration
        if api_key.expires_at and api_key.expires_at < now:
            logger.warning(
                "api_key_expired",
                key_name=api_key.key_name,
                expired_at=str(api_key.expires_at),
            )
            raise HTTPException(
                status_code=401,
                detail={"error": "expired_api_key", "message": "API key has expired"},
            )

        # Update last_used_at
        api_key.last_used_at = now
        await session.commit()

        return APIKeyContext(
            company_id=api_key.company_id,
            key_name=api_key.key_name,
            key_prefix=api_key.key_prefix,
            scopes=api_key.scopes or [],
        )


def check_scope(context: APIKeyContext, required_scope: str) -> None:
    """
    Check that the API key has the required scope.

    Raises HTTPException 403 if scope not granted.
    """
    if required_scope not in context.scopes:
        logger.warning(
            "api_key_scope_denied",
            key_name=context.key_name,
            required_scope=required_scope,
            granted_scopes=context.scopes,
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "insufficient_scope",
                "required": required_scope,
                "granted": context.scopes,
            },
        )
