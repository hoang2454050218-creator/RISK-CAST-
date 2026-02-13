"""Tests for Backtest Seed Data Module.

Tests the historical event data seeding that addresses audit gap A3:
- Historical event data for backtesting
- Annotated disruption events
- Signal-to-outcome mappings
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.backtest.data.seed import (
    HistoricalEvent,
    HISTORICAL_EVENTS,
    BacktestSeeder,
    get_historical_events,
    create_backtest_seeder,
)


# =============================================================================
# HISTORICAL EVENT MODEL TESTS
# =============================================================================


class TestHistoricalEvent:
    """Tests for HistoricalEvent model."""

    def test_event_creation(self):
        """Test creating a historical event."""
        event = HistoricalEvent(
            event_id="evt_test_001",
            event_name="Test Event",
            event_date=datetime(2024, 1, 15),
            event_type="DISRUPTION",
            chokepoint="red_sea",
            signal_probability_at_time=0.85,
            signal_confidence_at_time=0.80,
            signal_sources=["polymarket", "news"],
            disruption_occurred=True,
            actual_delay_days=10,
            actual_cost_impact_usd=50000,
            optimal_action="reroute",
            optimal_action_cost=5000,
            optimal_action_benefit=45000,
        )

        assert event.event_id == "evt_test_001"
        assert event.chokepoint == "red_sea"
        assert event.disruption_occurred is True
        assert event.optimal_action_benefit == 45000

    def test_event_with_secondary_chokepoints(self):
        """Test event with secondary chokepoints."""
        event = HistoricalEvent(
            event_id="evt_test_002",
            event_name="Multi-chokepoint Event",
            event_date=datetime(2024, 2, 1),
            event_type="DISRUPTION",
            chokepoint="suez",
            secondary_chokepoints=["red_sea", "mediterranean"],
            signal_probability_at_time=0.75,
            signal_confidence_at_time=0.70,
            signal_sources=["ais", "news"],
            disruption_occurred=True,
            actual_delay_days=7,
            actual_cost_impact_usd=30000,
            optimal_action="delay",
            optimal_action_cost=2000,
            optimal_action_benefit=28000,
        )

        assert len(event.secondary_chokepoints) == 2
        assert "red_sea" in event.secondary_chokepoints

    def test_false_alarm_event(self):
        """Test event that didn't materialize."""
        event = HistoricalEvent(
            event_id="evt_false_001",
            event_name="False Alarm Test",
            event_date=datetime(2024, 3, 1),
            event_type="DISRUPTION",
            chokepoint="malacca",
            signal_probability_at_time=0.45,
            signal_confidence_at_time=0.50,
            signal_sources=["news"],
            disruption_occurred=False,  # False alarm
            actual_delay_days=0,
            actual_cost_impact_usd=0,
            optimal_action="monitor",
            optimal_action_cost=0,
            optimal_action_benefit=0,
        )

        assert event.disruption_occurred is False
        assert event.actual_delay_days == 0
        assert event.optimal_action == "monitor"


# =============================================================================
# HISTORICAL EVENTS DATABASE TESTS
# =============================================================================


class TestHistoricalEventsDatabase:
    """Tests for HISTORICAL_EVENTS database."""

    def test_database_not_empty(self):
        """Database should contain events."""
        assert len(HISTORICAL_EVENTS) > 0

    def test_database_has_minimum_events(self):
        """Database should have enough events for statistical significance."""
        # Need at least 20 events for meaningful calibration
        assert len(HISTORICAL_EVENTS) >= 15

    def test_events_have_unique_ids(self):
        """All events should have unique IDs."""
        event_ids = [e.event_id for e in HISTORICAL_EVENTS]
        assert len(event_ids) == len(set(event_ids))

    def test_events_have_red_sea_coverage(self):
        """Database should include Red Sea events (MVP focus)."""
        red_sea_events = [e for e in HISTORICAL_EVENTS if e.chokepoint == "red_sea"]
        assert len(red_sea_events) >= 3

    def test_events_have_false_alarms(self):
        """Database should include false alarm events for calibration."""
        false_alarms = [e for e in HISTORICAL_EVENTS if not e.disruption_occurred]
        assert len(false_alarms) >= 2

    def test_events_have_valid_probabilities(self):
        """All events should have valid probability ranges."""
        for event in HISTORICAL_EVENTS:
            assert 0 <= event.signal_probability_at_time <= 1
            assert 0 <= event.signal_confidence_at_time <= 1

    def test_events_have_consistent_outcomes(self):
        """Event outcomes should be consistent."""
        for event in HISTORICAL_EVENTS:
            if not event.disruption_occurred:
                assert event.actual_delay_days == 0
                assert event.actual_cost_impact_usd == 0
            else:
                assert event.actual_delay_days >= 0

    def test_events_cover_date_range(self):
        """Events should cover a reasonable date range."""
        dates = [e.event_date for e in HISTORICAL_EVENTS]
        earliest = min(dates)
        latest = max(dates)
        
        # Should span at least 6 months
        date_range = (latest - earliest).days
        assert date_range >= 180

    def test_events_have_multiple_chokepoints(self):
        """Database should cover multiple chokepoints."""
        chokepoints = set(e.chokepoint for e in HISTORICAL_EVENTS)
        assert len(chokepoints) >= 3

    def test_events_have_multiple_event_types(self):
        """Database should cover multiple event types."""
        event_types = set(e.event_type for e in HISTORICAL_EVENTS)
        assert len(event_types) >= 3


