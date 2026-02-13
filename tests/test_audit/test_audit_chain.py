"""Tests for cryptographic audit chain integrity.

These tests verify:
1. Hash chain integrity (each record links to previous)
2. Tamper detection (modifications are detected)
3. Input snapshot immutability
4. Audit trail completeness
"""

import pytest
import hashlib
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

from app.audit import (
    AuditService,
    AuditRepository,
    AuditRecord,
    InputSnapshot,
    ProcessingRecord,
    AuditEventType,
    AuditChainVerification,
)
from app.audit.repository import InMemoryAuditRepository


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def in_memory_repo():
    """Create in-memory audit repository for testing."""
    return InMemoryAuditRepository()


@pytest.fixture
def audit_service(in_memory_repo):
    """Create audit service with in-memory repository."""
    service = AuditService(repository=in_memory_repo)
    # Initialize synchronously for tests
    import asyncio
    asyncio.get_event_loop().run_until_complete(service.initialize())
    return service


@pytest.fixture
def sample_signal_data():
    """Sample signal data for testing."""
    return {
        "signal_id": "sig_test_123",
        "title": "Red Sea Disruption Alert",
        "probability": 0.85,
        "category": "disruption",
        "geographic": {
            "primary_chokepoint": "red_sea",
            "affected_ports": ["JNPT", "SGSIN"],
        },
        "temporal": {
            "expected_start": "2026-02-05T00:00:00Z",
            "expected_duration_hours": 168,
        },
        "evidence": [
            {"source": "Polymarket", "confidence": 0.82},
            {"source": "News", "confidence": 0.78},
        ],
    }


@pytest.fixture
def sample_reality_data():
    """Sample reality data for testing."""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "correlation_status": "confirmed",
        "combined_confidence": 0.87,
        "vessels_confirming": 47,
        "rate_movement": 0.35,
        "chokepoint_health": {
            "red_sea": {"status": "degraded", "transit_delay_hours": 168},
        },
    }


@pytest.fixture
def sample_customer_context():
    """Sample customer context for testing."""
    return {
        "profile": {"customer_id": "cust_test_001"},
        "customer_id": "cust_test_001",
        "company_name": "Acme Corp",
        "shipments": [
            {
                "shipment_id": "shp_001",
                "cargo_value_usd": 150000,
                "route_chokepoints": ["red_sea"],
            },
            {
                "shipment_id": "shp_002",
                "cargo_value_usd": 85000,
                "route_chokepoints": ["red_sea", "suez"],
            },
        ],
        "risk_tolerance": "balanced",
        "version": 1,
    }


# ============================================================================
# HASH CHAIN INTEGRITY TESTS
# ============================================================================


