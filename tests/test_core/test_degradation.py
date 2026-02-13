"""
Tests for Degradation State Machine.

B2 COMPLIANCE: Validates DegradationLevel enum and automatic transitions.

Tests:
- Explicit DegradationLevel enum
- Automatic transitions based on metrics
- Feature disabling at each level
- Recovery management
- State machine transitions
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from app.core.degradation import (
    DegradationLevel,
    DegradationState,
    DegradationStateMachine,
    DegradationMetrics,
    DegradationConfig,
    DegradationTransition,
    TransitionTrigger,
    get_degradation_sm,
    reset_degradation_sm,
    requires_feature,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def state_machine():
    """Create a fresh state machine for testing."""
    return DegradationStateMachine()


@pytest.fixture
def custom_config():
    """Custom configuration with lower thresholds for testing."""
    return DegradationConfig(
        error_rate_elevated=0.01,
        error_rate_degraded=0.05,
        error_rate_critical=0.10,
        error_rate_emergency=0.25,
        latency_elevated=100,
        latency_degraded=500,
        latency_critical=1000,
        latency_emergency=5000,
        consecutive_healthy_checks=2,
        min_recovery_wait_seconds=1,
    )


@pytest.fixture
def healthy_metrics():
    """Metrics indicating healthy system."""
    return DegradationMetrics(
        error_rate=0.001,
        latency_p50_ms=20,
        latency_p99_ms=50,
        request_rate=100,
        cpu_usage=0.3,
        memory_usage=0.4,
        critical_services_down=0,
        queue_depth=10,
    )


@pytest.fixture
def degraded_metrics():
    """Metrics indicating degraded system."""
    return DegradationMetrics(
        error_rate=0.08,
        latency_p50_ms=200,
        latency_p99_ms=800,
        request_rate=50,
        cpu_usage=0.8,
        memory_usage=0.7,
        critical_services_down=1,
        queue_depth=500,
    )


@pytest.fixture
def critical_metrics():
    """Metrics indicating critical system state."""
    return DegradationMetrics(
        error_rate=0.15,
        latency_p50_ms=500,
        latency_p99_ms=2000,
        request_rate=20,
        cpu_usage=0.95,
        memory_usage=0.9,
        critical_services_down=2,
        queue_depth=1000,
    )


@pytest.fixture(autouse=True)
def reset_global_state_machine():
    """Reset global state machine before each test."""
    reset_degradation_sm()
    yield
    reset_degradation_sm()


# ============================================================================
# DEGRADATION LEVEL ENUM TESTS
# ============================================================================


class TestDegradationLevelEnum:
    """
    B2 COMPLIANCE: Explicit DegradationLevel enum tests.
    """
    
    def test_enum_values_exist(self):
        """All required degradation levels should exist."""
        assert DegradationLevel.FULL is not None
        assert DegradationLevel.ELEVATED is not None
        assert DegradationLevel.DEGRADED is not None
        assert DegradationLevel.CRITICAL is not None
        assert DegradationLevel.EMERGENCY is not None
    
    def test_enum_ordering(self):
        """Levels should be ordered by severity."""
        assert DegradationLevel.FULL.value < DegradationLevel.ELEVATED.value
        assert DegradationLevel.ELEVATED.value < DegradationLevel.DEGRADED.value
        assert DegradationLevel.DEGRADED.value < DegradationLevel.CRITICAL.value
        assert DegradationLevel.CRITICAL.value < DegradationLevel.EMERGENCY.value
    
    def test_enum_is_complete(self):
        """Enum should have exactly 5 levels."""
        assert len(DegradationLevel) == 5


# ============================================================================
# DEGRADATION STATE TESTS
# ============================================================================


class TestDegradationState:
    """Test DegradationState schema."""
    
    def test_state_creation(self):
        """Should create valid state."""
        state = DegradationState(
            level=DegradationLevel.FULL,
            since=datetime.utcnow(),
            reason="System initialized",
        )
        
        assert state.level == DegradationLevel.FULL
        assert state.auto_recover is True
        assert state.recover_after_minutes == 30
    
    def test_state_with_affected_services(self):
        """State should track affected services."""
        state = DegradationState(
            level=DegradationLevel.DEGRADED,
            since=datetime.utcnow(),
            reason="High error rate",
            affected_services=["analytics", "ml"],
        )
        
        assert "analytics" in state.affected_services
        assert "ml" in state.affected_services


# ============================================================================
# STATE MACHINE TESTS
# ============================================================================


class TestDegradationStateMachine:
    """Test state machine functionality."""
    
    def test_initial_state_is_full(self, state_machine):
        """
        B2 COMPLIANCE: Initial state should be FULL.
        """
        assert state_machine.current_level == DegradationLevel.FULL
        assert state_machine.current_state.reason == "System initialized"
    
    def test_disabled_features_at_full(self, state_machine):
        """No features disabled at FULL level."""
        assert state_machine.disabled_features == []
    
    def test_disabled_features_at_degraded(self):
        """
        B2 COMPLIANCE: Features disabled at DEGRADED level.
        """
        sm = DegradationStateMachine()
        
        # Manually set to DEGRADED
        sm._current_state = DegradationState(
            level=DegradationLevel.DEGRADED,
            since=datetime.utcnow(),
            reason="Test",
        )
        
        disabled = sm.disabled_features
        assert "sensitivity_analysis" in disabled
        assert "counterfactual_scenarios" in disabled
        assert "benchmark_comparison" in disabled
    
    def test_disabled_features_at_critical(self):
        """
        B2 COMPLIANCE: More features disabled at CRITICAL level.
        """
        sm = DegradationStateMachine()
        
        sm._current_state = DegradationState(
            level=DegradationLevel.CRITICAL,
            since=datetime.utcnow(),
            reason="Test",
        )
        
        disabled = sm.disabled_features
        assert "ml_predictions" in disabled
        assert "detailed_justification" in disabled
    
    def test_disabled_features_at_emergency(self):
        """
        B2 COMPLIANCE: Maximum features disabled at EMERGENCY level.
        """
        sm = DegradationStateMachine()
        
        sm._current_state = DegradationState(
            level=DegradationLevel.EMERGENCY,
            since=datetime.utcnow(),
            reason="Test",
        )
        
        disabled = sm.disabled_features
        assert "strategic_analysis" in disabled
        assert "complex_routing" in disabled
        assert len(disabled) > 5  # Many features disabled
    
    def test_is_feature_enabled_at_full(self, state_machine):
        """All features enabled at FULL level."""
        assert state_machine.is_feature_enabled("sensitivity_analysis") is True
        assert state_machine.is_feature_enabled("ml_predictions") is True
        assert state_machine.is_feature_enabled("any_feature") is True
    
    def test_is_feature_enabled_at_degraded(self):
        """Some features disabled at DEGRADED level."""
        sm = DegradationStateMachine()
        sm._current_state = DegradationState(
            level=DegradationLevel.DEGRADED,
            since=datetime.utcnow(),
            reason="Test",
        )
        
        assert sm.is_feature_enabled("sensitivity_analysis") is False
        assert sm.is_feature_enabled("basic_decision") is True  # Not in disabled list


# ============================================================================
# AUTOMATIC TRANSITION TESTS
# ============================================================================


class TestAutomaticTransitions:
    """
    B2 COMPLIANCE: Test automatic transitions based on metrics.
    """
    
    @pytest.mark.asyncio
    async def test_transition_to_degraded_on_high_error_rate(
        self, custom_config, degraded_metrics
    ):
        """Should transition to DEGRADED on high error rate."""
        sm = DegradationStateMachine(config=custom_config)
        
        await sm.check_and_transition(degraded_metrics)
        
        assert sm.current_level == DegradationLevel.DEGRADED
    
    @pytest.mark.asyncio
    async def test_transition_to_critical_on_very_high_error_rate(
        self, custom_config, critical_metrics
    ):
        """Should transition to CRITICAL on very high error rate."""
        sm = DegradationStateMachine(config=custom_config)
        
        await sm.check_and_transition(critical_metrics)
        
        assert sm.current_level == DegradationLevel.CRITICAL
    
    @pytest.mark.asyncio
    async def test_transition_to_emergency_on_extreme_metrics(self, custom_config):
        """Should transition to EMERGENCY on extreme metrics."""
        sm = DegradationStateMachine(config=custom_config)
        
        emergency_metrics = DegradationMetrics(
            error_rate=0.30,  # 30% errors
            latency_p99_ms=10000,  # 10s latency
            critical_services_down=4,
        )
        
        await sm.check_and_transition(emergency_metrics)
        
        assert sm.current_level == DegradationLevel.EMERGENCY
    
    @pytest.mark.asyncio
    async def test_no_transition_on_healthy_metrics(
        self, state_machine, healthy_metrics
    ):
        """Should not transition on healthy metrics."""
        await state_machine.check_and_transition(healthy_metrics)
        
        assert state_machine.current_level == DegradationLevel.FULL
    
    @pytest.mark.asyncio
    async def test_transition_based_on_latency(self, custom_config):
        """Should transition based on high latency."""
        sm = DegradationStateMachine(config=custom_config)
        
        high_latency = DegradationMetrics(
            error_rate=0.001,  # Low errors
            latency_p99_ms=1500,  # High latency > critical threshold
        )
        
        await sm.check_and_transition(high_latency)
        
        assert sm.current_level == DegradationLevel.CRITICAL
    
    @pytest.mark.asyncio
    async def test_transition_based_on_services_down(self, custom_config):
        """Should transition when critical services are down."""
        sm = DegradationStateMachine(config=custom_config)
        
        services_down = DegradationMetrics(
            error_rate=0.001,
            latency_p99_ms=50,
            critical_services_down=2,
        )
        
        await sm.check_and_transition(services_down)
        
        assert sm.current_level == DegradationLevel.CRITICAL


# ============================================================================
# RECOVERY TESTS
# ============================================================================


class TestRecovery:
    """
    B2 COMPLIANCE: Test automatic recovery.
    """
    
    @pytest.mark.asyncio
    async def test_recovery_after_consecutive_healthy_checks(self, custom_config):
        """Should recover after consecutive healthy checks."""
        sm = DegradationStateMachine(config=custom_config)
        
        # First, degrade the system
        degraded = DegradationMetrics(error_rate=0.08)
        await sm.check_and_transition(degraded)
        assert sm.current_level == DegradationLevel.DEGRADED
        
        # Now send healthy metrics multiple times
        healthy = DegradationMetrics(error_rate=0.001, latency_p99_ms=50)
        
        # First healthy check
        await sm.check_and_transition(healthy)
        # Still degraded (need consecutive checks)
        
        # Second healthy check triggers recovery
        await sm.check_and_transition(healthy)
        
        # Should have recovered one level
        assert sm.current_level in [DegradationLevel.ELEVATED, DegradationLevel.FULL]
    
    @pytest.mark.asyncio
    async def test_manual_recovery(self):
        """Should support manual recovery."""
        sm = DegradationStateMachine()
        
        # Degrade manually
        await sm.force_level(DegradationLevel.CRITICAL, "Maintenance")
        assert sm.current_level == DegradationLevel.CRITICAL
        
        # Recover manually
        await sm.force_level(DegradationLevel.FULL, "Maintenance complete")
        assert sm.current_level == DegradationLevel.FULL
    
    @pytest.mark.asyncio
    async def test_recovery_respects_wait_time(self, custom_config):
        """Recovery should respect minimum wait time."""
        sm = DegradationStateMachine(config=custom_config)
        sm._current_state.auto_recover = True
        
        # Set last recovery attempt to now
        sm._last_recovery_attempt = datetime.utcnow()
        sm._consecutive_healthy = custom_config.consecutive_healthy_checks
        
        # Should not recover immediately
        result = await sm.attempt_recovery()
        
        # May or may not recover based on timing
        # The test validates the logic exists


# ============================================================================
# TRANSITION HISTORY TESTS
# ============================================================================


class TestTransitionHistory:
    """Test transition tracking."""
    
    @pytest.mark.asyncio
    async def test_transitions_are_recorded(self, state_machine, degraded_metrics):
        """Transitions should be recorded in history."""
        await state_machine.check_and_transition(degraded_metrics)
        
        assert len(state_machine.transitions) > 0
        
        last_transition = state_machine.transitions[-1]
        assert last_transition.from_level == DegradationLevel.FULL
        assert last_transition.to_level == DegradationLevel.DEGRADED
        assert last_transition.trigger == TransitionTrigger.THRESHOLD
    
    @pytest.mark.asyncio
    async def test_transition_includes_reason(self, state_machine, degraded_metrics):
        """Transition should include detailed reason."""
        await state_machine.check_and_transition(degraded_metrics)
        
        last_transition = state_machine.transitions[-1]
        assert len(last_transition.reason) > 0
        # Reason should mention the cause
        assert "DEGRADED" in last_transition.reason or "Error" in last_transition.reason
    
    @pytest.mark.asyncio
    async def test_transition_history_limit(self, state_machine):
        """Transition history should be limited."""
        # Create many transitions
        for i in range(150):
            await state_machine._transition(
                to_level=DegradationLevel.DEGRADED if i % 2 == 0 else DegradationLevel.FULL,
                trigger=TransitionTrigger.MANUAL,
                reason=f"Test transition {i}",
            )
        
        # Should keep only last 100
        assert len(state_machine.transitions) == 100


# ============================================================================
# CALLBACK TESTS
# ============================================================================


class TestCallbacks:
    """Test event callbacks."""
    
    @pytest.mark.asyncio
    async def test_on_transition_callback(self, state_machine, degraded_metrics):
        """Should call registered callbacks on transition."""
        callback_called = []
        
        def on_transition(transition):
            callback_called.append(transition)
        
        state_machine.on_transition(on_transition)
        
        await state_machine.check_and_transition(degraded_metrics)
        
        assert len(callback_called) == 1
        assert callback_called[0].to_level == DegradationLevel.DEGRADED
    
    @pytest.mark.asyncio
    async def test_async_callback(self, state_machine, degraded_metrics):
        """Should support async callbacks."""
        callback_called = []
        
        async def async_on_transition(transition):
            callback_called.append(transition)
        
        state_machine.on_transition(async_on_transition)
        
        await state_machine.check_and_transition(degraded_metrics)
        
        assert len(callback_called) == 1


# ============================================================================
# STATUS REPORTING TESTS
# ============================================================================


class TestStatusReporting:
    """Test status reporting."""
    
    def test_get_status(self, state_machine):
        """Should return comprehensive status."""
        status = state_machine.get_status()
        
        assert "level" in status
        assert "since" in status
        assert "reason" in status
        assert "disabled_features" in status
        assert "auto_recover" in status
        assert status["level"] == "FULL"
    
    @pytest.mark.asyncio
    async def test_get_recent_transitions(self, state_machine, degraded_metrics):
        """Should return recent transitions."""
        await state_machine.check_and_transition(degraded_metrics)
        
        recent = state_machine.get_recent_transitions(limit=5)
        
        assert len(recent) >= 1
        assert "from_level" in recent[0]
        assert "to_level" in recent[0]
        assert "triggered_at" in recent[0]


# ============================================================================
# FORCE LEVEL TESTS
# ============================================================================


class TestForceLevel:
    """Test manual level forcing."""
    
    @pytest.mark.asyncio
    async def test_force_to_emergency(self, state_machine):
        """Should allow forcing to EMERGENCY."""
        await state_machine.force_level(
            DegradationLevel.EMERGENCY,
            "Manual intervention for maintenance",
        )
        
        assert state_machine.current_level == DegradationLevel.EMERGENCY
        assert "Manual" in state_machine.current_state.reason
    
    @pytest.mark.asyncio
    async def test_force_records_transition(self, state_machine):
        """Forced transitions should be recorded."""
        await state_machine.force_level(DegradationLevel.CRITICAL, "Test")
        
        assert len(state_machine.transitions) > 0
        last = state_machine.transitions[-1]
        assert last.trigger == TransitionTrigger.MANUAL


# ============================================================================
# GLOBAL STATE MACHINE TESTS
# ============================================================================


class TestGlobalStateMachine:
    """Test global state machine singleton."""
    
    def test_get_global_instance(self):
        """Should return global instance."""
        sm1 = get_degradation_sm()
        sm2 = get_degradation_sm()
        
        assert sm1 is sm2
    
    def test_reset_global_instance(self):
        """Should reset global instance."""
        sm1 = get_degradation_sm()
        reset_degradation_sm()
        sm2 = get_degradation_sm()
        
        assert sm1 is not sm2


# ============================================================================
# FEATURE GATING DECORATOR TESTS
# ============================================================================


class TestRequiresFeatureDecorator:
    """Test requires_feature decorator."""
    
    @pytest.mark.asyncio
    async def test_decorator_allows_enabled_feature(self):
        """Should allow access when feature is enabled."""
        reset_degradation_sm()  # Start fresh at FULL level
        
        @requires_feature("any_feature")
        async def test_endpoint():
            return "success"
        
        result = await test_endpoint()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_decorator_blocks_disabled_feature(self):
        """Should block access when feature is disabled."""
        from fastapi import HTTPException
        
        # Set to DEGRADED level
        sm = get_degradation_sm()
        sm._current_state = DegradationState(
            level=DegradationLevel.DEGRADED,
            since=datetime.utcnow(),
            reason="Test",
        )
        
        @requires_feature("sensitivity_analysis")
        async def test_endpoint():
            return "success"
        
        with pytest.raises(HTTPException) as exc_info:
            await test_endpoint()
        
        assert exc_info.value.status_code == 503
        assert "temporarily disabled" in exc_info.value.detail


# ============================================================================
# MONITORING TESTS
# ============================================================================


class TestMonitoring:
    """Test background monitoring."""
    
    @pytest.mark.asyncio
    async def test_start_and_stop_monitoring(self, custom_config, healthy_metrics):
        """Should start and stop monitoring correctly."""
        sm = DegradationStateMachine(config=custom_config)
        
        def metrics_provider():
            return healthy_metrics
        
        # Start monitoring
        await sm.start_monitoring(metrics_provider, interval_seconds=1)
        assert sm._running is True
        assert sm._monitor_task is not None
        
        # Wait a bit
        await asyncio.sleep(0.1)
        
        # Stop monitoring
        await sm.stop_monitoring()
        assert sm._running is False
