"""
Schema Versioning and Migration Support.

Provides:
- Schema version tracking
- Migration history
- Rollback support
- Schema compatibility checks
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base
import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# SCHEMA VERSION MODEL
# ============================================================================


class MigrationStatus(str, Enum):
    """Migration status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class SchemaVersion(Base):
    """
    Tracks database schema version and migrations.
    """
    
    __tablename__ = "schema_versions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    version = Column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        doc="Semantic version (e.g., 1.0.0)",
    )
    
    migration_name = Column(
        String(255),
        nullable=False,
        doc="Migration name/description",
    )
    
    migration_script = Column(
        Text,
        nullable=True,
        doc="SQL or script content",
    )
    
    status = Column(
        String(20),
        default=MigrationStatus.PENDING,
        nullable=False,
        doc="Migration status",
    )
    
    checksum = Column(
        String(64),
        nullable=True,
        doc="Checksum of migration for validation",
    )
    
    applied_at = Column(
        DateTime,
        nullable=True,
        doc="When migration was applied",
    )
    
    applied_by = Column(
        String(255),
        nullable=True,
        doc="User/system that applied migration",
    )
    
    execution_time_ms = Column(
        Integer,
        nullable=True,
        doc="How long the migration took",
    )
    
    rollback_script = Column(
        Text,
        nullable=True,
        doc="SQL or script to rollback",
    )
    
    rolled_back_at = Column(
        DateTime,
        nullable=True,
        doc="When migration was rolled back",
    )
    
    error_message = Column(
        Text,
        nullable=True,
        doc="Error message if migration failed",
    )
    
    is_breaking = Column(
        Boolean,
        default=False,
        doc="Whether this is a breaking change",
    )
    
    requires_downtime = Column(
        Boolean,
        default=False,
        doc="Whether this requires downtime",
    )


# ============================================================================
# SCHEMA VERSION SERVICE
# ============================================================================


class SchemaVersionService:
    """
    Service for managing schema versions.
    """
    
    # Current application schema version
    CURRENT_VERSION = "1.0.0"
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get_current_version(self) -> Optional[str]:
        """Get the current schema version."""
        stmt = (
            select(SchemaVersion)
            .where(SchemaVersion.status == MigrationStatus.COMPLETED)
            .order_by(SchemaVersion.applied_at.desc())
            .limit(1)
        )
        
        result = await self._session.execute(stmt)
        latest = result.scalar_one_or_none()
        
        return latest.version if latest else None
    
    async def is_schema_compatible(self) -> bool:
        """
        Check if current schema is compatible with application.
        """
        current = await self.get_current_version()
        
        if not current:
            # No migrations applied - need to initialize
            return False
        
        # Simple semver compatibility check
        current_parts = current.split(".")
        required_parts = self.CURRENT_VERSION.split(".")
        
        # Major version must match
        return current_parts[0] == required_parts[0]
    
    async def get_pending_migrations(self) -> List[SchemaVersion]:
        """Get migrations that haven't been applied."""
        stmt = (
            select(SchemaVersion)
            .where(SchemaVersion.status == MigrationStatus.PENDING)
            .order_by(SchemaVersion.version)
        )
        
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_migration_history(
        self,
        limit: int = 50,
    ) -> List[SchemaVersion]:
        """Get migration history."""
        stmt = (
            select(SchemaVersion)
            .order_by(SchemaVersion.applied_at.desc())
            .limit(limit)
        )
        
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    async def record_migration(
        self,
        version: str,
        name: str,
        script: Optional[str] = None,
        checksum: Optional[str] = None,
        is_breaking: bool = False,
        requires_downtime: bool = False,
    ) -> SchemaVersion:
        """Record a new migration."""
        migration = SchemaVersion(
            version=version,
            migration_name=name,
            migration_script=script,
            checksum=checksum,
            status=MigrationStatus.PENDING,
            is_breaking=is_breaking,
            requires_downtime=requires_downtime,
        )
        
        self._session.add(migration)
        await self._session.flush()
        
        logger.info(
            "migration_recorded",
            version=version,
            name=name,
        )
        
        return migration
    
    async def mark_migration_started(self, version: str) -> None:
        """Mark migration as started."""
        stmt = select(SchemaVersion).where(SchemaVersion.version == version)
        result = await self._session.execute(stmt)
        migration = result.scalar_one_or_none()
        
        if migration:
            migration.status = MigrationStatus.RUNNING
            await self._session.flush()
    
    async def mark_migration_completed(
        self,
        version: str,
        execution_time_ms: int,
        applied_by: str = "system",
    ) -> None:
        """Mark migration as completed."""
        stmt = select(SchemaVersion).where(SchemaVersion.version == version)
        result = await self._session.execute(stmt)
        migration = result.scalar_one_or_none()
        
        if migration:
            migration.status = MigrationStatus.COMPLETED
            migration.applied_at = datetime.utcnow()
            migration.applied_by = applied_by
            migration.execution_time_ms = execution_time_ms
            await self._session.flush()
            
            logger.info(
                "migration_completed",
                version=version,
                execution_time_ms=execution_time_ms,
            )
    
    async def mark_migration_failed(
        self,
        version: str,
        error_message: str,
    ) -> None:
        """Mark migration as failed."""
        stmt = select(SchemaVersion).where(SchemaVersion.version == version)
        result = await self._session.execute(stmt)
        migration = result.scalar_one_or_none()
        
        if migration:
            migration.status = MigrationStatus.FAILED
            migration.error_message = error_message
            await self._session.flush()
            
            logger.error(
                "migration_failed",
                version=version,
                error=error_message,
            )
    
    async def rollback_migration(
        self,
        version: str,
        rolled_back_by: str = "system",
    ) -> bool:
        """Rollback a migration."""
        stmt = select(SchemaVersion).where(SchemaVersion.version == version)
        result = await self._session.execute(stmt)
        migration = result.scalar_one_or_none()
        
        if not migration:
            return False
        
        if migration.status != MigrationStatus.COMPLETED:
            logger.warning(
                "cannot_rollback",
                version=version,
                status=migration.status,
            )
            return False
        
        # Execute rollback script if available
        if migration.rollback_script:
            # Would execute rollback_script here
            pass
        
        migration.status = MigrationStatus.ROLLED_BACK
        migration.rolled_back_at = datetime.utcnow()
        await self._session.flush()
        
        logger.info(
            "migration_rolled_back",
            version=version,
            rolled_back_by=rolled_back_by,
        )
        
        return True