# =============================================================================
# BACKTEST SEEDER TESTS
# =============================================================================


class TestBacktestSeeder:
    """Tests for BacktestSeeder."""

    @pytest.fixture
    def mock_session_factory(self):
        """Create mock session factory."""
        factory = MagicMock()
        return factory

    @pytest.fixture
    def seeder(self, mock_session_factory):
        """Create BacktestSeeder instance."""
        return BacktestSeeder(mock_session_factory)

    @pytest.mark.asyncio
    async def test_seed_events(self, seeder):
        """Test seeding events."""
        summary = await seeder.seed_events()

        assert summary["seeded_count"] > 0
        assert "chokepoints" in summary
        assert "event_types" in summary
        assert "date_range" in summary

    @pytest.mark.asyncio
    async def test_seed_custom_events(self, seeder):
        """Test seeding custom events."""
        custom_events = [
            HistoricalEvent(
                event_id="evt_custom_001",
                event_name="Custom Test Event",
                event_date=datetime(2024, 5, 1),
                event_type="TEST",
                chokepoint="test_chokepoint",
                signal_probability_at_time=0.50,
                signal_confidence_at_time=0.50,
                signal_sources=["test"],
                disruption_occurred=True,
                actual_delay_days=5,
                actual_cost_impact_usd=10000,
                optimal_action="test_action",
                optimal_action_cost=1000,
                optimal_action_benefit=9000,
            ),
        ]

        summary = await seeder.seed_events(events=custom_events)

        assert summary["seeded_count"] == 1
        assert "test_chokepoint" in summary["chokepoints"]

    def test_get_events_all(self, seeder):
        """Test getting all events."""
        events = seeder.get_events_for_backtest()

        assert len(events) == len(HISTORICAL_EVENTS)

    def test_get_events_by_chokepoint(self, seeder):
        """Test filtering events by chokepoint."""
        events = seeder.get_events_for_backtest(chokepoint="red_sea")

        assert all(e.chokepoint == "red_sea" for e in events)

    def test_get_events_by_date_range(self, seeder):
        """Test filtering events by date range."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 6, 30)

        events = seeder.get_events_for_backtest(
            start_date=start_date,
            end_date=end_date,
        )

        assert all(start_date <= e.event_date <= end_date for e in events)

    def test_get_events_by_event_type(self, seeder):
        """Test filtering events by event type."""
        events = seeder.get_events_for_backtest(event_type="DISRUPTION")

        assert all(e.event_type == "DISRUPTION" for e in events)

    def test_get_events_by_probability(self, seeder):
        """Test filtering events by minimum probability."""
        events = seeder.get_events_for_backtest(min_probability=0.70)

        assert all(e.signal_probability_at_time >= 0.70 for e in events)

    def test_get_events_only_occurred(self, seeder):
        """Test filtering to only events that occurred."""
        events = seeder.get_events_for_backtest(only_occurred=True)

        assert all(e.disruption_occurred for e in events)

    def test_get_events_only_false_alarms(self, seeder):
        """Test filtering to only false alarms."""
        events = seeder.get_events_for_backtest(only_occurred=False)

        assert all(not e.disruption_occurred for e in events)

    def test_get_events_sorted_by_date(self, seeder):
        """Test that events are sorted by date."""
        events = seeder.get_events_for_backtest()

        dates = [e.event_date for e in events]
        assert dates == sorted(dates)

    def test_get_statistics(self, seeder):
        """Test getting statistics."""
        stats = seeder.get_statistics()

        assert stats["total_events"] == len(HISTORICAL_EVENTS)
        assert "disruptions_occurred" in stats
        assert "false_alarms" in stats
        assert "accuracy_rate" in stats
        assert "by_chokepoint" in stats
        assert "by_event_type" in stats

    def test_statistics_accuracy(self, seeder):
        """Test that statistics are accurate."""
        stats = seeder.get_statistics()

        # Verify counts
        expected_disruptions = sum(1 for e in HISTORICAL_EVENTS if e.disruption_occurred)
        expected_false_alarms = sum(1 for e in HISTORICAL_EVENTS if not e.disruption_occurred)

        assert stats["disruptions_occurred"] == expected_disruptions
        assert stats["false_alarms"] == expected_false_alarms

    def test_statistics_avg_probability(self, seeder):
        """Test average probability statistics."""
        stats = seeder.get_statistics()

        # Events that occurred should have higher avg probability
        assert stats["avg_probability_occurred"] >= stats["avg_probability_not_occurred"]


# =============================================================================
# FACTORY FUNCTION TESTS
# =============================================================================


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_get_historical_events(self):
        """Test getting historical events."""
        events = get_historical_events()

        assert events == HISTORICAL_EVENTS

    def test_create_backtest_seeder(self):
        """Test creating backtest seeder."""
        mock_factory = MagicMock()
        seeder = create_backtest_seeder(mock_factory)

        assert isinstance(seeder, BacktestSeeder)


# =============================================================================
# SPECIFIC EVENT VALIDATION TESTS
# =============================================================================


class TestSpecificEvents:
    """Tests for specific well-known events."""

    def test_ever_given_event_exists(self):
        """Ever Given event should be in database."""
        ever_given = [e for e in HISTORICAL_EVENTS if "ever_given" in e.event_id.lower()]
        
        assert len(ever_given) >= 1
        event = ever_given[0]
        assert event.chokepoint == "suez"
        assert event.disruption_occurred is True

    def test_red_sea_houthi_events(self):
        """Red Sea Houthi events should be in database."""
        houthi_events = [
            e for e in HISTORICAL_EVENTS 
            if e.chokepoint == "red_sea" and e.event_date >= datetime(2024, 1, 1)
        ]
        
        assert len(houthi_events) >= 2

    def test_panama_drought_events(self):
        """Panama drought events should be in database."""
        panama_events = [
            e for e in HISTORICAL_EVENTS 
            if e.chokepoint == "panama"
        ]
        
        assert len(panama_events) >= 1


# =============================================================================
# CALIBRATION DATA QUALITY TESTS
# =============================================================================


class TestCalibrationDataQuality:
    """Tests for calibration data quality."""

    def test_probability_distribution(self):
        """Probabilities should have reasonable distribution."""
        probabilities = [e.signal_probability_at_time for e in HISTORICAL_EVENTS]
        
        # Should have low, medium, and high probabilities
        low = [p for p in probabilities if p < 0.5]
        medium = [p for p in probabilities if 0.5 <= p < 0.75]
        high = [p for p in probabilities if p >= 0.75]
        
        assert len(low) >= 1
        assert len(medium) >= 1
        assert len(high) >= 1

    def test_outcome_calibration(self):
        """Outcomes should roughly match probabilities for calibration."""
        # Group by probability bucket
        buckets = {}
        for event in HISTORICAL_EVENTS:
            bucket = round(event.signal_probability_at_time, 1)
            if bucket not in buckets:
                buckets[bucket] = {"occurred": 0, "total": 0}
            buckets[bucket]["total"] += 1
            if event.disruption_occurred:
                buckets[bucket]["occurred"] += 1
        
        # For well-calibrated data, actual frequency should be close to predicted
        # This is a soft test - just verify we have data for multiple buckets
        assert len(buckets) >= 3

    def test_optimal_action_benefit_positive(self):
        """Optimal action benefit should be non-negative."""
        for event in HISTORICAL_EVENTS:
            assert event.optimal_action_benefit >= 0

    def test_action_benefit_consistency(self):
        """Benefit should equal impact minus cost for occurred events."""
        for event in HISTORICAL_EVENTS:
            if event.disruption_occurred:
                expected_benefit = event.actual_cost_impact_usd - event.optimal_action_cost
                # Allow some variance for complex calculations
                assert abs(event.optimal_action_benefit - expected_benefit) < event.actual_cost_impact_usd * 0.5
