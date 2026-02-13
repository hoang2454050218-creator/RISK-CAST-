"""
Feedback Service for RISKCAST.

Central service for collecting, processing, and managing feedback.

Responsibilities:
1. Record customer feedback on decisions
2. Record actual outcomes when observed
3. Link feedback to decisions for analysis
4. Trigger improvement signals when patterns emerge
5. Maintain feedback metrics

Usage:
    from app.feedback import FeedbackService, create_feedback_service
    
    service = create_feedback_service(session)
    
    # Record customer feedback
    feedback = await service.record_customer_feedback(
        CustomerFeedbackCreate(
            decision_id="dec_123",
            action_followed=ActionFollowed.FOLLOWED_EXACTLY,
            satisfaction=SatisfactionLevel.SATISFIED,
        )
    )
    
    # Record outcome
    outcome = await service.record_outcome(
        OutcomeRecordCreate(
            decision_id="dec_123",
            event_occurred=True,
            actual_delay_days=14,
        )
    )
"""

from datetime import datetime, timedelta
from typing import Optional, Any
from collections import defaultdict
import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, update

from app.feedback.schemas import (
    FeedbackType,
    FeedbackSource,
    SatisfactionLevel,
    ActionFollowed,
    CustomerFeedback,
    CustomerFeedbackCreate,
    OutcomeRecord,
    OutcomeRecordCreate,
    ImprovementSignal,
    ImprovementArea,
)
from app.riskcast.schemas.decision import DecisionObject
from app.riskcast.outcome_tracking import (
    OutcomeTracker,
    OutcomeStatus,
    RecordOutcomeRequest,
    AccuracyMetrics,
)

logger = structlog.get_logger(__name__)


# =============================================================================
# FEEDBACK SERVICE
# =============================================================================


