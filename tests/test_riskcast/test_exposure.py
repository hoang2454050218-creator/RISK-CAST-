"""Tests for Exposure Matcher.

Tests ExposureMatch model and ExposureMatcher logic.
"""

from datetime import datetime, timedelta

import pytest

from app.omen.schemas import Chokepoint
from app.oracle.schemas import CorrelatedIntelligence, CorrelationStatus
from app.riskcast.constants import ShipmentStatus
from app.riskcast.matchers.exposure import ExposureMatch, ExposureMatcher
from app.riskcast.schemas.customer import CustomerContext, Shipment


class TestExposureMatch:
    """Tests for ExposureMatch model."""

    def test_has_exposure_true(self, sample_shipment: Shipment):
        """Test has_exposure is True when shipments exist."""
        match = ExposureMatch(
            customer_id="cust_test",
            signal_id="signal_test",
            affected_shipments=[sample_shipment],
            total_exposure_usd=150_000,
            total_teu=6.0,
            chokepoint_matched="red_sea",
            match_confidence=0.85,
            actionable_shipments=1,
        )
        assert match.has_exposure is True
        assert match.shipment_count == 1

    def test_has_exposure_false(self):
        """Test has_exposure is False when no shipments."""
        match = ExposureMatch(
            customer_id="cust_test",
            signal_id="signal_test",
            affected_shipments=[],
            total_exposure_usd=0,
            total_teu=0,
            chokepoint_matched="red_sea",
            match_confidence=0,
            actionable_shipments=0,
        )
        assert match.has_exposure is False
        assert match.shipment_count == 0

    def test_has_penalty_risk(self, sample_shipment: Shipment, pacific_shipment: Shipment):
        """Test penalty risk detection."""
        # With penalty shipments
        match_with_penalty = ExposureMatch(
            customer_id="cust_test",
            signal_id="signal_test",
            affected_shipments=[sample_shipment],
            total_exposure_usd=150_000,
            total_teu=6.0,
            chokepoint_matched="red_sea",
            match_confidence=0.85,
            actionable_shipments=1,
            shipments_with_penalties=1,
        )
        assert match_with_penalty.has_penalty_risk is True

        # Without penalty shipments
        match_no_penalty = ExposureMatch(
            customer_id="cust_test",
            signal_id="signal_test",
            affected_shipments=[pacific_shipment],
            total_exposure_usd=200_000,
            total_teu=10.0,
            chokepoint_matched="red_sea",
            match_confidence=0.85,
            actionable_shipments=1,
            shipments_with_penalties=0,
        )
        assert match_no_penalty.has_penalty_risk is False


