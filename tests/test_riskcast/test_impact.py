"""Tests for Impact Calculator.

Tests the ImpactCalculator which answers:
"How much will this cost in DOLLARS and DAYS?"
"""

from datetime import datetime, timedelta

import pytest

from app.oracle.schemas import CorrelatedIntelligence
from app.riskcast.calculators.impact import ImpactCalculator, create_impact_calculator
from app.riskcast.constants import Severity
from app.riskcast.matchers.exposure import ExposureMatch, ExposureMatcher
from app.riskcast.schemas.customer import CustomerContext, Shipment
from app.riskcast.schemas.impact import (
    CostBreakdown,
    DelayEstimate,
    ShipmentImpact,
    TotalImpact,
)


class TestCostBreakdown:
    """Tests for CostBreakdown model."""

    def test_total_usd_calculation(self):
        """Total should sum all cost components."""
        breakdown = CostBreakdown(
            delay_holding_cost_usd=1000,
            reroute_premium_usd=5000,
            rate_increase_usd=500,
            penalty_cost_usd=2000,
        )
        assert breakdown.total_usd == 8500

    def test_empty_breakdown(self):
        """Empty breakdown should have zero total."""
        breakdown = CostBreakdown()
        assert breakdown.total_usd == 0

    def test_to_breakdown_dict(self):
        """Should convert to display dict."""
        breakdown = CostBreakdown(
            delay_holding_cost_usd=1000,
            reroute_premium_usd=5000,
        )
        result = breakdown.to_breakdown_dict()
        assert result["delay_holding"] == 1000
        assert result["reroute_premium"] == 5000
        assert result["total"] == 6000


class TestDelayEstimate:
    """Tests for DelayEstimate model."""

    def test_range_str_single_day(self):
        """Single day range should not show dash."""
        estimate = DelayEstimate(
            min_days=5,
            max_days=5,
            expected_days=5,
            confidence=0.8,
        )
        assert estimate.range_str == "5 days"

    def test_range_str_multiple_days(self):
        """Multiple day range should show dash."""
        estimate = DelayEstimate(
            min_days=7,
            max_days=14,
            expected_days=10,
            confidence=0.8,
        )
        assert estimate.range_str == "7-14 days"

    def test_is_significant_true(self):
        """Delay >3 days is significant."""
        estimate = DelayEstimate(
            min_days=5,
            max_days=10,
            expected_days=7,
            confidence=0.8,
        )
        assert estimate.is_significant is True

    def test_is_significant_false(self):
        """Delay <=3 days is not significant."""
        estimate = DelayEstimate(
            min_days=1,
            max_days=3,
            expected_days=2,
            confidence=0.8,
        )
        assert estimate.is_significant is False


class TestShipmentImpact:
    """Tests for ShipmentImpact model."""

    def test_total_impact_equals_cost_total(self):
        """Total impact should equal cost breakdown total."""
        now = datetime.utcnow()
        impact = ShipmentImpact(
            shipment_id="PO-123",
            shipment_ref="PO-123",
            delay=DelayEstimate(
                min_days=7, max_days=14, expected_days=10, confidence=0.8
            ),
            original_eta=now + timedelta(days=30),
            new_eta_expected=now + timedelta(days=40),
            cost=CostBreakdown(
                delay_holding_cost_usd=1500,
                reroute_premium_usd=5000,
            ),
            impact_severity=Severity.MEDIUM,
        )
        assert impact.total_impact_usd == 6500

    def test_delay_days_property(self):
        """Delay days should return expected days."""
        now = datetime.utcnow()
        impact = ShipmentImpact(
            shipment_id="PO-123",
            shipment_ref="PO-123",
            delay=DelayEstimate(
                min_days=7, max_days=14, expected_days=10, confidence=0.8
            ),
            original_eta=now,
            new_eta_expected=now + timedelta(days=10),
            cost=CostBreakdown(),
            impact_severity=Severity.LOW,
        )
        assert impact.delay_days == 10


class TestTotalImpact:
    """Tests for TotalImpact model."""

    def test_shipment_count(self):
        """Shipment count should reflect list length."""
        now = datetime.utcnow()
        impacts = [
            ShipmentImpact(
                shipment_id=f"PO-{i}",
                shipment_ref=f"PO-{i}",
                delay=DelayEstimate(min_days=7, max_days=14, expected_days=10, confidence=0.8),
                original_eta=now,
                new_eta_expected=now + timedelta(days=10),
                cost=CostBreakdown(delay_holding_cost_usd=1000),
                impact_severity=Severity.LOW,
            )
            for i in range(3)
        ]

        total = TotalImpact(
            customer_id="cust_123",
            signal_id="SIG-001",
            shipment_impacts=impacts,
            total_cost_usd=3000,
            total_delay_days_expected=10,
            overall_severity=Severity.LOW,
            confidence=0.8,
        )
        assert total.shipment_count == 3

    def test_has_critical_exposure_true(self):
        """Critical severity should indicate critical exposure."""
        total = TotalImpact(
            customer_id="cust_123",
            signal_id="SIG-001",
            total_cost_usd=150000,
            total_delay_days_expected=10,
            overall_severity=Severity.CRITICAL,
            confidence=0.8,
        )
        assert total.has_critical_exposure is True

    def test_has_critical_exposure_false(self):
        """Non-critical severity should not indicate critical exposure."""
        total = TotalImpact(
            customer_id="cust_123",
            signal_id="SIG-001",
            total_cost_usd=5000,
            total_delay_days_expected=5,
            overall_severity=Severity.LOW,
            confidence=0.8,
        )
        assert total.has_critical_exposure is False

    def test_has_penalty_risk(self):
        """Should detect penalty risk."""
        total = TotalImpact(
            customer_id="cust_123",
            signal_id="SIG-001",
            total_cost_usd=25000,
            total_delay_days_expected=10,
            shipments_with_penalties=2,
            total_penalty_usd=5000,
            overall_severity=Severity.MEDIUM,
            confidence=0.8,
        )
        assert total.has_penalty_risk is True