class TestHashChainIntegrity:
    """Tests for cryptographic hash chain integrity."""
    
    @pytest.mark.asyncio
    async def test_first_record_has_genesis_previous_hash(self, in_memory_repo):
        """First record in chain should have genesis previous_hash."""
        service = AuditService(repository=in_memory_repo)
        await service.initialize()
        
        # Create first record using DECISION_GENERATED (correct enum value)
        record = await service._record_event(
            event_type=AuditEventType.DECISION_GENERATED,
            entity_type="decision",
            entity_id="dec_001",
            actor_type="system",
            payload={"test": "data"},
        )
        
        # First record's previous_hash should be "genesis"
        stored_records = in_memory_repo._records
        assert len(stored_records) == 1
        assert stored_records[0].previous_hash == "genesis"
        assert stored_records[0].sequence_number == 1
    
    @pytest.mark.asyncio
    async def test_subsequent_records_link_to_previous(self, in_memory_repo):
        """Each record should link to the hash of the previous record."""
        service = AuditService(repository=in_memory_repo)
        await service.initialize()
        
        # Create chain of records
        for i in range(5):
            await service._record_event(
                event_type=AuditEventType.DECISION_GENERATED,
                entity_type="decision",
                entity_id=f"dec_{i:03d}",
                actor_type="system",
                payload={"index": i},
            )
        
        # Get stored records
        records = in_memory_repo._records
        
        # Verify chain links
        for i in range(1, len(records)):
            assert records[i].previous_hash == records[i - 1].record_hash
            assert records[i].sequence_number == records[i - 1].sequence_number + 1
    
    @pytest.mark.asyncio
    async def test_record_hash_is_deterministic(self, in_memory_repo):
        """Same data should produce same hash."""
        service = AuditService(repository=in_memory_repo)
        await service.initialize()
        
        await service._record_event(
            event_type=AuditEventType.DECISION_GENERATED,
            entity_type="decision",
            entity_id="dec_001",
            actor_type="system",
            payload={"test": "data"},
        )
        
        record = in_memory_repo._records[0]
        
        # Recompute hash manually
        recomputed = record.compute_hash()
        assert recomputed == record.record_hash
    
    @pytest.mark.asyncio
    async def test_chain_verification_passes_for_valid_chain(self, in_memory_repo):
        """Verify chain returns success for unmodified chain."""
        service = AuditService(repository=in_memory_repo)
        await service.initialize()
        
        # Create records
        for i in range(10):
            await service._record_event(
                event_type=AuditEventType.DECISION_GENERATED,
                entity_type="decision",
                entity_id=f"dec_{i:03d}",
                actor_type="system",
                payload={"index": i},
            )
        
        # Verify chain - sequence starts from 1, not 0
        result = await service.verify_chain_integrity(1, 10)
        
        assert result.is_valid is True
        assert result.records_checked == 10
    
    @pytest.mark.asyncio
    async def test_chain_verification_detects_broken_link(self, in_memory_repo):
        """Verify chain detects when a link is broken."""
        service = AuditService(repository=in_memory_repo)
        await service.initialize()
        
        # Create records
        for i in range(5):
            await service._record_event(
                event_type=AuditEventType.DECISION_GENERATED,
                entity_type="decision",
                entity_id=f"dec_{i:03d}",
                actor_type="system",
                payload={"index": i},
            )
        
        # Tamper with a record's previous_hash (simulate corruption)
        tampered_record = in_memory_repo._records[2]
        object.__setattr__(tampered_record, 'previous_hash', 'corrupted_hash_' + '0' * 48)
        
        # Verify chain should detect the break - sequence starts from 1
        result = await service.verify_chain_integrity(1, 5)
        
        assert result.is_valid is False
        assert result.error_type == "chain_broken"
    
    @pytest.mark.asyncio
    async def test_chain_verification_detects_tampered_payload(self, in_memory_repo):
        """Verify chain detects when payload is tampered."""
        service = AuditService(repository=in_memory_repo)
        await service.initialize()
        
        # Create records
        for i in range(5):
            await service._record_event(
                event_type=AuditEventType.DECISION_GENERATED,
                entity_type="decision",
                entity_id=f"dec_{i:03d}",
                actor_type="system",
                payload={"index": i},
            )
        
        # Tamper with a record's payload
        tampered_record = in_memory_repo._records[2]
        original_payload = tampered_record.payload
        tampered_payload = {**original_payload, "tampered": True}
        object.__setattr__(tampered_record, 'payload', tampered_payload)
        
        # Verify chain should detect the tampering - sequence starts from 1
        result = await service.verify_chain_integrity(1, 5)
        
        assert result.is_valid is False
        assert result.error_type == "record_tampered"


# ============================================================================
# INPUT SNAPSHOT TESTS
# ============================================================================


