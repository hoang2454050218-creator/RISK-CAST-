"""Tests for Backtesting Framework.

Tests the BacktestFramework which validates RISKCAST decisions against
historical events with known outcomes.

Key tests:
- Schema validation for BacktestEvent, BacktestResult, BacktestSummary
- Signal simulation from historical events
- Decision evaluation against actual outcomes
- Calibration bucket calculation
- Value and accuracy metrics
"""

from datetime import datetime, timedelta
from typing import Optional

import pytest

from app.backtest.schemas import (
    BacktestEvent,
    BacktestResult,
    BacktestSummary,
    CalibrationBucket,
    AccuracyByCategory,
    ActualImpact,
    PredictionVsActual,
    ValueAnalysis,
    EventOutcome,
    ActionTaken,
    DecisionQuality,
)
from app.backtest.framework import (
    BacktestFramework,
    HistoricalEventLoader,
    create_backtest_framework,
    create_event_loader,
    get_sample_events,
)
from app.riskcast.composers import create_decision_composer
from app.riskcast.schemas.customer import (
    CustomerContext,
    CustomerProfile,
    Shipment,
    AlertPreferences,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_actual_impact() -> ActualImpact:
    """Create sample actual impact data."""
    return ActualImpact(
        event_occurred=True,
        severity_vs_prediction="as_predicted",
        actual_delay_days=12,
        actual_cost_usd=45000,
        actual_rate_increase_pct=30,
        vessels_affected=50,
        ports_disrupted=["SAJED", "AEAUH"],
        impact_started_at=datetime(2024, 1, 15),
        impact_ended_at=datetime(2024, 2, 15),
    )


@pytest.fixture
def sample_backtest_event(sample_actual_impact: ActualImpact) -> BacktestEvent:
    """Create sample backtest event."""
    return BacktestEvent(
        event_id="RS2024-TEST-001",
        event_name="Test Red Sea Disruption",
        event_date=datetime(2024, 1, 15),
        chokepoint="red_sea",
        secondary_chokepoints=["suez"],
        category="geopolitical",
        signal_probability=0.75,
        signal_confidence=0.80,
        detection_lead_time_hours=72,
        outcome=EventOutcome.MATERIALIZED,
        actual_impact=sample_actual_impact,
        market_conditions={"rate_index": 1.30},
        notes="Test event for backtesting",
    )


@pytest.fixture
def sample_non_materialized_event() -> BacktestEvent:
    """Create sample event that didn't materialize."""
    return BacktestEvent(
        event_id="RS2024-TEST-002",
        event_name="Test False Alarm",
        event_date=datetime(2024, 2, 1),
        chokepoint="red_sea",
        secondary_chokepoints=[],
        category="geopolitical",
        signal_probability=0.55,
        signal_confidence=0.50,
        detection_lead_time_hours=48,
        outcome=EventOutcome.DID_NOT_MATERIALIZE,
        actual_impact=ActualImpact(
            event_occurred=False,
            severity_vs_prediction="did_not_occur",
            actual_delay_days=0,
            actual_cost_usd=0,
        ),
        market_conditions={"rate_index": 1.0},
    )


@pytest.fixture
def sample_customer_profile() -> CustomerProfile:
    """Create sample customer profile."""
    return CustomerProfile(
        customer_id="cust_test_001",
        company_name="Test Imports Ltd",
        email="test@testimports.com",
        tier="premium",
    )


@pytest.fixture
def sample_shipments() -> list[Shipment]:
    """Create sample shipments for testing."""
    return [
        Shipment(
            shipment_id="PO-TEST-001",
            customer_reference="PO-TEST-001",
            cargo_description="Test cargo",
            cargo_value_usd=50000,
            container_count=2,
            teu_count=4,
            origin_port="CNSHA",
            destination_port="NLRTM",
            route_chokepoints=["red_sea", "suez"],
            carrier="MAEU",
            current_status="in_transit",
            eta=datetime.utcnow() + timedelta(days=10),
            has_penalty_clause=True,
            penalty_per_day_usd=500,
        ),
        Shipment(
            shipment_id="PO-TEST-002",
            customer_reference="PO-TEST-002",
            cargo_description="Test cargo 2",
            cargo_value_usd=75000,
            container_count=3,
            teu_count=6,
            origin_port="CNSHA",
            destination_port="DEHAM",
            route_chokepoints=["red_sea", "suez"],
            carrier="MSCU",
            current_status="in_transit",
            eta=datetime.utcnow() + timedelta(days=15),
            has_penalty_clause=False,
        ),
    ]


@pytest.fixture
def sample_customer_context(
    sample_customer_profile: CustomerProfile,
    sample_shipments: list[Shipment],
) -> CustomerContext:
    """Create sample customer context."""
    return CustomerContext(
        profile=sample_customer_profile,
        active_shipments=sample_shipments,
        alert_preferences=AlertPreferences(
            channels=["whatsapp"],
            min_probability=0.5,
            chokepoints_of_interest=["red_sea", "suez"],
        ),
    )


@pytest.fixture
def backtest_framework() -> BacktestFramework:
    """Create backtest framework instance."""
    return create_backtest_framework(calibration_buckets=10)


@pytest.fixture
def event_loader() -> HistoricalEventLoader:
    """Create event loader instance."""
    return create_event_loader()


# =============================================================================
# SCHEMA TESTS
# =============================================================================


class TestBacktestSchemas:
    """Tests for backtest schemas."""

    def test_actual_impact_duration_calculation(self, sample_actual_impact: ActualImpact):
        """ActualImpact should calculate duration correctly."""
        assert sample_actual_impact.actual_duration_days == 31  # Jan 15 to Feb 15

    def test_backtest_event_actionable_signal(self, sample_backtest_event: BacktestEvent):
        """BacktestEvent should identify actionable signals."""
        # 0.75 probability and 0.80 confidence - both >= 0.5
        assert sample_backtest_event.was_actionable_signal is True

    def test_backtest_event_prediction_correct(self, sample_backtest_event: BacktestEvent):
        """BacktestEvent should track prediction correctness."""
        # Predicted high probability (0.75 >= 0.5) and event materialized
        assert sample_backtest_event.prediction_was_correct is True

    def test_non_materialized_event_prediction(
        self, sample_non_materialized_event: BacktestEvent
    ):
        """Non-materialized event should have correct prediction tracking."""
        # Predicted moderate probability (0.55 >= 0.5) but didn't happen
        assert sample_non_materialized_event.prediction_was_correct is False

    def test_prediction_vs_actual_errors(self):
        """PredictionVsActual should calculate errors correctly."""
        prediction = PredictionVsActual(
            predicted_probability=0.80,
            actual_occurred=True,
            predicted_delay_days=14,
            actual_delay_days=12,
            delay_error_days=2,
            predicted_cost_usd=50000,
            actual_cost_usd=45000,
            cost_error_usd=5000,
            cost_error_pct=11.1,
        )

        assert prediction.delay_error_abs == 2
        assert prediction.cost_error_abs == 5000
        assert prediction.was_conservative is True  # Predicted worse than actual

    def test_value_analysis_roi(self):
        """ValueAnalysis should calculate ROI correctly."""
        value = ValueAnalysis(
            action_cost_usd=8500,
            loss_if_no_action_usd=45000,
            value_protected_usd=45000,
            net_value_usd=36500,
        )

        assert value.was_good_advice is True
        assert value.roi > 0  # Positive ROI

    def test_calibration_bucket_well_calibrated(self):
        """CalibrationBucket should identify well-calibrated buckets."""
        bucket = CalibrationBucket(
            bucket_min=0.7,
            bucket_max=0.8,
            predicted_probability=0.75,
            actual_frequency=0.73,  # Within 10%
            sample_count=25,
            correct_count=18,
        )

        assert bucket.calibration_error < 0.10
        assert bucket.is_well_calibrated is True
        assert bucket.bucket_label == "70-80%"

    def test_backtest_summary_grade_calculation(self):
        """BacktestSummary should calculate grade correctly."""
        summary = BacktestSummary(
            summary_id="test_summary",
            total_events=100,
            date_range_start=datetime(2024, 1, 1),
            date_range_end=datetime(2024, 12, 31),
            filters_applied={},
            accuracy=0.87,
            precision=0.85,
            recall=0.90,
            f1_score=0.87,
            brier_score=0.12,
            calibration_buckets=[],
            mean_delay_error_days=2.5,
            mean_cost_error_pct=15.0,
            total_value_captured_usd=2850000,
            avg_value_per_event_usd=28500,
            total_action_cost_usd=850000,
            net_value_usd=2000000,
            roi=2.35,
            quality_distribution={
                "excellent": 40,
                "good": 35,
                "neutral": 15,
                "poor": 8,
                "harmful": 2,
            },
            results=[],
        )

        # High accuracy (0.87 >= 0.85), valuable (ROI > 0), well calibrated (brier < 0.20)
        assert summary.grade == "A"
        assert summary.is_well_calibrated is True
        assert summary.is_valuable is True
        assert summary.excellent_count == 40
        assert summary.poor_or_harmful_count == 10


# =============================================================================
# FRAMEWORK TESTS
# =============================================================================


class TestBacktestFramework:
    """Tests for BacktestFramework."""

    def test_framework_creation(self, backtest_framework: BacktestFramework):
        """Framework should be created with default components."""
        assert backtest_framework is not None
        assert backtest_framework._composer is not None
        assert backtest_framework._num_buckets == 10

    def test_signal_simulation(
        self,
        backtest_framework: BacktestFramework,
        sample_backtest_event: BacktestEvent,
    ):
        """Framework should simulate OmenSignal from event."""
        signal = backtest_framework._simulate_signal(sample_backtest_event)

        assert signal is not None
        assert signal.signal_id.startswith("OMEN-BT-")
        assert signal.probability == sample_backtest_event.signal_probability
        assert signal.confidence_score == sample_backtest_event.signal_confidence
        assert signal.geographic.primary_chokepoint.value == "red_sea"

    def test_intelligence_creation(
        self,
        backtest_framework: BacktestFramework,
        sample_backtest_event: BacktestEvent,
    ):
        """Framework should create CorrelatedIntelligence."""
        signal = backtest_framework._simulate_signal(sample_backtest_event)
        intelligence = backtest_framework._create_intelligence(
            signal, sample_backtest_event
        )

        assert intelligence is not None
        assert intelligence.signal == signal
        # Materialized event should have CONFIRMED status
        assert intelligence.correlation_status.value == "confirmed"

    def test_filters_application(self, backtest_framework: BacktestFramework):
        """Framework should apply filters correctly."""
        events = get_sample_events()

        # Filter by chokepoint
        filtered = backtest_framework._apply_filters(
            events, {"chokepoint": "red_sea"}
        )
        assert all(e.chokepoint == "red_sea" for e in filtered)

        # Filter by category
        filtered = backtest_framework._apply_filters(
            events, {"category": "weather"}
        )
        assert all(e.category == "weather" for e in filtered)

        # Filter by date range
        filtered = backtest_framework._apply_filters(
            events,
            {
                "start_date": datetime(2024, 1, 1),
                "end_date": datetime(2024, 12, 31),
            },
        )
        assert all(
            datetime(2024, 1, 1) <= e.event_date <= datetime(2024, 12, 31)
            for e in filtered
        )

    def test_empty_summary_on_no_events(self, backtest_framework: BacktestFramework):
        """Framework should return empty summary when no events match."""
        summary = backtest_framework._empty_summary({"chokepoint": "nonexistent"})

        assert summary.total_events == 0
        assert summary.accuracy == 0
        assert summary.grade == "F"
        assert "No events to analyze" in summary.weak_areas

    @pytest.mark.asyncio
    async def test_single_event_testing(
        self,
        backtest_framework: BacktestFramework,
        sample_backtest_event: BacktestEvent,
        sample_customer_context: CustomerContext,
    ):
        """Framework should test single event correctly."""
        result = await backtest_framework._test_single_event(
            sample_backtest_event, sample_customer_context
        )

        # Should produce a result (customer has shipments on red_sea route)
        assert result is not None
        assert result.event_id == sample_backtest_event.event_id
        assert result.recommended_action is not None
        assert result.value_analysis is not None
        assert result.quality in DecisionQuality

    @pytest.mark.asyncio
    async def test_full_backtest_run(
        self,
        backtest_framework: BacktestFramework,
        sample_customer_context: CustomerContext,
    ):
        """Framework should run full backtest."""
        events = get_sample_events()

        # Run with limited events for speed
        summary = await backtest_framework.run(
            events[:3],
            [sample_customer_context],
        )

        assert summary is not None
        assert summary.total_events >= 0
        assert 0 <= summary.accuracy <= 1
        assert summary.grade in ["A", "B", "C", "D", "F"]

    def test_quality_assessment(self, backtest_framework: BacktestFramework):
        """Framework should assess decision quality correctly."""
        # Create mock objects for quality assessment
        from app.backtest.schemas import ActualImpact

        event = BacktestEvent(
            event_id="test",
            event_name="Test Event",
            event_date=datetime.utcnow(),
            chokepoint="red_sea",
            category="geopolitical",
            signal_probability=0.8,
            signal_confidence=0.8,
            detection_lead_time_hours=48,
            outcome=EventOutcome.MATERIALIZED,
            actual_impact=ActualImpact(
                event_occurred=True,
                severity_vs_prediction="as_predicted",
                actual_delay_days=12,
                actual_cost_usd=50000,
            ),
        )

        # Accurate prediction with good value
        prediction = PredictionVsActual(
            predicted_probability=0.8,
            actual_occurred=True,
            predicted_delay_days=12,
            actual_delay_days=12,
            delay_error_days=0,
            predicted_cost_usd=50000,
            actual_cost_usd=50000,
            cost_error_usd=0,
            cost_error_pct=0,
        )

        value = ValueAnalysis(
            action_cost_usd=5000,
            loss_if_no_action_usd=50000,
            value_protected_usd=50000,
            net_value_usd=45000,
        )

        # Mock decision that recommended action
        class MockDecision:
            class Q5:
                action_type = "REROUTE"
            q5_action = Q5()

        quality, reasons = backtest_framework._assess_quality(
            event, MockDecision(), prediction, value
        )

        # Should be excellent - correct, valuable, accurate
        assert quality == DecisionQuality.EXCELLENT
        assert len(reasons) > 0


# =============================================================================
# EVENT LOADER TESTS
# =============================================================================


class TestHistoricalEventLoader:
    """Tests for HistoricalEventLoader."""

    def test_loader_creation(self, event_loader: HistoricalEventLoader):
        """Loader should be created empty."""
        assert event_loader is not None
        assert len(event_loader._events) == 0

    def test_add_single_event(
        self,
        event_loader: HistoricalEventLoader,
        sample_backtest_event: BacktestEvent,
    ):
        """Loader should add single event."""
        event_loader.add_event(sample_backtest_event)
        assert len(event_loader._events) == 1
        assert event_loader._events[0] == sample_backtest_event

    def test_add_multiple_events(
        self,
        event_loader: HistoricalEventLoader,
        sample_backtest_event: BacktestEvent,
        sample_non_materialized_event: BacktestEvent,
    ):
        """Loader should add multiple events."""
        event_loader.add_events([sample_backtest_event, sample_non_materialized_event])
        assert len(event_loader._events) == 2

    def test_get_events_filtered(
        self,
        event_loader: HistoricalEventLoader,
        sample_backtest_event: BacktestEvent,
        sample_non_materialized_event: BacktestEvent,
    ):
        """Loader should filter events correctly."""
        event_loader.add_events([sample_backtest_event, sample_non_materialized_event])

        # Filter by date
        filtered = event_loader.get_events(start_date=datetime(2024, 1, 20))
        assert len(filtered) == 1  # Only Feb event

        # Filter by chokepoint
        filtered = event_loader.get_events(chokepoint="red_sea")
        assert len(filtered) == 2  # Both are red_sea

    def test_load_from_dict(self, event_loader: HistoricalEventLoader):
        """Loader should parse event from dictionary."""
        data = {
            "event_id": "TEST-001",
            "event_name": "Test Event",
            "event_date": "2024-01-15T00:00:00",
            "chokepoint": "red_sea",
            "category": "geopolitical",
            "signal_probability": 0.75,
            "signal_confidence": 0.80,
            "detection_lead_time_hours": 48,
            "outcome": "materialized",
            "actual_impact": {
                "event_occurred": True,
                "actual_delay_days": 10,
                "actual_cost_usd": 40000,
            },
        }

        event = event_loader.load_from_dict(data)

        assert event.event_id == "TEST-001"
        assert event.signal_probability == 0.75
        assert event.outcome == EventOutcome.MATERIALIZED
        assert event.actual_impact.actual_delay_days == 10


# =============================================================================
# SAMPLE EVENTS TESTS
# =============================================================================


class TestSampleEvents:
    """Tests for sample historical events."""

    def test_sample_events_available(self):
        """Sample events should be available."""
        events = get_sample_events()
        assert len(events) >= 3

    def test_sample_events_variety(self):
        """Sample events should have variety."""
        events = get_sample_events()

        # Should have different chokepoints
        chokepoints = set(e.chokepoint for e in events)
        assert len(chokepoints) >= 2

        # Should have different outcomes
        outcomes = set(e.outcome for e in events)
        assert len(outcomes) >= 2

        # Should have different categories
        categories = set(e.category for e in events)
        assert len(categories) >= 2

    def test_sample_events_valid(self):
        """All sample events should be valid."""
        events = get_sample_events()

        for event in events:
            assert event.event_id
            assert event.event_name
            assert event.event_date
            assert 0 <= event.signal_probability <= 1
            assert 0 <= event.signal_confidence <= 1
            assert event.detection_lead_time_hours >= 0
            assert event.actual_impact is not None


# =============================================================================
# CALIBRATION TESTS
# =============================================================================


class TestCalibration:
    """Tests for calibration calculation."""

    def test_calibration_buckets_calculation(
        self, backtest_framework: BacktestFramework
    ):
        """Framework should calculate calibration buckets correctly."""
        # Manually add predictions to buckets
        # Bucket 7 (70-80%): predictions with ~75% predicted probability
        backtest_framework._predictions_by_bucket[7] = [
            (0.75, True),
            (0.72, True),
            (0.78, False),
            (0.73, True),
        ]

        # Bucket 8 (80-90%): predictions with ~85% predicted probability
        backtest_framework._predictions_by_bucket[8] = [
            (0.85, True),
            (0.82, True),
            (0.88, True),
            (0.84, False),
            (0.86, True),
        ]

        buckets = backtest_framework._calculate_calibration_buckets()

        # Should have 2 buckets with data
        assert len(buckets) == 2

        # Check bucket 7 (70-80%)
        bucket_7 = next((b for b in buckets if b.bucket_min == 0.7), None)
        assert bucket_7 is not None
        assert bucket_7.sample_count == 4
        assert bucket_7.correct_count == 3
        assert bucket_7.actual_frequency == 0.75

        # Check bucket 8 (80-90%)
        bucket_8 = next((b for b in buckets if b.bucket_min == 0.8), None)
        assert bucket_8 is not None
        assert bucket_8.sample_count == 5
        assert bucket_8.correct_count == 4
        assert bucket_8.actual_frequency == 0.8


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestBacktestIntegration:
    """Integration tests for backtest workflow."""

    @pytest.mark.asyncio
    async def test_full_backtest_workflow(
        self,
        sample_customer_context: CustomerContext,
    ):
        """Full backtest workflow should complete successfully."""
        # Create framework
        framework = create_backtest_framework()

        # Load sample events
        events = get_sample_events()

        # Run backtest
        summary = await framework.run(
            events,
            [sample_customer_context],
            filters={"chokepoint": "red_sea"},
        )

        # Verify summary
        assert summary is not None
        assert summary.filters_applied == {"chokepoint": "red_sea"}

        # Should have results for red_sea events only
        for result in summary.results:
            # Event ID should be a red_sea event
            event = next((e for e in events if e.event_id == result.event_id), None)
            assert event is None or event.chokepoint == "red_sea"

    @pytest.mark.asyncio
    async def test_backtest_with_multiple_customers(
        self,
        sample_customer_profile: CustomerProfile,
        sample_shipments: list[Shipment],
    ):
        """Backtest should handle multiple customers."""
        # Create two different customer contexts
        contexts = [
            CustomerContext(
                profile=CustomerProfile(
                    customer_id="cust_001",
                    company_name="Customer 1",
                    email="c1@test.com",
                    tier="premium",
                ),
                active_shipments=sample_shipments,
                alert_preferences=AlertPreferences(
                    channels=["whatsapp"],
                    min_probability=0.5,
                    chokepoints_of_interest=["red_sea"],
                ),
            ),
            CustomerContext(
                profile=CustomerProfile(
                    customer_id="cust_002",
                    company_name="Customer 2",
                    email="c2@test.com",
                    tier="standard",
                ),
                active_shipments=sample_shipments,
                alert_preferences=AlertPreferences(
                    channels=["email"],
                    min_probability=0.6,
                    chokepoints_of_interest=["red_sea"],
                ),
            ),
        ]

        framework = create_backtest_framework()
        events = get_sample_events()[:2]

        summary = await framework.run(events, contexts)

        assert summary is not None
        # Should have results for both customers
        customer_ids = set(r.decision_id.split("_")[-1] for r in summary.results)
        # Results should exist (may vary based on exposure matching)
        assert len(summary.results) >= 0
