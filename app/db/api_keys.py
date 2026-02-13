"""
Database-backed API Key Management.

Provides persistent API key storage with:
- Key hashing (keys never stored in plain text)
- Expiration support
- Scope-based permissions
- Rate limit per key
- Audit logging
- Key rotation

This replaces the in-memory API key store for production use.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List

import structlog
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, Index, select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base
from app.core.encryption import hash_value, verify_hash

logger = structlog.get_logger(__name__)


# ============================================================================
# DATABASE MODEL
# ============================================================================


class APIKeyModel(Base):
    """
    API Key database model.
    
    Keys are stored as salted hashes - the raw key is only shown once at creation.
    """
    
    __tablename__ = "api_keys"
    __table_args__ = {"extend_existing": True}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Key identification
    key_id = Column(String(50), unique=True, nullable=False, index=True)
    key_hash = Column(String(128), nullable=False)  # salt:hash format
    key_prefix = Column(String(10), nullable=False)  # First 8 chars for identification
    
    # Ownership
    owner_id = Column(String(50), nullable=False, index=True)
    owner_type = Column(String(20), default="customer")  # customer, service, admin
    
    # Metadata
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    
    # Permissions
    scopes = Column(JSON, default=list)  # ["decisions:read", "decisions:write"]
    
    # Rate limiting
    rate_limit_per_minute = Column(Integer, default=60)
    rate_limit_per_day = Column(Integer, default=10000)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime)
    revoked_reason = Column(String(200))
    
    # Expiration
    expires_at = Column(DateTime)
    
    # Usage tracking
    last_used_at = Column(DateTime)
    last_used_ip = Column(String(45))  # IPv6 max length
    total_requests = Column(Integer, default=0)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(50))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_api_keys_owner", "owner_id", "is_active"),
        Index("ix_api_keys_prefix", "key_prefix"),
    )


# ============================================================================
# API KEY SERVICE
# ============================================================================


class APIKeyService:
    """
    Service for managing API keys with database persistence.
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def create_key(
        self,
        owner_id: str,
        name: str,
        scopes: List[str],
        owner_type: str = "customer",
        description: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        rate_limit_per_minute: int = 60,
        rate_limit_per_day: int = 10000,
        created_by: Optional[str] = None,
    ) -> tuple[str, "APIKeyModel"]:
        """
        Create a new API key.
        
        Args:
            owner_id: Customer or service ID that owns this key
            name: Human-readable name
            scopes: List of permission scopes
            owner_type: Type of owner (customer, service, admin)
            description: Optional description
            expires_in_days: Days until expiration (None = never)
            rate_limit_per_minute: Requests per minute
            rate_limit_per_day: Requests per day
            created_by: ID of user creating the key
            
        Returns:
            Tuple of (raw_key, APIKeyModel)
            NOTE: raw_key is only returned once and should be shown to user!
        """
        # Generate secure key
        raw_key = f"rk_{secrets.token_urlsafe(32)}"
        key_id = f"key_{secrets.token_hex(8)}"
        key_prefix = raw_key[:10]
        
        # Hash the key for storage
        key_hash = hash_value(raw_key)
        
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Create model
        model = APIKeyModel(
            key_id=key_id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            owner_id=owner_id,
            owner_type=owner_type,
            name=name,
            description=description,
            scopes=scopes,
            rate_limit_per_minute=rate_limit_per_minute,
            rate_limit_per_day=rate_limit_per_day,
            expires_at=expires_at,
            created_by=created_by,
        )
        
        self._session.add(model)
        await self._session.flush()
        
        logger.info(
            "api_key_created",
            key_id=key_id,
            owner_id=owner_id,
            owner_type=owner_type,
            scopes=scopes,
            expires_at=expires_at.isoformat() if expires_at else None,
        )
        
        return raw_key, model
    
    async def validate_key(
        self,
        raw_key: str,
        client_ip: Optional[str] = None,
    ) -> Optional["APIKeyModel"]:
        """
        Validate an API key and return the model if valid.
        
        Args:
            raw_key: The raw API key to validate
            client_ip: Client IP for logging
            
        Returns:
            APIKeyModel if valid, None otherwise
        """
        if not raw_key or not raw_key.startswith("rk_"):
            return None
        
        # Get prefix for quick lookup
        key_prefix = raw_key[:10]
        
        # Find candidate keys
        result = await self._session.execute(
            select(APIKeyModel).where(
                and_(
                    APIKeyModel.key_prefix == key_prefix,
                    APIKeyModel.is_active == True,
                    APIKeyModel.is_revoked == False,
                )
            )
        )
        candidates = result.scalars().all()
        
        # Verify hash
        for model in candidates:
            if verify_hash(raw_key, model.key_hash):
                # Found matching key
                
                # Check expiration
                if model.expires_at and model.expires_at < datetime.utcnow():
                    logger.warning(
                        "api_key_expired",
                        key_id=model.key_id,
                        owner_id=model.owner_id,
                    )
                    return None
                
                # Update usage
                model.last_used_at = datetime.utcnow()
                model.last_used_ip = client_ip
                model.total_requests = (model.total_requests or 0) + 1
                await self._session.flush()
                
                return model
        
        logger.warning("api_key_invalid", key_prefix=key_prefix)
        return None
    
    async def revoke_key(
        self,
        key_id: str,
        reason: str,
        revoked_by: Optional[str] = None,
    ) -> bool:
        """
        Revoke an API key.
        
        Args:
            key_id: Key ID to revoke
            reason: Reason for revocation
            revoked_by: ID of user revoking the key
            
        Returns:
            True if revoked, False if not found
        """
        result = await self._session.execute(
            select(APIKeyModel).where(APIKeyModel.key_id == key_id)
        )
        model = result.scalar_one_or_none()
        
        if not model:
            return False
        
        model.is_revoked = True
        model.is_active = False
        model.revoked_at = datetime.utcnow()
        model.revoked_reason = reason
        
        await self._session.flush()
        
        logger.info(
            "api_key_revoked",
            key_id=key_id,
            owner_id=model.owner_id,
            reason=reason,
            revoked_by=revoked_by,
        )
        
        return True
    
    async def rotate_key(
        self,
        key_id: str,
        rotated_by: Optional[str] = None,
    ) -> Optional[tuple[str, "APIKeyModel"]]:
        """
        Rotate an API key (create new, revoke old).
        
        Args:
            key_id: Key ID to rotate
            rotated_by: ID of user rotating the key
            
        Returns:
            Tuple of (new_raw_key, new_model) or None if old key not found
        """
        # Get old key
        result = await self._session.execute(
            select(APIKeyModel).where(
                and_(
                    APIKeyModel.key_id == key_id,
                    APIKeyModel.is_active == True,
                )
            )
        )
        old_model = result.scalar_one_or_none()
        
        if not old_model:
            return None
        
        # Create new key with same properties
        new_raw_key, new_model = await self.create_key(
            owner_id=old_model.owner_id,
            name=f"{old_model.name} (rotated)",
            scopes=old_model.scopes,
            owner_type=old_model.owner_type,
            description=old_model.description,
            rate_limit_per_minute=old_model.rate_limit_per_minute,
            rate_limit_per_day=old_model.rate_limit_per_day,
            created_by=rotated_by,
        )
        
        # Revoke old key
        await self.revoke_key(
            key_id=key_id,
            reason="Rotated",
            revoked_by=rotated_by,
        )
        
        logger.info(
            "api_key_rotated",
            old_key_id=key_id,
            new_key_id=new_model.key_id,
            owner_id=old_model.owner_id,
        )
        
        return new_raw_key, new_model
    
    async def get_keys_for_owner(
        self,
        owner_id: str,
        include_revoked: bool = False,
    ) -> List["APIKeyModel"]:
        """Get all API keys for an owner."""
        conditions = [APIKeyModel.owner_id == owner_id]
        
        if not include_revoked:
            conditions.append(APIKeyModel.is_revoked == False)
        
        result = await self._session.execute(
            select(APIKeyModel).where(and_(*conditions))
        )
        
        return list(result.scalars().all())
    
    async def get_key_by_id(self, key_id: str) -> Optional["APIKeyModel"]:
        """Get API key by ID."""
        result = await self._session.execute(
            select(APIKeyModel).where(APIKeyModel.key_id == key_id)
        )
        return result.scalar_one_or_none()
    
    async def update_scopes(
        self,
        key_id: str,
        scopes: List[str],
        updated_by: Optional[str] = None,
    ) -> Optional["APIKeyModel"]:
        """Update scopes for an API key."""
        result = await self._session.execute(
            select(APIKeyModel).where(APIKeyModel.key_id == key_id)
        )
        model = result.scalar_one_or_none()
        
        if not model:
            return None
        
        model.scopes = scopes
        await self._session.flush()
        
        logger.info(
            "api_key_scopes_updated",
            key_id=key_id,
            scopes=scopes,
            updated_by=updated_by,
        )
        
        return model
    
    async def cleanup_expired(self) -> int:
        """
        Deactivate expired keys.
        
        Returns:
            Number of keys deactivated
        """
        result = await self._session.execute(
            select(APIKeyModel).where(
                and_(
                    APIKeyModel.is_active == True,
                    APIKeyModel.expires_at < datetime.utcnow(),
                )
            )
        )
        expired = result.scalars().all()
        
        for model in expired:
            model.is_active = False
        
        if expired:
            await self._session.flush()
            logger.info("expired_api_keys_deactivated", count=len(expired))
        
        return len(expired)
    
    async def get_usage_stats(self, key_id: str) -> Optional[dict]:
        """Get usage statistics for a key."""
        model = await self.get_key_by_id(key_id)
        
        if not model:
            return None
        
        return {
            "key_id": model.key_id,
            "total_requests": model.total_requests,
            "last_used_at": model.last_used_at.isoformat() if model.last_used_at else None,
            "created_at": model.created_at.isoformat(),
            "rate_limit_per_minute": model.rate_limit_per_minute,
            "rate_limit_per_day": model.rate_limit_per_day,
        }


# ============================================================================
# FACTORY
# ============================================================================


def get_api_key_service(session: AsyncSession) -> APIKeyService:
    """Create API key service with database session."""
    return APIKeyService(session)
