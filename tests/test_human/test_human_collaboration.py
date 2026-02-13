"""
Tests for Human-AI Collaboration System.

Tests cover:
- Override: Creating and recording overrides
- Escalation: Creating, routing, and resolving escalations
- Feedback: Submitting and retrieving feedback
- Trust Metrics: Calculating collaboration metrics
- Audit Integration: Verifying all interactions create audit records
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

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
)
from app.human.service import (
    HumanCollaborationService,
    EscalationConfig,
    create_human_collaboration_service,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_audit_service():
    """Create mock audit service."""
    audit = AsyncMock()
    audit.record_human_override = AsyncMock(return_value="audit_override_123")
    audit.record_escalation = AsyncMock(return_value="audit_esc_123")
    audit.record_escalation_resolution = AsyncMock(return_value="audit_res_123")
    audit.record_feedback = AsyncMock(return_value="audit_feedback_123")
    return audit


@pytest.fixture
def mock_decision_repo():
    """Create mock decision repository."""
    repo = AsyncMock()
    
    # Create mock decision
    mock_decision = MagicMock()
    mock_decision.q5_action = MagicMock()
    mock_decision.q5_action.action_type = "reroute"
    
    repo.get_decision = AsyncMock(return_value=mock_decision)
    return repo


@pytest.fixture
def human_service(mock_audit_service, mock_decision_repo):
    """Create human collaboration service with mocks."""
    return HumanCollaborationService(
        audit_service=mock_audit_service,
        decision_repository=mock_decision_repo,
    )


@pytest.fixture
def sample_decision():
    """Create sample decision for testing."""
    return MagicMock(
        model_dump=MagicMock(return_value={
            "decision_id": "dec_test_123",
            "customer_id": "cust_123",
            "q2_when": {"urgency": "urgent"},
            "q3_severity": {"total_exposure_usd": 50000},
            "q5_action": {"action_type": "reroute"},
            "q6_confidence": {"score": 0.75},
        })
    )


# ============================================================================
# OVERRIDE TESTS
# ============================================================================


class TestOverride:
    """Tests for decision override functionality."""

    @pytest.mark.asyncio
    async def test_override_creates_audit_record(
        self, human_service, mock_audit_service
    ):
        """Override must create an audit record."""
        request = OverrideRequest(
            decision_id="dec_123",
            new_action_type="delay",
            reason=OverrideReason.BETTER_INFORMATION,
            reason_details="Received updated shipping information from carrier",
        )
        
        result = await human_service.override_decision(
            user_id="user_456",
            request=request,
        )
        
        # Verify audit was called
        mock_audit_service.record_human_override.assert_called_once()
        call_args = mock_audit_service.record_human_override.call_args
        
        assert call_args.kwargs["decision_id"] == "dec_123"
        assert call_args.kwargs["user_id"] == "user_456"
        assert call_args.kwargs["new_action"] == "delay"
        assert call_args.kwargs["reason_category"] == "better_information"

    @pytest.mark.asyncio
    async def test_override_result_has_all_fields(
        self, human_service
    ):
        """Override result must have all required fields."""
        request = OverrideRequest(
            decision_id="dec_123",
            new_action_type="monitor",
            reason=OverrideReason.CUSTOMER_REQUEST,
            reason_details="Customer explicitly requested to just monitor for now",
        )
        
        result = await human_service.override_decision(
            user_id="user_789",
            request=request,
        )
        
        # Verify result structure
        assert result.override_id is not None
        assert result.override_id.startswith("override_")
        assert result.decision_id == "dec_123"
        assert result.new_action == "monitor"
        assert result.overridden_by == "user_789"
        assert result.overridden_at is not None
        assert result.reason == OverrideReason.CUSTOMER_REQUEST
        assert result.audit_record_id is not None

    @pytest.mark.asyncio
    async def test_override_requires_detailed_reason(self):
        """Override request must require detailed reason."""
        # Should fail with short reason
        with pytest.raises(ValueError):
            OverrideRequest(
                decision_id="dec_123",
                new_action_type="delay",
                reason=OverrideReason.OTHER,
                reason_details="Too short",  # Less than 20 chars
            )

    @pytest.mark.asyncio
    async def test_override_supports_all_reason_types(
        self, human_service
    ):
        """All override reason types should be supported."""
        for reason in OverrideReason:
            request = OverrideRequest(
                decision_id=f"dec_{reason.value}",
                new_action_type="monitor",
                reason=reason,
                reason_details=f"Testing override reason: {reason.value} with details",
            )
            
            result = await human_service.override_decision(
                user_id="user_test",
                request=request,
            )
            
            assert result.reason == reason


# ============================================================================
# ESCALATION TESTS
# ============================================================================


class TestEscalation:
    """Tests for decision escalation functionality."""

    @pytest.mark.asyncio
    async def test_escalation_creates_audit_record(
        self, human_service, mock_audit_service, sample_decision
    ):
        """Escalation must create an audit record."""
        escalation = await human_service.escalate_decision(
            decision=sample_decision,
            trigger=EscalationTrigger.LOW_CONFIDENCE,
            trigger_details="Confidence 0.45 below threshold 0.60",
            escalated_to=["user_123", "user_456"],
        )
        
        # Verify audit was called
        mock_audit_service.record_escalation.assert_called_once()
        call_args = mock_audit_service.record_escalation.call_args
        
        assert call_args.kwargs["trigger"] == "low_confidence"
        assert call_args.kwargs["escalated_to"] == ["user_123", "user_456"]

    @pytest.mark.asyncio
    async def test_escalation_has_deadline(
        self, human_service, sample_decision
    ):
        """Escalation must have a deadline."""
        escalation = await human_service.escalate_decision(
            decision=sample_decision,
            trigger=EscalationTrigger.HIGH_VALUE,
            trigger_details="Exposure $500,000 above threshold",
        )
        
        assert escalation.deadline is not None
        assert escalation.deadline > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_escalation_deadline_based_on_urgency(
        self, human_service
    ):
        """Escalation deadline should be based on decision urgency."""
        # Immediate urgency
        immediate_decision = MagicMock(
            model_dump=MagicMock(return_value={
                "decision_id": "dec_immediate",
                "customer_id": "cust_123",
                "q2_when": {"urgency": "immediate"},
                "q3_severity": {"total_exposure_usd": 50000},
                "q5_action": {"action_type": "reroute"},
                "q6_confidence": {"score": 0.75},
            })
        )
        
        esc1 = await human_service.escalate_decision(
            decision=immediate_decision,
            trigger=EscalationTrigger.MANUAL_REQUEST,
            trigger_details="Testing immediate urgency",
        )
        
        # Standard urgency
        standard_decision = MagicMock(
            model_dump=MagicMock(return_value={
                "decision_id": "dec_standard",
                "customer_id": "cust_123",
                "q2_when": {"urgency": "standard"},
                "q3_severity": {"total_exposure_usd": 50000},
                "q5_action": {"action_type": "reroute"},
                "q6_confidence": {"score": 0.75},
            })
        )
        
        esc2 = await human_service.escalate_decision(
            decision=standard_decision,
            trigger=EscalationTrigger.MANUAL_REQUEST,
            trigger_details="Testing standard urgency",
        )
        
        # Immediate should have shorter deadline
        assert esc1.deadline < esc2.deadline

    @pytest.mark.asyncio
    async def test_should_escalate_low_confidence(
        self, human_service
    ):
        """Should escalate when confidence is below threshold."""
        low_confidence_decision = MagicMock(
            model_dump=MagicMock(return_value={
                "decision_id": "dec_low_conf",
                "customer_id": "cust_123",
                "q6_confidence": {"score": 0.45},  # Below 0.60 threshold
                "q3_severity": {"total_exposure_usd": 10000},
            })
        )
        
        should, trigger, reason = await human_service.should_escalate(
            low_confidence_decision
        )
        
        assert should is True
        assert trigger == EscalationTrigger.LOW_CONFIDENCE
        assert "below threshold" in reason.lower()

    @pytest.mark.asyncio
    async def test_should_escalate_high_value(
        self, human_service
    ):
        """Should escalate when exposure is above threshold."""
        high_value_decision = MagicMock(
            model_dump=MagicMock(return_value={
                "decision_id": "dec_high_val",
                "customer_id": "cust_123",
                "q6_confidence": {"score": 0.70},
                "q3_severity": {"total_exposure_usd": 600000},  # Above $500k critical
            })
        )
        
        should, trigger, reason = await human_service.should_escalate(
            high_value_decision
        )
        
        assert should is True
        assert trigger == EscalationTrigger.HIGH_VALUE

    @pytest.mark.asyncio
    async def test_should_not_escalate_confident_low_value(
        self, human_service
    ):
        """Should not escalate when confident and low value."""
        good_decision = MagicMock(
            model_dump=MagicMock(return_value={
                "decision_id": "dec_good",
                "customer_id": "cust_123",
                "q6_confidence": {"score": 0.90},  # High confidence
                "q3_severity": {"total_exposure_usd": 10000},  # Low exposure
            })
        )
        
        should, trigger, reason = await human_service.should_escalate(
            good_decision
        )
        
        assert should is False
        assert trigger is None

    @pytest.mark.asyncio
    async def test_resolve_escalation_creates_audit(
        self, human_service, mock_audit_service, sample_decision
    ):
        """Resolving escalation must create audit record."""
        # First create an escalation
        escalation = await human_service.escalate_decision(
            decision=sample_decision,
            trigger=EscalationTrigger.MANUAL_REQUEST,
            trigger_details="Testing resolution",
        )
        
        # Resolve it
        resolution = await human_service.resolve_escalation(
            user_id="resolver_user",
            escalation_id=escalation.escalation_id,
            resolution="APPROVE",
            final_action="reroute",
            resolution_reason="Reviewed and approved the recommendation",
        )
        
        # Verify audit
        mock_audit_service.record_escalation_resolution.assert_called_once()
        assert resolution.resolved_by == "resolver_user"
        assert resolution.resolution == "APPROVE"

    @pytest.mark.asyncio
    async def test_resolution_tracks_time_to_resolution(
        self, human_service, sample_decision
    ):
        """Resolution should track time to resolution."""
        escalation = await human_service.escalate_decision(
            decision=sample_decision,
            trigger=EscalationTrigger.MANUAL_REQUEST,
            trigger_details="Testing time tracking",
        )
        
        resolution = await human_service.resolve_escalation(
            user_id="resolver",
            escalation_id=escalation.escalation_id,
            resolution="MODIFY",
            final_action="delay",
            resolution_reason="Modified to delay instead of reroute",
        )
        
        assert resolution.time_to_resolution_minutes >= 0

    @pytest.mark.asyncio
    async def test_cannot_resolve_already_resolved(
        self, human_service, sample_decision
    ):
        """Cannot resolve an already resolved escalation."""
        escalation = await human_service.escalate_decision(
            decision=sample_decision,
            trigger=EscalationTrigger.MANUAL_REQUEST,
            trigger_details="Testing double resolution",
        )
        
        # First resolution
        await human_service.resolve_escalation(
            user_id="resolver1",
            escalation_id=escalation.escalation_id,
            resolution="APPROVE",
            final_action="reroute",
            resolution_reason="First resolution",
        )
        
        # Second resolution should fail
        with pytest.raises(ValueError, match="already resolved"):
            await human_service.resolve_escalation(
                user_id="resolver2",
                escalation_id=escalation.escalation_id,
                resolution="REJECT",
                final_action="do_nothing",
                resolution_reason="Trying to resolve again",
            )

    @pytest.mark.asyncio
    async def test_get_pending_escalations(
        self, human_service, sample_decision
    ):
        """Should retrieve pending escalations."""
        # Create some escalations
        esc1 = await human_service.escalate_decision(
            decision=sample_decision,
            trigger=EscalationTrigger.MANUAL_REQUEST,
            trigger_details="Test escalation 1",
            escalated_to=["user_a", "user_b"],
        )
        
        esc2 = await human_service.escalate_decision(
            decision=sample_decision,
            trigger=EscalationTrigger.LOW_CONFIDENCE,
            trigger_details="Test escalation 2",
            escalated_to=["user_a"],
        )
        
        # Get pending
        pending = await human_service.get_pending_escalations()
        assert len(pending) == 2
        
        # Filter by user
        user_a_pending = await human_service.get_pending_escalations(
            user_id="user_a"
        )
        assert len(user_a_pending) == 2
        
        user_b_pending = await human_service.get_pending_escalations(
            user_id="user_b"
        )
        assert len(user_b_pending) == 1


# ============================================================================
# FEEDBACK TESTS
# ============================================================================


class TestFeedback:
    """Tests for feedback submission functionality."""

    @pytest.mark.asyncio
    async def test_feedback_creates_audit_record(
        self, human_service, mock_audit_service
    ):
        """Feedback must create an audit record."""
        feedback = FeedbackSubmission(
            decision_id="dec_123",
            feedback_type=FeedbackType.DECISION_QUALITY,
            rating=4,
            comment="Good recommendation, helped us avoid significant delays",
            would_follow_again=True,
        )
        
        feedback_id = await human_service.submit_feedback(
            user_id="user_123",
            feedback=feedback,
        )
        
        # Verify audit
        mock_audit_service.record_feedback.assert_called_once()
        call_args = mock_audit_service.record_feedback.call_args
        
        assert call_args.kwargs["decision_id"] == "dec_123"
        assert call_args.kwargs["feedback_type"] == "decision_quality"
        assert call_args.kwargs["rating"] == 4

    @pytest.mark.asyncio
    async def test_feedback_with_actual_outcome(
        self, human_service
    ):
        """Feedback can include actual outcome for calibration."""
        feedback = FeedbackSubmission(
            decision_id="dec_456",
            feedback_type=FeedbackType.DELAY_ACCURACY,
            rating=3,
            comment="Delay estimate was higher than actual",
            would_follow_again=True,
            actual_delay_days=5,  # System predicted 8
            actual_cost_usd=12000.0,  # System predicted $15,000
            event_occurred=True,
        )
        
        feedback_id = await human_service.submit_feedback(
            user_id="user_789",
            feedback=feedback,
        )
        
        assert feedback_id is not None

    @pytest.mark.asyncio
    async def test_feedback_rating_validation(self):
        """Feedback rating must be 1-5."""
        # Valid ratings
        for rating in [1, 2, 3, 4, 5]:
            feedback = FeedbackSubmission(
                decision_id="dec_test",
                feedback_type=FeedbackType.GENERAL,
                rating=rating,
                comment="",
                would_follow_again=True,
            )
            assert feedback.rating == rating
        
        # Invalid ratings
        with pytest.raises(ValueError):
            FeedbackSubmission(
                decision_id="dec_test",
                feedback_type=FeedbackType.GENERAL,
                rating=0,  # Too low
                comment="",
                would_follow_again=True,
            )
        
        with pytest.raises(ValueError):
            FeedbackSubmission(
                decision_id="dec_test",
                feedback_type=FeedbackType.GENERAL,
                rating=6,  # Too high
                comment="",
                would_follow_again=True,
            )

    @pytest.mark.asyncio
    async def test_get_feedback_for_decision(
        self, human_service
    ):
        """Should retrieve all feedback for a decision."""
        decision_id = "dec_feedback_test"
        
        # Submit multiple feedbacks
        await human_service.submit_feedback(
            user_id="user_1",
            feedback=FeedbackSubmission(
                decision_id=decision_id,
                feedback_type=FeedbackType.DECISION_QUALITY,
                rating=4,
                comment="Good overall",
                would_follow_again=True,
            ),
        )
        
        await human_service.submit_feedback(
            user_id="user_2",
            feedback=FeedbackSubmission(
                decision_id=decision_id,
                feedback_type=FeedbackType.TIMING,
                rating=3,
                comment="Timing was off",
                would_follow_again=True,
            ),
        )
        
        # Retrieve
        feedbacks = await human_service.get_feedback_for_decision(decision_id)
        assert len(feedbacks) == 2


# ============================================================================
# TRUST METRICS TESTS
# ============================================================================


class TestTrustMetrics:
    """Tests for trust metrics calculation."""

    @pytest.mark.asyncio
    async def test_trust_metrics_structure(
        self, human_service
    ):
        """Trust metrics must have complete structure."""
        metrics = await human_service.calculate_trust_metrics(period_days=30)
        
        # Required fields
        assert hasattr(metrics, 'period_days')
        assert hasattr(metrics, 'total_decisions')
        assert hasattr(metrics, 'decisions_followed')
        assert hasattr(metrics, 'decisions_overridden')
        assert hasattr(metrics, 'decisions_escalated')
        assert hasattr(metrics, 'follow_rate')
        assert hasattr(metrics, 'override_rate')
        assert hasattr(metrics, 'escalation_rate')
        assert hasattr(metrics, 'feedback_count')
        assert hasattr(metrics, 'top_override_reasons')
        assert hasattr(metrics, 'top_escalation_triggers')

    @pytest.mark.asyncio
    async def test_trust_metrics_rates_valid(
        self, human_service
    ):
        """Trust metrics rates must be between 0 and 1."""
        metrics = await human_service.calculate_trust_metrics(period_days=30)
        
        assert 0.0 <= metrics.follow_rate <= 1.0
        assert 0.0 <= metrics.override_rate <= 1.0
        assert 0.0 <= metrics.escalation_rate <= 1.0

    @pytest.mark.asyncio
    async def test_trust_metrics_tracks_escalation_triggers(
        self, human_service, sample_decision
    ):
        """Trust metrics should track top escalation triggers."""
        # Create escalations with different triggers
        for _ in range(3):
            await human_service.escalate_decision(
                decision=sample_decision,
                trigger=EscalationTrigger.LOW_CONFIDENCE,
                trigger_details="Low confidence test",
            )
        
        for _ in range(2):
            await human_service.escalate_decision(
                decision=sample_decision,
                trigger=EscalationTrigger.HIGH_VALUE,
                trigger_details="High value test",
            )
        
        metrics = await human_service.calculate_trust_metrics(period_days=30)
        
        # Should have escalation triggers tracked
        assert len(metrics.top_escalation_triggers) > 0
        
        # LOW_CONFIDENCE should be most common
        if metrics.top_escalation_triggers:
            assert metrics.top_escalation_triggers[0]["trigger"] == "low_confidence"


# ============================================================================
# SCHEMA VALIDATION TESTS
# ============================================================================


class TestSchemaValidation:
    """Tests for schema validation."""

    def test_override_request_requires_reason_details(self):
        """Override request must require reason details."""
        with pytest.raises(ValueError):
            OverrideRequest(
                decision_id="dec_123",
                new_action_type="delay",
                reason=OverrideReason.OTHER,
                reason_details="",  # Empty
            )

    def test_escalation_resolution_valid_types(self):
        """Escalation resolution must validate resolution type."""
        # Valid resolutions
        for res in ["APPROVE", "MODIFY", "REJECT"]:
            resolution = EscalationResolution(
                escalation_id="esc_123",
                resolved_by="user_123",
                resolved_at=datetime.utcnow(),
                resolution=res,
                final_action="monitor",
                resolution_reason="Test resolution",
                time_to_resolution_minutes=10,
            )
            assert resolution.resolution == res
        
        # Invalid resolution should be rejected
        with pytest.raises(ValueError):
            EscalationResolution(
                escalation_id="esc_123",
                resolved_by="user_123",
                resolved_at=datetime.utcnow(),
                resolution="INVALID",
                final_action="monitor",
                resolution_reason="Test resolution",
                time_to_resolution_minutes=10,
            )

    def test_feedback_submission_valid_types(self):
        """Feedback submission must accept all feedback types."""
        for fb_type in FeedbackType:
            feedback = FeedbackSubmission(
                decision_id="dec_123",
                feedback_type=fb_type,
                rating=3,
                comment="Test feedback",
                would_follow_again=True,
            )
            assert feedback.feedback_type == fb_type

    def test_trust_metrics_optional_fields(self):
        """Trust metrics optional fields should allow None."""
        metrics = TrustMetrics(
            period_days=30,
            total_decisions=100,
            decisions_followed=90,
            decisions_overridden=5,
            decisions_escalated=5,
            follow_rate=0.90,
            override_rate=0.05,
            escalation_rate=0.05,
            feedback_count=0,
            average_rating=None,  # No feedback
            would_follow_again_rate=None,
            calibration_accuracy=None,
            top_override_reasons=[],
            top_escalation_triggers=[],
        )
        
        assert metrics.average_rating is None
        assert metrics.calibration_accuracy is None


# ============================================================================
# FACTORY TESTS
# ============================================================================


class TestFactory:
    """Tests for factory functions."""

    def test_create_service_with_defaults(self, mock_audit_service):
        """Should create service with default config."""
        service = create_human_collaboration_service(
            audit_service=mock_audit_service,
        )
        
        assert service is not None
        assert service._config is not None

    def test_create_service_with_custom_config(self, mock_audit_service):
        """Should create service with custom config."""
        config = EscalationConfig()
        config.MIN_CONFIDENCE_FOR_AUTO = 0.5
        config.HIGH_VALUE_THRESHOLD_USD = 50000
        
        service = create_human_collaboration_service(
            audit_service=mock_audit_service,
            config=config,
        )
        
        assert service._config.MIN_CONFIDENCE_FOR_AUTO == 0.5
        assert service._config.HIGH_VALUE_THRESHOLD_USD == 50000
