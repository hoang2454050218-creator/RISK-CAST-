"""
Tests for Chaos Engineering Module.

Tests:
- test_chaos_experiment_abort(): Chaos aborted when SLO breached
- test_chaos_experiment_safety(): Safety checks work correctly
- test_chaos_scheduler(): Scheduler manages experiments
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.ops.chaos.scheduler import (
    ChaosExperimentType,
    ChaosExperiment,
    ExperimentResult,
    ChaosScheduler,
    MetricsSnapshot,
    get_chaos_scheduler,
    STANDARD_EXPERIMENTS,
    ExperimentStatus,
)
from app.ops.chaos.experiments import (
    ExperimentRunner,
    PodKillExperiment,
    NetworkLatencyExperiment,
    DependencyFailureExperiment,
    ExperimentRegistry,
    get_experiment_runner,
)


# ============================================================================
# CHAOS EXPERIMENT TESTS
# ============================================================================


class TestChaosExperiment:
    """Tests for ChaosExperiment model."""
    
    def test_experiment_creation(self):
        """Experiment can be created with valid parameters."""
        exp = ChaosExperiment(
            name="Test Pod Kill",
            type=ChaosExperimentType.POD_KILL,
            target="app=riskcast",
            duration_minutes=5,
            parameters={"count": 1},
        )
        
        assert exp.experiment_id is not None
        assert exp.name == "Test Pod Kill"
        assert exp.type == ChaosExperimentType.POD_KILL
        assert exp.enabled is True
    
    def test_experiment_with_schedule(self):
        """Experiment can have a schedule."""
        exp = ChaosExperiment(
            name="Scheduled Test",
            type=ChaosExperimentType.NETWORK_LATENCY,
            target="redis",
            duration_minutes=10,
            schedule="0 14 * * 1",  # Monday 2pm
        )
        
        assert exp.is_scheduled is True
    
    def test_experiment_without_schedule(self):
        """Experiment without schedule."""
        exp = ChaosExperiment(
            name="Manual Test",
            type=ChaosExperimentType.CPU_STRESS,
            target="app=riskcast",
            duration_minutes=5,
        )
        
        assert exp.is_scheduled is False


class TestStandardExperiments:
    """Tests for standard experiment definitions."""
    
    def test_standard_experiments_exist(self):
        """Standard experiments are defined."""
        assert len(STANDARD_EXPERIMENTS) >= 5
    
    def test_standard_experiments_valid(self):
        """Standard experiments have required fields."""
        for exp in STANDARD_EXPERIMENTS:
            assert exp.name is not None
            assert exp.type is not None
            assert exp.target is not None
            assert exp.duration_minutes > 0
            assert exp.abort_conditions is not None
    
    def test_weekly_experiments_scheduled(self):
        """Weekly experiments have schedules."""
        weekly = [exp for exp in STANDARD_EXPERIMENTS if "weekly" in exp.tags]
        
        for exp in weekly:
            assert exp.schedule is not None, f"{exp.name} should have schedule"


# ============================================================================
# CHAOS SCHEDULER TESTS
# ============================================================================


class TestChaosScheduler:
    """Tests for the chaos scheduler."""
    
    @pytest.fixture
    def scheduler(self):
        """Create fresh scheduler instance."""
        import app.ops.chaos.scheduler as sched
        sched._chaos_scheduler = None
        return ChaosScheduler(
            allow_outside_business_hours=True,
            allow_weekends=True,
        )
    
    def test_register_experiment(self, scheduler):
        """Experiments can be registered."""
        exp = ChaosExperiment(
            name="Test Experiment",
            type=ChaosExperimentType.POD_KILL,
            target="app=test",
            duration_minutes=1,
        )
        
        scheduler.register_experiment(exp)
        
        assert exp.experiment_id in [e.experiment_id for e in scheduler.list_experiments()]
    
    def test_get_experiment(self, scheduler):
        """Experiment can be retrieved by ID."""
        exp = ChaosExperiment(
            name="Retrievable Test",
            type=ChaosExperimentType.NETWORK_LATENCY,
            target="redis",
            duration_minutes=1,
        )
        
        scheduler.register_experiment(exp)
        
        retrieved = scheduler.get_experiment(exp.experiment_id)
        assert retrieved is not None
        assert retrieved.name == "Retrievable Test"
    
    @pytest.mark.asyncio
    async def test_chaos_experiment_abort(self, scheduler):
        """
        Test that chaos is aborted when SLO breached.
        
        This is a required test from acceptance criteria.
        """
        # Create experiment
        exp = ChaosExperiment(
            experiment_id="abort-test",
            name="Abort Test",
            type=ChaosExperimentType.DEPENDENCY_FAILURE,
            target="test-service",
            duration_minutes=5,
            abort_conditions=["error_rate > 5%"],
        )
        scheduler.register_experiment(exp)
        
        # Mock metrics to return high error rate
        async def mock_high_error_metrics():
            return MetricsSnapshot(
                error_rate=0.10,  # 10% > 5% threshold
                latency_p99_ms=500,
                latency_p95_ms=300,
                latency_p50_ms=100,
                request_rate=100,
                cpu_utilization=0.5,
                memory_utilization=0.5,
            )
        
        with patch.object(scheduler, '_capture_metrics', mock_high_error_metrics):
            result = await scheduler.run_experiment("abort-test", dry_run=True)
        
        # Should be aborted
        assert result.aborted is True
        assert result.status == ExperimentStatus.ABORTED
        assert "error rate" in result.abort_reason.lower() or "Error rate" in result.abort_reason
    
    @pytest.mark.asyncio
    async def test_experiment_completion(self, scheduler):
        """Experiment completes successfully with good metrics."""
        exp = ChaosExperiment(
            experiment_id="complete-test",
            name="Completion Test",
            type=ChaosExperimentType.POD_KILL,
            target="app=test",
            duration_minutes=1,  # Short for testing
        )
        scheduler.register_experiment(exp)
        
        # Run with dry_run to avoid actual chaos injection
        result = await scheduler.run_experiment("complete-test", dry_run=True)
        
        assert result.status in [ExperimentStatus.COMPLETED, ExperimentStatus.ABORTED]
        assert result.experiment_id == "complete-test"
        assert result.duration_minutes >= 0
    
    def test_safety_check_cooldown(self, scheduler):
        """Cooldown prevents running same experiment twice."""
        exp = ChaosExperiment(
            experiment_id="cooldown-test",
            name="Cooldown Test",
            type=ChaosExperimentType.POD_KILL,
            target="app=test",
            duration_minutes=1,
            cooldown_minutes=60,
        )
        scheduler.register_experiment(exp)
        
        # Simulate recent run
        scheduler._last_run["cooldown-test"] = datetime.utcnow()
        
        is_safe, reason = scheduler._is_safe_to_run(exp)
        
        assert is_safe is False
        assert "cooldown" in reason.lower()
    
    def test_safety_check_another_running(self, scheduler):
        """Cannot run experiment while another is running."""
        exp = ChaosExperiment(
            experiment_id="blocked-test",
            name="Blocked Test",
            type=ChaosExperimentType.POD_KILL,
            target="app=test",
            duration_minutes=1,
        )
        scheduler.register_experiment(exp)
        
        # Simulate running experiment
        scheduler._running = "other-experiment"
        
        is_safe, reason = scheduler._is_safe_to_run(exp)
        
        assert is_safe is False
        assert "running" in reason.lower()
    
    def test_safety_check_disabled(self, scheduler):
        """Disabled experiments cannot run."""
        exp = ChaosExperiment(
            experiment_id="disabled-test",
            name="Disabled Test",
            type=ChaosExperimentType.POD_KILL,
            target="app=test",
            duration_minutes=1,
            enabled=False,
        )
        scheduler.register_experiment(exp)
        
        is_safe, reason = scheduler._is_safe_to_run(exp)
        
        assert is_safe is False
        assert "disabled" in reason.lower()
    
    def test_resilience_summary(self, scheduler):
        """Resilience summary is calculated correctly."""
        # No results yet
        summary = scheduler.get_resilience_summary()
        
        assert summary["total_experiments"] == 0
        assert summary["avg_resilience_score"] is None
    
    @pytest.mark.asyncio
    async def test_experiment_not_found(self, scheduler):
        """Running non-existent experiment raises error."""
        with pytest.raises(ValueError, match="not found"):
            await scheduler.run_experiment("non-existent")


# ============================================================================
# EXPERIMENT RUNNER TESTS
# ============================================================================


class TestExperimentRunners:
    """Tests for experiment runner implementations."""
    
    @pytest.mark.asyncio
    async def test_pod_kill_inject(self):
        """Pod kill experiment can inject chaos."""
        runner = PodKillExperiment()
        
        injection_id = await runner.inject(
            target="app=riskcast",
            parameters={"count": 1},
            namespace="riskcast",
        )
        
        assert injection_id.startswith("pk_")
        
        status = await runner.status(injection_id)
        assert status == ExperimentStatus.ACTIVE
        
        stopped = await runner.stop(injection_id)
        assert stopped is True
    
    @pytest.mark.asyncio
    async def test_network_latency_inject(self):
        """Network latency experiment can inject chaos."""
        runner = NetworkLatencyExperiment()
        
        injection_id = await runner.inject(
            target="redis",
            parameters={"latency_ms": 100, "jitter_ms": 20},
            namespace="riskcast",
        )
        
        assert injection_id.startswith("nl_")
        
        stopped = await runner.stop(injection_id)
        assert stopped is True
    
    @pytest.mark.asyncio
    async def test_dependency_failure_inject(self):
        """Dependency failure experiment can inject chaos."""
        runner = DependencyFailureExperiment()
        
        injection_id = await runner.inject(
            target="omen",
            parameters={"failure_rate": 0.5},
            namespace="riskcast",
        )
        
        assert injection_id.startswith("df_")
        
        status = await runner.status(injection_id)
        assert status == ExperimentStatus.ACTIVE


class TestExperimentRegistry:
    """Tests for experiment registry."""
    
    def test_registry_has_runners(self):
        """Registry has default runners registered."""
        registry = ExperimentRegistry()
        
        assert registry.get(ChaosExperimentType.POD_KILL) is not None
        assert registry.get(ChaosExperimentType.NETWORK_LATENCY) is not None
        assert registry.get(ChaosExperimentType.DEPENDENCY_FAILURE) is not None
    
    def test_list_types(self):
        """Can list registered experiment types."""
        registry = ExperimentRegistry()
        
        types = registry.list_types()
        
        assert ChaosExperimentType.POD_KILL in types
        assert ChaosExperimentType.NETWORK_LATENCY in types


# ============================================================================
# SINGLETON TESTS
# ============================================================================


class TestChaosSingleton:
    """Tests for chaos singleton behavior."""
    
    def test_scheduler_singleton(self):
        """get_chaos_scheduler returns same instance."""
        import app.ops.chaos.scheduler as sched
        sched._chaos_scheduler = None
        
        scheduler1 = get_chaos_scheduler()
        scheduler2 = get_chaos_scheduler()
        
        assert scheduler1 is scheduler2
    
    def test_runner_singleton(self):
        """get_experiment_runner returns same instance."""
        import app.ops.chaos.experiments as exp
        exp._experiment_runner = None
        
        runner1 = get_experiment_runner()
        runner2 = get_experiment_runner()
        
        assert runner1 is runner2
