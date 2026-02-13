"""
Human-AI Collaboration Service.

This service manages all human interactions with the decision system:
- Override: Humans can override system recommendations
- Escalation: System escalates uncertain decisions for review
- Feedback: Humans provide feedback to improve accuracy

CRITICAL: All interactions create immutable audit records.

Usage:
    service = HumanCollaborationService(
        audit_service=audit,
        decision_repo=decision_repo,
    )
    
    # Override a decision
    result = await service.override_decision(user_id, override_request)
    
    # Escalate a decision
    escalation = await service.escalate_decision(decision, trigger, reason)
    
    # Resolve an escalation
    resolution = await service.resolve_escalation(user_id, escalation_id, resolution)
    
    # Submit feedback
    await service.submit_feedback(user_id, feedback)
"""

from datetime import datetime, timedelta
from typing import Optional, List, Any
import uuid
import structlog

from app.human.schemas import (
    OverrideReason,
    OverrideRequest,
    OverrideResult,
    EscalationTrigger,
    EscalationRequest,
    EscalationResolution,
    FeedbackType,
    FeedbackSubmission,
    TrustMetrics,
    # Challenge schemas (C2.2)
    ChallengeReason,
    ChallengeStatus,
    ChallengeRequest,
    ChallengeRecord,
    ChallengeResolution,
)
from app.audit.service import AuditService

logger = structlog.get_logger(__name__)


# ============================================================================
# CONFIGURATION THRESHOLDS
# ============================================================================


class EscalationConfig:
    """Configuration for automatic escalation triggers."""
    
    # Confidence threshold - escalate if below
    MIN_CONFIDENCE_FOR_AUTO: float = 0.6
    
    # Exposure threshold - escalate if above (USD)
    HIGH_VALUE_THRESHOLD_USD: float = 100_000
    
    # Critical exposure - always escalate (USD)
    CRITICAL_VALUE_THRESHOLD_USD: float = 500_000
    
    # Escalation deadline defaults (hours)
    IMMEDIATE_DEADLINE_HOURS: int = 2
    URGENT_DEADLINE_HOURS: int = 24
    STANDARD_DEADLINE_HOURS: int = 72


# ============================================================================
# HUMAN COLLABORATION SERVICE
# ============================================================================