class TestInputSnapshot:
    """Tests for input snapshot immutability and hashing."""
    
    def test_snapshot_hash_is_deterministic(
        self, sample_signal_data, sample_reality_data, sample_customer_context
    ):
        """Same inputs should produce same combined hash."""
        # Create mock objects with model_dump method
        signal_mock1 = MagicMock()
        signal_mock1.model_dump = MagicMock(return_value=sample_signal_data)
        
        reality_mock1 = MagicMock()
        reality_mock1.model_dump = MagicMock(return_value=sample_reality_data)
        
        context_mock1 = MagicMock()
        context_mock1.model_dump = MagicMock(return_value=sample_customer_context)
        
        snapshot1 = InputSnapshot.capture(
            signal=signal_mock1,
            reality=reality_mock1,
            context=context_mock1,  # Correct parameter name
        )
        
        # Create second set of mocks
        signal_mock2 = MagicMock()
        signal_mock2.model_dump = MagicMock(return_value=sample_signal_data)
        
        reality_mock2 = MagicMock()
        reality_mock2.model_dump = MagicMock(return_value=sample_reality_data)
        
        context_mock2 = MagicMock()
        context_mock2.model_dump = MagicMock(return_value=sample_customer_context)
        
        snapshot2 = InputSnapshot.capture(
            signal=signal_mock2,
            reality=reality_mock2,
            context=context_mock2,
        )
        
        # Hashes should match for same data
        assert snapshot1.signal_hash == snapshot2.signal_hash
        assert snapshot1.reality_hash == snapshot2.reality_hash
        assert snapshot1.customer_context_hash == snapshot2.customer_context_hash
    
    def test_snapshot_detects_signal_changes(
        self, sample_signal_data, sample_reality_data, sample_customer_context
    ):
        """Different signal data should produce different hash."""
        signal_mock1 = MagicMock()
        signal_mock1.model_dump = MagicMock(return_value=sample_signal_data)
        
        reality_mock = MagicMock()
        reality_mock.model_dump = MagicMock(return_value=sample_reality_data)
        
        context_mock = MagicMock()
        context_mock.model_dump = MagicMock(return_value=sample_customer_context)
        
        snapshot1 = InputSnapshot.capture(
            signal=signal_mock1,
            reality=reality_mock,
            context=context_mock,
        )
        
        # Modify signal data
        modified_signal = {**sample_signal_data, "probability": 0.95}
        signal_mock2 = MagicMock()
        signal_mock2.model_dump = MagicMock(return_value=modified_signal)
        
        snapshot2 = InputSnapshot.capture(
            signal=signal_mock2,
            reality=reality_mock,
            context=context_mock,
        )
        
        assert snapshot1.signal_hash != snapshot2.signal_hash
        assert snapshot1.combined_hash != snapshot2.combined_hash
    
    def test_snapshot_captures_staleness(
        self, sample_signal_data, sample_customer_context
    ):
        """Snapshot should capture reality data staleness."""
        signal_mock = MagicMock()
        signal_mock.model_dump = MagicMock(return_value=sample_signal_data)
        
        # Reality data from 5 minutes ago
        old_timestamp = datetime.utcnow() - timedelta(minutes=5)
        reality_data = {
            "timestamp": old_timestamp.isoformat(),
            "correlation_status": "confirmed",
        }
        reality_mock = MagicMock()
        reality_mock.model_dump = MagicMock(return_value=reality_data)
        
        context_mock = MagicMock()
        context_mock.model_dump = MagicMock(return_value=sample_customer_context)
        
        snapshot = InputSnapshot.capture(
            signal=signal_mock,
            reality=reality_mock,
            context=context_mock,
        )
        
        # Staleness should be approximately 300 seconds
        assert snapshot.reality_staleness_seconds >= 290
        assert snapshot.reality_staleness_seconds <= 320
    
    def test_snapshot_is_frozen(
        self, sample_signal_data, sample_reality_data, sample_customer_context
    ):
        """Snapshot should be immutable after creation."""
        signal_mock = MagicMock()
        signal_mock.model_dump = MagicMock(return_value=sample_signal_data)
        
        reality_mock = MagicMock()
        reality_mock.model_dump = MagicMock(return_value=sample_reality_data)
        
        context_mock = MagicMock()
        context_mock.model_dump = MagicMock(return_value=sample_customer_context)
        
        snapshot = InputSnapshot.capture(
            signal=signal_mock,
            reality=reality_mock,
            context=context_mock,
        )
        
        # Attempting to modify should raise error (Pydantic frozen model)
        with pytest.raises(Exception):  # ValidationError or similar
            snapshot.signal_hash = "modified"


# ============================================================================
# PROCESSING RECORD TESTS
# ============================================================================


