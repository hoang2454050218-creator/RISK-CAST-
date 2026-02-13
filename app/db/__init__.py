"""
Database module for RISKCAST.

Provides:
- Base models with audit fields
- API key management
- Schema versioning
- Repository patterns
"""

from app.db.base_model import (
    AuditMixin,
    AuditedModel,
    BaseRepository,
    OptimisticLockError,
    QueryFilter,
    SoftDeleteMixin,
    TenantAuditedModel,
    TenantMixin,
    VersionMixin,
    update_with_optimistic_lock,
)
from app.db.api_keys import (
    APIKeyModel,
    APIKeyService,
)
from app.db.schema_versioning import (
    APIVersion,
    MigrationStatus,
    SchemaCompatibility,
    SchemaVersion,
    SchemaVersionService,
)

__all__ = [
    # Base models
    "AuditMixin",
    "AuditedModel",
    "BaseRepository",
    "OptimisticLockError",
    "QueryFilter",
    "SoftDeleteMixin",
    "TenantAuditedModel",
    "TenantMixin",
    "VersionMixin",
    "update_with_optimistic_lock",
    # API keys
    "APIKeyModel",
    "APIKeyService",
    # Schema versioning
    "APIVersion",
    "MigrationStatus",
    "SchemaCompatibility",
    "SchemaVersion",
    "SchemaVersionService",
]