class FeedbackService:
    """
    Central service for feedback collection and processing.
    
    This service is THE KEY to the self-improving system.
    Every piece of feedback makes RISKCAST better.
    """
    
    def __init__(
        self,
        session: Optional[AsyncSession] = None,
        outcome_tracker: Optional[OutcomeTracker] = None,
    ):
        """
        Initialize feedback service.
        
        Args:
            session: Database session for persistence
            outcome_tracker: Outcome tracker for accuracy metrics
        """
        self._session = session
        self._outcome_tracker = outcome_tracker
        
        # In-memory storage for development
        self._feedback_store: dict[str, CustomerFeedback] = {}
        self._outcome_store: dict[str, OutcomeRecord] = {}
        self._by_decision: dict[str, list[str]] = defaultdict(list)
        self._by_customer: dict[str, list[str]] = defaultdict(list)
    
    # =========================================================================
    # CUSTOMER FEEDBACK
    # =========================================================================
    
    async def record_customer_feedback(
        self,
        feedback: CustomerFeedbackCreate,
        customer_id: str,
    ) -> CustomerFeedback:
        """
        Record customer feedback on a decision.
        
        Args:
            feedback: Feedback data
            customer_id: Customer ID
            
        Returns:
            Complete CustomerFeedback record
        """
        feedback_id = f"fb_{uuid.uuid4().hex[:12]}"
        
        complete_feedback = CustomerFeedback(
            feedback_id=feedback_id,
            customer_id=customer_id,
            **feedback.model_dump(),
        )
        
        # Store feedback
        self._feedback_store[feedback_id] = complete_feedback
        self._by_decision[feedback.decision_id].append(feedback_id)
        self._by_customer[customer_id].append(feedback_id)
        
        # If feedback includes outcome data, also record outcome
        if complete_feedback.has_outcome_data:
            await self._create_outcome_from_feedback(complete_feedback)
        
        # Update outcome tracker if we have action info
        if feedback.action_followed and self._outcome_tracker:
            try:
                await self._outcome_tracker.record_outcome(
                    RecordOutcomeRequest(
                        decision_id=feedback.decision_id,
                        actual_action_taken=feedback.actual_action_taken,
                        actual_impact_usd=feedback.actual_cost_usd,
                        actual_delay_days=float(feedback.actual_delay_days) if feedback.actual_delay_days else None,
                        feedback_notes=feedback.notes,
                    )
                )
            except Exception as e:
                logger.warning(
                    "outcome_tracker_update_failed",
                    decision_id=feedback.decision_id,
                    error=str(e),
                )
        
        logger.info(
            "customer_feedback_recorded",
            feedback_id=feedback_id,
            decision_id=feedback.decision_id,
            customer_id=customer_id,
            feedback_type=feedback.feedback_type.value,
            satisfaction=feedback.satisfaction.value if feedback.satisfaction else None,
        )
        
        return complete_feedback
    
    async def get_feedback(self, feedback_id: str) -> Optional[CustomerFeedback]:
        """Get feedback by ID."""
        return self._feedback_store.get(feedback_id)
    
    async def get_feedback_for_decision(
        self,
        decision_id: str,
    ) -> list[CustomerFeedback]:
        """Get all feedback for a decision."""
        feedback_ids = self._by_decision.get(decision_id, [])
        return [
            self._feedback_store[fid]
            for fid in feedback_ids
            if fid in self._feedback_store
        ]
    
    async def get_customer_feedback(
        self,
        customer_id: str,
        limit: int = 100,
    ) -> list[CustomerFeedback]:
        """Get all feedback from a customer."""
        feedback_ids = self._by_customer.get(customer_id, [])[:limit]
        return [
            self._feedback_store[fid]
            for fid in feedback_ids
            if fid in self._feedback_store
        ]
    
    # =========================================================================
    # OUTCOME RECORDS
    # =========================================================================
    
    async def record_outcome(
        self,
        outcome_data: OutcomeRecordCreate,
        decision: Optional[DecisionObject] = None,
    ) -> OutcomeRecord:
        """
        Record actual outcome for a decision.
        
        Args:
            outcome_data: Outcome data
            decision: Original decision (if available)
            
        Returns:
            Complete OutcomeRecord
        """
        outcome_id = f"out_{uuid.uuid4().hex[:12]}"
        
        # Get prediction data from decision or defaults
        if decision:
            predicted_event = True  # We predicted something would happen
            predicted_delay = decision.q3_severity.expected_delay_days
            predicted_cost = decision.q3_severity.total_exposure_usd
            predicted_confidence = decision.q6_confidence.score
            recommended_action = decision.q5_action.action_type
            customer_id = decision.customer_id
            signal_id = decision.signal_id
            predicted_at = decision.generated_at
        else:
            # Defaults when decision not available
            predicted_event = True
            predicted_delay = None
            predicted_cost = None
            predicted_confidence = 0.5
            recommended_action = "UNKNOWN"
            customer_id = "unknown"
            signal_id = "unknown"
            predicted_at = datetime.utcnow()
        
        # Calculate errors
        delay_error = None
        cost_error = None
        cost_error_pct = None
        
        if predicted_delay is not None and outcome_data.actual_delay_days is not None:
            delay_error = predicted_delay - outcome_data.actual_delay_days
        
        if predicted_cost is not None and outcome_data.actual_cost_usd is not None:
            cost_error = predicted_cost - outcome_data.actual_cost_usd
            if outcome_data.actual_cost_usd > 0:
                cost_error_pct = (cost_error / outcome_data.actual_cost_usd) * 100
        
        # Assess accuracy
        prediction_correct = (
            predicted_event == outcome_data.event_occurred
            if predicted_event is not None
            else False
        )
        
        delay_accurate = None
        if delay_error is not None and predicted_delay and predicted_delay > 0:
            delay_accurate = abs(delay_error) / predicted_delay <= 0.3
        
        cost_accurate = None
        if cost_error is not None and predicted_cost and predicted_cost > 0:
            cost_accurate = abs(cost_error) / predicted_cost <= 0.3
        
        # Calculate value delivered
        value_delivered = None
        if outcome_data.event_occurred and outcome_data.actual_cost_usd:
            action_cost = outcome_data.action_cost_usd or 0
            if outcome_data.action_taken and outcome_data.action_taken != "DO_NOTHING":
                # Value = loss avoided - action cost
                estimated_loss = outcome_data.actual_cost_usd
                value_delivered = max(0, estimated_loss - action_cost)
        
        outcome = OutcomeRecord(
            outcome_id=outcome_id,
            decision_id=outcome_data.decision_id,
            customer_id=customer_id,
            signal_id=signal_id,
            # Predictions
            predicted_event=predicted_event,
            predicted_delay_days=predicted_delay,
            predicted_cost_usd=predicted_cost,
            predicted_confidence=predicted_confidence,
            recommended_action=recommended_action,
            # Actual
            event_occurred=outcome_data.event_occurred,
            event_severity=outcome_data.event_severity,
            actual_delay_days=outcome_data.actual_delay_days,
            actual_cost_usd=outcome_data.actual_cost_usd,
            actual_rate_increase_pct=outcome_data.actual_rate_increase_pct,
            action_taken=outcome_data.action_taken,
            action_cost_usd=outcome_data.action_cost_usd,
            # Errors
            delay_error_days=delay_error,
            cost_error_usd=cost_error,
            cost_error_pct=cost_error_pct,
            # Accuracy
            prediction_correct=prediction_correct,
            delay_accurate=delay_accurate,
            cost_accurate=cost_accurate,
            # Value
            value_delivered_usd=value_delivered,
            # Metadata
            source=outcome_data.source,
            evidence_urls=outcome_data.evidence_urls,
            notes=outcome_data.notes,
            predicted_at=predicted_at,
        )
        
        # Store outcome
        self._outcome_store[outcome_id] = outcome
        self._by_decision[outcome_data.decision_id].append(outcome_id)
        
        logger.info(
            "outcome_recorded",
            outcome_id=outcome_id,
            decision_id=outcome_data.decision_id,
            event_occurred=outcome_data.event_occurred,
            prediction_correct=prediction_correct,
            delay_error=delay_error,
            cost_error_pct=cost_error_pct,
            value_delivered=value_delivered,
        )
        
        return outcome
    
    async def get_outcome(self, outcome_id: str) -> Optional[OutcomeRecord]:
        """Get outcome by ID."""
        return self._outcome_store.get(outcome_id)
    
    async def get_outcome_for_decision(
        self,
        decision_id: str,
    ) -> Optional[OutcomeRecord]:
        """Get outcome for a decision."""
        record_ids = self._by_decision.get(decision_id, [])
        for record_id in record_ids:
            if record_id.startswith("out_"):
                return self._outcome_store.get(record_id)
        return None
    
    async def get_outcomes(
        self,
        customer_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[OutcomeRecord]:
        """Get outcomes with optional filtering."""
        outcomes = list(self._outcome_store.values())
        
        if customer_id:
            outcomes = [o for o in outcomes if o.customer_id == customer_id]
        
        if since:
            outcomes = [o for o in outcomes if o.observed_at >= since]
        
        return sorted(
            outcomes,
            key=lambda o: o.observed_at,
            reverse=True
        )[:limit]
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    async def _create_outcome_from_feedback(
        self,
        feedback: CustomerFeedback,
    ) -> Optional[OutcomeRecord]:
        """Create outcome record from customer feedback."""
        if not feedback.has_outcome_data:
            return None
        
        outcome_data = OutcomeRecordCreate(
            decision_id=feedback.decision_id,
            event_occurred=feedback.event_occurred or True,
            actual_delay_days=feedback.actual_delay_days,
            actual_cost_usd=feedback.actual_cost_usd,
            action_taken=feedback.actual_action_taken,
            source=FeedbackSource.CUSTOMER_MANUAL,
            notes=feedback.notes,
        )
        
        return await self.record_outcome(outcome_data)
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    async def get_feedback_stats(
        self,
        customer_id: Optional[str] = None,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get feedback statistics."""
        since = datetime.utcnow() - timedelta(days=days)
        
        if customer_id:
            feedback_list = await self.get_customer_feedback(customer_id, limit=1000)
        else:
            feedback_list = list(self._feedback_store.values())
        
        feedback_list = [
            f for f in feedback_list
            if f.submitted_at >= since
        ]
        
        if not feedback_list:
            return {
                "total_feedback": 0,
                "period_days": days,
            }
        
        # Calculate stats
        satisfaction_scores = [
            f.satisfaction.value
            for f in feedback_list
            if f.satisfaction
        ]
        
        action_followed = [
            f for f in feedback_list
            if f.action_followed in [ActionFollowed.FOLLOWED_EXACTLY, ActionFollowed.FOLLOWED_PARTIALLY]
        ]
        
        positive = [f for f in feedback_list if f.is_positive]
        
        return {
            "total_feedback": len(feedback_list),
            "period_days": days,
            "avg_satisfaction": (
                sum(satisfaction_scores) / len(satisfaction_scores)
                if satisfaction_scores else None
            ),
            "action_uptake_rate": (
                len(action_followed) / len(feedback_list)
                if feedback_list else 0
            ),
            "positive_feedback_rate": (
                len(positive) / len(feedback_list)
                if feedback_list else 0
            ),
            "feedback_with_outcomes": sum(1 for f in feedback_list if f.has_outcome_data),
        }
    
    async def get_outcome_stats(
        self,
        customer_id: Optional[str] = None,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get outcome statistics."""
        outcomes = await self.get_outcomes(
            customer_id=customer_id,
            since=datetime.utcnow() - timedelta(days=days),
            limit=1000,
        )
        
        if not outcomes:
            return {
                "total_outcomes": 0,
                "period_days": days,
            }
        
        correct_predictions = [o for o in outcomes if o.prediction_correct]
        delay_accurate = [o for o in outcomes if o.delay_accurate]
        cost_accurate = [o for o in outcomes if o.cost_accurate]
        
        delay_errors = [
            o.delay_error_abs for o in outcomes
            if o.delay_error_abs is not None
        ]
        cost_errors = [
            o.cost_error_abs for o in outcomes
            if o.cost_error_abs is not None
        ]
        
        values = [
            o.value_delivered_usd for o in outcomes
            if o.value_delivered_usd is not None
        ]
        
        return {
            "total_outcomes": len(outcomes),
            "period_days": days,
            "prediction_accuracy": len(correct_predictions) / len(outcomes),
            "delay_accuracy_rate": (
                len(delay_accurate) / len(outcomes)
                if outcomes else 0
            ),
            "cost_accuracy_rate": (
                len(cost_accurate) / len(outcomes)
                if outcomes else 0
            ),
            "mean_delay_error_days": (
                sum(delay_errors) / len(delay_errors)
                if delay_errors else None
            ),
            "mean_cost_error_usd": (
                sum(cost_errors) / len(cost_errors)
                if cost_errors else None
            ),
            "total_value_delivered_usd": sum(values),
            "avg_value_per_decision_usd": (
                sum(values) / len(values)
                if values else 0
            ),
        }
    
    # =========================================================================
    # IMPROVEMENT SIGNALS
    # =========================================================================
    
    async def check_for_improvement_signals(
        self,
        min_samples: int = 10,
    ) -> list[ImprovementSignal]:
        """
        Analyze recent outcomes to identify improvement opportunities.
        
        Returns signals when:
        - Accuracy drops below threshold
        - Systematic bias detected (over/under estimation)
        - Specific chokepoint/category underperforming
        """
        signals = []
        
        outcomes = await self.get_outcomes(
            since=datetime.utcnow() - timedelta(days=30),
            limit=1000,
        )
        
        if len(outcomes) < min_samples:
            return signals
        
        # Check delay estimation accuracy
        delay_errors = [
            (o.delay_error_days, o.predicted_delay_days)
            for o in outcomes
            if o.delay_error_days is not None and o.predicted_delay_days
        ]
        
        if len(delay_errors) >= min_samples:
            mean_error = sum(e[0] for e in delay_errors) / len(delay_errors)
            overestimates = sum(1 for e in delay_errors if e[0] > 0)
            
            # Check for systematic overestimation
            if overestimates / len(delay_errors) > 0.7:
                signals.append(ImprovementSignal(
                    signal_id=f"imp_{uuid.uuid4().hex[:8]}",
                    area=ImprovementArea.DELAY_ESTIMATION,
                    severity="medium",
                    message=f"Systematic overestimation of delays: {overestimates}/{len(delay_errors)} predictions were too high",
                    evidence={
                        "mean_error_days": mean_error,
                        "overestimate_rate": overestimates / len(delay_errors),
                        "sample_count": len(delay_errors),
                    },
                    recommended_action="Consider reducing delay estimates by 10-15%",
                    sample_count=len(delay_errors),
                ))
        
        # Check cost estimation accuracy
        cost_errors = [
            (o.cost_error_pct, o.predicted_cost_usd)
            for o in outcomes
            if o.cost_error_pct is not None and o.predicted_cost_usd
        ]
        
        if len(cost_errors) >= min_samples:
            mean_error_pct = sum(e[0] for e in cost_errors) / len(cost_errors)
            
            if abs(mean_error_pct) > 20:
                direction = "overestimating" if mean_error_pct > 0 else "underestimating"
                signals.append(ImprovementSignal(
                    signal_id=f"imp_{uuid.uuid4().hex[:8]}",
                    area=ImprovementArea.COST_ESTIMATION,
                    severity="high" if abs(mean_error_pct) > 30 else "medium",
                    message=f"Systematic {direction} of costs by {abs(mean_error_pct):.1f}%",
                    evidence={
                        "mean_error_pct": mean_error_pct,
                        "sample_count": len(cost_errors),
                    },
                    recommended_action=f"Adjust cost estimates {'down' if mean_error_pct > 0 else 'up'} by ~{abs(mean_error_pct):.0f}%",
                    sample_count=len(cost_errors),
                ))
        
        # Check accuracy by chokepoint
        by_chokepoint: dict[str, list[bool]] = defaultdict(list)
        for o in outcomes:
            # Get chokepoint from signal_id or other source
            chokepoint = self._extract_chokepoint(o)
            if chokepoint:
                by_chokepoint[chokepoint].append(o.prediction_correct)
        
        for chokepoint, accuracies in by_chokepoint.items():
            if len(accuracies) >= min_samples:
                accuracy = sum(accuracies) / len(accuracies)
                if accuracy < 0.65:
                    signals.append(ImprovementSignal(
                        signal_id=f"imp_{uuid.uuid4().hex[:8]}",
                        area=ImprovementArea.CHOKEPOINT_DETECTION,
                        severity="high" if accuracy < 0.50 else "medium",
                        message=f"Low accuracy for {chokepoint}: {accuracy:.0%}",
                        evidence={
                            "accuracy": accuracy,
                            "sample_count": len(accuracies),
                        },
                        chokepoint=chokepoint,
                        recommended_action=f"Review {chokepoint} prediction model and data sources",
                        sample_count=len(accuracies),
                    ))
        
        return signals
    
    def _extract_chokepoint(self, outcome: OutcomeRecord) -> Optional[str]:
        """Extract chokepoint from outcome record."""
        signal_id = outcome.signal_id.lower()
        
        chokepoints = ["red_sea", "suez", "panama", "malacca", "hormuz"]
        for cp in chokepoints:
            if cp.replace("_", "") in signal_id or cp in signal_id:
                return cp
        
        return None


# =============================================================================
# FACTORY
# =============================================================================


def create_feedback_service(
    session: Optional[AsyncSession] = None,
) -> FeedbackService:
    """
    Create feedback service instance.
    
    Args:
        session: Database session (optional)
        
    Returns:
        FeedbackService instance
    """
    outcome_tracker = None
    if session:
        outcome_tracker = OutcomeTracker(session)
    
    return FeedbackService(
        session=session,
        outcome_tracker=outcome_tracker,
    )


# =============================================================================
# SINGLETON
# =============================================================================


_feedback_service: Optional[FeedbackService] = None


def get_feedback_service() -> FeedbackService:
    """Get global feedback service instance."""
    global _feedback_service
    
    if _feedback_service is None:
        _feedback_service = create_feedback_service()
    
    return _feedback_service