class TestProcessingRecord:
    """Tests for processing record creation."""
    
    def test_processing_record_captures_version(self):
        """Processing record should capture model and config versions."""
        record = ProcessingRecord(
            model_version="v2.0.0",
            config_version="config-v1.0.0",
            computation_time_ms=150,
        )
        
        assert record.model_version == "v2.0.0"
        assert record.config_version == "config-v1.0.0"
    
    def test_processing_record_captures_timing(self):
        """Processing record should capture computation time."""
        record = ProcessingRecord(
            model_version="v2.0.0",
            config_version="config-v1.0.0",
            computation_time_ms=150,
            memory_used_mb=45.5,
        )
        
        assert record.computation_time_ms == 150
        assert record.memory_used_mb == 45.5
    
    def test_processing_record_captures_warnings(self):
        """Processing record should capture any warnings."""
        record = ProcessingRecord(
            model_version="v2.0.0",
            config_version="config-v1.0.0",
            computation_time_ms=150,
            warnings=["Rate data is 2 hours stale", "Missing carrier schedule"],
            stale_data_sources=["rates_api"],
            missing_data_sources=["carrier_api"],
        )
        
        assert len(record.warnings) == 2
        assert "rates_api" in record.stale_data_sources
        assert "carrier_api" in record.missing_data_sources
    
    def test_processing_record_has_unique_id(self):
        """Each processing record should have unique ID."""
        record1 = ProcessingRecord(
            model_version="v2.0.0",
            config_version="config-v1.0.0",
            computation_time_ms=150,
        )
        record2 = ProcessingRecord(
            model_version="v2.0.0",
            config_version="config-v1.0.0",
            computation_time_ms=150,
        )
        
        assert record1.record_id != record2.record_id


# ============================================================================
# AUDIT TRAIL COMPLETENESS TESTS
# ============================================================================