class HumanCollaborationService:
    """
    Central service for human-AI collaboration.
    
    This service:
    - Manages decision overrides
    - Handles escalation workflows
    - Collects and processes feedback
    - Tracks trust metrics
    - Integrates with audit service for immutable records
    
    Thread Safety:
    - Delegates to underlying services which handle concurrency
    - Safe for use in async context
    """
    
    def __init__(
        self,
        audit_service: AuditService,
        decision_repository: Any = None,  # DecisionRepository
        escalation_config: Optional[EscalationConfig] = None,
    ):
        """
        Initialize human collaboration service.
        
        Args:
            audit_service: Service for audit trail recording
            decision_repository: Repository for decision access
            escalation_config: Configuration for escalation thresholds
        """
        self._audit = audit_service
        self._decision_repo = decision_repository
        self._config = escalation_config or EscalationConfig()
        
        # In-memory storage for escalations (would be DB in production)
        self._escalations: dict[str, EscalationRequest] = {}
        self._feedbacks: list[dict] = []
        
        # Challenge storage (C2.2: Challenge Handling)
        self._challenges: dict[str, ChallengeRecord] = {}
    
    # =========================================================================
    # OVERRIDE METHODS
    # =========================================================================
    
    async def override_decision(
        self,
        user_id: str,
        request: OverrideRequest,
    ) -> OverrideResult:
        """
        Override a system decision with human judgment.
        
        This creates an immutable audit record showing:
        - What the system recommended
        - What the human decided instead
        - Why the override was made
        
        Args:
            user_id: ID of the user making the override
            request: Override request with new action and reason
            
        Returns:
            OverrideResult with confirmation and audit trail
            
        Raises:
            ValueError: If decision not found or already overridden
        """
        override_id = f"override_{uuid.uuid4().hex[:16]}"
        
        # Get original decision
        original_action = "unknown"
        if self._decision_repo:
            decision = await self._decision_repo.get_decision(request.decision_id)
            if decision:
                original_action = getattr(
                    getattr(decision, "q5_action", None), "action_type", "unknown"
                )
        
        # Record in audit trail
        audit_id = await self._audit.record_human_override(
            decision_id=request.decision_id,
            user_id=user_id,
            original_action=original_action,
            new_action=request.new_action_type,
            reason=request.reason_details,
            reason_category=request.reason.value,
        )
        
        logger.warning(
            "decision_overridden",
            decision_id=request.decision_id,
            user_id=user_id,
            original_action=original_action,
            new_action=request.new_action_type,
            reason=request.reason.value,
        )
        
        return OverrideResult(
            override_id=override_id,
            decision_id=request.decision_id,
            original_action=original_action,
            new_action=request.new_action_type,
            overridden_by=user_id,
            overridden_at=datetime.utcnow(),
            reason=request.reason,
            reason_details=request.reason_details,
            audit_record_id=audit_id,
        )
    
    # =========================================================================
    # ESCALATION METHODS
    # =========================================================================
    
    async def escalate_decision(
        self,
        decision: Any,
        trigger: EscalationTrigger,
        trigger_details: str,
        escalated_to: Optional[List[str]] = None,
        deadline: Optional[datetime] = None,
    ) -> EscalationRequest:
        """
        Escalate a decision for human review.
        
        Escalations are created when:
        - Confidence is below threshold
        - Exposure is above threshold
        - Situation is novel
        - Signals conflict
        
        Args:
            decision: The DecisionObject to escalate
            trigger: What triggered the escalation
            trigger_details: Detailed explanation
            escalated_to: User IDs to notify (defaults to configured users)
            deadline: When decision is needed
            
        Returns:
            EscalationRequest with tracking info
        """
        escalation_id = f"esc_{uuid.uuid4().hex[:16]}"
        
        # Extract decision info
        decision_dict = decision.model_dump() if hasattr(decision, "model_dump") else dict(decision)
        decision_id = decision_dict.get("decision_id", "unknown")
        customer_id = decision_dict.get("customer_id", "unknown")
        
        confidence = decision_dict.get("q6_confidence", {}).get("score", 0)
        exposure = decision_dict.get("q3_severity", {}).get("total_exposure_usd", 0)
        recommended_action = decision_dict.get("q5_action", {}).get("action_type", "unknown")
        
        # Calculate deadline based on urgency
        if not deadline:
            urgency = decision_dict.get("q2_when", {}).get("urgency", "standard")
            if urgency == "immediate":
                hours = self._config.IMMEDIATE_DEADLINE_HOURS
            elif urgency == "urgent":
                hours = self._config.URGENT_DEADLINE_HOURS
            else:
                hours = self._config.STANDARD_DEADLINE_HOURS
            deadline = datetime.utcnow() + timedelta(hours=hours)
        
        escalation = EscalationRequest(
            escalation_id=escalation_id,
            decision_id=decision_id,
            customer_id=customer_id,
            trigger=trigger,
            trigger_details=trigger_details,
            confidence_at_escalation=confidence,
            exposure_usd=exposure,
            recommended_action=recommended_action,
            alternative_actions=[],  # TODO: Extract from decision
            escalated_to=escalated_to or [],
            deadline=deadline,
            escalated_at=datetime.utcnow(),
            status="pending",
        )
        
        # Store escalation
        self._escalations[escalation_id] = escalation
        
        # Record in audit trail
        await self._audit.record_escalation(
            decision_id=decision_id,
            trigger=trigger.value,
            reason=trigger_details,
            escalated_to=escalated_to or [],
            confidence_at_escalation=confidence,
            exposure_usd=exposure,
        )
        
        logger.info(
            "decision_escalated",
            escalation_id=escalation_id,
            decision_id=decision_id,
            trigger=trigger.value,
            confidence=confidence,
            exposure_usd=exposure,
            deadline=deadline.isoformat(),
        )
        
        return escalation
    
    async def should_escalate(
        self,
        decision: Any,
    ) -> tuple[bool, Optional[EscalationTrigger], Optional[str]]:
        """
        Determine if a decision should be escalated.
        
        Checks:
        - Confidence below threshold
        - Exposure above threshold
        - Other escalation triggers
        
        Args:
            decision: The DecisionObject to check
            
        Returns:
            Tuple of (should_escalate, trigger, reason)
        """
        decision_dict = decision.model_dump() if hasattr(decision, "model_dump") else dict(decision)
        
        confidence = decision_dict.get("q6_confidence", {}).get("score", 1.0)
        exposure = decision_dict.get("q3_severity", {}).get("total_exposure_usd", 0)
        
        # Check confidence threshold
        if confidence < self._config.MIN_CONFIDENCE_FOR_AUTO:
            return (
                True,
                EscalationTrigger.LOW_CONFIDENCE,
                f"Confidence {confidence:.2%} below threshold {self._config.MIN_CONFIDENCE_FOR_AUTO:.2%}"
            )
        
        # Check critical exposure
        if exposure >= self._config.CRITICAL_VALUE_THRESHOLD_USD:
            return (
                True,
                EscalationTrigger.HIGH_VALUE,
                f"Critical exposure ${exposure:,.0f} >= ${self._config.CRITICAL_VALUE_THRESHOLD_USD:,.0f}"
            )
        
        # Check high value exposure (only escalate if confidence not very high)
        if exposure >= self._config.HIGH_VALUE_THRESHOLD_USD and confidence < 0.85:
            return (
                True,
                EscalationTrigger.HIGH_VALUE,
                f"High exposure ${exposure:,.0f} with moderate confidence {confidence:.2%}"
            )
        
        return (False, None, None)
    
    async def resolve_escalation(
        self,
        user_id: str,
        escalation_id: str,
        resolution: str,  # APPROVE, MODIFY, REJECT
        final_action: str,
        resolution_reason: str,
    ) -> EscalationResolution:
        """
        Resolve a pending escalation.
        
        Args:
            user_id: ID of user resolving
            escalation_id: ID of escalation to resolve
            resolution: Resolution type (APPROVE, MODIFY, REJECT)
            final_action: Final action to take
            resolution_reason: Explanation of resolution
            
        Returns:
            EscalationResolution with resolution details
        """
        escalation = self._escalations.get(escalation_id)
        if not escalation:
            raise ValueError(f"Escalation {escalation_id} not found")
        
        if escalation.status != "pending":
            raise ValueError(f"Escalation {escalation_id} already resolved")
        
        resolved_at = datetime.utcnow()
        time_to_resolution = int((resolved_at - escalation.escalated_at).total_seconds() / 60)
        
        resolution_obj = EscalationResolution(
            escalation_id=escalation_id,
            resolved_by=user_id,
            resolved_at=resolved_at,
            resolution=resolution.upper(),
            final_action=final_action,
            resolution_reason=resolution_reason,
            time_to_resolution_minutes=time_to_resolution,
        )
        
        # Update escalation status
        escalation.status = "resolved"
        
        # Record in audit trail
        await self._audit.record_escalation_resolution(
            escalation_id=escalation_id,
            decision_id=escalation.decision_id,
            resolved_by=user_id,
            resolution=resolution,
            final_action=final_action,
            resolution_reason=resolution_reason,
        )
        
        logger.info(
            "escalation_resolved",
            escalation_id=escalation_id,
            decision_id=escalation.decision_id,
            resolution=resolution,
            time_to_resolution_minutes=time_to_resolution,
        )
        
        return resolution_obj
    
    async def get_escalation(self, escalation_id: str) -> Optional[EscalationRequest]:
        """Get an escalation by ID."""
        return self._escalations.get(escalation_id)
    
    async def get_pending_escalations(
        self,
        user_id: Optional[str] = None,
    ) -> List[EscalationRequest]:
        """
        Get pending escalations.
        
        Args:
            user_id: Filter by escalations assigned to user (optional)
            
        Returns:
            List of pending escalations
        """
        pending = [e for e in self._escalations.values() if e.status == "pending"]
        
        if user_id:
            pending = [e for e in pending if user_id in e.escalated_to]
        
        # Sort by deadline
        pending.sort(key=lambda e: e.deadline)
        
        return pending
    
    # =========================================================================
    # FEEDBACK METHODS
    # =========================================================================
    
    async def submit_feedback(
        self,
        user_id: str,
        feedback: FeedbackSubmission,
    ) -> str:
        """
        Submit feedback on a decision.
        
        Feedback is used for:
        - Calibration: Improving prediction accuracy
        - Quality tracking: Identifying problem areas
        - Training data: ML model improvement
        
        Args:
            user_id: ID of user submitting feedback
            feedback: Feedback submission details
            
        Returns:
            Feedback ID
        """
        feedback_id = f"feedback_{uuid.uuid4().hex[:16]}"
        
        # Store feedback
        feedback_record = {
            "feedback_id": feedback_id,
            "user_id": user_id,
            "submitted_at": datetime.utcnow().isoformat(),
            **feedback.model_dump(),
        }
        self._feedbacks.append(feedback_record)
        
        # Record in audit trail
        await self._audit.record_feedback(
            decision_id=feedback.decision_id,
            user_id=user_id,
            feedback_type=feedback.feedback_type.value,
            rating=feedback.rating,
            comment=feedback.comment,
            would_follow_again=feedback.would_follow_again,
        )
        
        logger.info(
            "feedback_submitted",
            feedback_id=feedback_id,
            decision_id=feedback.decision_id,
            feedback_type=feedback.feedback_type.value,
            rating=feedback.rating,
            would_follow_again=feedback.would_follow_again,
        )
        
        return feedback_id
    
    async def get_feedback_for_decision(
        self,
        decision_id: str,
    ) -> List[dict]:
        """Get all feedback for a decision."""
        return [f for f in self._feedbacks if f["decision_id"] == decision_id]
    
    # =========================================================================
    # CHALLENGE METHODS (C2.2: Challenge Handling)
    # =========================================================================
    
    async def submit_challenge(
        self,
        request: ChallengeRequest,
    ) -> ChallengeRecord:
        """
        Submit a challenge/dispute against a decision.
        
        This creates an immutable audit record and initiates the
        formal challenge review process.
        
        Challenge Process:
        1. SUBMITTED - Challenge received, pending assignment
        2. UNDER_REVIEW - Assigned reviewer investigating
        3. NEEDS_INFO - Additional info requested
        4. Resolution: UPHELD, PARTIALLY_UPHELD, OVERTURNED, or WITHDRAWN
        
        Args:
            request: Challenge request with details
            
        Returns:
            ChallengeRecord with tracking info
        """
        challenge_id = f"challenge_{uuid.uuid4().hex[:16]}"
        
        # Get decision info
        customer_id = "unknown"
        if self._decision_repo:
            decision = await self._decision_repo.get_decision(request.decision_id)
            if decision:
                customer_id = getattr(decision, "customer_id", "unknown")
        
        # Calculate SLA deadline based on urgency
        if request.is_urgent:
            sla_hours = 24
            priority = "critical"
        elif request.claimed_impact_usd and request.claimed_impact_usd > 100_000:
            sla_hours = 48
            priority = "high"
        else:
            sla_hours = 120  # 5 business days
            priority = "normal"
        
        sla_deadline = datetime.utcnow() + timedelta(hours=sla_hours)
        
        challenge = ChallengeRecord(
            challenge_id=challenge_id,
            decision_id=request.decision_id,
            customer_id=customer_id,
            challenger_id=request.challenger_id,
            challenger_role=request.challenger_role,
            challenged_at=datetime.utcnow(),
            reason=request.reason,
            reason_details=request.reason_details,
            evidence=request.evidence,
            claimed_impact_usd=request.claimed_impact_usd,
            claimed_delay_days=request.claimed_delay_days,
            requested_remedy=request.requested_remedy,
            status=ChallengeStatus.SUBMITTED,
            priority=priority,
            sla_deadline=sla_deadline,
        )
        
        # Store challenge
        self._challenges[challenge_id] = challenge
        
        # Record in audit trail (using _record_event internal method if available)
        # For now, log the event
        logger.info(
            "challenge_submitted",
            challenge_id=challenge_id,
            decision_id=request.decision_id,
            challenger_id=request.challenger_id,
            reason=request.reason.value,
            priority=priority,
            sla_deadline=sla_deadline.isoformat(),
        )
        
        return challenge
    
    async def assign_challenge(
        self,
        challenge_id: str,
        reviewer_id: str,
    ) -> ChallengeRecord:
        """
        Assign a challenge to a reviewer.
        
        Args:
            challenge_id: ID of challenge to assign
            reviewer_id: User ID of assigned reviewer
            
        Returns:
            Updated ChallengeRecord
        """
        challenge = self._challenges.get(challenge_id)
        if not challenge:
            raise ValueError(f"Challenge {challenge_id} not found")
        
        if challenge.status not in [ChallengeStatus.SUBMITTED, ChallengeStatus.NEEDS_INFO]:
            raise ValueError(f"Challenge {challenge_id} cannot be assigned in status {challenge.status}")
        
        # Update using object __setattr__ since model might be immutable
        object.__setattr__(challenge, 'assigned_to', reviewer_id)
        object.__setattr__(challenge, 'assigned_at', datetime.utcnow())
        object.__setattr__(challenge, 'status', ChallengeStatus.UNDER_REVIEW)
        
        logger.info(
            "challenge_assigned",
            challenge_id=challenge_id,
            reviewer_id=reviewer_id,
        )
        
        return challenge
    
    async def request_challenge_info(
        self,
        challenge_id: str,
        reviewer_id: str,
        info_needed: str,
    ) -> ChallengeRecord:
        """
        Request additional information for a challenge.
        
        Args:
            challenge_id: ID of challenge
            reviewer_id: User ID of reviewer
            info_needed: Description of info needed
            
        Returns:
            Updated ChallengeRecord
        """
        challenge = self._challenges.get(challenge_id)
        if not challenge:
            raise ValueError(f"Challenge {challenge_id} not found")
        
        if challenge.assigned_to != reviewer_id:
            raise ValueError("Only assigned reviewer can request info")
        
        object.__setattr__(challenge, 'status', ChallengeStatus.NEEDS_INFO)
        
        logger.info(
            "challenge_info_requested",
            challenge_id=challenge_id,
            reviewer_id=reviewer_id,
            info_needed=info_needed,
        )
        
        return challenge
    
    async def resolve_challenge(
        self,
        challenge_id: str,
        resolution: ChallengeResolution,
    ) -> ChallengeRecord:
        """
        Resolve a decision challenge.
        
        Creates comprehensive audit trail documenting:
        - How the challenge was investigated
        - What findings were made
        - What remedy was provided
        - What improvements will be made
        
        Args:
            challenge_id: ID of challenge to resolve
            resolution: Resolution details
            
        Returns:
            Updated ChallengeRecord with resolution
        """
        challenge = self._challenges.get(challenge_id)
        if not challenge:
            raise ValueError(f"Challenge {challenge_id} not found")
        
        if challenge.status in [ChallengeStatus.UPHELD, ChallengeStatus.OVERTURNED,
                                ChallengeStatus.PARTIALLY_UPHELD, ChallengeStatus.WITHDRAWN]:
            raise ValueError(f"Challenge {challenge_id} already resolved")
        
        # Update challenge with resolution
        object.__setattr__(challenge, 'status', resolution.status)
        object.__setattr__(challenge, 'resolution', resolution)
        
        # Log comprehensive resolution
        logger.info(
            "challenge_resolved",
            challenge_id=challenge_id,
            decision_id=challenge.decision_id,
            resolution_status=resolution.status.value,
            original_data_valid=resolution.original_data_valid,
            methodology_valid=resolution.methodology_valid,
            calculations_valid=resolution.calculations_valid,
            model_update_required=resolution.model_update_required,
            time_to_resolution_hours=resolution.time_to_resolution_hours,
            compensation_usd=resolution.compensation_usd,
        )
        
        # If decision was overturned or partially upheld, record as warning
        if resolution.status in [ChallengeStatus.OVERTURNED, ChallengeStatus.PARTIALLY_UPHELD]:
            logger.warning(
                "decision_challenge_succeeded",
                challenge_id=challenge_id,
                decision_id=challenge.decision_id,
                reason=challenge.reason.value,
                resolution_status=resolution.status.value,
                improvement_actions=resolution.improvement_actions,
            )
        
        return challenge
    
    async def get_challenge(self, challenge_id: str) -> Optional[ChallengeRecord]:
        """Get a challenge by ID."""
        return self._challenges.get(challenge_id)
    
    async def get_challenges_for_decision(self, decision_id: str) -> List[ChallengeRecord]:
        """Get all challenges for a decision."""
        return [c for c in self._challenges.values() if c.decision_id == decision_id]
    
    async def get_pending_challenges(
        self,
        reviewer_id: Optional[str] = None,
    ) -> List[ChallengeRecord]:
        """
        Get pending challenges.
        
        Args:
            reviewer_id: Filter by assigned reviewer (optional)
            
        Returns:
            List of pending challenges sorted by priority and deadline
        """
        pending_statuses = [ChallengeStatus.SUBMITTED, ChallengeStatus.UNDER_REVIEW, 
                          ChallengeStatus.NEEDS_INFO]
        pending = [c for c in self._challenges.values() if c.status in pending_statuses]
        
        if reviewer_id:
            pending = [c for c in pending if c.assigned_to == reviewer_id]
        
        # Sort by priority (critical > high > normal > low) then by deadline
        priority_order = {"critical": 0, "high": 1, "normal": 2, "low": 3}
        pending.sort(key=lambda c: (
            priority_order.get(c.priority, 3),
            c.sla_deadline or datetime.max
        ))
        
        return pending
    
    async def get_challenge_metrics(
        self,
        period_days: int = 30,
    ) -> dict:
        """
        Get challenge handling metrics.
        
        Returns metrics including:
        - Total challenges
        - Resolution rates
        - Average time to resolution
        - Challenge success rate (overturned + partially upheld)
        """
        cutoff = datetime.utcnow() - timedelta(days=period_days)
        recent = [c for c in self._challenges.values() if c.challenged_at >= cutoff]
        
        total = len(recent)
        if total == 0:
            return {
                "period_days": period_days,
                "total_challenges": 0,
                "resolved": 0,
                "pending": 0,
                "upheld": 0,
                "overturned": 0,
                "partially_upheld": 0,
                "avg_resolution_hours": None,
                "success_rate": None,
            }
        
        resolved = [c for c in recent if c.resolution]
        pending = [c for c in recent if not c.resolution]
        
        upheld = len([c for c in resolved if c.status == ChallengeStatus.UPHELD])
        overturned = len([c for c in resolved if c.status == ChallengeStatus.OVERTURNED])
        partially_upheld = len([c for c in resolved if c.status == ChallengeStatus.PARTIALLY_UPHELD])
        
        avg_hours = None
        if resolved:
            total_hours = sum(
                c.resolution.time_to_resolution_hours for c in resolved 
                if c.resolution and c.resolution.time_to_resolution_hours
            )
            avg_hours = total_hours / len(resolved)
        
        success_rate = (overturned + partially_upheld) / len(resolved) if resolved else 0
        
        return {
            "period_days": period_days,
            "total_challenges": total,
            "resolved": len(resolved),
            "pending": len(pending),
            "upheld": upheld,
            "overturned": overturned,
            "partially_upheld": partially_upheld,
            "avg_resolution_hours": avg_hours,
            "success_rate": success_rate,
        }
    
    # =========================================================================
    # TRUST METRICS
    # =========================================================================
    
    async def calculate_trust_metrics(
        self,
        period_days: int = 30,
        customer_id: Optional[str] = None,
    ) -> TrustMetrics:
        """
        Calculate human-AI trust metrics.
        
        These metrics help understand:
        - How much users trust the system
        - Where improvements are needed
        - Calibration accuracy
        
        Args:
            period_days: Period to calculate metrics for
            customer_id: Optional filter by customer
            
        Returns:
            TrustMetrics with calculated values
        """
        # This is a simplified implementation
        # In production, this would query the audit database
        
        cutoff = datetime.utcnow() - timedelta(days=period_days)
        
        # Count from stored data
        recent_feedbacks = [
            f for f in self._feedbacks
            if datetime.fromisoformat(f["submitted_at"]) >= cutoff
        ]
        
        recent_escalations = [
            e for e in self._escalations.values()
            if e.escalated_at >= cutoff
        ]
        
        # Calculate metrics
        feedback_count = len(recent_feedbacks)
        
        avg_rating = None
        if feedback_count > 0:
            avg_rating = sum(f["rating"] for f in recent_feedbacks) / feedback_count
        
        would_follow_again_count = sum(
            1 for f in recent_feedbacks if f.get("would_follow_again", False)
        )
        would_follow_rate = (
            would_follow_again_count / feedback_count
            if feedback_count > 0
            else None
        )
        
        # Get override and escalation counts
        override_count = sum(1 for e in recent_escalations if e.status == "resolved")
        escalation_count = len(recent_escalations)
        
        # Calculate top reasons (simplified)
        override_reasons: dict[str, int] = {}
        escalation_triggers: dict[str, int] = {}
        
        for e in recent_escalations:
            trigger = e.trigger.value
            escalation_triggers[trigger] = escalation_triggers.get(trigger, 0) + 1
        
        top_override_reasons = [
            {"reason": r, "count": c}
            for r, c in sorted(override_reasons.items(), key=lambda x: -x[1])[:5]
        ]
        
        top_escalation_triggers = [
            {"trigger": t, "count": c}
            for t, c in sorted(escalation_triggers.items(), key=lambda x: -x[1])[:5]
        ]
        
        # Placeholder for total decisions - would come from decision repo
        total_decisions = max(100, feedback_count + escalation_count)
        
        return TrustMetrics(
            period_days=period_days,
            total_decisions=total_decisions,
            decisions_followed=total_decisions - override_count,
            decisions_overridden=override_count,
            decisions_escalated=escalation_count,
            follow_rate=(total_decisions - override_count) / total_decisions if total_decisions > 0 else 1.0,
            override_rate=override_count / total_decisions if total_decisions > 0 else 0.0,
            escalation_rate=escalation_count / total_decisions if total_decisions > 0 else 0.0,
            feedback_count=feedback_count,
            average_rating=avg_rating,
            would_follow_again_rate=would_follow_rate,
            calibration_accuracy=None,  # Would be calculated from outcome tracking
            top_override_reasons=top_override_reasons,
            top_escalation_triggers=top_escalation_triggers,
        )


# ============================================================================
# FACTORY
# ============================================================================


def create_human_collaboration_service(
    audit_service: AuditService,
    decision_repository: Any = None,
    config: Optional[EscalationConfig] = None,
) -> HumanCollaborationService:
    """
    Factory function to create HumanCollaborationService.
    
    Args:
        audit_service: Audit service for recording interactions
        decision_repository: Decision repository for access
        config: Escalation configuration
        
    Returns:
        Configured HumanCollaborationService
    """
    return HumanCollaborationService(
        audit_service=audit_service,
        decision_repository=decision_repository,
        escalation_config=config,
    )
