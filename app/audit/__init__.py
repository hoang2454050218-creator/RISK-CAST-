"""
RISKCAST Audit System - Cryptographic Accountability Framework.

This module provides enterprise-grade audit capabilities:
- Immutable audit trail with cryptographic chaining
- Input snapshots for decision reproducibility
- Legal defensibility documentation
- Human override tracking
- Pipeline integration hooks

CRITICAL: Every decision MUST go through the audit service.
A decision without an audit trail is not defensible.

Usage:
    from app.audit import AuditedDecisionComposer, create_audited_composer
    
    # Create audited composer
    composer = create_audited_composer()
    
    # Generate decision with full audit trail
    decision = await composer.compose(intelligence, context)
"""

from app.audit.schemas import (
    AuditEventType,
    AuditRecord,
    InputSnapshot,
    ProcessingRecord,
    AuditChainVerification,
    DecisionAuditTrail,
)
from app.audit.service import AuditService
from app.audit.repository import AuditRepository, InMemoryAuditRepository
from app.audit.justification import (
    JustificationLevel,
    Audience,
    EvidenceItem,
    AlternativeAnalysis,
    LimitationsDisclosure,
    LegalJustification,
    JustificationGenerator,
    create_justification_generator,
)

# Import trail components (may have deferred imports internally)
from app.audit.trail import (
    AuditedDecisionComposer,
    AuditPipelineHooks,
    AuditChainVerifier,
    audit_decision,
    create_audited_composer,
    create_pipeline_hooks,
    create_chain_verifier,
)

# Import snapshot components
from app.audit.snapshots import (
    SnapshotManager,
    SnapshotValidationResult,
    SnapshotDiff,
    SnapshotCompressor,
    SnapshotArchiver,
    create_snapshot_manager,
    create_snapshot_archiver,
)

__all__ = [
    # Schemas
    "AuditEventType",
    "AuditRecord",
    "InputSnapshot",
    "ProcessingRecord",
    "AuditChainVerification",
    "DecisionAuditTrail",
    # Service
    "AuditService",
    # Repository
    "AuditRepository",
    "InMemoryAuditRepository",
    # Justification
    "JustificationLevel",
    "Audience",
    "EvidenceItem",
    "AlternativeAnalysis",
    "LimitationsDisclosure",
    "LegalJustification",
    "JustificationGenerator",
    "create_justification_generator",
    # Trail integration
    "AuditedDecisionComposer",
    "AuditPipelineHooks",
    "AuditChainVerifier",
    "audit_decision",
    "create_audited_composer",
    "create_pipeline_hooks",
    "create_chain_verifier",
    # Snapshots
    "SnapshotManager",
    "SnapshotValidationResult",
    "SnapshotDiff",
    "SnapshotCompressor",
    "SnapshotArchiver",
    "create_snapshot_manager",
    "create_snapshot_archiver",
]