# ============================================================================
# SCHEMA COMPATIBILITY CHECKER
# ============================================================================


class SchemaCompatibility:
    """
    Checks schema compatibility between versions.
    """
    
    @staticmethod
    def is_backward_compatible(
        old_version: str,
        new_version: str,
    ) -> bool:
        """
        Check if new version is backward compatible with old.
        
        Follows semantic versioning:
        - Major: Breaking changes
        - Minor: Backward compatible features
        - Patch: Bug fixes
        """
        old_parts = [int(x) for x in old_version.split(".")]
        new_parts = [int(x) for x in new_version.split(".")]
        
        # Pad with zeros if needed
        while len(old_parts) < 3:
            old_parts.append(0)
        while len(new_parts) < 3:
            new_parts.append(0)
        
        # Major version change = breaking
        if new_parts[0] != old_parts[0]:
            return False
        
        # Minor/patch increases are backward compatible
        if new_parts[1] >= old_parts[1]:
            return True
        
        return False
    
    @staticmethod
    def requires_migration(
        current_version: str,
        target_version: str,
    ) -> bool:
        """Check if migration is required."""
        return current_version != target_version
    
    @staticmethod
    def get_migration_path(
        current_version: str,
        target_version: str,
        available_migrations: List[str],
    ) -> List[str]:
        """
        Get ordered list of migrations to apply.
        
        Returns migrations between current and target versions.
        """
        # Filter and sort migrations
        path = []
        
        for migration in sorted(available_migrations):
            if migration > current_version and migration <= target_version:
                path.append(migration)
        
        return path


# ============================================================================
# API VERSION SUPPORT
# ============================================================================


class APIVersion:
    """
    API versioning support.
    """
    
    CURRENT = "v1"
    SUPPORTED = ["v1"]
    DEPRECATED = []
    
    @classmethod
    def is_supported(cls, version: str) -> bool:
        """Check if API version is supported."""
        return version in cls.SUPPORTED
    
    @classmethod
    def is_deprecated(cls, version: str) -> bool:
        """Check if API version is deprecated."""
        return version in cls.DEPRECATED
    
    @classmethod
    def get_deprecation_warning(cls, version: str) -> Optional[str]:
        """Get deprecation warning message."""
        if cls.is_deprecated(version):
            return (
                f"API version {version} is deprecated. "
                f"Please migrate to {cls.CURRENT}."
            )
        return None
