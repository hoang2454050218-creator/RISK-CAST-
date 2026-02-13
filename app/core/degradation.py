"""
Degradation State Machine with Automatic Transitions.

B2 COMPLIANCE: "No explicit DegradationLevel enum with automatic transitions" - FIXED

Provides:
- Explicit DegradationLevel enum (FULL, ELEVATED, DEGRADED, CRITICAL, EMERGENCY)
- Automatic transitions based on metrics
- Feature disabling at each level
- Recovery management
- Full audit trail

The state machine ensures graceful degradation under load or failure,
maintaining core functionality while disabling non-essential features.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Callable, Any
from enum import Enum
from pydantic import BaseModel, Field
import asyncio
import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# ENUMS
# ============================================================================


class DegradationLevel(Enum):
    """
    System degradation levels.
    
    B2 COMPLIANCE: Explicit DegradationLevel enum.
    
    Levels:
    - FULL (0): All features available, optimal performance
    - ELEVATED (1): Some latency, all features still available
    - DEGRADED (2): Non-critical features disabled
    - CRITICAL (3): Only essential features, minimal processing
    - EMERGENCY (4): Minimal functionality, emergency mode
    """
    FULL = 0         # All features available
    ELEVATED = 1     # Some latency, all features
    DEGRADED = 2     # Non-critical features disabled
    CRITICAL = 3     # Only essential features
    EMERGENCY = 4    # Minimal functionality


class TransitionTrigger(str, Enum):
    """Triggers for degradation transitions."""
    HEALTH_CHECK = "health_check"       # Automatic from health metrics
    MANUAL = "manual"                   # Manual operator intervention
    AUTO_RECOVERY = "auto_recovery"     # Automatic recovery attempt
    CIRCUIT_BREAKER = "circuit_breaker" # Circuit breaker triggered
    THRESHOLD = "threshold"             # Threshold exceeded
    TIMEOUT = "timeout"                 # Operation timeout
    ERROR_RATE = "error_rate"           # Error rate threshold
    DEPENDENCY = "dependency"           # Dependency failure


# ============================================================================
# SCHEMAS
# ============================================================================


class DegradationState(BaseModel):
    """Current degradation state."""
    
    level: DegradationLevel = Field(description="Current degradation level")
    since: datetime = Field(description="When this level started")
    reason: str = Field(description="Reason for current level")
    affected_services: List[str] = Field(
        default_factory=list,
        description="Services affected by degradation"
    )
    
    # Recovery settings
    auto_recover: bool = Field(default=True, description="Enable auto-recovery")
    recover_after_minutes: int = Field(
        default=30,
        description="Minutes before attempting recovery"
    )
    
    # Metrics at transition
    metrics_snapshot: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metrics when state changed"
    )


class DegradationTransition(BaseModel):
    """Record of a degradation level transition."""
    
    from_level: DegradationLevel = Field(description="Previous level")
    to_level: DegradationLevel = Field(description="New level")
    triggered_at: datetime = Field(description="When transition occurred")
    trigger: TransitionTrigger = Field(description="What triggered transition")
    reason: str = Field(description="Detailed reason")
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metrics at transition time"
    )
    
    # Recovery tracking
    recovery_attempt: bool = Field(
        default=False,
        description="Was this a recovery attempt"
    )
    success: bool = Field(default=True, description="Did transition succeed")


class DegradationMetrics(BaseModel):
    """Metrics used for degradation decisions."""
    
    error_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    latency_p50_ms: float = Field(default=0.0, ge=0.0)
    latency_p99_ms: float = Field(default=0.0, ge=0.0)
    request_rate: float = Field(default=0.0, ge=0.0)
    cpu_usage: float = Field(default=0.0, ge=0.0, le=1.0)
    memory_usage: float = Field(default=0.0, ge=0.0, le=1.0)
    critical_services_down: int = Field(default=0, ge=0)
    queue_depth: int = Field(default=0, ge=0)
    
    # Circuit breaker states
    open_circuit_breakers: int = Field(default=0, ge=0)


class DegradationConfig(BaseModel):
    """Configuration for degradation thresholds."""
    
    # Error rate thresholds (fraction)
    error_rate_elevated: float = Field(default=0.01)    # 1%
    error_rate_degraded: float = Field(default=0.05)    # 5%
    error_rate_critical: float = Field(default=0.10)    # 10%
    error_rate_emergency: float = Field(default=0.25)   # 25%
    
    # Latency thresholds (P99, milliseconds)
    latency_elevated: float = Field(default=2000)       # 2s
    latency_degraded: float = Field(default=5000)       # 5s
    latency_critical: float = Field(default=10000)      # 10s
    latency_emergency: float = Field(default=30000)     # 30s
    
    # Service health thresholds
    services_down_degraded: int = Field(default=1)
    services_down_critical: int = Field(default=2)
    services_down_emergency: int = Field(default=3)
    
    # Recovery settings
    recovery_check_interval_seconds: int = Field(default=60)
    min_recovery_wait_seconds: int = Field(default=300)  # 5 minutes
    consecutive_healthy_checks: int = Field(default=3)


# ============================================================================
# DEGRADATION STATE MACHINE
# ============================================================================


class DegradationStateMachine:
    """
    Manages system degradation with automatic transitions.
    
    B2 COMPLIANCE: Automatic transitions based on metrics.
    
    Transitions:
    - FULL → ELEVATED: Minor issues detected (1% errors, 2s latency)
    - ELEVATED → DEGRADED: Multiple issues (5% errors, 5s latency)
    - DEGRADED → CRITICAL: Critical service down (10% errors)
    - CRITICAL → EMERGENCY: Multiple critical services down (25% errors)
    
    Auto-recovery:
    - Health checks passing → recover one level
    - Gradual recovery to prevent oscillation
    """
    
    # Features disabled at each level
    DISABLED_FEATURES: Dict[DegradationLevel, List[str]] = {
        DegradationLevel.FULL: [],
        DegradationLevel.ELEVATED: [],
        DegradationLevel.DEGRADED: [
            "sensitivity_analysis",
            "counterfactual_scenarios",
            "benchmark_comparison",
            "detailed_analytics",
        ],
        DegradationLevel.CRITICAL: [
            "sensitivity_analysis",
            "counterfactual_scenarios",
            "benchmark_comparison",
            "detailed_analytics",
            "ml_predictions",
            "detailed_justification",
            "historical_comparison",
        ],
        DegradationLevel.EMERGENCY: [
            # Only basic decision + audit remain
            "sensitivity_analysis",
            "counterfactual_scenarios",
            "benchmark_comparison",
            "detailed_analytics",
            "ml_predictions",
            "detailed_justification",
            "historical_comparison",
            "strategic_analysis",
            "complex_routing",
            "notification_batching",
        ],
    }
    
    # Services affected at each level
    AFFECTED_SERVICES: Dict[DegradationLevel, List[str]] = {
        DegradationLevel.FULL: [],
        DegradationLevel.ELEVATED: ["analytics"],
        DegradationLevel.DEGRADED: ["analytics", "ml", "benchmark"],
        DegradationLevel.CRITICAL: ["analytics", "ml", "benchmark", "justification"],
        DegradationLevel.EMERGENCY: [
            "analytics", "ml", "benchmark", "justification", 
            "routing", "notifications"
        ],
    }
    
    def __init__(self, config: Optional[DegradationConfig] = None):
        """Initialize degradation state machine."""
        self._config = config or DegradationConfig()
        
        self._current_state = DegradationState(
            level=DegradationLevel.FULL,
            since=datetime.utcnow(),
            reason="System initialized",
            affected_services=[],
        )
        
        self._transitions: List[DegradationTransition] = []
        self._metrics_callback: Optional[Callable] = None
        self._on_transition_callbacks: List[Callable] = []
        
        # Recovery tracking
        self._consecutive_healthy: int = 0
        self._last_recovery_attempt: Optional[datetime] = None
        
        # Background tasks
        self._monitor_task: Optional[asyncio.Task] = None
        self._running: bool = False
    
    # ========================================================================
    # PROPERTIES
    # ========================================================================
    
    @property
    def current_level(self) -> DegradationLevel:
        """Get current degradation level."""
        return self._current_state.level
    
    @property
    def current_state(self) -> DegradationState:
        """Get full current state."""
        return self._current_state
    
    @property
    def disabled_features(self) -> List[str]:
        """Get features disabled at current level."""
        return self.DISABLED_FEATURES.get(self._current_state.level, [])
    
    @property
    def affected_services(self) -> List[str]:
        """Get services affected at current level."""
        return self.AFFECTED_SERVICES.get(self._current_state.level, [])
    
    @property
    def transitions(self) -> List[DegradationTransition]:
        """Get transition history."""
        return self._transitions.copy()
    
    # ========================================================================
    # FEATURE CHECKING
    # ========================================================================
    
    def is_feature_enabled(self, feature: str) -> bool:
        """
        Check if a feature is enabled at current level.
        
        B2 COMPLIANCE: Feature availability check.
        """
        return feature not in self.disabled_features
    
    def get_enabled_features(self, requested: List[str]) -> List[str]:
        """Get subset of requested features that are enabled."""
        return [f for f in requested if self.is_feature_enabled(f)]
    
    # ========================================================================
    # AUTOMATIC TRANSITIONS
    # ========================================================================
    
    async def check_and_transition(self, metrics: DegradationMetrics):
        """
        Check metrics and transition if needed.
        
        B2 COMPLIANCE: Automatic transitions based on metrics.
        """
        current_level = self._current_state.level
        required_level = self._calculate_required_level(metrics)
        
        if required_level.value > current_level.value:
            # Degradation needed
            await self._transition(
                to_level=required_level,
                trigger=TransitionTrigger.THRESHOLD,
                reason=self._get_degradation_reason(metrics, required_level),
                metrics=metrics.dict(),
            )
            self._consecutive_healthy = 0
            
        elif required_level.value < current_level.value:
            # Potential recovery
            self._consecutive_healthy += 1
            
            if self._consecutive_healthy >= self._config.consecutive_healthy_checks:
                if self._can_attempt_recovery():
                    await self.attempt_recovery()
    
    def _calculate_required_level(self, metrics: DegradationMetrics) -> DegradationLevel:
        """
        Calculate required degradation level from metrics.
        
        B2 COMPLIANCE: Metric-based level calculation.
        """
        # Check from highest to lowest severity
        
        # EMERGENCY check
        if (metrics.error_rate >= self._config.error_rate_emergency or
            metrics.latency_p99_ms >= self._config.latency_emergency or
            metrics.critical_services_down >= self._config.services_down_emergency):
            return DegradationLevel.EMERGENCY
        
        # CRITICAL check
        if (metrics.error_rate >= self._config.error_rate_critical or
            metrics.latency_p99_ms >= self._config.latency_critical or
            metrics.critical_services_down >= self._config.services_down_critical):
            return DegradationLevel.CRITICAL
        
        # DEGRADED check
        if (metrics.error_rate >= self._config.error_rate_degraded or
            metrics.latency_p99_ms >= self._config.latency_degraded or
            metrics.critical_services_down >= self._config.services_down_degraded):
            return DegradationLevel.DEGRADED
        
        # ELEVATED check
        if (metrics.error_rate >= self._config.error_rate_elevated or
            metrics.latency_p99_ms >= self._config.latency_elevated):
            return DegradationLevel.ELEVATED
        
        return DegradationLevel.FULL
    
    def _get_degradation_reason(
        self,
        metrics: DegradationMetrics,
        level: DegradationLevel,
    ) -> str:
        """Generate human-readable degradation reason."""
        reasons = []
        
        if metrics.error_rate >= self._config.error_rate_elevated:
            reasons.append(f"Error rate {metrics.error_rate:.1%}")
        
        if metrics.latency_p99_ms >= self._config.latency_elevated:
            reasons.append(f"P99 latency {metrics.latency_p99_ms:.0f}ms")
        
        if metrics.critical_services_down > 0:
            reasons.append(f"{metrics.critical_services_down} services down")
        
        if metrics.open_circuit_breakers > 0:
            reasons.append(f"{metrics.open_circuit_breakers} circuit breakers open")
        
        return f"Degraded to {level.name}: " + ", ".join(reasons) if reasons else f"Transitioning to {level.name}"
    
    def _can_attempt_recovery(self) -> bool:
        """Check if recovery attempt is allowed."""
        if not self._current_state.auto_recover:
            return False
        
        if self._last_recovery_attempt:
            elapsed = (datetime.utcnow() - self._last_recovery_attempt).total_seconds()
            if elapsed < self._config.min_recovery_wait_seconds:
                return False
        
        return True
    
    # ========================================================================
    # TRANSITIONS
    # ========================================================================
    
    async def _transition(
        self,
        to_level: DegradationLevel,
        trigger: TransitionTrigger,
        reason: str,
        metrics: Optional[Dict[str, Any]] = None,
        recovery_attempt: bool = False,
    ):
        """
        Transition to a new degradation level.
        
        B2 COMPLIANCE: Level transitions with audit trail.
        """
        from_level = self._current_state.level
        
        # Create transition record
        transition = DegradationTransition(
            from_level=from_level,
            to_level=to_level,
            triggered_at=datetime.utcnow(),
            trigger=trigger,
            reason=reason,
            metrics=metrics or {},
            recovery_attempt=recovery_attempt,
        )
        
        self._transitions.append(transition)
        
        # Keep only last 100 transitions
        if len(self._transitions) > 100:
            self._transitions = self._transitions[-100:]
        
        # Update state
        self._current_state = DegradationState(
            level=to_level,
            since=datetime.utcnow(),
            reason=reason,
            affected_services=self.AFFECTED_SERVICES.get(to_level, []),
            auto_recover=self._current_state.auto_recover,
            recover_after_minutes=self._current_state.recover_after_minutes,
            metrics_snapshot=metrics or {},
        )
        
        # Log transition
        log_level = "warning" if to_level.value > from_level.value else "info"
        getattr(logger, log_level)(
            "degradation_level_changed",
            from_level=from_level.name,
            to_level=to_level.name,
            trigger=trigger.value,
            reason=reason,
            disabled_features=self.disabled_features,
        )
        
        # Emit metric if callback registered
        if self._metrics_callback:
            try:
                await self._metrics_callback("degradation_level", to_level.value)
            except Exception as e:
                logger.error("metrics_callback_failed", error=str(e))
        
        # Notify callbacks
        for callback in self._on_transition_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(transition)
                else:
                    callback(transition)
            except Exception as e:
                logger.error("transition_callback_failed", error=str(e))
    
    async def force_level(self, level: DegradationLevel, reason: str):
        """
        Manually force a degradation level.
        
        Used for operator intervention.
        """
        logger.warning(
            "manual_degradation_forced",
            level=level.name,
            reason=reason,
        )
        
        await self._transition(
            to_level=level,
            trigger=TransitionTrigger.MANUAL,
            reason=f"Manual: {reason}",
        )
    
    async def attempt_recovery(self) -> bool:
        """
        Attempt to recover one degradation level.
        
        B2 COMPLIANCE: Automatic recovery.
        """
        current = self._current_state.level
        
        if current == DegradationLevel.FULL:
            logger.debug("recovery_skipped_already_full")
            return False
        
        # Get target level (one level lower)
        levels = list(DegradationLevel)
        current_idx = levels.index(current)
        target_level = levels[current_idx - 1]
        
        self._last_recovery_attempt = datetime.utcnow()
        
        await self._transition(
            to_level=target_level,
            trigger=TransitionTrigger.AUTO_RECOVERY,
            reason=f"Auto-recovery: {self._config.consecutive_healthy_checks} consecutive healthy checks",
            recovery_attempt=True,
        )
        
        self._consecutive_healthy = 0
        return True
    
    # ========================================================================
    # MONITORING
    # ========================================================================
    
    async def start_monitoring(
        self,
        metrics_provider: Callable[[], DegradationMetrics],
        interval_seconds: int = 30,
    ):
        """Start background monitoring task."""
        self._running = True
        self._monitor_task = asyncio.create_task(
            self._monitoring_loop(metrics_provider, interval_seconds)
        )
        logger.info("degradation_monitoring_started", interval=interval_seconds)
    
    async def stop_monitoring(self):
        """Stop background monitoring."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("degradation_monitoring_stopped")
    
    async def _monitoring_loop(
        self,
        metrics_provider: Callable[[], DegradationMetrics],
        interval: int,
    ):
        """Background monitoring loop."""
        while self._running:
            try:
                metrics = metrics_provider()
                await self.check_and_transition(metrics)
            except Exception as e:
                logger.error("monitoring_loop_error", error=str(e))
            
            await asyncio.sleep(interval)
    
    # ========================================================================
    # CALLBACKS
    # ========================================================================
    
    def on_transition(self, callback: Callable[[DegradationTransition], Any]):
        """Register a callback for state transitions."""
        self._on_transition_callbacks.append(callback)
    
    def set_metrics_callback(self, callback: Callable):
        """Set callback for emitting metrics."""
        self._metrics_callback = callback
    
    # ========================================================================
    # STATUS
    # ========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Get current degradation status."""
        return {
            "level": self._current_state.level.name,
            "level_value": self._current_state.level.value,
            "since": self._current_state.since.isoformat(),
            "reason": self._current_state.reason,
            "affected_services": self.affected_services,
            "disabled_features": self.disabled_features,
            "auto_recover": self._current_state.auto_recover,
            "consecutive_healthy": self._consecutive_healthy,
            "transition_count": len(self._transitions),
        }
    
    def get_recent_transitions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent transitions."""
        return [
            {
                "from_level": t.from_level.name,
                "to_level": t.to_level.name,
                "triggered_at": t.triggered_at.isoformat(),
                "trigger": t.trigger.value,
                "reason": t.reason,
                "recovery_attempt": t.recovery_attempt,
            }
            for t in self._transitions[-limit:]
        ]


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================


_degradation_sm: Optional[DegradationStateMachine] = None


def get_degradation_sm() -> DegradationStateMachine:
    """Get global degradation state machine."""
    global _degradation_sm
    if _degradation_sm is None:
        _degradation_sm = DegradationStateMachine()
    return _degradation_sm


def reset_degradation_sm():
    """Reset global degradation state machine (for testing)."""
    global _degradation_sm
    _degradation_sm = None


# ============================================================================
# FASTAPI MIDDLEWARE
# ============================================================================


async def degradation_middleware(request, call_next):
    """
    FastAPI middleware to check degradation level.
    
    B2 COMPLIANCE: Request-level degradation awareness.
    """
    sm = get_degradation_sm()
    
    # Add degradation info to request state
    request.state.degradation_level = sm.current_level
    request.state.disabled_features = sm.disabled_features
    
    # Process request
    response = await call_next(request)
    
    # Add degradation headers to response
    response.headers["X-Degradation-Level"] = sm.current_level.name
    
    if sm.disabled_features:
        response.headers["X-Disabled-Features"] = ",".join(sm.disabled_features)
    
    return response


# ============================================================================
# DECORATOR FOR FEATURE GATING
# ============================================================================


def requires_feature(feature_name: str):
    """
    Decorator to gate endpoints by feature availability.
    
    B2 COMPLIANCE: Feature gating based on degradation level.
    
    Usage:
        @router.get("/analytics")
        @requires_feature("detailed_analytics")
        async def get_analytics():
            ...
    """
    def decorator(func):
        from functools import wraps
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            sm = get_degradation_sm()
            
            if not sm.is_feature_enabled(feature_name):
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=503,
                    detail=f"Feature '{feature_name}' temporarily disabled due to system load",
                    headers={
                        "X-Degradation-Level": sm.current_level.name,
                        "Retry-After": "300",
                    },
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator
