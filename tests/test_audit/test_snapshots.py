"""Tests for Input Snapshot Management.

These tests verify:
1. SnapshotManager captures snapshots correctly
2. SnapshotValidation detects issues
3. SnapshotDiff identifies changes between snapshots
4. SnapshotArchiver handles retention policies
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
import json

from app.audit.schemas import InputSnapshot
from app.audit.snapshots import (
    SnapshotManager,
    SnapshotValidationResult,
    SnapshotDiff,
    SnapshotCompressor,
    SnapshotArchiver,
    create_snapshot_manager,
    create_snapshot_archiver,
)

# Type checking only imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass  # Could import types here if needed


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def snapshot_manager():
    """Create snapshot manager with default settings."""
    return SnapshotManager(max_staleness_seconds=900)


@pytest.fixture
def mock_signal():
    """Create mock OMEN signal."""
    signal = MagicMock()
    signal.signal_id = "sig_test_001"
    signal.probability = 0.85
    signal.confidence = 0.9
    signal.category = "disruption"
    signal.chokepoint = "red_sea"
    signal.model_dump.return_value = {
        "signal_id": "sig_test_001",
        "probability": 0.85,
        "confidence": 0.9,
        "category": "disruption",
        "chokepoint": "red_sea",
        "title": "Red Sea Disruption Alert",
        "evidence": [
            {"source": "Polymarket", "confidence": 0.82},
            {"source": "News", "confidence": 0.78},
        ],
    }
    return signal


@pytest.fixture
def mock_reality():
    """Create mock reality data."""
    reality = MagicMock()
    reality.timestamp = datetime.utcnow()
    reality.correlation_status = "confirmed"
    reality.combined_confidence = 0.87
    reality.model_dump.return_value = {
        "timestamp": datetime.utcnow().isoformat(),
        "captured_at": datetime.utcnow().isoformat(),
        "correlation_status": "confirmed",
        "combined_confidence": 0.87,
        "vessels_confirming": 47,
    }
    return reality


@pytest.fixture
def mock_stale_reality():
    """Create mock stale reality data (30 minutes old)."""
    stale_time = datetime.utcnow() - timedelta(minutes=30)
    reality = MagicMock()
    reality.timestamp = stale_time
    reality.model_dump.return_value = {
        "timestamp": stale_time.isoformat(),
        "captured_at": stale_time.isoformat(),
        "correlation_status": "confirmed",
    }
    return reality


@pytest.fixture
def mock_customer_context():
    """Create mock customer context."""
    context = MagicMock()
    context.profile = MagicMock()
    context.profile.customer_id = "cust_test_001"
    context.version = 1
    context.model_dump.return_value = {
        "profile": {
            "customer_id": "cust_test_001",
            "company_name": "Test Corp",
            "risk_tolerance": "balanced",
        },
        "active_shipments": [
            {
                "shipment_id": "shp_001",
                "cargo_value_usd": 150000.0,
                "route_chokepoints": ["red_sea"],
            }
        ],
        "version": 1,
    }
    return context


@pytest.fixture
def sample_snapshot(mock_signal, mock_reality, mock_customer_context):
    """Create a sample input snapshot."""
    return InputSnapshot.capture(
        signal=mock_signal,
        reality=mock_reality,
        context=mock_customer_context,
    )


# ============================================================================
# SNAPSHOT MANAGER TESTS
# ============================================================================


class TestSnapshotManager:
    """Tests for SnapshotManager."""
    
    def test_capture_creates_valid_snapshot(
        self, snapshot_manager, mock_signal, mock_reality, mock_customer_context
    ):
        """Should create a valid snapshot from inputs."""
        snapshot = snapshot_manager.capture(
            signal=mock_signal,
            reality=mock_reality,
            context=mock_customer_context,
        )
        
        assert snapshot is not None
        assert snapshot.snapshot_id.startswith("snap_")
        assert snapshot.signal_id == "sig_test_001"
        assert snapshot.customer_id == "cust_test_001"
    
    def test_capture_computes_hashes(
        self, snapshot_manager, mock_signal, mock_reality, mock_customer_context
    ):
        """Should compute hashes for all input components."""
        snapshot = snapshot_manager.capture(
            signal=mock_signal,
            reality=mock_reality,
            context=mock_customer_context,
        )
        
        assert len(snapshot.signal_hash) == 64  # SHA-256 hex
        assert len(snapshot.reality_hash) == 64
        assert len(snapshot.customer_context_hash) == 64
        assert len(snapshot.combined_hash) == 64
    
    def test_capture_records_staleness(
        self, snapshot_manager, mock_signal, mock_stale_reality, mock_customer_context
    ):
        """Should record reality data staleness."""
        snapshot = snapshot_manager.capture(
            signal=mock_signal,
            reality=mock_stale_reality,
            context=mock_customer_context,
        )
        
        # 30 minutes = 1800 seconds
        assert snapshot.reality_staleness_seconds >= 1790
        assert snapshot.reality_staleness_seconds <= 1810


# ============================================================================
# SNAPSHOT VALIDATION TESTS
# ============================================================================


class TestSnapshotValidation:
    """Tests for snapshot validation."""
    
    def test_validates_fresh_complete_snapshot(
        self, snapshot_manager, sample_snapshot
    ):
        """Should pass validation for fresh, complete snapshot."""
        result = snapshot_manager.validate(sample_snapshot)
        
        assert result.is_valid is True
        assert result.integrity_check is True
        assert result.completeness_check is True
        assert result.freshness_check is True
    
    def test_fails_validation_for_stale_data(
        self, snapshot_manager, mock_signal, mock_stale_reality, mock_customer_context
    ):
        """Should fail validation for stale reality data."""
        snapshot = snapshot_manager.capture(
            signal=mock_signal,
            reality=mock_stale_reality,
            context=mock_customer_context,
        )
        
        result = snapshot_manager.validate(
            snapshot,
            max_staleness_seconds=600,  # 10 minutes max
        )
        
        assert result.is_valid is False
        assert result.freshness_check is False
        assert result.staleness_seconds > 600
    
    def test_warns_for_moderately_stale_data(
        self, snapshot_manager, mock_signal, mock_customer_context
    ):
        """Should warn when data is moderately stale."""
        # Create reality 8 minutes old (within 15 min limit but > 7.5 min warning)
        moderately_stale_time = datetime.utcnow() - timedelta(minutes=8)
        reality = MagicMock()
        reality.timestamp = moderately_stale_time
        reality.model_dump.return_value = {
            "timestamp": moderately_stale_time.isoformat(),
            "captured_at": moderately_stale_time.isoformat(),
        }
        
        snapshot = snapshot_manager.capture(
            signal=mock_signal,
            reality=reality,
            context=mock_customer_context,
        )
        
        result = snapshot_manager.validate(snapshot)
        
        # Should still be valid but have warnings
        assert result.is_valid is True
        assert len(result.warnings) > 0
        assert any("stale" in w.lower() for w in result.warnings)
    
    def test_provides_validation_summary(
        self, snapshot_manager, sample_snapshot
    ):
        """Should provide human-readable summary."""
        result = snapshot_manager.validate(sample_snapshot)
        
        summary = result.summary
        assert isinstance(summary, str)
        assert len(summary) > 0


# ============================================================================
# SNAPSHOT COMPARISON TESTS
# ============================================================================


class TestSnapshotComparison:
    """Tests for snapshot comparison/diff."""
    
    def test_compare_identical_snapshots(
        self, snapshot_manager, mock_signal, mock_reality, mock_customer_context
    ):
        """Should detect no changes for identical snapshots."""
        snapshot1 = snapshot_manager.capture(
            signal=mock_signal,
            reality=mock_reality,
            context=mock_customer_context,
        )
        snapshot2 = snapshot_manager.capture(
            signal=mock_signal,
            reality=mock_reality,
            context=mock_customer_context,
        )
        
        diff = snapshot_manager.compare(snapshot1, snapshot2)
        
        assert diff.has_changes is False
        assert diff.signal_changed is False
        assert diff.reality_changed is False
        assert diff.context_changed is False
    
    def test_compare_detects_signal_changes(
        self, snapshot_manager, mock_signal, mock_reality, mock_customer_context
    ):
        """Should detect signal changes."""
        snapshot1 = snapshot_manager.capture(
            signal=mock_signal,
            reality=mock_reality,
            context=mock_customer_context,
        )
        
        # Modify signal
        modified_signal = MagicMock()
        modified_signal.model_dump.return_value = {
            **mock_signal.model_dump(),
            "probability": 0.95,  # Changed
        }
        
        snapshot2 = snapshot_manager.capture(
            signal=modified_signal,
            reality=mock_reality,
            context=mock_customer_context,
        )
        
        diff = snapshot_manager.compare(snapshot1, snapshot2)
        
        assert diff.has_changes is True
        assert diff.signal_changed is True
        assert diff.signal_diff is not None
    
    def test_compare_calculates_time_diff(
        self, snapshot_manager, mock_signal, mock_reality, mock_customer_context
    ):
        """Should calculate time difference between snapshots."""
        snapshot1 = snapshot_manager.capture(
            signal=mock_signal,
            reality=mock_reality,
            context=mock_customer_context,
        )
        
        # Sleep equivalent (modify captured_at)
        import time
        time.sleep(0.1)
        
        snapshot2 = snapshot_manager.capture(
            signal=mock_signal,
            reality=mock_reality,
            context=mock_customer_context,
        )
        
        diff = snapshot_manager.compare(snapshot1, snapshot2)
        
        assert diff.time_diff_seconds >= 0


# ============================================================================
# SNAPSHOT RECONSTRUCTION TESTS
# ============================================================================


class TestSnapshotReconstruction:
    """Tests for reconstructing inputs from snapshots."""
    
    def test_reconstruct_signal_returns_dict(
        self, snapshot_manager, sample_snapshot
    ):
        """Should reconstruct signal data as dictionary."""
        signal_data = snapshot_manager.reconstruct_signal(sample_snapshot)
        
        assert isinstance(signal_data, dict)
        assert "signal_id" in signal_data
        assert signal_data["signal_id"] == "sig_test_001"
    
    def test_reconstruct_reality_returns_dict(
        self, snapshot_manager, sample_snapshot
    ):
        """Should reconstruct reality data as dictionary."""
        reality_data = snapshot_manager.reconstruct_reality(sample_snapshot)
        
        assert isinstance(reality_data, dict)
    
    def test_reconstruct_context_returns_dict(
        self, snapshot_manager, sample_snapshot
    ):
        """Should reconstruct context data as dictionary."""
        context_data = snapshot_manager.reconstruct_context(sample_snapshot)
        
        assert isinstance(context_data, dict)
        assert "profile" in context_data
    
    def test_reconstruct_returns_copies(
        self, snapshot_manager, sample_snapshot
    ):
        """Reconstructed data should be copies (modifications don't affect snapshot)."""
        signal1 = snapshot_manager.reconstruct_signal(sample_snapshot)
        signal2 = snapshot_manager.reconstruct_signal(sample_snapshot)
        
        # Modify one
        signal1["modified"] = True
        
        # Other should be unaffected
        assert "modified" not in signal2


# ============================================================================
# SNAPSHOT COMPRESSOR TESTS
# ============================================================================


class TestSnapshotCompressor:
    """Tests for SnapshotCompressor."""
    
    def test_compress_reduces_size(self, sample_snapshot):
        """Compressed snapshot should have fewer fields."""
        compressor = SnapshotCompressor()
        
        compressed = compressor.compress(sample_snapshot)
        
        # Check essential fields preserved
        assert compressed["snapshot_id"] == sample_snapshot.snapshot_id
        assert compressed["signal_hash"] == sample_snapshot.signal_hash
        assert compressed["combined_hash"] == sample_snapshot.combined_hash
        
        # Should have signal_essential instead of full signal_data
        assert "signal_essential" in compressed
        assert "signal_data" not in compressed
    
    def test_compress_preserves_hashes(self, sample_snapshot):
        """Compression should preserve all hashes for verification."""
        compressor = SnapshotCompressor()
        
        compressed = compressor.compress(sample_snapshot)
        
        assert compressed["signal_hash"] == sample_snapshot.signal_hash
        assert compressed["reality_hash"] == sample_snapshot.reality_hash
        assert compressed["customer_context_hash"] == sample_snapshot.customer_context_hash
        assert compressed["combined_hash"] == sample_snapshot.combined_hash
    
    def test_is_compressed_detects_compressed_data(self, sample_snapshot):
        """Should correctly identify compressed vs full snapshots."""
        compressor = SnapshotCompressor()
        
        full_data = sample_snapshot.model_dump()
        compressed = compressor.compress(sample_snapshot)
        
        assert compressor.is_compressed(full_data) is False
        assert compressor.is_compressed(compressed) is True


# ============================================================================
# SNAPSHOT ARCHIVER TESTS
# ============================================================================


class TestSnapshotArchiver:
    """Tests for SnapshotArchiver."""
    
    def test_should_archive_old_snapshots(self, sample_snapshot):
        """Should identify snapshots that should be archived."""
        archiver = SnapshotArchiver(compress_after_days=7)
        
        # Fresh snapshot - should not archive
        assert archiver.should_archive(sample_snapshot) is False
        
        # Simulate old snapshot by modifying captured_at
        old_snapshot = MagicMock(spec=InputSnapshot)
        old_snapshot.captured_at = datetime.utcnow() - timedelta(days=10)
        
        assert archiver.should_archive(old_snapshot) is True
    
    def test_should_delete_expired_snapshots(self):
        """Should identify snapshots past retention period."""
        archiver = SnapshotArchiver(retention_days=365)
        
        # Snapshot within retention - should not delete
        recent_snapshot = MagicMock(spec=InputSnapshot)
        recent_snapshot.captured_at = datetime.utcnow() - timedelta(days=100)
        assert archiver.should_delete(recent_snapshot) is False
        
        # Snapshot past retention - should delete
        old_snapshot = MagicMock(spec=InputSnapshot)
        old_snapshot.captured_at = datetime.utcnow() - timedelta(days=400)
        assert archiver.should_delete(old_snapshot) is True
    
    def test_archive_creates_archived_representation(self, sample_snapshot):
        """Should create archived representation with metadata."""
        archiver = SnapshotArchiver()
        
        archived = archiver.archive(sample_snapshot)
        
        assert archived["type"] == "archived_snapshot"
        assert "archived_at" in archived
        assert archived["original_snapshot_id"] == sample_snapshot.snapshot_id
        assert "compressed_data" in archived
    
    def test_get_retention_policy(self):
        """Should return current retention policy."""
        archiver = SnapshotArchiver(
            retention_days=730,
            compress_after_days=60,
        )
        
        policy = archiver.get_retention_policy()
        
        assert policy["retention_days"] == 730
        assert policy["compress_after_days"] == 60
        assert "policy_version" in policy


# ============================================================================
# FACTORY FUNCTION TESTS
# ============================================================================


class TestSnapshotFactoryFunctions:
    """Tests for snapshot module factory functions."""
    
    def test_create_snapshot_manager_with_defaults(self):
        """Should create manager with default settings."""
        manager = create_snapshot_manager()
        
        assert manager is not None
        assert isinstance(manager, SnapshotManager)
    
    def test_create_snapshot_manager_with_custom_staleness(self):
        """Should accept custom staleness threshold."""
        manager = create_snapshot_manager(max_staleness_seconds=300)
        
        assert manager._max_staleness == 300
    
    def test_create_snapshot_archiver_with_defaults(self):
        """Should create archiver with default settings."""
        archiver = create_snapshot_archiver()
        
        assert archiver is not None
        assert isinstance(archiver, SnapshotArchiver)
    
    def test_create_snapshot_archiver_with_custom_retention(self):
        """Should accept custom retention settings."""
        archiver = create_snapshot_archiver(
            retention_days=1825,  # 5 years
            compress_after_days=90,
        )
        
        assert archiver._retention_days == 1825
        assert archiver._compress_after_days == 90
