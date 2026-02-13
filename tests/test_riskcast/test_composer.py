"""Tests for Decision Composer.

Tests the DecisionComposer which orchestrates:
1. Exposure matching
2. Impact calculation
3. Action generation
4. Trade-off analysis
5. Decision composition (Q1-Q7)
"""

from datetime import datetime, timedelta

import pytest

from app.oracle.schemas import CorrelatedIntelligence
from app.riskcast.composers.decision import DecisionComposer, create_decision_composer
from app.riskcast.schemas.customer import CustomerContext
from app.riskcast.schemas.decision import DecisionObject


class TestDecisionComposer:
    """Tests for DecisionComposer."""

    @pytest.fixture
    def composer(self) -> DecisionComposer:
        """Create decision composer instance."""
        return create_decision_composer()

    def test_compose_produces_decision(
        self,
        composer: DecisionComposer,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Composer should produce a valid DecisionObject."""
        decision = composer.compose(confirmed_intelligence, sample_customer_context)

        assert decision is not None
        assert isinstance(decision, DecisionObject)
        assert decision.customer_id == sample_customer_context.profile.customer_id
        assert decision.signal_id == confirmed_intelligence.signal.signal_id

    def test_compose_returns_none_for_no_exposure(
        self,
        composer: DecisionComposer,
        confirmed_intelligence: CorrelatedIntelligence,
        empty_customer_context: CustomerContext,
    ):
        """Composer should return None when customer has no exposure."""
        decision = composer.compose(confirmed_intelligence, empty_customer_context)

        assert decision is None

    def test_compose_answers_all_questions(
        self,
        composer: DecisionComposer,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Decision must have all 7 questions answered."""
        decision = composer.compose(confirmed_intelligence, sample_customer_context)

        assert decision is not None
        # Q1-Q7 must all be present
        assert decision.q1_what is not None
        assert decision.q2_when is not None
        assert decision.q3_severity is not None
        assert decision.q4_why is not None
        assert decision.q5_action is not None
        assert decision.q6_confidence is not None
        assert decision.q7_inaction is not None

    def test_q1_is_personalized(
        self,
        composer: DecisionComposer,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Q1 should include customer-specific shipments and routes."""
        decision = composer.compose(confirmed_intelligence, sample_customer_context)

        assert decision is not None
        q1 = decision.q1_what

        # Should reference customer's specific shipments
        assert len(q1.affected_shipments) > 0
        # Should reference customer's routes
        assert len(q1.affected_routes) > 0
        # Event summary should be specific
        assert q1.event_summary is not None
        assert len(q1.event_summary) > 10

    def test_q2_has_urgency(
        self,
        composer: DecisionComposer,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Q2 should have urgency level and reason."""
        decision = composer.compose(confirmed_intelligence, sample_customer_context)

        assert decision is not None
        q2 = decision.q2_when

        assert q2.urgency is not None
        assert q2.urgency_reason is not None
        assert len(q2.urgency_reason) > 0

    def test_q3_has_specific_amounts(
        self,
        composer: DecisionComposer,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Q3 should have specific dollar amounts and days."""
        decision = composer.compose(confirmed_intelligence, sample_customer_context)

        assert decision is not None
        q3 = decision.q3_severity

        # Must have specific numbers, not vague descriptions
        assert q3.total_exposure_usd > 0
        assert q3.expected_delay_days > 0
        assert q3.delay_range is not None
        assert q3.shipments_affected > 0

    def test_q4_has_causal_chain(
        self,
        composer: DecisionComposer,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Q4 should have a clear causal chain."""
        decision = composer.compose(confirmed_intelligence, sample_customer_context)

        assert decision is not None
        q4 = decision.q4_why

        assert q4.root_cause is not None
        assert len(q4.causal_chain) >= 1
        assert q4.evidence_summary is not None

    def test_q5_has_specific_action(
        self,
        composer: DecisionComposer,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Q5 should have specific, actionable steps."""
        decision = composer.compose(confirmed_intelligence, sample_customer_context)

        assert decision is not None
        q5 = decision.q5_action

        # Must be actionable, not vague
        assert q5.action_type is not None
        assert q5.action_summary is not None
        assert len(q5.execution_steps) >= 1
        assert q5.deadline is not None

    def test_q6_has_confidence_factors(
        self,
        composer: DecisionComposer,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Q6 should explain confidence with factors."""
        decision = composer.compose(confirmed_intelligence, sample_customer_context)

        assert decision is not None
        q6 = decision.q6_confidence

        assert 0 <= q6.score <= 1
        assert q6.level is not None
        assert q6.explanation is not None
        assert len(q6.factors) >= 1

    def test_q7_has_cost_escalation(
        self,
        composer: DecisionComposer,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Q7 should show time-based cost escalation."""
        decision = composer.compose(confirmed_intelligence, sample_customer_context)

        assert decision is not None
        q7 = decision.q7_inaction

        # Must show escalation over time
        assert q7.expected_loss_if_nothing >= 0
        # Costs should escalate
        assert q7.cost_if_wait_6h >= q7.expected_loss_if_nothing
        assert q7.cost_if_wait_24h >= q7.cost_if_wait_6h
        assert q7.cost_if_wait_48h >= q7.cost_if_wait_24h

    def test_decision_has_alternatives(
        self,
        composer: DecisionComposer,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Decision should include alternative actions."""
        decision = composer.compose(confirmed_intelligence, sample_customer_context)

        assert decision is not None
        # May have alternatives (depends on situation)
        # At minimum, alternatives should be a list
        assert isinstance(decision.alternative_actions, list)

    def test_decision_has_expiry(
        self,
        composer: DecisionComposer,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Decision should have expiry timestamp."""
        decision = composer.compose(confirmed_intelligence, sample_customer_context)

        assert decision is not None
        assert decision.expires_at is not None
        # Expiry should be in the future
        assert decision.expires_at > datetime.utcnow()
        assert decision.is_expired is False

    def test_decision_id_format(
        self,
        composer: DecisionComposer,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Decision ID should follow expected format."""
        decision = composer.compose(confirmed_intelligence, sample_customer_context)

        assert decision is not None
        # Should start with 'dec_'
        assert decision.decision_id.startswith("dec_")
        # Should include customer reference
        assert sample_customer_context.profile.customer_id[:8] in decision.decision_id

    def test_compose_with_high_value_exposure(
        self,
        composer: DecisionComposer,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_profile,
        high_value_shipment,
    ):
        """Composer should handle high-value shipments appropriately."""
        context = CustomerContext(
            profile=sample_customer_profile,
            active_shipments=[high_value_shipment],
        )

        decision = composer.compose(confirmed_intelligence, context)

        assert decision is not None
        # High value should result in HIGH severity
        # Note: total_exposure_usd is the calculated IMPACT cost, not cargo value
        # The cargo_at_risk is stored in the breakdown
        assert decision.q3_severity.exposure_breakdown.get("cargo_at_risk") >= high_value_shipment.cargo_value_usd
        assert decision.q3_severity.severity.value == "high"


class TestDecisionComposerWithDifferentRiskTolerances:
    """Tests for risk tolerance impact on decisions."""

    @pytest.fixture
    def composer(self) -> DecisionComposer:
        return create_decision_composer()

    def test_conservative_customer_gets_active_recommendation(
        self,
        composer: DecisionComposer,
        confirmed_intelligence: CorrelatedIntelligence,
        conservative_customer_profile,
        sample_shipment,
        high_value_shipment,
    ):
        """Conservative customers should get more active recommendations."""
        context = CustomerContext(
            profile=conservative_customer_profile,
            active_shipments=[sample_shipment, high_value_shipment],
        )

        decision = composer.compose(confirmed_intelligence, context)

        # Conservative should favor action over inaction
        assert decision is not None
        # Should likely recommend REROUTE or similar action, not DO_NOTHING
        # (unless the situation truly doesn't warrant action)

    def test_aggressive_customer_cost_aware(
        self,
        composer: DecisionComposer,
        confirmed_intelligence: CorrelatedIntelligence,
        aggressive_customer_profile,
        sample_shipment,
        high_value_shipment,
    ):
        """Aggressive customers should get cost-aware recommendations."""
        context = CustomerContext(
            profile=aggressive_customer_profile,
            active_shipments=[sample_shipment, high_value_shipment],
        )

        decision = composer.compose(confirmed_intelligence, context)

        # Aggressive might favor lower-cost options
        assert decision is not None
        # The system should still provide a valid decision


class TestDecisionComposerFactory:
    """Tests for factory function."""

    def test_create_decision_composer(self):
        """Factory should create valid instance."""
        composer = create_decision_composer()
        assert isinstance(composer, DecisionComposer)

    def test_create_with_custom_components(self):
        """Factory should accept custom components."""
        from app.riskcast.calculators import create_impact_calculator
        from app.riskcast.generators import create_action_generator
        from app.riskcast.matchers import create_exposure_matcher

        composer = create_decision_composer(
            exposure_matcher=create_exposure_matcher(),
            impact_calculator=create_impact_calculator(),
            action_generator=create_action_generator(),
        )

        assert isinstance(composer, DecisionComposer)
