"""
PostgreSQL API Key Repository.

Production-grade API key storage with:
- Secure key hashing (SHA-256)
- Rate limiting integration
- Usage tracking
- Key rotation support
- Audit logging
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List
from abc import ABC, abstractmethod

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from pydantic import BaseModel, Field
import structlog

from app.db.models import Base
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, JSON, Float, Text
)
from sqlalchemy.orm import Mapped, mapped_column

logger = structlog.get_logger(__name__)


# ============================================================================
# DATABASE MODEL
# ============================================================================


class APIKeyModel(Base):
    """SQLAlchemy model for API keys."""
    
    __tablename__ = "api_keys"
    __table_args__ = {"extend_existing": True}
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    owner_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    owner_type: Mapped[str] = mapped_column(String(20), nullable=False, default="customer")
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    scopes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)


# ============================================================================
# DOMAIN MODELS
# ============================================================================


class APIKey(BaseModel):
    """API key domain model."""
    
    key_id: str
    key_hash: str
    owner_id: str
    owner_type: str = "customer"
    name: str
    scopes: List[str] = Field(default_factory=list)
    is_active: bool = True
    rate_limit_per_minute: int = 60
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if key has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def has_scope(self, scope: str) -> bool:
        """Check if key has a specific scope."""
        return scope in self.scopes or "admin" in self.scopes
    
    def can_access_owner(self, owner_id: str) -> bool:
        """Check if key can access a specific owner."""
        if "admin" in self.scopes:
            return True
        return self.owner_id == owner_id


class CreateAPIKeyRequest(BaseModel):
    """Request to create a new API key."""
    
    owner_id: str
    owner_type: str = "customer"
    name: str
    scopes: List[str] = Field(default_factory=list)
    rate_limit_per_minute: int = 60
    expires_in_days: Optional[int] = None
    metadata: dict = Field(default_factory=dict)


class APIKeyResponse(BaseModel):
    """Response when creating an API key (includes raw key)."""
    
    raw_key: str = Field(description="Only returned once on creation")
    api_key: APIKey


# ============================================================================
# REPOSITORY INTERFACE
# ============================================================================


class APIKeyRepository(ABC):
    """Abstract base class for API key repositories."""
    
    @abstractmethod
    async def create(self, request: CreateAPIKeyRequest) -> APIKeyResponse:
        """Create a new API key."""
        pass
    
    @abstractmethod
    async def get_by_id(self, key_id: str) -> Optional[APIKey]:
        """Get API key by ID."""
        pass
    
    @abstractmethod
    async def get_by_hash(self, key_hash: str) -> Optional[APIKey]:
        """Get API key by hash (for validation)."""
        pass
    
    @abstractmethod
    async def get_by_owner(self, owner_id: str) -> List[APIKey]:
        """Get all API keys for an owner."""
        pass
    
    @abstractmethod
    async def update_last_used(self, key_id: str) -> None:
        """Update last used timestamp."""
        pass
    
    @abstractmethod
    async def deactivate(self, key_id: str) -> bool:
        """Deactivate an API key."""
        pass
    
    @abstractmethod
    async def delete(self, key_id: str) -> bool:
        """Delete an API key."""
        pass
    
    @abstractmethod
    async def validate(self, raw_key: str) -> Optional[APIKey]:
        """Validate a raw API key and return if valid."""
        pass


# ============================================================================
# POSTGRESQL IMPLEMENTATION
# ============================================================================


class PostgresAPIKeyRepository(APIKeyRepository):
    """PostgreSQL-based API key repository."""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    @staticmethod
    def _generate_key() -> tuple[str, str, str]:
        """Generate a new API key.
        
        Returns:
            Tuple of (key_id, raw_key, key_hash)
        """
        # Generate key ID (public identifier)
        key_id = f"rk_{secrets.token_hex(8)}"
        
        # Generate raw key (secret)
        raw_key = f"{key_id}.{secrets.token_urlsafe(32)}"
        
        # Hash for storage
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        return key_id, raw_key, key_hash
    
    @staticmethod
    def _hash_key(raw_key: str) -> str:
        """Hash a raw key for lookup."""
        return hashlib.sha256(raw_key.encode()).hexdigest()
    
    def _model_to_domain(self, model: APIKeyModel) -> APIKey:
        """Convert database model to domain model."""
        return APIKey(
            key_id=model.key_id,
            key_hash=model.key_hash,
            owner_id=model.owner_id,
            owner_type=model.owner_type,
            name=model.name,
            scopes=model.scopes,
            is_active=model.is_active,
            rate_limit_per_minute=model.rate_limit_per_minute,
            expires_at=model.expires_at,
            last_used_at=model.last_used_at,
            created_at=model.created_at,
            metadata=model.metadata_json,
        )
    
    async def create(self, request: CreateAPIKeyRequest) -> APIKeyResponse:
        """Create a new API key."""
        key_id, raw_key, key_hash = self._generate_key()
        
        expires_at = None
        if request.expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)
        
        model = APIKeyModel(
            key_id=key_id,
            key_hash=key_hash,
            owner_id=request.owner_id,
            owner_type=request.owner_type,
            name=request.name,
            scopes=request.scopes,
            rate_limit_per_minute=request.rate_limit_per_minute,
            expires_at=expires_at,
            metadata_json=request.metadata,
        )
        
        self._session.add(model)
        await self._session.flush()
        
        logger.info(
            "api_key_created",
            key_id=key_id,
            owner_id=request.owner_id,
            scopes=request.scopes,
        )
        
        return APIKeyResponse(
            raw_key=raw_key,
            api_key=self._model_to_domain(model),
        )
    
    async def get_by_id(self, key_id: str) -> Optional[APIKey]:
        """Get API key by ID."""
        result = await self._session.execute(
            select(APIKeyModel).where(APIKeyModel.key_id == key_id)
        )
        model = result.scalar_one_or_none()
        return self._model_to_domain(model) if model else None
    
    async def get_by_hash(self, key_hash: str) -> Optional[APIKey]:
        """Get API key by hash."""
        result = await self._session.execute(
            select(APIKeyModel).where(APIKeyModel.key_hash == key_hash)
        )
        model = result.scalar_one_or_none()
        return self._model_to_domain(model) if model else None
    
    async def get_by_owner(self, owner_id: str) -> List[APIKey]:
        """Get all API keys for an owner."""
        result = await self._session.execute(
            select(APIKeyModel)
            .where(APIKeyModel.owner_id == owner_id)
            .order_by(APIKeyModel.created_at.desc())
        )
        models = result.scalars().all()
        return [self._model_to_domain(m) for m in models]
    
    async def update_last_used(self, key_id: str) -> None:
        """Update last used timestamp."""
        await self._session.execute(
            update(APIKeyModel)
            .where(APIKeyModel.key_id == key_id)
            .values(last_used_at=datetime.utcnow())
        )
    
    async def deactivate(self, key_id: str) -> bool:
        """Deactivate an API key."""
        result = await self._session.execute(
            update(APIKeyModel)
            .where(APIKeyModel.key_id == key_id)
            .values(is_active=False)
        )
        
        if result.rowcount > 0:
            logger.info("api_key_deactivated", key_id=key_id)
            return True
        return False
    
    async def delete(self, key_id: str) -> bool:
        """Delete an API key."""
        result = await self._session.execute(
            delete(APIKeyModel).where(APIKeyModel.key_id == key_id)
        )
        
        if result.rowcount > 0:
            logger.info("api_key_deleted", key_id=key_id)
            return True
        return False
    
    async def validate(self, raw_key: str) -> Optional[APIKey]:
        """Validate a raw API key and return if valid."""
        if not raw_key:
            return None
        
        key_hash = self._hash_key(raw_key)
        api_key = await self.get_by_hash(key_hash)
        
        if api_key is None:
            logger.warning("api_key_not_found", key_hash=key_hash[:8])
            return None
        
        if not api_key.is_active:
            logger.warning("api_key_inactive", key_id=api_key.key_id)
            return None
        
        if api_key.is_expired():
            logger.warning("api_key_expired", key_id=api_key.key_id)
            return None
        
        # Update last used (non-blocking)
        await self.update_last_used(api_key.key_id)
        
        return api_key


# ============================================================================
# IN-MEMORY IMPLEMENTATION (for testing)
# ============================================================================


class InMemoryAPIKeyRepository(APIKeyRepository):
    """In-memory API key repository for testing."""
    
    def __init__(self):
        self._keys: dict[str, APIKey] = {}
        self._by_hash: dict[str, str] = {}  # hash -> key_id
        self._by_owner: dict[str, list[str]] = {}  # owner_id -> [key_id]
    
    async def create(self, request: CreateAPIKeyRequest) -> APIKeyResponse:
        """Create a new API key."""
        key_id = f"rk_{secrets.token_hex(8)}"
        raw_key = f"{key_id}.{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        expires_at = None
        if request.expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)
        
        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            owner_id=request.owner_id,
            owner_type=request.owner_type,
            name=request.name,
            scopes=request.scopes,
            rate_limit_per_minute=request.rate_limit_per_minute,
            expires_at=expires_at,
            metadata=request.metadata,
        )
        
        self._keys[key_id] = api_key
        self._by_hash[key_hash] = key_id
        
        if request.owner_id not in self._by_owner:
            self._by_owner[request.owner_id] = []
        self._by_owner[request.owner_id].append(key_id)
        
        return APIKeyResponse(raw_key=raw_key, api_key=api_key)
    
    async def get_by_id(self, key_id: str) -> Optional[APIKey]:
        return self._keys.get(key_id)
    
    async def get_by_hash(self, key_hash: str) -> Optional[APIKey]:
        key_id = self._by_hash.get(key_hash)
        return self._keys.get(key_id) if key_id else None
    
    async def get_by_owner(self, owner_id: str) -> List[APIKey]:
        key_ids = self._by_owner.get(owner_id, [])
        return [self._keys[kid] for kid in key_ids if kid in self._keys]
    
    async def update_last_used(self, key_id: str) -> None:
        if key_id in self._keys:
            self._keys[key_id].last_used_at = datetime.utcnow()
    
    async def deactivate(self, key_id: str) -> bool:
        if key_id in self._keys:
            self._keys[key_id].is_active = False
            return True
        return False
    
    async def delete(self, key_id: str) -> bool:
        if key_id in self._keys:
            api_key = self._keys.pop(key_id)
            self._by_hash.pop(api_key.key_hash, None)
            if api_key.owner_id in self._by_owner:
                self._by_owner[api_key.owner_id].remove(key_id)
            return True
        return False
    
    async def validate(self, raw_key: str) -> Optional[APIKey]:
        if not raw_key:
            return None
        
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        api_key = await self.get_by_hash(key_hash)
        
        if api_key and api_key.is_active and not api_key.is_expired():
            await self.update_last_used(api_key.key_id)
            return api_key
        
        return None
