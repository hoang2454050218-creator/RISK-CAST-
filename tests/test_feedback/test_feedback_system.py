"""Tests for Feedback Loop System.

Tests the feedback collection, outcome tracking, and accuracy analysis
that enables RISKCAST to continuously improve.

Key tests:
- Schema validation
- Feedback recording
- Outcome tracking
- Accuracy calculation
- Calibration analysis
- Improvement signal generation
"""

from datetime import datetime, timedelta
from typing import Optional

import pytest

from app.feedback.schemas import (
    FeedbackType,
    FeedbackSource,
    SatisfactionLevel,
    ActionFollowed,
    CustomerFeedback,
    CustomerFeedbackCreate,
    OutcomeRecord,
    OutcomeRecordCreate,
    AccuracyReport,
    CalibrationReport,
    TrendAnalysis,
    ImprovementSignal,
    ImprovementArea,
)
from app.feedback.service import (
    FeedbackService,
    create_feedback_service,
    get_feedback_service,
)
from app.feedback.analyzer import (
    FeedbackAnalyzer,
    create_feedback_analyzer,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def feedback_service() -> FeedbackService:
    """Create feedback service instance."""
    return create_feedback_service()


@pytest.fixture
def feedback_analyzer(feedback_service: FeedbackService) -> FeedbackAnalyzer:
    """Create feedback analyzer instance."""
    return create_feedback_analyzer(feedback_service)


@pytest.fixture
def sample_feedback_create() -> CustomerFeedbackCreate:
    """Create sample feedback request."""
    return CustomerFeedbackCreate(
        decision_id="dec_test_001",
        feedback_type=FeedbackType.ACTION_TAKEN,
        action_followed=ActionFollowed.FOLLOWED_EXACTLY,
        actual_action_taken="REROUTE",
        satisfaction=SatisfactionLevel.SATISFIED,
        actual_delay_days=14,
        actual_cost_usd=45000,
        event_occurred=True,
        notes="Great advice, avoided major delays",
        what_helped="Specific action recommendation with cost",
        source=FeedbackSource.CUSTOMER_MANUAL,
    )


@pytest.fixture
def sample_outcome_create() -> OutcomeRecordCreate:
    """Create sample outcome request."""
    return OutcomeRecordCreate(
        decision_id="dec_test_002",
        event_occurred=True,
        event_severity="as_predicted",
        actual_delay_days=12,
        actual_cost_usd=50000,
        actual_rate_increase_pct=30,
        action_taken="REROUTE",
        action_cost_usd=8500,
        source=FeedbackSource.SYSTEM_OBSERVED,
        notes="Event materialized as predicted",
    )


# =============================================================================
# SCHEMA TESTS
# =============================================================================


class TestFeedbackSchemas:
    """Tests for feedback schemas."""

    def test_customer_feedback_create_valid(self, sample_feedback_create: CustomerFeedbackCreate):
        """CustomerFeedbackCreate should validate correctly."""
        assert sample_feedback_create.decision_id == "dec_test_001"
        assert sample_feedback_create.action_followed == ActionFollowed.FOLLOWED_EXACTLY
        assert sample_feedback_create.satisfaction == SatisfactionLevel.SATISFIED

    def test_customer_feedback_has_outcome_data(self):
        """CustomerFeedback should detect outcome data."""
        feedback = CustomerFeedback(
            feedback_id="fb_001",
            customer_id="cust_001",
            decision_id="dec_001",
            feedback_type=FeedbackType.ACTION_TAKEN,
            actual_delay_days=14,
            actual_cost_usd=45000,
        )

        assert feedback.has_outcome_data is True

    def test_customer_feedback_no_outcome_data(self):
        """CustomerFeedback should detect missing outcome data."""
        feedback = CustomerFeedback(
            feedback_id="fb_002",
            customer_id="cust_001",
            decision_id="dec_001",
            feedback_type=FeedbackType.SATISFACTION,
            satisfaction=SatisfactionLevel.SATISFIED,
        )

        assert feedback.has_outcome_data is False

    def test_customer_feedback_is_positive(self):
        """CustomerFeedback should identify positive feedback."""
        positive = CustomerFeedback(
            feedback_id="fb_003",
            customer_id="cust_001",
            decision_id="dec_001",
            feedback_type=FeedbackType.SATISFACTION,
            satisfaction=SatisfactionLevel.SATISFIED,
        )

        negative = CustomerFeedback(
            feedback_id="fb_004",
            customer_id="cust_001",
            decision_id="dec_001",
            feedback_type=FeedbackType.SATISFACTION,
            satisfaction=SatisfactionLevel.DISSATISFIED,
        )

        assert positive.is_positive is True
        assert negative.is_positive is False

    def test_outcome_record_error_calculations(self):
        """OutcomeRecord should calculate errors correctly."""
        outcome = OutcomeRecord(
            outcome_id="out_001",
            decision_id="dec_001",
            customer_id="cust_001",
            signal_id="sig_001",
            predicted_event=True,
            predicted_delay_days=14,
            predicted_cost_usd=50000,
            predicted_confidence=0.75,
            recommended_action="REROUTE",
            event_occurred=True,
            actual_delay_days=12,
            actual_cost_usd=45000,
            delay_error_days=2,
            cost_error_usd=5000,
            cost_error_pct=11.1,
            prediction_correct=True,
            delay_accurate=True,
            cost_accurate=True,
            predicted_at=datetime.utcnow() - timedelta(days=7),
        )

        assert outcome.delay_error_abs == 2
        assert outcome.cost_error_abs == 5000
        assert outcome.was_overestimate is True  # Predicted more than actual

    def test_accuracy_report_grade_calculation(self):
        """AccuracyReport should calculate grade correctly."""
        high_accuracy = AccuracyReport(
            report_id="acc_001",
            period_start=datetime.utcnow() - timedelta(days=30),
            period_end=datetime.utcnow(),
            period_days=30,
            total_decisions=100,
            decisions_with_outcome=90,
            overall_accuracy=0.87,
            precision=0.85,
            recall=0.90,
            f1_score=0.87,
            action_uptake_rate=0.75,
            total_value_delivered_usd=500000,
            avg_value_per_decision_usd=5555,
        )

        low_accuracy = AccuracyReport(
            report_id="acc_002",
            period_start=datetime.utcnow() - timedelta(days=30),
            period_end=datetime.utcnow(),
            period_days=30,
            total_decisions=100,
            decisions_with_outcome=90,
            overall_accuracy=0.55,
            precision=0.50,
            recall=0.60,
            f1_score=0.55,
            action_uptake_rate=0.40,
            total_value_delivered_usd=100000,
            avg_value_per_decision_usd=1111,
        )

        assert high_accuracy.grade == "A"
        assert low_accuracy.grade == "F"

    def test_calibration_report_well_calibrated(self):
        """CalibrationReport should identify calibration quality."""
        good_cal = CalibrationReport(
            report_id="cal_001",
            period_start=datetime.utcnow() - timedelta(days=30),
            period_end=datetime.utcnow(),
            brier_score=0.12,
            buckets=[],
            overconfident_buckets=[],
            underconfident_buckets=[],
            recommended_adjustments={},
            sample_count=100,
        )

        bad_cal = CalibrationReport(
            report_id="cal_002",
            period_start=datetime.utcnow() - timedelta(days=30),
            period_end=datetime.utcnow(),
            brier_score=0.35,
            buckets=[],
            overconfident_buckets=["70-80%", "80-90%"],
            underconfident_buckets=[],
            recommended_adjustments={"70-80%": -0.15},
            sample_count=100,
        )

        assert good_cal.is_well_calibrated is True
        assert bad_cal.is_well_calibrated is False
        assert bad_cal.needs_attention is True

    def test_trend_analysis_direction(self):
        """TrendAnalysis should identify trend direction."""
        improving = TrendAnalysis(
            metric="overall_accuracy",
            trend="improving",
            change_pct=7.5,
            data_points=[],
            current_value=0.85,
            previous_value=0.79,
            period_type="weekly",
            periods_analyzed=4,
        )

        declining = TrendAnalysis(
            metric="overall_accuracy",
            trend="declining",
            change_pct=-8.0,
            data_points=[],
            current_value=0.72,
            previous_value=0.78,
            period_type="weekly",
            periods_analyzed=4,
        )

        assert improving.is_improving is True
        assert improving.is_concerning is False
        assert declining.is_improving is False
        assert declining.is_concerning is True


# =============================================================================
# SERVICE TESTS
# =============================================================================


class TestFeedbackService:
    """Tests for FeedbackService."""

    @pytest.mark.asyncio
    async def test_record_customer_feedback(
        self,
        feedback_service: FeedbackService,
        sample_feedback_create: CustomerFeedbackCreate,
    ):
        """Service should record customer feedback."""
        feedback = await feedback_service.record_customer_feedback(
            feedback=sample_feedback_create,
            customer_id="cust_test_001",
        )

        assert feedback.feedback_id.startswith("fb_")
        assert feedback.customer_id == "cust_test_001"
        assert feedback.decision_id == sample_feedback_create.decision_id
        assert feedback.satisfaction == SatisfactionLevel.SATISFIED

    @pytest.mark.asyncio
    async def test_get_feedback_by_id(
        self,
        feedback_service: FeedbackService,
        sample_feedback_create: CustomerFeedbackCreate,
    ):
        """Service should retrieve feedback by ID."""
        created = await feedback_service.record_customer_feedback(
            feedback=sample_feedback_create,
            customer_id="cust_test_001",
        )

        retrieved = await feedback_service.get_feedback(created.feedback_id)

        assert retrieved is not None
        assert retrieved.feedback_id == created.feedback_id

    @pytest.mark.asyncio
    async def test_get_feedback_for_decision(
        self,
        feedback_service: FeedbackService,
    ):
        """Service should get all feedback for a decision."""
        decision_id = "dec_multi_feedback"

        # Create multiple feedback records
        for i in range(3):
            await feedback_service.record_customer_feedback(
                feedback=CustomerFeedbackCreate(
                    decision_id=decision_id,
                    feedback_type=FeedbackType.SATISFACTION,
                    satisfaction=SatisfactionLevel.SATISFIED,
                    notes=f"Feedback {i}",
                ),
                customer_id="cust_test",
            )

        feedback_list = await feedback_service.get_feedback_for_decision(decision_id)

        assert len(feedback_list) == 3

    @pytest.mark.asyncio
    async def test_record_outcome(
        self,
        feedback_service: FeedbackService,
        sample_outcome_create: OutcomeRecordCreate,
    ):
        """Service should record outcome."""
        outcome = await feedback_service.record_outcome(
            outcome_data=sample_outcome_create,
        )

        assert outcome.outcome_id.startswith("out_")
        assert outcome.event_occurred is True
        assert outcome.actual_delay_days == 12
        assert outcome.actual_cost_usd == 50000

    @pytest.mark.asyncio
    async def test_outcome_error_calculation(
        self,
        feedback_service: FeedbackService,
    ):
        """Service should calculate prediction errors."""
        # Create a mock decision to provide predictions
        from app.riskcast.schemas.decision import (
            DecisionObject,
            Q1WhatIsHappening,
            Q2WhenWillItHappen,
            Q3HowBadIsIt,
            Q4WhyIsThisHappening,
            Q5WhatToDoNow,
            Q6HowConfident,
            Q7WhatIfNothing,
        )
        from app.riskcast.constants import Severity, Urgency, ConfidenceLevel

        mock_decision = DecisionObject(
            decision_id="dec_with_predictions",
            customer_id="cust_001",
            signal_id="sig_001",
            q1_what=Q1WhatIsHappening(
                event_type="DISRUPTION",
                event_summary="Test event",
                affected_chokepoint="red_sea",
            ),
            q2_when=Q2WhenWillItHappen(
                status="CONFIRMED",
                impact_timeline="3 days",
                urgency=Urgency.URGENT,
                urgency_reason="Test",
            ),
            q3_severity=Q3HowBadIsIt(
                total_exposure_usd=60000,
                expected_delay_days=15,
                delay_range="14-16 days",
                shipments_affected=2,
                severity=Severity.HIGH,
            ),
            q4_why=Q4WhyIsThisHappening(
                root_cause="Test cause",
                causal_chain=["A", "B", "C"],
                evidence_summary="Test evidence",
            ),
            q5_action=Q5WhatToDoNow(
                action_type="REROUTE",
                action_summary="Test action",
                estimated_cost_usd=8000,
                deadline=datetime.utcnow() + timedelta(hours=6),
                deadline_reason="Test deadline",
            ),
            q6_confidence=Q6HowConfident(
                score=0.80,
                level=ConfidenceLevel.HIGH,
                explanation="Test confidence",
            ),
            q7_inaction=Q7WhatIfNothing(
                expected_loss_if_nothing=50000,
                cost_if_wait_6h=52000,
                cost_if_wait_24h=58000,
                cost_if_wait_48h=65000,
                worst_case_cost=70000,
                worst_case_scenario="Test worst case",
                inaction_summary="Test inaction",
            ),
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )

        outcome = await feedback_service.record_outcome(
            outcome_data=OutcomeRecordCreate(
                decision_id="dec_with_predictions",
                event_occurred=True,
                actual_delay_days=12,
                actual_cost_usd=50000,
            ),
            decision=mock_decision,
        )

        # Check error calculations
        assert outcome.predicted_delay_days == 15
        assert outcome.actual_delay_days == 12
        assert outcome.delay_error_days == 3  # 15 - 12
        assert outcome.predicted_cost_usd == 60000
        assert outcome.cost_error_usd == 10000  # 60000 - 50000

    @pytest.mark.asyncio
    async def test_feedback_stats(
        self,
        feedback_service: FeedbackService,
    ):
        """Service should calculate feedback statistics."""
        # Create some feedback
        for i in range(5):
            await feedback_service.record_customer_feedback(
                feedback=CustomerFeedbackCreate(
                    decision_id=f"dec_stats_{i}",
                    feedback_type=FeedbackType.ACTION_TAKEN,
                    action_followed=ActionFollowed.FOLLOWED_EXACTLY,
                    satisfaction=SatisfactionLevel.SATISFIED if i < 4 else SatisfactionLevel.NEUTRAL,
                ),
                customer_id="cust_stats",
            )

        stats = await feedback_service.get_feedback_stats(
            customer_id="cust_stats",
            days=30,
        )

        assert stats["total_feedback"] == 5
        assert stats["avg_satisfaction"] >= 3.5  # Mostly satisfied
        assert stats["action_uptake_rate"] == 1.0  # All followed

    @pytest.mark.asyncio
    async def test_improvement_signals(
        self,
        feedback_service: FeedbackService,
    ):
        """Service should detect improvement signals."""
        # Create outcomes with systematic bias (overestimating delays)
        for i in range(15):
            outcome = OutcomeRecord(
                outcome_id=f"out_bias_{i}",
                decision_id=f"dec_bias_{i}",
                customer_id="cust_bias",
                signal_id="sig_red_sea_001",
                predicted_event=True,
                predicted_delay_days=15,
                predicted_cost_usd=50000,
                predicted_confidence=0.75,
                recommended_action="REROUTE",
                event_occurred=True,
                actual_delay_days=10,  # Actually less than predicted
                actual_cost_usd=45000,
                delay_error_days=5,  # Overestimated
                cost_error_usd=5000,
                cost_error_pct=11,
                prediction_correct=True,
                delay_accurate=False,
                predicted_at=datetime.utcnow() - timedelta(days=7),
            )
            feedback_service._outcome_store[outcome.outcome_id] = outcome

        signals = await feedback_service.check_for_improvement_signals(min_samples=10)

        # Should detect delay overestimation
        delay_signal = next(
            (s for s in signals if s.area == ImprovementArea.DELAY_ESTIMATION),
            None
        )
        assert delay_signal is not None
        assert "overestimation" in delay_signal.message.lower()


# =============================================================================
# ANALYZER TESTS
# =============================================================================


class TestFeedbackAnalyzer:
    """Tests for FeedbackAnalyzer."""

    @pytest.mark.asyncio
    async def test_generate_accuracy_report_empty(
        self,
        feedback_analyzer: FeedbackAnalyzer,
    ):
        """Analyzer should handle empty data."""
        report = await feedback_analyzer.generate_accuracy_report(days=30)

        assert report.total_decisions == 0
        assert report.overall_accuracy == 0

    @pytest.mark.asyncio
    async def test_generate_accuracy_report_with_data(
        self,
        feedback_service: FeedbackService,
        feedback_analyzer: FeedbackAnalyzer,
    ):
        """Analyzer should calculate accuracy from outcomes."""
        # Create outcomes
        for i in range(20):
            correct = i < 16  # 80% correct
            outcome = OutcomeRecord(
                outcome_id=f"out_acc_{i}",
                decision_id=f"dec_acc_{i}",
                customer_id="cust_acc",
                signal_id="sig_001",
                predicted_event=True,
                predicted_delay_days=14,
                predicted_cost_usd=50000,
                predicted_confidence=0.75,
                recommended_action="REROUTE",
                event_occurred=correct,
                actual_delay_days=12 if correct else 0,
                actual_cost_usd=45000 if correct else 0,
                prediction_correct=correct,
                delay_accurate=correct,
                cost_accurate=correct,
                value_delivered_usd=35000 if correct else 0,
                predicted_at=datetime.utcnow() - timedelta(days=7),
            )
            feedback_service._outcome_store[outcome.outcome_id] = outcome

        report = await feedback_analyzer.generate_accuracy_report(days=30)

        assert report.total_decisions == 20
        assert report.overall_accuracy == 0.8  # 16/20

    @pytest.mark.asyncio
    async def test_generate_calibration_report(
        self,
        feedback_service: FeedbackService,
        feedback_analyzer: FeedbackAnalyzer,
    ):
        """Analyzer should calculate calibration metrics."""
        # Create outcomes with varying confidence levels
        for i in range(30):
            confidence = 0.7 + (i % 3) * 0.1  # 0.7, 0.8, 0.9
            occurred = i % 4 != 0  # 75% occur

            outcome = OutcomeRecord(
                outcome_id=f"out_cal_{i}",
                decision_id=f"dec_cal_{i}",
                customer_id="cust_cal",
                signal_id="sig_001",
                predicted_event=True,
                predicted_delay_days=14,
                predicted_cost_usd=50000,
                predicted_confidence=confidence,
                recommended_action="REROUTE",
                event_occurred=occurred,
                prediction_correct=occurred,
                predicted_at=datetime.utcnow() - timedelta(days=7),
            )
            feedback_service._outcome_store[outcome.outcome_id] = outcome

        report = await feedback_analyzer.generate_calibration_report(days=30)

        assert report.sample_count == 30
        assert 0 <= report.brier_score <= 1
        assert len(report.buckets) > 0

    @pytest.mark.asyncio
    async def test_analyze_trend(
        self,
        feedback_service: FeedbackService,
        feedback_analyzer: FeedbackAnalyzer,
    ):
        """Analyzer should calculate trends."""
        # Create outcomes spread over time
        for week in range(4):
            accuracy = 0.70 + week * 0.05  # Improving: 70%, 75%, 80%, 85%

            for i in range(10):
                correct = i < int(accuracy * 10)
                outcome = OutcomeRecord(
                    outcome_id=f"out_trend_{week}_{i}",
                    decision_id=f"dec_trend_{week}_{i}",
                    customer_id="cust_trend",
                    signal_id="sig_001",
                    predicted_event=True,
                    predicted_delay_days=14,
                    predicted_cost_usd=50000,
                    predicted_confidence=0.75,
                    recommended_action="REROUTE",
                    event_occurred=correct,
                    prediction_correct=correct,
                    predicted_at=datetime.utcnow() - timedelta(weeks=3-week),
                )
                outcome.observed_at = datetime.utcnow() - timedelta(weeks=3-week)
                feedback_service._outcome_store[outcome.outcome_id] = outcome

        trend = await feedback_analyzer.analyze_trend(
            metric="overall_accuracy",
            periods=4,
            period_type="weekly",
        )

        assert trend.metric == "overall_accuracy"
        # Should show improving trend
        assert trend.current_value > trend.previous_value

    @pytest.mark.asyncio
    async def test_get_improvement_insights(
        self,
        feedback_service: FeedbackService,
        feedback_analyzer: FeedbackAnalyzer,
    ):
        """Analyzer should generate improvement insights."""
        # Create some outcomes
        for i in range(20):
            outcome = OutcomeRecord(
                outcome_id=f"out_insight_{i}",
                decision_id=f"dec_insight_{i}",
                customer_id="cust_insight",
                signal_id="sig_red_sea_001",
                predicted_event=True,
                predicted_delay_days=14,
                predicted_cost_usd=50000,
                predicted_confidence=0.75,
                recommended_action="REROUTE",
                event_occurred=True,
                actual_delay_days=12,
                actual_cost_usd=45000,
                prediction_correct=True,
                delay_accurate=True,
                cost_accurate=True,
                value_delivered_usd=35000,
                predicted_at=datetime.utcnow() - timedelta(days=7),
            )
            feedback_service._outcome_store[outcome.outcome_id] = outcome

        insights = await feedback_analyzer.get_improvement_insights(
            days=30,
            min_samples=10,
        )

        assert "summary" in insights
        assert "strengths" in insights
        assert "weaknesses" in insights
        assert "recommendations" in insights
        assert "overall_grade" in insights["summary"]


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestFeedbackIntegration:
    """Integration tests for feedback system."""

    @pytest.mark.asyncio
    async def test_full_feedback_workflow(self):
        """Full feedback workflow should work end-to-end."""
        # Create service and analyzer
        service = create_feedback_service()
        analyzer = create_feedback_analyzer(service)

        # 1. Record customer feedback
        feedback = await service.record_customer_feedback(
            feedback=CustomerFeedbackCreate(
                decision_id="dec_workflow_001",
                feedback_type=FeedbackType.ACTION_TAKEN,
                action_followed=ActionFollowed.FOLLOWED_EXACTLY,
                actual_action_taken="REROUTE",
                satisfaction=SatisfactionLevel.VERY_SATISFIED,
                actual_delay_days=10,
                actual_cost_usd=40000,
                event_occurred=True,
                notes="Excellent recommendation!",
            ),
            customer_id="cust_workflow",
        )

        assert feedback.feedback_id is not None
        assert feedback.is_positive is True

        # 2. Record outcome
        outcome = await service.record_outcome(
            outcome_data=OutcomeRecordCreate(
                decision_id="dec_workflow_002",
                event_occurred=True,
                actual_delay_days=12,
                actual_cost_usd=48000,
                action_taken="REROUTE",
                action_cost_usd=8000,
            )
        )

        assert outcome.outcome_id is not None

        # 3. Get stats
        stats = await service.get_feedback_stats(
            customer_id="cust_workflow",
            days=30,
        )

        assert stats["total_feedback"] >= 1

        # 4. Generate reports
        accuracy = await analyzer.generate_accuracy_report(days=30)
        calibration = await analyzer.generate_calibration_report(days=30)
        insights = await analyzer.get_improvement_insights(days=30)

        assert accuracy.report_id is not None
        assert calibration.report_id is not None
        assert insights is not None

    @pytest.mark.asyncio
    async def test_singleton_service(self):
        """Global service singleton should work."""
        service1 = get_feedback_service()
        service2 = get_feedback_service()

        assert service1 is service2
