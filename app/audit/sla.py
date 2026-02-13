"""
SLA enforcement for human-AI challenge response times.

This module implements GAP C2.1: SLA enforcement missing for human-AI challenges.
Tracks and enforces response time requirements for human review requests.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import asyncio
import structlog

logger = structlog.get_logger(__name__)


class ChallengePriority(str, Enum):
    """Priority levels for challenges."""
    CRITICAL = "critical"  # Must respond immediately
    HIGH = "high"          # Must respond within 1 hour
    MEDIUM = "medium"      # Must respond within 4 hours
    LOW = "low"            # Must respond within 24 hours


class ChallengeStatus(str, Enum):
    """Status of a challenge."""
    PENDING = "pending"          # Awaiting response
    IN_PROGRESS = "in_progress"  # Being reviewed
    RESOLVED = "resolved"        # Completed
    ESCALATED = "escalated"      # Escalated due to SLA breach
    EXPIRED = "expired"          # SLA breached, auto-resolved


class EscalationLevel(str, Enum):
    """Escalation levels."""
    NONE = "none"
    L1 = "l1"        # First escalation
    L2 = "l2"        # Second escalation
    L3 = "l3"        # Management escalation
    EXECUTIVE = "executive"  # Executive escalation


@dataclass
class SLAConfig:
    """SLA configuration for a priority level."""
    priority: ChallengePriority
    response_time_minutes: int
    resolution_time_minutes: int
    escalation_thresholds: List[int]  # Minutes until each escalation
    auto_resolve_on_expire: bool = False
    default_resolution: Optional[str] = None
    
    def is_response_breached(self, elapsed_minutes: float) -> bool:
        """Check if response SLA is breached."""
        return elapsed_minutes > self.response_time_minutes
    
    def is_resolution_breached(self, elapsed_minutes: float) -> bool:
        """Check if resolution SLA is breached."""
        return elapsed_minutes > self.resolution_time_minutes
    
    def get_escalation_level(self, elapsed_minutes: float) -> EscalationLevel:
        """Get escalation level based on elapsed time."""
        levels = [EscalationLevel.L1, EscalationLevel.L2, EscalationLevel.L3, EscalationLevel.EXECUTIVE]
        
        for i, threshold in enumerate(self.escalation_thresholds):
            if elapsed_minutes < threshold:
                return levels[i - 1] if i > 0 else EscalationLevel.NONE
        
        if len(self.escalation_thresholds) > 0:
            return levels[min(len(self.escalation_thresholds), len(levels)) - 1]
        return EscalationLevel.NONE


@dataclass
class Challenge:
    """A human-AI challenge requiring review."""
    challenge_id: str
    created_at: datetime
    priority: ChallengePriority
    
    # Context
    decision_id: str
    signal_id: Optional[str] = None
    reason: str = ""
    ai_recommendation: str = ""
    
    # Status
    status: ChallengeStatus = ChallengeStatus.PENDING
    escalation_level: EscalationLevel = EscalationLevel.NONE
    
    # Assignment
    assigned_to: Optional[str] = None
    assigned_at: Optional[datetime] = None
    
    # Response
    responded_at: Optional[datetime] = None
    response_by: Optional[str] = None
    response: Optional[str] = None
    
    # Resolution
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution: Optional[str] = None
    human_override: bool = False
    
    # Escalation history
    escalation_history: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def elapsed_minutes(self) -> float:
        """Get minutes since creation."""
        end_time = self.resolved_at or datetime.utcnow()
        return (end_time - self.created_at).total_seconds() / 60
    
    @property
    def response_time_minutes(self) -> Optional[float]:
        """Get response time in minutes."""
        if self.responded_at:
            return (self.responded_at - self.created_at).total_seconds() / 60
        return None
    
    @property
    def resolution_time_minutes(self) -> Optional[float]:
        """Get resolution time in minutes."""
        if self.resolved_at:
            return (self.resolved_at - self.created_at).total_seconds() / 60
        return None


@dataclass
class SLAMetrics:
    """SLA performance metrics."""
    period_start: datetime
    period_end: datetime
    
    # Volume
    total_challenges: int = 0
    challenges_by_priority: Dict[str, int] = field(default_factory=dict)
    
    # Response SLA
    response_sla_met: int = 0
    response_sla_breached: int = 0
    avg_response_time_minutes: float = 0.0
    p95_response_time_minutes: float = 0.0
    
    # Resolution SLA
    resolution_sla_met: int = 0
    resolution_sla_breached: int = 0
    avg_resolution_time_minutes: float = 0.0
    p95_resolution_time_minutes: float = 0.0
    
    # Escalations
    total_escalations: int = 0
    escalations_by_level: Dict[str, int] = field(default_factory=dict)
    
    # Auto-resolutions
    auto_resolved: int = 0
    human_overrides: int = 0
    
    @property
    def response_sla_compliance_pct(self) -> float:
        """Get response SLA compliance percentage."""
        total = self.response_sla_met + self.response_sla_breached
        if total == 0:
            return 100.0
        return (self.response_sla_met / total) * 100
    
    @property
    def resolution_sla_compliance_pct(self) -> float:
        """Get resolution SLA compliance percentage."""
        total = self.resolution_sla_met + self.resolution_sla_breached
        if total == 0:
            return 100.0
        return (self.resolution_sla_met / total) * 100


class SLAEnforcer:
    """
    Enforces SLAs for human-AI challenges.
    
    Tracks response times, triggers escalations, and auto-resolves
    when SLAs are breached.
    """
    
    # Default SLA configurations
    DEFAULT_SLAS = {
        ChallengePriority.CRITICAL: SLAConfig(
            priority=ChallengePriority.CRITICAL,
            response_time_minutes=15,
            resolution_time_minutes=60,
            escalation_thresholds=[10, 30, 45, 55],
            auto_resolve_on_expire=True,
            default_resolution="auto_approved_critical_timeout",
        ),
        ChallengePriority.HIGH: SLAConfig(
            priority=ChallengePriority.HIGH,
            response_time_minutes=60,
            resolution_time_minutes=240,
            escalation_thresholds=[30, 90, 180, 220],
            auto_resolve_on_expire=True,
            default_resolution="auto_approved_high_timeout",
        ),
        ChallengePriority.MEDIUM: SLAConfig(
            priority=ChallengePriority.MEDIUM,
            response_time_minutes=240,
            resolution_time_minutes=480,
            escalation_thresholds=[120, 300, 420, 460],
            auto_resolve_on_expire=False,
        ),
        ChallengePriority.LOW: SLAConfig(
            priority=ChallengePriority.LOW,
            response_time_minutes=1440,  # 24 hours
            resolution_time_minutes=2880,  # 48 hours
            escalation_thresholds=[720, 1440, 2160, 2700],
            auto_resolve_on_expire=False,
        ),
    }
    
    def __init__(
        self,
        sla_configs: Optional[Dict[ChallengePriority, SLAConfig]] = None,
        notification_service: Optional[Any] = None,
    ):
        self._slas = sla_configs or self.DEFAULT_SLAS
        self._notifier = notification_service
        self._challenges: Dict[str, Challenge] = {}
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self._on_escalate: Optional[Callable] = None
        self._on_breach: Optional[Callable] = None
        self._on_resolve: Optional[Callable] = None
    
    def set_callbacks(
        self,
        on_escalate: Optional[Callable] = None,
        on_breach: Optional[Callable] = None,
        on_resolve: Optional[Callable] = None,
    ) -> None:
        """Set event callbacks."""
        self._on_escalate = on_escalate
        self._on_breach = on_breach
        self._on_resolve = on_resolve
    
    async def start_monitoring(self) -> None:
        """Start the SLA monitoring loop."""
        if self._running:
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("sla_monitoring_started")
    
    async def stop_monitoring(self) -> None:
        """Stop the SLA monitoring loop."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("sla_monitoring_stopped")
    
    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                await self._check_all_challenges()
            except Exception as e:
                logger.error("sla_monitor_error", error=str(e))
            
            await asyncio.sleep(60)  # Check every minute
    
    async def _check_all_challenges(self) -> None:
        """Check all pending challenges for SLA compliance."""
        for challenge in list(self._challenges.values()):
            if challenge.status not in [
                ChallengeStatus.PENDING,
                ChallengeStatus.IN_PROGRESS,
            ]:
                continue
            
            await self._check_challenge(challenge)
    
    async def _check_challenge(self, challenge: Challenge) -> None:
        """Check a single challenge for SLA compliance."""
        sla = self._slas.get(challenge.priority)
        if not sla:
            return
        
        elapsed = challenge.elapsed_minutes
        
        # Check for escalation
        new_level = sla.get_escalation_level(elapsed)
        if new_level != challenge.escalation_level and new_level != EscalationLevel.NONE:
            await self._escalate(challenge, new_level)
        
        # Check for response SLA breach
        if (
            challenge.responded_at is None
            and sla.is_response_breached(elapsed)
        ):
            await self._handle_response_breach(challenge, sla)
        
        # Check for resolution SLA breach
        if sla.is_resolution_breached(elapsed):
            await self._handle_resolution_breach(challenge, sla)
    
    async def _escalate(
        self,
        challenge: Challenge,
        new_level: EscalationLevel,
    ) -> None:
        """Escalate a challenge."""
        old_level = challenge.escalation_level
        challenge.escalation_level = new_level
        challenge.escalation_history.append({
            "from_level": old_level.value,
            "to_level": new_level.value,
            "timestamp": datetime.utcnow().isoformat(),
            "elapsed_minutes": challenge.elapsed_minutes,
        })
        
        logger.warning(
            "challenge_escalated",
            challenge_id=challenge.challenge_id,
            from_level=old_level.value,
            to_level=new_level.value,
            elapsed_minutes=challenge.elapsed_minutes,
        )
        
        # Notify
        if self._notifier:
            await self._notifier.send_escalation(
                challenge_id=challenge.challenge_id,
                level=new_level,
                priority=challenge.priority,
            )
        
        if self._on_escalate:
            await self._on_escalate(challenge, old_level, new_level)
    
    async def _handle_response_breach(
        self,
        challenge: Challenge,
        sla: SLAConfig,
    ) -> None:
        """Handle response SLA breach."""
        logger.warning(
            "response_sla_breached",
            challenge_id=challenge.challenge_id,
            priority=challenge.priority.value,
            elapsed_minutes=challenge.elapsed_minutes,
            sla_minutes=sla.response_time_minutes,
        )
        
        if self._on_breach:
            await self._on_breach(challenge, "response")
    
    async def _handle_resolution_breach(
        self,
        challenge: Challenge,
        sla: SLAConfig,
    ) -> None:
        """Handle resolution SLA breach."""
        logger.warning(
            "resolution_sla_breached",
            challenge_id=challenge.challenge_id,
            priority=challenge.priority.value,
            elapsed_minutes=challenge.elapsed_minutes,
            sla_minutes=sla.resolution_time_minutes,
        )
        
        # Auto-resolve if configured
        if sla.auto_resolve_on_expire and challenge.status != ChallengeStatus.EXPIRED:
            await self._auto_resolve(challenge, sla)
        
        if self._on_breach:
            await self._on_breach(challenge, "resolution")
    
    async def _auto_resolve(
        self,
        challenge: Challenge,
        sla: SLAConfig,
    ) -> None:
        """Auto-resolve a challenge due to SLA breach."""
        challenge.status = ChallengeStatus.EXPIRED
        challenge.resolved_at = datetime.utcnow()
        challenge.resolved_by = "system_auto_resolve"
        challenge.resolution = sla.default_resolution or "auto_resolved_sla_breach"
        
        logger.info(
            "challenge_auto_resolved",
            challenge_id=challenge.challenge_id,
            resolution=challenge.resolution,
            elapsed_minutes=challenge.elapsed_minutes,
        )
        
        if self._on_resolve:
            await self._on_resolve(challenge)
    
    def create_challenge(
        self,
        decision_id: str,
        priority: ChallengePriority,
        reason: str,
        ai_recommendation: str,
        signal_id: Optional[str] = None,
    ) -> Challenge:
        """Create a new challenge."""
        import uuid
        
        challenge = Challenge(
            challenge_id=f"chl_{uuid.uuid4().hex[:16]}",
            created_at=datetime.utcnow(),
            priority=priority,
            decision_id=decision_id,
            signal_id=signal_id,
            reason=reason,
            ai_recommendation=ai_recommendation,
        )
        
        self._challenges[challenge.challenge_id] = challenge
        
        logger.info(
            "challenge_created",
            challenge_id=challenge.challenge_id,
            priority=priority.value,
            decision_id=decision_id,
        )
        
        return challenge
    
    async def respond_to_challenge(
        self,
        challenge_id: str,
        responder: str,
        response: str,
    ) -> Challenge:
        """Record a response to a challenge."""
        challenge = self._challenges.get(challenge_id)
        if not challenge:
            raise ValueError(f"Challenge {challenge_id} not found")
        
        challenge.responded_at = datetime.utcnow()
        challenge.response_by = responder
        challenge.response = response
        challenge.status = ChallengeStatus.IN_PROGRESS
        
        sla = self._slas.get(challenge.priority)
        response_time = challenge.response_time_minutes
        
        if sla and response_time:
            sla_met = response_time <= sla.response_time_minutes
            logger.info(
                "challenge_responded",
                challenge_id=challenge_id,
                response_time_minutes=response_time,
                sla_met=sla_met,
            )
        
        return challenge
    
    async def resolve_challenge(
        self,
        challenge_id: str,
        resolver: str,
        resolution: str,
        human_override: bool = False,
    ) -> Challenge:
        """Resolve a challenge."""
        challenge = self._challenges.get(challenge_id)
        if not challenge:
            raise ValueError(f"Challenge {challenge_id} not found")
        
        challenge.resolved_at = datetime.utcnow()
        challenge.resolved_by = resolver
        challenge.resolution = resolution
        challenge.human_override = human_override
        challenge.status = ChallengeStatus.RESOLVED
        
        sla = self._slas.get(challenge.priority)
        resolution_time = challenge.resolution_time_minutes
        
        if sla and resolution_time:
            sla_met = resolution_time <= sla.resolution_time_minutes
            logger.info(
                "challenge_resolved",
                challenge_id=challenge_id,
                resolution_time_minutes=resolution_time,
                sla_met=sla_met,
                human_override=human_override,
            )
        
        if self._on_resolve:
            await self._on_resolve(challenge)
        
        return challenge
    
    def get_challenge(self, challenge_id: str) -> Optional[Challenge]:
        """Get a challenge by ID."""
        return self._challenges.get(challenge_id)
    
    def get_pending_challenges(
        self,
        priority: Optional[ChallengePriority] = None,
    ) -> List[Challenge]:
        """Get all pending challenges."""
        pending = [
            c for c in self._challenges.values()
            if c.status in [ChallengeStatus.PENDING, ChallengeStatus.IN_PROGRESS]
        ]
        
        if priority:
            pending = [c for c in pending if c.priority == priority]
        
        return sorted(pending, key=lambda c: c.created_at)
    
    def calculate_metrics(
        self,
        period_days: int = 30,
    ) -> SLAMetrics:
        """Calculate SLA metrics for a period."""
        now = datetime.utcnow()
        period_start = now - timedelta(days=period_days)
        
        metrics = SLAMetrics(
            period_start=period_start,
            period_end=now,
        )
        
        # Filter challenges in period
        period_challenges = [
            c for c in self._challenges.values()
            if c.created_at >= period_start
        ]
        
        metrics.total_challenges = len(period_challenges)
        
        response_times = []
        resolution_times = []
        
        for challenge in period_challenges:
            # Count by priority
            priority = challenge.priority.value
            metrics.challenges_by_priority[priority] = (
                metrics.challenges_by_priority.get(priority, 0) + 1
            )
            
            sla = self._slas.get(challenge.priority)
            if not sla:
                continue
            
            # Response SLA
            if challenge.response_time_minutes is not None:
                response_times.append(challenge.response_time_minutes)
                if challenge.response_time_minutes <= sla.response_time_minutes:
                    metrics.response_sla_met += 1
                else:
                    metrics.response_sla_breached += 1
            
            # Resolution SLA
            if challenge.resolution_time_minutes is not None:
                resolution_times.append(challenge.resolution_time_minutes)
                if challenge.resolution_time_minutes <= sla.resolution_time_minutes:
                    metrics.resolution_sla_met += 1
                else:
                    metrics.resolution_sla_breached += 1
            
            # Escalations
            metrics.total_escalations += len(challenge.escalation_history)
            for esc in challenge.escalation_history:
                level = esc.get("to_level", "unknown")
                metrics.escalations_by_level[level] = (
                    metrics.escalations_by_level.get(level, 0) + 1
                )
            
            # Auto-resolutions
            if challenge.status == ChallengeStatus.EXPIRED:
                metrics.auto_resolved += 1
            if challenge.human_override:
                metrics.human_overrides += 1
        
        # Calculate averages
        if response_times:
            metrics.avg_response_time_minutes = sum(response_times) / len(response_times)
            sorted_response = sorted(response_times)
            p95_idx = int(len(sorted_response) * 0.95)
            metrics.p95_response_time_minutes = sorted_response[min(p95_idx, len(sorted_response) - 1)]
        
        if resolution_times:
            metrics.avg_resolution_time_minutes = sum(resolution_times) / len(resolution_times)
            sorted_resolution = sorted(resolution_times)
            p95_idx = int(len(sorted_resolution) * 0.95)
            metrics.p95_resolution_time_minutes = sorted_resolution[min(p95_idx, len(sorted_resolution) - 1)]
        
        return metrics
    
    @property
    def is_monitoring(self) -> bool:
        """Check if SLA monitoring is active."""
        return self._running
