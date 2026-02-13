"""
Input Snapshot Management and Validation.

This module provides utilities for:
1. Capturing input snapshots before decision generation
2. Validating snapshot integrity
3. Comparing snapshots for debugging
4. Reconstructing inputs for replay

CRITICAL: Snapshots MUST be captured BEFORE decision generation.

Usage:
    from app.audit.snapshots import SnapshotManager
    
    manager = SnapshotManager()
    
    # Capture before decision
    snapshot = await manager.capture(signal, reality, context)
    
    # Validate integrity
    is_valid = await manager.validate(snapshot)
    
    # Reconstruct for replay
    signal, reality, context = await manager.reconstruct(snapshot)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Any, TypeVar, Generic, TYPE_CHECKING
from pydantic import BaseModel, Field
import hashlib
import json
import difflib

import structlog

from app.audit.schemas import InputSnapshot

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from app.omen.schemas import OmenSignal
    from app.oracle.schemas import CorrelatedIntelligence, RealitySnapshot
    from app.riskcast.schemas.customer import CustomerContext, CustomerProfile, Shipment

logger = structlog.get_logger(__name__)


# =============================================================================
# SNAPSHOT VALIDATION
# =============================================================================


class SnapshotValidationResult(BaseModel):
    """Result of snapshot validation."""
    
    is_valid: bool = Field(description="Whether the snapshot is valid")
    integrity_check: bool = Field(description="Hash integrity check passed")
    completeness_check: bool = Field(description="All required fields present")
    freshness_check: bool = Field(description="Data is not too stale")
    
    # Details
    staleness_seconds: int = Field(ge=0, description="How stale the reality data is")
    max_staleness_seconds: int = Field(ge=0, description="Maximum allowed staleness")
    missing_fields: list[str] = Field(default_factory=list, description="Missing required fields")
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")
    
    @property
    def summary(self) -> str:
        """Human-readable summary of validation result."""
        if self.is_valid:
            return "Snapshot is valid and ready for decision generation"
        
        issues = []
        if not self.integrity_check:
            issues.append("integrity compromised")
        if not self.completeness_check:
            issues.append(f"missing fields: {', '.join(self.missing_fields)}")
        if not self.freshness_check:
            issues.append(f"data is {self.staleness_seconds}s stale (max {self.max_staleness_seconds}s)")
        
        return f"Snapshot validation failed: {'; '.join(issues)}"


class SnapshotDiff(BaseModel):
    """Difference between two snapshots."""
    
    snapshot_a_id: str
    snapshot_b_id: str
    time_diff_seconds: float
    
    # What changed
    signal_changed: bool = Field(default=False)
    reality_changed: bool = Field(default=False)
    context_changed: bool = Field(default=False)
    
    # Details
    signal_diff: Optional[str] = Field(default=None, description="Signal differences")
    reality_diff: Optional[str] = Field(default=None, description="Reality differences")
    context_diff: Optional[str] = Field(default=None, description="Context differences")
    
    @property
    def has_changes(self) -> bool:
        """Whether any changes were detected."""
        return self.signal_changed or self.reality_changed or self.context_changed


# =============================================================================
# SNAPSHOT MANAGER
# =============================================================================


class SnapshotManager:
    """
    Manager for input snapshots.
    
    Provides:
    - Capture: Create immutable snapshot of all inputs
    - Validate: Verify snapshot integrity and completeness
    - Compare: Diff two snapshots for debugging
    - Reconstruct: Rebuild inputs from snapshot for replay
    """
    
    def __init__(
        self,
        max_staleness_seconds: int = 900,  # 15 minutes default
        require_all_fields: bool = True,
    ):
        """
        Initialize snapshot manager.
        
        Args:
            max_staleness_seconds: Maximum allowed staleness for reality data
            require_all_fields: Whether to require all fields for completeness
        """
        self._max_staleness = max_staleness_seconds
        self._require_all_fields = require_all_fields
    
    def capture(
        self,
        signal: "OmenSignal",
        reality: Any,  # RealitySnapshot or similar
        context: "CustomerContext",
    ) -> InputSnapshot:
        """
        Capture immutable snapshot of all inputs.
        
        MUST be called BEFORE decision generation begins.
        
        Args:
            signal: The OMEN signal triggering this decision
            reality: The reality snapshot from ORACLE
            context: The customer context
            
        Returns:
            InputSnapshot with all data hashed for integrity
        """
        snapshot = InputSnapshot.capture(
            signal=signal,
            reality=reality,
            context=context,
        )
        
        logger.info(
            "snapshot_captured",
            snapshot_id=snapshot.snapshot_id,
            signal_id=snapshot.signal_id,
            customer_id=snapshot.customer_id,
            staleness_seconds=snapshot.reality_staleness_seconds,
        )
        
        return snapshot
    
    def validate(
        self,
        snapshot: InputSnapshot,
        max_staleness_seconds: Optional[int] = None,
    ) -> SnapshotValidationResult:
        """
        Validate snapshot integrity and completeness.
        
        Checks:
        1. Hash integrity (no tampering)
        2. Completeness (all required fields present)
        3. Freshness (data not too stale)
        
        Args:
            snapshot: The snapshot to validate
            max_staleness_seconds: Override max staleness (optional)
            
        Returns:
            SnapshotValidationResult with details
        """
        max_stale = max_staleness_seconds or self._max_staleness
        warnings: list[str] = []
        missing_fields: list[str] = []
        
        # 1. INTEGRITY CHECK
        integrity_check = snapshot.verify_integrity()
        if not integrity_check:
            warnings.append("Hash integrity check failed - data may have been tampered with")
        
        # 2. COMPLETENESS CHECK
        completeness_check = True
        
        # Check signal data
        required_signal_fields = ["signal_id", "probability", "category", "chokepoint"]
        for field in required_signal_fields:
            if field not in snapshot.signal_data:
                missing_fields.append(f"signal.{field}")
                completeness_check = False
        
        # Check reality data
        required_reality_fields = ["timestamp"]  # Minimal requirement
        for field in required_reality_fields:
            if field not in snapshot.reality_data and "captured_at" not in snapshot.reality_data:
                missing_fields.append(f"reality.{field}")
                # Don't fail completeness for reality - may be degraded mode
                warnings.append(f"Reality data missing {field}")
        
        # Check customer context
        required_context_fields = ["profile"]
        for field in required_context_fields:
            if field not in snapshot.customer_context_data:
                missing_fields.append(f"context.{field}")
                completeness_check = False
        
        # 3. FRESHNESS CHECK
        freshness_check = snapshot.reality_staleness_seconds <= max_stale
        if not freshness_check:
            warnings.append(
                f"Reality data is {snapshot.reality_staleness_seconds}s stale "
                f"(max allowed: {max_stale}s)"
            )
        
        # Add warning for moderately stale data
        if snapshot.reality_staleness_seconds > max_stale // 2:
            warnings.append(
                f"Reality data is getting stale ({snapshot.reality_staleness_seconds}s)"
            )
        
        is_valid = integrity_check and completeness_check and freshness_check
        
        return SnapshotValidationResult(
            is_valid=is_valid,
            integrity_check=integrity_check,
            completeness_check=completeness_check,
            freshness_check=freshness_check,
            staleness_seconds=snapshot.reality_staleness_seconds,
            max_staleness_seconds=max_stale,
            missing_fields=missing_fields,
            warnings=warnings,
        )
    
    def compare(
        self,
        snapshot_a: InputSnapshot,
        snapshot_b: InputSnapshot,
    ) -> SnapshotDiff:
        """
        Compare two snapshots and identify differences.
        
        Useful for:
        - Debugging decision differences
        - Understanding input changes over time
        - Validating replay accuracy
        
        Args:
            snapshot_a: First snapshot
            snapshot_b: Second snapshot
            
        Returns:
            SnapshotDiff with details of changes
        """
        time_diff = (snapshot_b.captured_at - snapshot_a.captured_at).total_seconds()
        
        # Compare signals
        signal_changed = snapshot_a.signal_hash != snapshot_b.signal_hash
        signal_diff = None
        if signal_changed:
            signal_diff = self._compute_json_diff(
                snapshot_a.signal_data,
                snapshot_b.signal_data,
            )
        
        # Compare reality
        reality_changed = snapshot_a.reality_hash != snapshot_b.reality_hash
        reality_diff = None
        if reality_changed:
            reality_diff = self._compute_json_diff(
                snapshot_a.reality_data,
                snapshot_b.reality_data,
            )
        
        # Compare context
        context_changed = snapshot_a.customer_context_hash != snapshot_b.customer_context_hash
        context_diff = None
        if context_changed:
            context_diff = self._compute_json_diff(
                snapshot_a.customer_context_data,
                snapshot_b.customer_context_data,
            )
        
        return SnapshotDiff(
            snapshot_a_id=snapshot_a.snapshot_id,
            snapshot_b_id=snapshot_b.snapshot_id,
            time_diff_seconds=time_diff,
            signal_changed=signal_changed,
            reality_changed=reality_changed,
            context_changed=context_changed,
            signal_diff=signal_diff,
            reality_diff=reality_diff,
            context_diff=context_diff,
        )
    
    def reconstruct_signal(self, snapshot: InputSnapshot) -> dict:
        """
        Reconstruct signal data from snapshot.
        
        Note: Returns dict, not OmenSignal, to avoid
        deserialization issues.
        
        Args:
            snapshot: The snapshot containing signal data
            
        Returns:
            Signal data as dictionary
        """
        return snapshot.signal_data.copy()
    
    def reconstruct_reality(self, snapshot: InputSnapshot) -> dict:
        """
        Reconstruct reality data from snapshot.
        
        Args:
            snapshot: The snapshot containing reality data
            
        Returns:
            Reality data as dictionary
        """
        return snapshot.reality_data.copy()
    
    def reconstruct_context(self, snapshot: InputSnapshot) -> dict:
        """
        Reconstruct customer context from snapshot.
        
        Args:
            snapshot: The snapshot containing context data
            
        Returns:
            Context data as dictionary
        """
        return snapshot.customer_context_data.copy()
    
    def _compute_json_diff(
        self,
        dict_a: dict,
        dict_b: dict,
    ) -> str:
        """
        Compute human-readable diff between two dictionaries.
        """
        json_a = json.dumps(dict_a, sort_keys=True, indent=2, default=str)
        json_b = json.dumps(dict_b, sort_keys=True, indent=2, default=str)
        
        diff_lines = list(difflib.unified_diff(
            json_a.splitlines(),
            json_b.splitlines(),
            fromfile='snapshot_a',
            tofile='snapshot_b',
            lineterm='',
        ))
        
        return '\n'.join(diff_lines[:100])  # Limit output size


# =============================================================================
# SNAPSHOT COMPRESSOR
# =============================================================================


class SnapshotCompressor:
    """
    Compress snapshots for efficient storage.
    
    In production, snapshots can be large (especially reality data).
    This compressor reduces storage requirements while maintaining
    reproducibility.
    """
    
    def compress(self, snapshot: InputSnapshot) -> dict:
        """
        Compress snapshot to minimal representation.
        
        Preserves:
        - All hashes for integrity verification
        - Minimal data needed for replay
        
        Args:
            snapshot: Full snapshot
            
        Returns:
            Compressed snapshot dictionary
        """
        return {
            "snapshot_id": snapshot.snapshot_id,
            "captured_at": snapshot.captured_at.isoformat(),
            "signal_id": snapshot.signal_id,
            "signal_hash": snapshot.signal_hash,
            # Store only essential signal data
            "signal_essential": {
                "probability": snapshot.signal_data.get("probability"),
                "confidence": snapshot.signal_data.get("confidence"),
                "category": snapshot.signal_data.get("category"),
                "chokepoint": snapshot.signal_data.get("chokepoint"),
            },
            "reality_hash": snapshot.reality_hash,
            "reality_staleness_seconds": snapshot.reality_staleness_seconds,
            # Store only essential reality data
            "reality_essential": {
                "timestamp": snapshot.reality_data.get("timestamp") or snapshot.reality_data.get("captured_at"),
            },
            "customer_id": snapshot.customer_id,
            "customer_context_hash": snapshot.customer_context_hash,
            "customer_context_version": snapshot.customer_context_version,
            "combined_hash": snapshot.combined_hash,
        }
    
    def is_compressed(self, data: dict) -> bool:
        """Check if data is a compressed snapshot."""
        return (
            "snapshot_id" in data
            and "signal_essential" in data
            and "signal_data" not in data
        )


# =============================================================================
# SNAPSHOT ARCHIVER
# =============================================================================


class SnapshotArchiver:
    """
    Archive old snapshots for long-term storage.
    
    Supports:
    - Compression for storage efficiency
    - Retention policies
    - Retrieval for audits
    """
    
    def __init__(
        self,
        retention_days: int = 365,  # 1 year default
        compress_after_days: int = 30,
    ):
        """
        Initialize archiver.
        
        Args:
            retention_days: How long to keep snapshots
            compress_after_days: When to compress snapshots
        """
        self._retention_days = retention_days
        self._compress_after_days = compress_after_days
        self._compressor = SnapshotCompressor()
    
    def should_archive(self, snapshot: InputSnapshot) -> bool:
        """Check if snapshot should be archived."""
        age_days = (datetime.utcnow() - snapshot.captured_at).days
        return age_days >= self._compress_after_days
    
    def should_delete(self, snapshot: InputSnapshot) -> bool:
        """Check if snapshot should be deleted (past retention)."""
        age_days = (datetime.utcnow() - snapshot.captured_at).days
        return age_days >= self._retention_days
    
    def archive(self, snapshot: InputSnapshot) -> dict:
        """
        Archive a snapshot for long-term storage.
        
        Args:
            snapshot: Snapshot to archive
            
        Returns:
            Archived representation
        """
        return {
            "type": "archived_snapshot",
            "archived_at": datetime.utcnow().isoformat(),
            "original_snapshot_id": snapshot.snapshot_id,
            "compressed_data": self._compressor.compress(snapshot),
        }
    
    def get_retention_policy(self) -> dict:
        """Get current retention policy."""
        return {
            "retention_days": self._retention_days,
            "compress_after_days": self._compress_after_days,
            "policy_version": "1.0",
        }


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================


def create_snapshot_manager(
    max_staleness_seconds: int = 900,
) -> SnapshotManager:
    """
    Create a snapshot manager.
    
    Args:
        max_staleness_seconds: Maximum allowed staleness
        
    Returns:
        SnapshotManager instance
    """
    return SnapshotManager(max_staleness_seconds=max_staleness_seconds)


def create_snapshot_archiver(
    retention_days: int = 365,
    compress_after_days: int = 30,
) -> SnapshotArchiver:
    """
    Create a snapshot archiver.
    
    Args:
        retention_days: How long to keep snapshots
        compress_after_days: When to compress snapshots
        
    Returns:
        SnapshotArchiver instance
    """
    return SnapshotArchiver(
        retention_days=retention_days,
        compress_after_days=compress_after_days,
    )