class TestExposureMatcher:
    """Tests for ExposureMatcher."""

    def test_match_finds_affected_shipments(
        self,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Test that matcher finds shipments affected by signal."""
        match = exposure_matcher.match(confirmed_intelligence, sample_customer_context)

        assert match.has_exposure is True
        assert match.shipment_count == 2  # Both shipments go through Red Sea
        assert match.total_exposure_usd == 650_000
        assert match.chokepoint_matched == "red_sea"

    def test_match_no_exposure_for_unrelated_chokepoint(
        self,
        exposure_matcher: ExposureMatcher,
        intelligence_factory,
        sample_customer_context: CustomerContext,
    ):
        """Test no exposure when signal is for unrelated chokepoint."""
        # Create signal for Panama (customer's shipments don't go through Panama)
        panama_intel = intelligence_factory(
            signal_id="OMEN-PANAMA-001",
            chokepoint=Chokepoint.PANAMA,
        )

        match = exposure_matcher.match(panama_intel, sample_customer_context)

        assert match.has_exposure is False
        assert match.shipment_count == 0
        assert match.total_exposure_usd == 0

    def test_match_no_exposure_for_empty_context(
        self,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        empty_customer_context: CustomerContext,
    ):
        """Test no exposure when customer has no shipments."""
        match = exposure_matcher.match(confirmed_intelligence, empty_customer_context)

        assert match.has_exposure is False
        assert match.shipment_count == 0

    def test_match_excludes_delivered_shipments(
        self,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        mixed_shipments_context: CustomerContext,
    ):
        """Test that delivered shipments are excluded."""
        match = exposure_matcher.match(confirmed_intelligence, mixed_shipments_context)

        # Should find: sample_shipment (BOOKED), in_transit_shipment (IN_TRANSIT)
        # Should exclude: delivered_shipment (DELIVERED)
        # Should exclude: pacific_shipment (wrong chokepoint)
        affected_ids = [s.shipment_id for s in match.affected_shipments]

        assert "PO-4521" in affected_ids  # sample_shipment
        assert "PO-TRANSIT-001" in affected_ids  # in_transit
        assert "PO-DELIVERED" not in affected_ids  # excluded
        assert "PO-PACIFIC-001" not in affected_ids  # wrong route

    def test_match_excludes_pacific_route(
        self,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        mixed_shipments_context: CustomerContext,
    ):
        """Test that Pacific route shipments are excluded from Red Sea signal."""
        match = exposure_matcher.match(confirmed_intelligence, mixed_shipments_context)

        affected_ids = [s.shipment_id for s in match.affected_shipments]
        assert "PO-PACIFIC-001" not in affected_ids

    def test_timing_overlap_past_shipment(
        self,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_profile,
        now: datetime,
    ):
        """Test that shipments arriving before event are excluded."""
        # Create shipment that already arrived
        past_shipment = Shipment(
            shipment_id="PO-PAST",
            customer_id=sample_customer_profile.customer_id,
            origin_port="VNHCM",
            destination_port="NLRTM",
            route_chokepoints=["malacca", "red_sea", "suez"],
            etd=now - timedelta(days=60),
            eta=now - timedelta(days=20),  # Arrived 20 days ago
            cargo_value_usd=100_000,
            status=ShipmentStatus.IN_TRANSIT,  # Even if status not updated
        )

        context = CustomerContext(
            profile=sample_customer_profile,
            active_shipments=[past_shipment],
        )

        match = exposure_matcher.match(confirmed_intelligence, context)

        # Should not find this shipment (already past the event window)
        assert match.has_exposure is False

    def test_timing_overlap_future_shipment(
        self,
        exposure_matcher: ExposureMatcher,
        intelligence_factory,
        sample_customer_profile,
        now: datetime,
    ):
        """Test that shipments departing after event ends are excluded."""
        # Create intelligence with short event window
        short_intel = intelligence_factory(
            signal_id="OMEN-SHORT-001",
            chokepoint=Chokepoint.RED_SEA,
        )
        # Modify temporal scope to end soon
        short_intel.signal.temporal.latest_resolution = now + timedelta(days=5)

        # Create shipment departing after event ends
        future_shipment = Shipment(
            shipment_id="PO-FUTURE",
            customer_id=sample_customer_profile.customer_id,
            origin_port="VNHCM",
            destination_port="NLRTM",
            route_chokepoints=["malacca", "red_sea", "suez"],
            etd=now + timedelta(days=30),  # Departs way after event ends
            eta=now + timedelta(days=60),
            cargo_value_usd=100_000,
            status=ShipmentStatus.BOOKED,
        )

        context = CustomerContext(
            profile=sample_customer_profile,
            active_shipments=[future_shipment],
        )

        match = exposure_matcher.match(short_intel, context)

        # Should not find this shipment (departs after event ends)
        assert match.has_exposure is False

    def test_confidence_calculation(
        self,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Test confidence calculation."""
        match = exposure_matcher.match(confirmed_intelligence, sample_customer_context)

        # Confidence should be between 0 and 1
        assert 0 <= match.match_confidence <= 1

        # CONFIRMED status with good data should have high confidence
        assert match.match_confidence >= 0.7

    def test_confidence_lower_for_predicted(
        self,
        exposure_matcher: ExposureMatcher,
        predicted_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Test that predicted (non-confirmed) signals have lower confidence."""
        match = exposure_matcher.match(predicted_intelligence, sample_customer_context)

        # Should still find shipments
        assert match.has_exposure is True

        # But confidence should be lower than confirmed
        # predicted_intelligence has combined_confidence of 0.65
        assert match.match_confidence < 0.85

    def test_earliest_impact_calculation(
        self,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Test earliest impact time calculation."""
        match = exposure_matcher.match(confirmed_intelligence, sample_customer_context)

        assert match.earliest_impact is not None
        # Should be the earlier ETA of the two shipments
        etas = [s.eta for s in match.affected_shipments]
        assert match.earliest_impact == min(etas)

    def test_actionable_count(
        self,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        mixed_shipments_context: CustomerContext,
    ):
        """Test counting actionable shipments."""
        match = exposure_matcher.match(confirmed_intelligence, mixed_shipments_context)

        # sample_shipment is BOOKED (actionable)
        # in_transit_shipment is IN_TRANSIT (not actionable)
        assert match.actionable_shipments == 1

    def test_penalty_shipments_count(
        self,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Test counting shipments with penalty clauses."""
        match = exposure_matcher.match(confirmed_intelligence, sample_customer_context)

        # sample_shipment and high_value_shipment both have penalties
        assert match.shipments_with_penalties == 2

    def test_match_multiple_customers(
        self,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
        empty_customer_context: CustomerContext,
    ):
        """Test matching against multiple customers."""
        contexts = [sample_customer_context, empty_customer_context]

        matches = exposure_matcher.match_multiple(confirmed_intelligence, contexts)

        # Should find 1 customer with exposure
        assert len(matches) == 1
        assert matches[0].customer_id == sample_customer_context.profile.customer_id


class TestExposureMatcherEdgeCases:
    """Edge case tests for ExposureMatcher."""

    def test_match_with_no_temporal_info(
        self,
        exposure_matcher: ExposureMatcher,
        intelligence_factory,
        sample_customer_context: CustomerContext,
    ):
        """Test matching when signal has no temporal info."""
        intel = intelligence_factory(signal_id="OMEN-NO-TIME-001")
        # Clear temporal info
        intel.signal.temporal.earliest_impact = None
        intel.signal.temporal.latest_resolution = None

        match = exposure_matcher.match(intel, sample_customer_context)

        # Should still work with default assumptions
        assert match.has_exposure is True

    def test_match_with_single_shipment(
        self,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_profile,
        sample_shipment: Shipment,
    ):
        """Test matching with single shipment."""
        context = CustomerContext(
            profile=sample_customer_profile,
            active_shipments=[sample_shipment],
        )

        match = exposure_matcher.match(confirmed_intelligence, context)

        assert match.has_exposure is True
        assert match.shipment_count == 1
        assert match.total_exposure_usd == 150_000

    def test_match_case_insensitive_chokepoint(
        self,
        exposure_matcher: ExposureMatcher,
        intelligence_factory,
        sample_customer_profile,
        now: datetime,
    ):
        """Test that chokepoint matching is case-insensitive."""
        intel = intelligence_factory(chokepoint=Chokepoint.RED_SEA)

        # Create shipment with lowercase chokepoint
        shipment = Shipment(
            shipment_id="PO-CASE-TEST",
            customer_id=sample_customer_profile.customer_id,
            origin_port="VNHCM",
            destination_port="NLRTM",
            route_chokepoints=["MALACCA", "RED_SEA", "SUEZ"],  # Uppercase
            etd=now + timedelta(days=5),
            eta=now + timedelta(days=35),
            cargo_value_usd=100_000,
        )

        context = CustomerContext(
            profile=sample_customer_profile,
            active_shipments=[shipment],
        )

        match = exposure_matcher.match(intel, context)

        assert match.has_exposure is True
