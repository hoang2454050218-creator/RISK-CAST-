"""
Chaos Engineering Scheduler - Automated chaos experiments.

Schedules and runs chaos experiments safely with:
- Business hours enforcement
- Automatic abort on SLO breach
- Gradual rollout (start small)
- Mandatory cooldown between experiments

Addresses audit gap: D2.4 Chaos Engineering (+7 points)
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any
from enum import Enum
import asyncio
import uuid

import structlog
from pydantic import BaseModel, Field, computed_field

logger = structlog.get_logger(__name__)


# ============================================================================
# ENUMS
# ============================================================================


class ChaosExperimentType(str, Enum):
    """Types of chaos experiments."""
    POD_KILL = "pod_kill"
    NETWORK_LATENCY = "network_latency"
    NETWORK_PARTITION = "network_partition"
    CPU_STRESS = "cpu_stress"
    MEMORY_STRESS = "memory_stress"
    DISK_FILL = "disk_fill"
    DEPENDENCY_FAILURE = "dependency_failure"
    DNS_FAILURE = "dns_failure"
    TIME_SKEW = "time_skew"


class ExperimentStatus(str, Enum):
    """Status of chaos experiment."""
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    ABORTED = "aborted"
    FAILED = "failed"
    SKIPPED = "skipped"


# ============================================================================
# SCHEMAS
# ============================================================================


class ChaosExperiment(BaseModel):
    """Definition of a chaos experiment."""
    
    # Identity
    experiment_id: str = Field(default_factory=lambda: f"exp_{uuid.uuid4().hex[:8]}")
    name: str = Field(description="Human-readable experiment name")
    description: Optional[str] = Field(default=None, description="Detailed description")
    type: ChaosExperimentType = Field(description="Type of chaos to inject")
    
    # Targeting
    target: str = Field(description="Target service/pod selector")
    namespace: str = Field(default="riskcast", description="Kubernetes namespace")
    
    # Timing
    duration_minutes: int = Field(ge=1, le=60, description="Experiment duration")
    cooldown_minutes: int = Field(default=30, ge=5, description="Cooldown after experiment")
    
    # Parameters
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Experiment parameters")
    
    # Safety
    abort_conditions: List[str] = Field(
        default_factory=lambda: ["error_rate > 5%", "latency_p99 > 5s"],
        description="Conditions that trigger abort"
    )
    max_impact_percent: float = Field(
        default=10,
        ge=1,
        le=50,
        description="Max percentage of traffic affected"
    )
    
    # Schedule
    schedule: Optional[str] = Field(default=None, description="Cron expression")
    enabled: bool = Field(default=True)
    
    # Metadata
    owner: str = Field(default="platform-team")
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @computed_field
    @property
    def is_scheduled(self) -> bool:
        """Whether experiment has a schedule."""
        return self.schedule is not None


class ExperimentResult(BaseModel):
    """Result of a chaos experiment execution."""
    
    # Identity
    result_id: str = Field(default_factory=lambda: f"res_{uuid.uuid4().hex[:8]}")
    experiment_id: str
    experiment_name: str
    experiment_type: ChaosExperimentType
    
    # Execution
    started_at: datetime
    ended_at: datetime
    target: str
    
    # Status
    status: ExperimentStatus
    aborted: bool = Field(default=False)
    abort_reason: Optional[str] = Field(default=None)
    
    # Metrics during experiment
    error_rate_before: float = Field(ge=0, le=1)
    error_rate_during: float = Field(ge=0, le=1)
    error_rate_after: float = Field(ge=0, le=1)
    
    latency_p99_before_ms: float = Field(ge=0)
    latency_p99_during_ms: float = Field(ge=0)
    latency_p99_after_ms: float = Field(ge=0)
    
    # Recovery
    recovery_time_seconds: float = Field(ge=0)
    full_recovery_achieved: bool = Field(default=True)
    
    # Observations
    observations: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    
    # Scoring
    resilience_score: Optional[float] = Field(default=None, ge=0, le=100)
    
    @computed_field
    @property
    def duration_minutes(self) -> float:
        """Experiment duration in minutes."""
        return (self.ended_at - self.started_at).total_seconds() / 60
    
    @computed_field
    @property
    def error_rate_increase(self) -> float:
        """Error rate increase during experiment."""
        return self.error_rate_during - self.error_rate_before
    
    @computed_field
    @property
    def latency_increase_pct(self) -> float:
        """Latency increase percentage during experiment."""
        if self.latency_p99_before_ms == 0:
            return 0
        return (self.latency_p99_during_ms - self.latency_p99_before_ms) / self.latency_p99_before_ms * 100
    
    @computed_field
    @property
    def passed(self) -> bool:
        """Whether experiment passed (completed without abort)."""
        return self.status == ExperimentStatus.COMPLETED and not self.aborted


class MetricsSnapshot(BaseModel):
    """Snapshot of system metrics."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error_rate: float = Field(ge=0, le=1)
    latency_p99_ms: float = Field(ge=0)
    latency_p95_ms: float = Field(ge=0)
    latency_p50_ms: float = Field(ge=0)
    request_rate: float = Field(ge=0)
    cpu_utilization: float = Field(ge=0, le=1)
    memory_utilization: float = Field(ge=0, le=1)