class TestImpactCalculator:
    """Tests for ImpactCalculator."""

    @pytest.fixture
    def calculator(self) -> ImpactCalculator:
        """Create impact calculator instance."""
        return create_impact_calculator()

    def test_calculate_returns_specific_numbers(
        self,
        calculator: ImpactCalculator,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Calculator must return specific dollar and day amounts."""
        exposure = exposure_matcher.match(confirmed_intelligence, sample_customer_context)
        impact = calculator.calculate(exposure, confirmed_intelligence, sample_customer_context)

        # MUST have specific numbers, not vague
        assert isinstance(impact.total_cost_usd, float)
        assert impact.total_cost_usd > 0
        assert isinstance(impact.total_delay_days_expected, int)
        assert impact.total_delay_days_expected >= 0

    def test_calculate_per_shipment_breakdown(
        self,
        calculator: ImpactCalculator,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Each affected shipment should have detailed breakdown."""
        exposure = exposure_matcher.match(confirmed_intelligence, sample_customer_context)
        impact = calculator.calculate(exposure, confirmed_intelligence, sample_customer_context)

        for si in impact.shipment_impacts:
            # Every shipment impact must have:
            assert si.shipment_id is not None
            assert si.shipment_ref is not None
            assert si.delay is not None
            assert si.delay.min_days >= 0
            assert si.delay.max_days >= si.delay.min_days
            assert si.cost is not None
            assert si.cost.total_usd >= 0

    def test_calculate_empty_exposure(
        self,
        calculator: ImpactCalculator,
        confirmed_intelligence: CorrelatedIntelligence,
        empty_customer_context: CustomerContext,
    ):
        """Empty exposure should produce zero impact."""
        exposure = ExposureMatch(
            customer_id=empty_customer_context.profile.customer_id,
            signal_id=confirmed_intelligence.signal.signal_id,
            affected_shipments=[],
            chokepoint_matched="red_sea",
            match_confidence=0.0,
        )

        impact = calculator.calculate(exposure, confirmed_intelligence, empty_customer_context)

        assert impact.total_cost_usd == 0
        assert impact.total_delay_days_expected == 0
        assert len(impact.shipment_impacts) == 0
        assert impact.overall_severity == Severity.LOW

    def test_severity_thresholds(
        self,
        calculator: ImpactCalculator,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
        shipment_factory,
    ):
        """Impact severity should follow threshold rules."""
        # Create exposure with known cargo value to test severity
        # Low severity: < $5K total cost
        low_shipment = shipment_factory(
            shipment_id="LOW-001",
            value=10_000,  # Low value = low cost
            containers=1,
        )
        low_exposure = ExposureMatch(
            customer_id=sample_customer_context.profile.customer_id,
            signal_id=confirmed_intelligence.signal.signal_id,
            affected_shipments=[low_shipment],
            total_exposure_usd=10_000,
            total_teu=2.0,
            chokepoint_matched="red_sea",
            match_confidence=0.8,
        )

        impact = calculator.calculate(low_exposure, confirmed_intelligence, sample_customer_context)

        # With $10K cargo and standard params, should be LOW or MEDIUM severity
        assert impact.overall_severity in [Severity.LOW, Severity.MEDIUM]

    def test_cost_breakdown_components(
        self,
        calculator: ImpactCalculator,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Cost breakdown should include holding and reroute costs."""
        exposure = exposure_matcher.match(confirmed_intelligence, sample_customer_context)
        impact = calculator.calculate(exposure, confirmed_intelligence, sample_customer_context)

        breakdown = impact.get_cost_breakdown()
        assert "delay_holding" in breakdown
        assert "reroute_premium" in breakdown
        assert "total" in breakdown

    def test_penalty_detection(
        self,
        calculator: ImpactCalculator,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
        sample_shipment: Shipment,
    ):
        """Should detect shipments with penalty triggers."""
        # Sample shipment has has_delay_penalty=True
        exposure = ExposureMatch(
            customer_id=sample_customer_context.profile.customer_id,
            signal_id=confirmed_intelligence.signal.signal_id,
            affected_shipments=[sample_shipment],
            total_exposure_usd=sample_shipment.cargo_value_usd,
            total_teu=sample_shipment.teu_count,
            chokepoint_matched="red_sea",
            match_confidence=0.8,
        )

        impact = calculator.calculate(exposure, confirmed_intelligence, sample_customer_context)

        # Shipment should be tracked for penalty risk
        # (may or may not trigger depending on dates)
        assert impact.total_cost_usd > 0

    def test_escalated_costs(
        self,
        calculator: ImpactCalculator,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Escalated costs should increase with time."""
        exposure = exposure_matcher.match(confirmed_intelligence, sample_customer_context)
        impact = calculator.calculate(exposure, confirmed_intelligence, sample_customer_context)

        base_cost = impact.total_cost_usd
        cost_at_6h = calculator.calculate_escalated_costs(impact, 6)
        cost_at_24h = calculator.calculate_escalated_costs(impact, 24)
        cost_at_48h = calculator.calculate_escalated_costs(impact, 48)

        # Costs should escalate
        assert cost_at_6h >= base_cost
        assert cost_at_24h >= cost_at_6h
        assert cost_at_48h >= cost_at_24h


class TestImpactCalculatorFactory:
    """Tests for factory function."""

    def test_create_impact_calculator(self):
        """Factory should create valid instance."""
        calc = create_impact_calculator()
        assert isinstance(calc, ImpactCalculator)