class TestAuditTrailCompleteness:
    """Tests for complete audit trail retrieval."""
    
    @pytest.mark.asyncio
    async def test_decision_audit_trail_includes_all_events(self, in_memory_repo):
        """Decision audit trail should include all related events."""
        service = AuditService(repository=in_memory_repo)
        await service.initialize()
        
        decision_id = "dec_test_001"
        customer_id = "cust_001"
        signal_id = "sig_001"
        
        # Create input snapshot
        snapshot = InputSnapshot(
            snapshot_id="snap_001",
            signal_id=signal_id,
            signal_data={"test": "signal"},
            signal_hash="hash1",
            reality_data={"test": "reality"},
            reality_hash="hash2",
            reality_staleness_seconds=60,
            customer_id=customer_id,
            customer_context_data={"test": "context"},
            customer_context_hash="hash3",
            customer_context_version=1,
            combined_hash="combined_hash",
            captured_at=datetime.utcnow(),
        )
        await in_memory_repo.store_snapshot(snapshot)
        
        # Create processing record
        processing = ProcessingRecord(
            record_id="proc_001",
            model_version="v2.0.0",
            config_version="config-v1.0.0",
            computation_time_ms=150,
        )
        
        # Create mock decision object
        mock_decision = MagicMock()
        mock_decision.model_dump = MagicMock(return_value={
            "decision_id": decision_id,
            "customer_id": customer_id,
            "signal_id": signal_id,
            "q5_action": {"action_type": "reroute"},
            "q6_confidence": {"score": 0.85},
            "q3_severity": {"total_exposure_usd": 50000},
        })
        
        # Record decision using actual service method signature
        await service.record_decision(
            decision=mock_decision,
            snapshot=snapshot,
            processing=processing,
        )
        
        # Record delivery
        await service.record_delivery(
            decision_id=decision_id,
            channel="whatsapp",
            status="delivered",
            recipient="+1234567890",
        )
        
        # Record feedback (using correct signature)
        await service.record_feedback(
            decision_id=decision_id,
            user_id="user_001",
            feedback_type="helpful",
            rating=5,
            comment="This was accurate",
        )
        
        # Get complete audit trail
        trail = await service.get_decision_audit_trail(decision_id)
        
        # Verify all components are present
        assert trail.decision_id == decision_id
        assert len(trail.audit_events) >= 3  # decision, delivery, feedback
        
        event_types = [e.event_type.value for e in trail.audit_events]
        assert AuditEventType.DECISION_GENERATED.value in event_types
        assert AuditEventType.DECISION_DELIVERED.value in event_types
        assert AuditEventType.HUMAN_FEEDBACK.value in event_types
    
    @pytest.mark.asyncio
    async def test_audit_trail_includes_overrides(self, in_memory_repo):
        """Audit trail should include human overrides."""
        service = AuditService(repository=in_memory_repo)
        await service.initialize()
        
        decision_id = "dec_test_002"
        
        # Create snapshot and processing for record_decision
        snapshot = InputSnapshot(
            snapshot_id="snap_002",
            signal_id="sig_001",
            signal_data={"test": "signal"},
            signal_hash="hash1",
            reality_data={"test": "reality"},
            reality_hash="hash2",
            reality_staleness_seconds=60,
            customer_id="cust_001",
            customer_context_data={"test": "context"},
            customer_context_hash="hash3",
            customer_context_version=1,
            combined_hash="combined_hash",
            captured_at=datetime.utcnow(),
        )
        processing = ProcessingRecord(
            model_version="v2.0.0",
            config_version="config-v1.0.0",
            computation_time_ms=150,
        )
        
        mock_decision = MagicMock()
        mock_decision.model_dump = MagicMock(return_value={
            "decision_id": decision_id,
            "q5_action": {"action_type": "reroute"},
            "q6_confidence": {"score": 0.85},
            "q3_severity": {"total_exposure_usd": 50000},
        })
        
        # Record decision
        await service.record_decision(
            decision=mock_decision,
            snapshot=snapshot,
            processing=processing,
        )
        
        # Record override
        override_id = await service.record_human_override(
            decision_id=decision_id,
            user_id="ops_manager",
            original_action="reroute",
            new_action="delay",
            reason="Customer requested delay due to storage constraints",
        )
        
        # Get trail
        trail = await service.get_decision_audit_trail(decision_id)
        
        event_types = [e.event_type.value for e in trail.audit_events]
        assert AuditEventType.HUMAN_OVERRIDE.value in event_types
        
        # Find override event
        override_events = [
            e for e in trail.audit_events
            if e.event_type == AuditEventType.HUMAN_OVERRIDE
        ]
        assert len(override_events) == 1
        assert override_events[0].payload["original_action"] == "reroute"
        assert override_events[0].payload["new_action"] == "delay"
    
    @pytest.mark.asyncio
    async def test_audit_trail_includes_outcome(self, in_memory_repo):
        """Audit trail should include recorded outcomes."""
        service = AuditService(repository=in_memory_repo)
        await service.initialize()
        
        decision_id = "dec_test_003"
        
        # Create snapshot and processing for record_decision
        snapshot = InputSnapshot(
            snapshot_id="snap_003",
            signal_id="sig_001",
            signal_data={"test": "signal"},
            signal_hash="hash1",
            reality_data={"test": "reality"},
            reality_hash="hash2",
            reality_staleness_seconds=60,
            customer_id="cust_001",
            customer_context_data={"test": "context"},
            customer_context_hash="hash3",
            customer_context_version=1,
            combined_hash="combined_hash",
            captured_at=datetime.utcnow(),
        )
        processing = ProcessingRecord(
            model_version="v2.0.0",
            config_version="config-v1.0.0",
            computation_time_ms=150,
        )
        
        mock_decision = MagicMock()
        mock_decision.model_dump = MagicMock(return_value={
            "decision_id": decision_id,
            "q5_action": {"action_type": "reroute"},
            "q6_confidence": {"score": 0.85},
            "q3_severity": {"total_exposure_usd": 50000},
        })
        
        # Record decision
        await service.record_decision(
            decision=mock_decision,
            snapshot=snapshot,
            processing=processing,
        )
        
        # Record outcome (using correct signature)
        await service.record_outcome(
            decision_id=decision_id,
            actual_outcome={
                "event_occurred": True,
                "actual_impact_usd": 12500.0,
                "actual_delay_days": 8,
            },
            accuracy_assessment="accurate",
            prediction_result="correct",
        )
        
        # Get trail
        trail = await service.get_decision_audit_trail(decision_id)
        
        event_types = [e.event_type.value for e in trail.audit_events]
        assert AuditEventType.DECISION_OUTCOME_RECORDED.value in event_types