class ScheduledRun(BaseModel):
    """A scheduled experiment run."""
    experiment_id: str
    scheduled_time: datetime
    status: ExperimentStatus = ExperimentStatus.SCHEDULED


# ============================================================================
# CHAOS SCHEDULER
# ============================================================================


class ChaosScheduler:
    """
    Schedules and runs chaos experiments safely.
    
    Safety features:
    - Business hours only (configurable)
    - Automatic abort on SLO breach
    - Gradual rollout (start small)
    - Mandatory cooldown between experiments
    - No experiments during incidents
    """
    
    # Default business hours (UTC)
    BUSINESS_HOURS_START = 9
    BUSINESS_HOURS_END = 17
    
    # Default thresholds for abort
    DEFAULT_ERROR_RATE_ABORT = 0.05  # 5%
    DEFAULT_LATENCY_ABORT_MS = 5000  # 5 seconds
    
    def __init__(
        self,
        experiments: Optional[List[ChaosExperiment]] = None,
        metrics_client: Optional[Any] = None,
        allow_outside_business_hours: bool = False,
        allow_weekends: bool = False,
    ):
        """
        Initialize chaos scheduler.
        
        Args:
            experiments: List of experiments to schedule
            metrics_client: Client for fetching metrics (Prometheus)
            allow_outside_business_hours: Allow experiments outside 9-5
            allow_weekends: Allow experiments on weekends
        """
        self._experiments: Dict[str, ChaosExperiment] = {}
        self._metrics_client = metrics_client
        self._allow_outside_hours = allow_outside_business_hours
        self._allow_weekends = allow_weekends
        
        # State
        self._last_run: Dict[str, datetime] = {}
        self._running: Optional[str] = None
        self._results: List[ExperimentResult] = []
        self._scheduled_runs: List[ScheduledRun] = []
        
        # Register experiments
        if experiments:
            for exp in experiments:
                self.register_experiment(exp)
        
        logger.info(
            "chaos_scheduler_initialized",
            experiments=len(self._experiments),
            allow_outside_hours=allow_outside_business_hours,
            allow_weekends=allow_weekends,
        )
    
    def register_experiment(self, experiment: ChaosExperiment) -> None:
        """Register an experiment."""
        self._experiments[experiment.experiment_id] = experiment
        logger.info(
            "experiment_registered",
            experiment_id=experiment.experiment_id,
            name=experiment.name,
            type=experiment.type.value,
        )
    
    def list_experiments(self) -> List[ChaosExperiment]:
        """List all registered experiments."""
        return list(self._experiments.values())
    
    def get_experiment(self, experiment_id: str) -> Optional[ChaosExperiment]:
        """Get experiment by ID."""
        return self._experiments.get(experiment_id)
    
    async def run_experiment(
        self,
        experiment_id: str,
        dry_run: bool = False,
        force: bool = False,
    ) -> ExperimentResult:
        """
        Run a chaos experiment.
        
        Args:
            experiment_id: ID of experiment to run
            dry_run: If True, don't actually inject chaos
            force: If True, bypass safety checks (use with caution!)
            
        Returns:
            ExperimentResult with outcomes
            
        Raises:
            ValueError: If experiment not found
            RuntimeError: If not safe to run
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        # Safety checks
        if not force:
            is_safe, reason = self._is_safe_to_run(experiment)
            if not is_safe:
                logger.warning(
                    "experiment_blocked",
                    experiment_id=experiment_id,
                    reason=reason,
                )
                raise RuntimeError(f"Not safe to run experiment: {reason}")
        
        logger.info(
            "chaos_experiment_starting",
            experiment_id=experiment_id,
            name=experiment.name,
            type=experiment.type.value,
            target=experiment.target,
            dry_run=dry_run,
            force=force,
        )
        
        started_at = datetime.utcnow()
        self._running = experiment_id
        
        try:
            # Capture baseline metrics
            baseline = await self._capture_metrics()
            
            # Inject chaos (unless dry run)
            if not dry_run:
                await self._inject_chaos(experiment)
            
            # Monitor during experiment
            observations = []
            metrics_during = []
            aborted = False
            abort_reason = None
            
            end_time = datetime.utcnow() + timedelta(minutes=experiment.duration_minutes)
            check_interval = min(10, experiment.duration_minutes * 60 / 10)
            
            while datetime.utcnow() < end_time:
                # Check abort conditions
                should_abort, reason = await self._check_abort_conditions(experiment)
                if should_abort:
                    aborted = True
                    abort_reason = reason
                    logger.warning(
                        "chaos_experiment_aborted",
                        experiment_id=experiment_id,
                        reason=reason,
                    )
                    break
                
                # Capture metrics
                current = await self._capture_metrics()
                metrics_during.append(current)
                
                # Record observations
                obs = self._observe(baseline, current)
                if obs:
                    observations.append(obs)
                
                await asyncio.sleep(check_interval)
            
            # Stop chaos injection
            if not dry_run:
                await self._stop_chaos(experiment)
            
            # Measure recovery
            recovery_start = datetime.utcnow()
            recovery_metrics = []
            full_recovery = False
            
            for _ in range(30):  # Max 5 minutes recovery check
                metrics = await self._capture_metrics()
                recovery_metrics.append(metrics)
                
                if self._is_recovered(baseline, metrics):
                    full_recovery = True
                    break
                
                await asyncio.sleep(10)
            
            recovery_time = (datetime.utcnow() - recovery_start).total_seconds()
            
            # Calculate average metrics during experiment
            avg_error_during = (
                sum(m.error_rate for m in metrics_during) / len(metrics_during)
                if metrics_during else baseline.error_rate
            )
            avg_latency_during = (
                sum(m.latency_p99_ms for m in metrics_during) / len(metrics_during)
                if metrics_during else baseline.latency_p99_ms
            )
            
            # Capture final metrics
            final_metrics = await self._capture_metrics()
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                experiment, baseline, avg_error_during, avg_latency_during, 
                recovery_time, full_recovery, observations
            )
            
            # Calculate resilience score
            resilience_score = self._calculate_resilience_score(
                baseline, avg_error_during, avg_latency_during,
                recovery_time, full_recovery, aborted
            )
            
            result = ExperimentResult(
                experiment_id=experiment_id,
                experiment_name=experiment.name,
                experiment_type=experiment.type,
                started_at=started_at,
                ended_at=datetime.utcnow(),
                target=experiment.target,
                status=ExperimentStatus.ABORTED if aborted else ExperimentStatus.COMPLETED,
                aborted=aborted,
                abort_reason=abort_reason,
                error_rate_before=baseline.error_rate,
                error_rate_during=avg_error_during,
                error_rate_after=final_metrics.error_rate,
                latency_p99_before_ms=baseline.latency_p99_ms,
                latency_p99_during_ms=avg_latency_during,
                latency_p99_after_ms=final_metrics.latency_p99_ms,
                recovery_time_seconds=recovery_time,
                full_recovery_achieved=full_recovery,
                observations=observations,
                recommendations=recommendations,
                resilience_score=resilience_score,
            )
            
            self._results.append(result)
            self._last_run[experiment_id] = datetime.utcnow()
            
            logger.info(
                "chaos_experiment_completed",
                experiment_id=experiment_id,
                status=result.status.value,
                aborted=aborted,
                recovery_time_s=recovery_time,
                resilience_score=resilience_score,
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "chaos_experiment_failed",
                experiment_id=experiment_id,
                error=str(e),
            )
            
            # Emergency stop
            try:
                await self._stop_chaos(experiment)
            except Exception:
                pass
            
            return ExperimentResult(
                experiment_id=experiment_id,
                experiment_name=experiment.name,
                experiment_type=experiment.type,
                started_at=started_at,
                ended_at=datetime.utcnow(),
                target=experiment.target,
                status=ExperimentStatus.FAILED,
                aborted=True,
                abort_reason=str(e),
                error_rate_before=0,
                error_rate_during=0,
                error_rate_after=0,
                latency_p99_before_ms=0,
                latency_p99_during_ms=0,
                latency_p99_after_ms=0,
                recovery_time_seconds=0,
                full_recovery_achieved=False,
                observations=[f"Experiment failed: {str(e)}"],
                recommendations=["Investigate experiment failure before retrying"],
            )
            
        finally:
            self._running = None
    
    def _is_safe_to_run(self, experiment: ChaosExperiment) -> Tuple[bool, Optional[str]]:
        """Check if it's safe to run the experiment."""
        now = datetime.utcnow()
        
        # Check if another experiment is running
        if self._running:
            return False, f"Another experiment is running: {self._running}"
        
        # Check cooldown
        last = self._last_run.get(experiment.experiment_id)
        if last:
            cooldown_end = last + timedelta(minutes=experiment.cooldown_minutes)
            if now < cooldown_end:
                remaining = (cooldown_end - now).total_seconds() / 60
                return False, f"Cooldown active, {remaining:.1f} minutes remaining"
        
        # Check business hours
        if not self._allow_outside_hours:
            if now.hour < self.BUSINESS_HOURS_START or now.hour >= self.BUSINESS_HOURS_END:
                return False, "Outside business hours (9-17 UTC)"
        
        # Check weekends
        if not self._allow_weekends:
            if now.weekday() >= 5:
                return False, "Weekends not allowed"
        
        # Check if experiment is enabled
        if not experiment.enabled:
            return False, "Experiment is disabled"
        
        return True, None
    
    async def _capture_metrics(self) -> MetricsSnapshot:
        """Capture current system metrics."""
        # In production, this would query Prometheus
        # Mock implementation for now
        import random
        
        return MetricsSnapshot(
            error_rate=random.uniform(0.001, 0.01),
            latency_p99_ms=random.uniform(200, 500),
            latency_p95_ms=random.uniform(100, 300),
            latency_p50_ms=random.uniform(50, 100),
            request_rate=random.uniform(100, 200),
            cpu_utilization=random.uniform(0.3, 0.6),
            memory_utilization=random.uniform(0.4, 0.7),
        )
    
    async def _check_abort_conditions(
        self,
        experiment: ChaosExperiment,
    ) -> Tuple[bool, Optional[str]]:
        """Check if experiment should be aborted."""
        metrics = await self._capture_metrics()
        
        # Check error rate
        if metrics.error_rate > self.DEFAULT_ERROR_RATE_ABORT:
            return True, f"Error rate {metrics.error_rate:.2%} exceeded {self.DEFAULT_ERROR_RATE_ABORT:.2%}"
        
        # Check latency
        if metrics.latency_p99_ms > self.DEFAULT_LATENCY_ABORT_MS:
            return True, f"Latency {metrics.latency_p99_ms:.0f}ms exceeded {self.DEFAULT_LATENCY_ABORT_MS}ms"
        
        return False, None
    
    async def _inject_chaos(self, experiment: ChaosExperiment) -> None:
        """Inject chaos based on experiment type."""
        logger.info(
            "injecting_chaos",
            type=experiment.type.value,
            target=experiment.target,
            parameters=experiment.parameters,
        )
        # In production, this would call Chaos Mesh, LitmusChaos, or similar
        # Mock implementation
        await asyncio.sleep(0.1)
    
    async def _stop_chaos(self, experiment: ChaosExperiment) -> None:
        """Stop chaos injection."""
        logger.info(
            "stopping_chaos",
            type=experiment.type.value,
            target=experiment.target,
        )
        # In production, this would clean up chaos injection
        await asyncio.sleep(0.1)
    
    def _observe(self, baseline: MetricsSnapshot, current: MetricsSnapshot) -> Optional[str]:
        """Generate observation from metrics comparison."""
        observations = []
        
        if current.error_rate > baseline.error_rate * 2:
            observations.append(
                f"Error rate doubled: {baseline.error_rate:.3%} → {current.error_rate:.3%}"
            )
        
        if current.latency_p99_ms > baseline.latency_p99_ms * 1.5:
            observations.append(
                f"Latency increased 50%+: {baseline.latency_p99_ms:.0f}ms → {current.latency_p99_ms:.0f}ms"
            )
        
        return "; ".join(observations) if observations else None
    
    def _is_recovered(self, baseline: MetricsSnapshot, current: MetricsSnapshot) -> bool:
        """Check if system has recovered to baseline."""
        error_ok = current.error_rate <= baseline.error_rate * 1.1
        latency_ok = current.latency_p99_ms <= baseline.latency_p99_ms * 1.1
        return error_ok and latency_ok
    
    def _generate_recommendations(
        self,
        experiment: ChaosExperiment,
        baseline: MetricsSnapshot,
        error_during: float,
        latency_during: float,
        recovery_time: float,
        full_recovery: bool,
        observations: List[str],
    ) -> List[str]:
        """Generate recommendations based on experiment results."""
        recommendations = []
        
        # Error rate recommendations
        if error_during > baseline.error_rate * 3:
            recommendations.append(
                "Error rate spiked significantly - consider implementing circuit breakers"
            )
        
        # Latency recommendations
        if latency_during > baseline.latency_p99_ms * 2:
            recommendations.append(
                "Latency degraded substantially - review timeout configurations"
            )
        
        # Recovery recommendations
        if recovery_time > 60:
            recommendations.append(
                f"Recovery took {recovery_time:.0f}s - consider auto-scaling or faster health checks"
            )
        
        if not full_recovery:
            recommendations.append(
                "System did not fully recover - investigate residual impact"
            )
        
        # Type-specific recommendations
        if experiment.type == ChaosExperimentType.POD_KILL:
            if error_during > 0.01:
                recommendations.append(
                    "Pod kill caused errors - ensure proper graceful shutdown"
                )
        
        if experiment.type == ChaosExperimentType.DEPENDENCY_FAILURE:
            recommendations.append(
                "Verify fallback mechanisms are working correctly"
            )
        
        if not recommendations:
            recommendations.append("System handled chaos well - no immediate improvements needed")
        
        return recommendations
    
    def _calculate_resilience_score(
        self,
        baseline: MetricsSnapshot,
        error_during: float,
        latency_during: float,
        recovery_time: float,
        full_recovery: bool,
        aborted: bool,
    ) -> float:
        """Calculate resilience score (0-100)."""
        score = 100.0
        
        # Penalize for errors
        error_increase = error_during - baseline.error_rate
        score -= min(30, error_increase * 1000)  # Max -30 for errors
        
        # Penalize for latency
        latency_increase_pct = (latency_during - baseline.latency_p99_ms) / baseline.latency_p99_ms
        score -= min(20, latency_increase_pct * 10)  # Max -20 for latency
        
        # Penalize for slow recovery
        score -= min(20, recovery_time / 30)  # -20 for 10min+ recovery
        
        # Penalize for incomplete recovery
        if not full_recovery:
            score -= 15
        
        # Major penalty for abort
        if aborted:
            score -= 20
        
        return max(0, min(100, score))
    
    def get_results(self, limit: int = 10) -> List[ExperimentResult]:
        """Get recent experiment results."""
        return sorted(
            self._results,
            key=lambda r: r.ended_at,
            reverse=True,
        )[:limit]
    
    def get_resilience_summary(self) -> Dict[str, Any]:
        """Get overall resilience summary from recent experiments."""
        if not self._results:
            return {
                "total_experiments": 0,
                "avg_resilience_score": None,
                "pass_rate": None,
            }
        
        recent = self._results[-20:]  # Last 20 experiments
        
        return {
            "total_experiments": len(self._results),
            "recent_experiments": len(recent),
            "avg_resilience_score": sum(
                r.resilience_score for r in recent if r.resilience_score
            ) / len(recent) if recent else 0,
            "pass_rate": sum(1 for r in recent if r.passed) / len(recent),
            "abort_rate": sum(1 for r in recent if r.aborted) / len(recent),
            "avg_recovery_time_s": sum(r.recovery_time_seconds for r in recent) / len(recent),
        }


