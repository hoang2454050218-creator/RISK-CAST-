"""
Base Database Models with Audit Fields.

Provides:
- Automatic timestamp tracking
- Soft delete support
- Audit trail columns
- Optimistic locking
- Multi-tenancy support
"""

from datetime import datetime
from typing import Optional, Any
import uuid

from sqlalchemy import Column, String, DateTime, Boolean, Integer, event, inspect
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.middleware import customer_id_var


# ============================================================================
# AUDIT MIXIN
# ============================================================================


class AuditMixin:
    """
    Mixin that adds audit fields to any model.
    
    Fields:
    - created_at: When the record was created
    - updated_at: When the record was last updated
    - created_by: Who created the record
    - updated_by: Who last updated the record
    """
    
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
        doc="Timestamp when record was created",
    )
    
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        index=True,
        doc="Timestamp when record was last updated",
    )
    
    created_by = Column(
        String(255),
        nullable=True,
        doc="User/system that created the record",
    )
    
    updated_by = Column(
        String(255),
        nullable=True,
        doc="User/system that last updated the record",
    )


# ============================================================================
# SOFT DELETE MIXIN
# ============================================================================


class SoftDeleteMixin:
    """
    Mixin for soft delete support.
    
    Records are never actually deleted - they're marked as deleted
    and can be restored later.
    """
    
    is_deleted = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Whether record is soft-deleted",
    )
    
    deleted_at = Column(
        DateTime,
        nullable=True,
        doc="Timestamp when record was soft-deleted",
    )
    
    deleted_by = Column(
        String(255),
        nullable=True,
        doc="User/system that deleted the record",
    )
    
    def soft_delete(self, deleted_by: Optional[str] = None) -> None:
        """Mark this record as deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.deleted_by = deleted_by
    
    def restore(self, restored_by: Optional[str] = None) -> None:
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.updated_by = restored_by
        self.updated_at = datetime.utcnow()


# ============================================================================
# OPTIMISTIC LOCKING MIXIN
# ============================================================================


class VersionMixin:
    """
    Mixin for optimistic locking using version numbers.
    
    Prevents lost updates in concurrent scenarios.
    """
    
    version = Column(
        Integer,
        default=1,
        nullable=False,
        doc="Version number for optimistic locking",
    )
    
    def increment_version(self) -> None:
        """Increment version for optimistic locking."""
        self.version += 1


# ============================================================================
# MULTI-TENANCY MIXIN
# ============================================================================


class TenantMixin:
    """
    Mixin for multi-tenancy support.
    
    All tenant-scoped queries should filter by tenant_id.
    """
    
    tenant_id = Column(
        String(255),
        nullable=False,
        index=True,
        doc="Tenant/Customer identifier for multi-tenancy",
    )
    
    @classmethod
    def for_tenant(cls, query, tenant_id: str):
        """Filter query by tenant."""
        return query.filter(cls.tenant_id == tenant_id)


# ============================================================================
# BASE MODEL
# ============================================================================


class AuditedModel(Base, AuditMixin, SoftDeleteMixin, VersionMixin):
    """
    Base model with full audit capabilities.
    
    Includes:
    - Automatic timestamps
    - Soft delete
    - Optimistic locking
    """
    
    __abstract__ = True
    
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        doc="UUID primary key",
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def update_from_dict(self, data: dict, ignore_keys: Optional[list] = None) -> None:
        """Update model from dictionary."""
        ignore = ignore_keys or ["id", "created_at", "created_by", "version"]
        
        for key, value in data.items():
            if key not in ignore and hasattr(self, key):
                setattr(self, key, value)


class TenantAuditedModel(AuditedModel, TenantMixin):
    """
    Base model for tenant-scoped entities.
    
    Use this for any customer/tenant-specific data.
    """
    
    __abstract__ = True


# ============================================================================
# EVENT LISTENERS
# ============================================================================


@event.listens_for(AuditedModel, "before_update", propagate=True)
def receive_before_update(mapper, connection, target):
    """Automatically increment version on update."""
    target.version += 1


@event.listens_for(Session, "before_flush")
def receive_before_flush(session, flush_context, instances):
    """
    Set created_by and updated_by from context.
    """
    # Try to get current user from context
    current_user = None
    try:
        current_user = customer_id_var.get()
    except Exception:
        pass
    
    for obj in session.new:
        if hasattr(obj, "created_by") and obj.created_by is None:
            obj.created_by = current_user or "system"
        if hasattr(obj, "updated_by"):
            obj.updated_by = current_user or "system"
    
    for obj in session.dirty:
        if hasattr(obj, "updated_by"):
            obj.updated_by = current_user or "system"


# ============================================================================
# QUERY HELPERS
# ============================================================================


class QueryFilter:
    """
    Helper for common query filters.
    """
    
    @staticmethod
    def not_deleted(query, model_class):
        """Filter out soft-deleted records."""
        if hasattr(model_class, "is_deleted"):
            return query.filter(model_class.is_deleted == False)
        return query
    
    @staticmethod
    def for_tenant(query, model_class, tenant_id: str):
        """Filter by tenant."""
        if hasattr(model_class, "tenant_id"):
            return query.filter(model_class.tenant_id == tenant_id)
        return query
    
    @staticmethod
    def created_between(query, model_class, start: datetime, end: datetime):
        """Filter by creation date range."""
        return query.filter(
            model_class.created_at >= start,
            model_class.created_at <= end,
        )
    
    @staticmethod
    def updated_since(query, model_class, since: datetime):
        """Filter records updated since a given time."""
        return query.filter(model_class.updated_at >= since)


# ============================================================================
# REPOSITORY BASE
# ============================================================================


class BaseRepository:
    """
    Base repository with common CRUD operations.
    """
    
    def __init__(self, session: Session, model_class):
        self._session = session
        self._model = model_class
    
    async def get_by_id(self, id: str) -> Optional[Any]:
        """Get entity by ID."""
        return await self._session.get(self._model, id)
    
    async def get_by_id_for_update(self, id: str) -> Optional[Any]:
        """Get entity with row lock for update."""
        from sqlalchemy import select
        
        stmt = (
            select(self._model)
            .where(self._model.id == id)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def save(self, entity) -> Any:
        """Save entity (insert or update)."""
        self._session.add(entity)
        await self._session.flush()
        return entity
    
    async def delete(self, entity, hard: bool = False) -> None:
        """Delete entity (soft or hard)."""
        if hard:
            await self._session.delete(entity)
        elif hasattr(entity, "soft_delete"):
            entity.soft_delete()
        else:
            await self._session.delete(entity)
        await self._session.flush()
    
    async def exists(self, id: str) -> bool:
        """Check if entity exists."""
        from sqlalchemy import select, func
        
        stmt = select(func.count()).where(self._model.id == id)
        result = await self._session.execute(stmt)
        return result.scalar() > 0


# ============================================================================
# OPTIMISTIC LOCK EXCEPTION
# ============================================================================


class OptimisticLockError(Exception):
    """
    Raised when optimistic lock fails.
    
    This means another process updated the record
    between our read and write.
    """
    
    def __init__(self, entity_type: str, entity_id: str, expected_version: int):
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.expected_version = expected_version
        super().__init__(
            f"Optimistic lock failed for {entity_type}({entity_id}): "
            f"expected version {expected_version}"
        )


async def update_with_optimistic_lock(
    session: Session,
    entity,
    updates: dict,
    expected_version: int,
) -> Any:
    """
    Update entity with optimistic locking.
    
    Args:
        session: Database session
        entity: Entity to update
        updates: Dictionary of updates
        expected_version: Expected version number
        
    Raises:
        OptimisticLockError: If version mismatch
    """
    if entity.version != expected_version:
        raise OptimisticLockError(
            entity_type=entity.__class__.__name__,
            entity_id=entity.id,
            expected_version=expected_version,
        )
    
    for key, value in updates.items():
        if hasattr(entity, key):
            setattr(entity, key, value)
    
    session.add(entity)
    await session.flush()
    
    return entity