# ============================================================================
# TAMPER DETECTION TESTS
# ============================================================================


class TestTamperDetection:
    """Tests for tamper detection capabilities."""
    
    @pytest.mark.asyncio
    async def test_detects_payload_modification(self, in_memory_repo):
        """Should detect when payload is modified after recording."""
        service = AuditService(repository=in_memory_repo)
        await service.initialize()
        
        # Record event
        await service._record_event(
            event_type=AuditEventType.DECISION_GENERATED,
            entity_type="decision",
            entity_id="dec_001",
            actor_type="system",
            payload={"original": "data"},
        )
        
        record = in_memory_repo._records[0]
        
        # Verify original is valid
        original_hash = record.record_hash
        recomputed = record.compute_hash()
        assert original_hash == recomputed
        
        # Tamper with payload
        tampered_payload = {**record.payload, "tampered": True}
        object.__setattr__(record, 'payload', tampered_payload)
        
        # Recomputed hash should differ
        tampered_hash = record.compute_hash()
        assert tampered_hash != original_hash
    
    @pytest.mark.asyncio
    async def test_detects_sequence_manipulation(self, in_memory_repo):
        """Should detect when sequence number is manipulated."""
        service = AuditService(repository=in_memory_repo)
        await service.initialize()
        
        # Create chain
        for i in range(5):
            await service._record_event(
                event_type=AuditEventType.DECISION_GENERATED,
                entity_type="decision",
                entity_id=f"dec_{i:03d}",
                actor_type="system",
                payload={"index": i},
            )
        
        # Manipulate sequence number
        record = in_memory_repo._records[2]
        original_hash = record.record_hash
        object.__setattr__(record, 'sequence_number', 99)
        
        # Hash should no longer match
        recomputed = record.compute_hash()
        assert recomputed != original_hash
    
    @pytest.mark.asyncio
    async def test_detects_timestamp_manipulation(self, in_memory_repo):
        """Should detect when timestamp is manipulated."""
        service = AuditService(repository=in_memory_repo)
        await service.initialize()
        
        await service._record_event(
            event_type=AuditEventType.DECISION_GENERATED,
            entity_type="decision",
            entity_id="dec_001",
            actor_type="system",
            payload={"test": "data"},
        )
        
        record = in_memory_repo._records[0]
        
        # Manipulate timestamp
        original_hash = record.record_hash
        new_timestamp = datetime.utcnow() - timedelta(days=1)
        object.__setattr__(record, 'timestamp', new_timestamp)
        
        # Hash should no longer match
        recomputed = record.compute_hash()
        assert recomputed != original_hash


# ============================================================================
# CONCURRENT ACCESS TESTS
# ============================================================================


class TestConcurrentAccess:
    """Tests for thread-safe concurrent access."""
    
    @pytest.mark.asyncio
    async def test_concurrent_record_creation_maintains_sequence(self, in_memory_repo):
        """Concurrent record creation should maintain proper sequence."""
        import asyncio
        
        service = AuditService(repository=in_memory_repo)
        await service.initialize()
        
        # Create many records concurrently
        async def create_record(i: int):
            return await service._record_event(
                event_type=AuditEventType.DECISION_GENERATED,
                entity_type="decision",
                entity_id=f"dec_{i:03d}",
                actor_type="system",
                payload={"index": i},
            )
        
        # Create 50 records concurrently
        tasks = [create_record(i) for i in range(50)]
        await asyncio.gather(*tasks)
        
        # Verify sequence numbers are unique and sequential
        records = in_memory_repo._records
        sequence_numbers = sorted([r.sequence_number for r in records])
        expected = list(range(1, 51))
        assert sequence_numbers == expected
        
        # Verify chain integrity - sequence starts from 1
        result = await service.verify_chain_integrity(1, 50)
        assert result.is_valid is True
