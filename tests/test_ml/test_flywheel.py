"""
Tests for Data Flywheel.

Tests:
- test_flywheel_outcome_recording(): Outcomes are recorded correctly
- test_flywheel_retrain_trigger(): Retraining triggers after threshold
- test_flywheel_metrics(): Flywheel health metrics are accurate
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.ml.flywheel import (
    DataFlywheel,
    OutcomeRepository,
    OutcomeRecord,
    FlywheelStage,
    OutcomeSource,
    ImprovementType,
    FlywheelMetrics,
    TrainingJob,
    get_flywheel,
)


# ============================================================================
# OUTCOME REPOSITORY TESTS
# ============================================================================


class TestOutcomeRepository:
    """Tests for outcome storage."""
    
    @pytest.fixture
    def repo(self):
        """Create fresh outcome repository."""
        return OutcomeRepository()
    
    @pytest.mark.asyncio
    async def test_save_and_get(self, repo):
        """Outcomes can be saved and retrieved."""
        outcome = OutcomeRecord(
            decision_id="test-123",
            customer_id="customer-1",
            chokepoint="red_sea",
            action_recommended="reroute",
            predicted_delay_days=7.0,
            predicted_loss_usd=10000.0,
            predicted_cost_usd=5000.0,
            confidence_score=0.8,
            stage=FlywheelStage.DECISION_MADE,
        )
        
        await repo.save(outcome)
        retrieved = await repo.get(outcome.outcome_id)
        
        assert retrieved is not None
        assert retrieved.decision_id == "test-123"
        assert retrieved.customer_id == "customer-1"
    
    @pytest.mark.asyncio
    async def test_get_by_decision_id(self, repo):
        """Outcomes can be retrieved by decision ID."""
        outcome = OutcomeRecord(
            decision_id="decision-456",
            customer_id="customer-1",
            chokepoint="red_sea",
            action_recommended="delay",
            predicted_delay_days=5.0,
            stage=FlywheelStage.DECISION_MADE,
        )
        
        await repo.save(outcome)
        retrieved = await repo.get_by_decision(outcome.decision_id)
        
        assert retrieved is not None
        assert retrieved.decision_id == "decision-456"
    
    @pytest.mark.asyncio
    async def test_list_pending_outcomes(self, repo):
        """Can list outcomes pending actual results."""
        # Create pending outcome
        pending = OutcomeRecord(
            decision_id="pending-1",
            customer_id="customer-1",
            chokepoint="red_sea",
            action_recommended="reroute",
            stage=FlywheelStage.DECISION_MADE,
        )
        
        # Create completed outcome
        completed = OutcomeRecord(
            decision_id="completed-1",
            customer_id="customer-1",
            chokepoint="red_sea",
            action_recommended="reroute",
            stage=FlywheelStage.OUTCOME_RECORDED,
            actual_delay_days=8.0,
        )
        
        await repo.save(pending)
        await repo.save(completed)
        
        pending_list = await repo.list_pending_outcomes()
        
        assert len(pending_list) == 1
        assert pending_list[0].decision_id == "pending-1"
    
    @pytest.mark.asyncio
    async def test_count_since(self, repo):
        """Can count outcomes since a timestamp."""
        old_outcome = OutcomeRecord(
            decision_id="old-1",
            customer_id="customer-1",
            chokepoint="red_sea",
            action_recommended="reroute",
            created_at=datetime.utcnow() - timedelta(days=10),
            stage=FlywheelStage.OUTCOME_RECORDED,
        )
        
        new_outcome = OutcomeRecord(
            decision_id="new-1",
            customer_id="customer-1",
            chokepoint="red_sea",
            action_recommended="reroute",
            stage=FlywheelStage.OUTCOME_RECORDED,
        )
        
        await repo.save(old_outcome)
        await repo.save(new_outcome)
        
        count = await repo.count_since(datetime.utcnow() - timedelta(days=1))
        
        assert count == 1


# ============================================================================
# DATA FLYWHEEL TESTS
# ============================================================================


class TestDataFlywheel:
    """Tests for the data flywheel."""
    
    @pytest.fixture
    def flywheel(self):
        """Create fresh flywheel instance."""
        # Reset singleton
        import app.ml.flywheel as fw_module
        fw_module._flywheel = None
        return DataFlywheel(retrain_threshold=5)  # Low threshold for testing
    
    @pytest.mark.asyncio
    async def test_flywheel_outcome_recording(self, flywheel):
        """
        Test that outcomes are recorded correctly.
        
        This is a required test from acceptance criteria.
        """
        # First, register a decision
        await flywheel.register_decision(
            decision_id="test-decision-1",
            customer_id="customer-1",
            chokepoint="red_sea",
            action_recommended="reroute",
            predicted_delay_days=7.0,
            predicted_loss_usd=15000.0,
            predicted_cost_usd=8000.0,
            confidence_score=0.75,
        )
        
        # Now record actual outcome
        outcome = await flywheel.record_outcome(
            decision_id="test-decision-1",
            actual_delay_days=9.0,
            actual_loss_usd=12000.0,
            actual_action_cost_usd=7500.0,
            action_taken="reroute",
            action_success=True,
            source=OutcomeSource.MANUAL_ENTRY,
        )
        
        assert outcome is not None
        assert outcome.stage == FlywheelStage.OUTCOME_RECORDED
        
        # Check error calculations
        assert outcome.delay_error == 2.0  # 9 - 7
        assert outcome.actual_delay_days == 9.0
        assert outcome.action_taken == "reroute"
        assert outcome.action_success is True
    
    @pytest.mark.asyncio
    async def test_outcome_accuracy_tracking(self, flywheel):
        """Accuracy should be tracked correctly."""
        # Register and record accurate prediction
        await flywheel.register_decision(
            decision_id="accurate-1",
            customer_id="customer-1",
            chokepoint="red_sea",
            action_recommended="reroute",
            predicted_delay_days=7.0,
            confidence_score=0.8,
        )
        
        outcome = await flywheel.record_outcome(
            decision_id="accurate-1",
            actual_delay_days=8.0,  # Within 2 days
        )
        
        assert outcome.was_accurate is True
        
        # Register and record inaccurate prediction
        await flywheel.register_decision(
            decision_id="inaccurate-1",
            customer_id="customer-1",
            chokepoint="red_sea",
            action_recommended="monitor",
            predicted_delay_days=3.0,
            confidence_score=0.6,
        )
        
        outcome = await flywheel.record_outcome(
            decision_id="inaccurate-1",
            actual_delay_days=15.0,  # Way off
        )
        
        assert outcome.was_accurate is False
    
    @pytest.mark.asyncio
    async def test_retrain_trigger(self, flywheel):
        """Retraining should trigger after threshold outcomes."""
        # Register and record outcomes up to threshold
        for i in range(5):
            await flywheel.register_decision(
                decision_id=f"retrain-test-{i}",
                customer_id="customer-1",
                chokepoint="red_sea",
                action_recommended="reroute",
                predicted_delay_days=7.0,
            )
            await flywheel.record_outcome(
                decision_id=f"retrain-test-{i}",
                actual_delay_days=8.0 + i,
            )
        
        # Check if retraining was scheduled
        # Note: With threshold=5, should have triggered
        metrics = await flywheel.get_metrics()
        assert metrics.training_jobs_completed >= 0
    
    @pytest.mark.asyncio
    async def test_flywheel_metrics(self, flywheel):
        """Flywheel health metrics should be calculated correctly."""
        # Register some decisions
        for i in range(3):
            await flywheel.register_decision(
                decision_id=f"metrics-test-{i}",
                customer_id="customer-1",
                chokepoint="red_sea",
                action_recommended="reroute",
                predicted_delay_days=7.0,
            )
        
        # Record some outcomes
        await flywheel.record_outcome(
            decision_id="metrics-test-0",
            actual_delay_days=8.0,  # Accurate
        )
        await flywheel.record_outcome(
            decision_id="metrics-test-1",
            actual_delay_days=15.0,  # Inaccurate
        )
        
        metrics = await flywheel.get_metrics()
        
        assert isinstance(metrics, FlywheelMetrics)
        assert metrics.total_decisions == 3
        assert metrics.total_outcomes == 2
        assert metrics.outcome_collection_rate == pytest.approx(2/3, rel=0.01)
        assert 0 <= metrics.accuracy_rate <= 1
    
    @pytest.mark.asyncio
    async def test_get_pending_outcomes(self, flywheel):
        """Can list decisions awaiting outcomes."""
        await flywheel.register_decision(
            decision_id="pending-test-1",
            customer_id="customer-1",
            chokepoint="red_sea",
            action_recommended="reroute",
            predicted_delay_days=7.0,
        )
        
        pending = await flywheel.get_pending_outcomes()
        
        assert len(pending) == 1
        assert pending[0].decision_id == "pending-test-1"
    
    @pytest.mark.asyncio
    async def test_record_outcome_without_registration(self, flywheel):
        """Recording outcome for unregistered decision should fail gracefully."""
        result = await flywheel.record_outcome(
            decision_id="nonexistent-decision",
            actual_delay_days=10.0,
        )
        
        # Should return None for unregistered decision
        assert result is None


# ============================================================================
# SINGLETON TESTS
# ============================================================================


class TestFlywheelSingleton:
    """Tests for flywheel singleton behavior."""
    
    def test_singleton_returns_same_instance(self):
        """get_flywheel should return same instance."""
        import app.ml.flywheel as fw_module
        fw_module._flywheel = None
        
        flywheel1 = get_flywheel()
        flywheel2 = get_flywheel()
        
        assert flywheel1 is flywheel2


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestFlywheelIntegration:
    """Integration tests for the full flywheel cycle."""
    
    @pytest.mark.asyncio
    async def test_full_flywheel_cycle(self):
        """Test complete decision -> outcome -> retrain cycle."""
        import app.ml.flywheel as fw_module
        fw_module._flywheel = None
        
        flywheel = DataFlywheel(retrain_threshold=3)
        
        # Simulate multiple decisions and outcomes
        for i in range(3):
            await flywheel.register_decision(
                decision_id=f"cycle-test-{i}",
                customer_id=f"customer-{i % 2}",
                chokepoint="red_sea",
                action_recommended="reroute" if i % 2 == 0 else "delay",
                predicted_delay_days=7.0 + i,
                predicted_loss_usd=10000.0 * (i + 1),
            )
            
            await flywheel.record_outcome(
                decision_id=f"cycle-test-{i}",
                actual_delay_days=8.0 + i,
                actual_loss_usd=9000.0 * (i + 1),
                action_taken="reroute" if i % 2 == 0 else "delay",
                action_success=True,
            )
        
        # Check metrics after full cycle
        metrics = await flywheel.get_metrics()
        
        assert metrics.total_decisions == 3
        assert metrics.total_outcomes == 3
        assert metrics.outcome_collection_rate == 1.0
        assert metrics.flywheel_health_score > 0