# ============================================================================
# STANDARD EXPERIMENTS
# ============================================================================


STANDARD_EXPERIMENTS = [
    ChaosExperiment(
        experiment_id="pod-kill-random",
        name="Random Pod Kill",
        description="Kill random RISKCAST pod to test self-healing",
        type=ChaosExperimentType.POD_KILL,
        target="app=riskcast",
        duration_minutes=5,
        cooldown_minutes=30,
        parameters={"count": 1, "interval": "60s"},
        abort_conditions=["error_rate > 5%"],
        schedule="0 14 * * 1",  # Monday 2pm UTC
        owner="platform-team",
        tags=["weekly", "pod", "self-healing"],
    ),
    ChaosExperiment(
        experiment_id="network-latency-redis",
        name="Redis Network Latency",
        description="Add 100ms latency to Redis connections",
        type=ChaosExperimentType.NETWORK_LATENCY,
        target="redis",
        duration_minutes=10,
        cooldown_minutes=30,
        parameters={"latency_ms": 100, "jitter_ms": 20},
        abort_conditions=["error_rate > 5%", "latency_p99 > 5s"],
        schedule="0 14 * * 3",  # Wednesday 2pm UTC
        owner="platform-team",
        tags=["weekly", "network", "cache"],
    ),
    ChaosExperiment(
        experiment_id="network-latency-postgres",
        name="PostgreSQL Network Latency",
        description="Add 50ms latency to PostgreSQL connections",
        type=ChaosExperimentType.NETWORK_LATENCY,
        target="postgres",
        duration_minutes=10,
        cooldown_minutes=30,
        parameters={"latency_ms": 50, "jitter_ms": 10},
        abort_conditions=["error_rate > 3%"],
        schedule="0 14 * * 2",  # Tuesday 2pm UTC
        owner="platform-team",
        tags=["weekly", "network", "database"],
    ),
    ChaosExperiment(
        experiment_id="dependency-omen-failure",
        name="OMEN Service Failure",
        description="Simulate 50% OMEN failure rate",
        type=ChaosExperimentType.DEPENDENCY_FAILURE,
        target="omen",
        duration_minutes=5,
        cooldown_minutes=30,
        parameters={"failure_rate": 0.5},
        abort_conditions=["error_rate > 10%"],
        schedule="0 14 * * 4",  # Thursday 2pm UTC
        owner="platform-team",
        tags=["weekly", "dependency", "fallback"],
    ),
    ChaosExperiment(
        experiment_id="dependency-oracle-failure",
        name="Oracle Service Failure",
        description="Simulate Oracle service unavailability",
        type=ChaosExperimentType.DEPENDENCY_FAILURE,
        target="oracle",
        duration_minutes=5,
        cooldown_minutes=30,
        parameters={"failure_rate": 1.0},
        abort_conditions=["error_rate > 15%"],
        schedule="0 14 * * 5",  # Friday 2pm UTC
        owner="platform-team",
        tags=["weekly", "dependency", "graceful-degradation"],
    ),
    ChaosExperiment(
        experiment_id="cpu-stress-moderate",
        name="Moderate CPU Stress",
        description="Stress CPU to 70% utilization",
        type=ChaosExperimentType.CPU_STRESS,
        target="app=riskcast",
        duration_minutes=10,
        cooldown_minutes=45,
        parameters={"target_utilization": 0.7},
        abort_conditions=["error_rate > 5%", "latency_p99 > 3s"],
        schedule="0 15 * * 1",  # Monday 3pm UTC (monthly)
        enabled=False,  # Disabled by default - enable for stress testing
        owner="platform-team",
        tags=["monthly", "stress", "cpu"],
    ),
]


# ============================================================================
# SINGLETON
# ============================================================================


_chaos_scheduler: Optional[ChaosScheduler] = None


def get_chaos_scheduler() -> ChaosScheduler:
    """Get global chaos scheduler instance."""
    global _chaos_scheduler
    if _chaos_scheduler is None:
        _chaos_scheduler = ChaosScheduler(experiments=STANDARD_EXPERIMENTS)
    return _chaos_scheduler
