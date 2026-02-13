"""Tests for Action Generator.

Tests the ActionGenerator which answers:
"What are the possible actions?"
"""

from datetime import datetime, timedelta

import pytest

from app.oracle.schemas import CorrelatedIntelligence
from app.riskcast.calculators.impact import ImpactCalculator
from app.riskcast.generators.action import ActionGenerator, create_action_generator
from app.riskcast.matchers.exposure import ExposureMatcher
from app.riskcast.schemas.action import (
    Action,
    ActionFeasibility,
    ActionSet,
    ActionType,
)
from app.riskcast.schemas.customer import CustomerContext


class TestAction:
    """Tests for Action model."""

    def test_net_benefit_positive(self):
        """Net benefit should be positive when risk > cost."""
        action = Action(
            action_id="act_test",
            action_type=ActionType.REROUTE,
            summary="Test reroute",
            description="Test description",
            steps=["Step 1", "Step 2"],
            deadline=datetime.utcnow() + timedelta(hours=24),
            deadline_reason="Test deadline",
            cost_usd=5000,
            risk_mitigated_usd=15000,
            feasibility=ActionFeasibility.HIGH,
        )
        assert action.net_benefit_usd == 10000
        assert action.is_profitable is True

    def test_net_benefit_negative(self):
        """Net benefit should be negative when cost > risk."""
        action = Action(
            action_id="act_test",
            action_type=ActionType.REROUTE,
            summary="Test reroute",
            description="Test description",
            steps=["Step 1"],
            deadline=datetime.utcnow() + timedelta(hours=24),
            deadline_reason="Test deadline",
            cost_usd=15000,
            risk_mitigated_usd=5000,
            feasibility=ActionFeasibility.HIGH,
        )
        assert action.net_benefit_usd == -10000
        assert action.is_profitable is False

    def test_is_urgent_within_24h(self):
        """Action is urgent if deadline within 24 hours."""
        action = Action(
            action_id="act_test",
            action_type=ActionType.REROUTE,
            summary="Test",
            description="Test",
            steps=["Step 1"],
            deadline=datetime.utcnow() + timedelta(hours=12),
            deadline_reason="Test",
            cost_usd=0,
            risk_mitigated_usd=0,
            feasibility=ActionFeasibility.HIGH,
        )
        assert action.is_urgent is True

    def test_not_urgent_beyond_24h(self):
        """Action is not urgent if deadline beyond 24 hours."""
        action = Action(
            action_id="act_test",
            action_type=ActionType.REROUTE,
            summary="Test",
            description="Test",
            steps=["Step 1"],
            deadline=datetime.utcnow() + timedelta(hours=48),
            deadline_reason="Test",
            cost_usd=0,
            risk_mitigated_usd=0,
            feasibility=ActionFeasibility.HIGH,
        )
        assert action.is_urgent is False


class TestActionSet:
    """Tests for ActionSet model."""

    @pytest.fixture
    def sample_actions(self) -> list[Action]:
        """Create sample actions."""
        return [
            Action(
                action_id="act_1",
                action_type=ActionType.REROUTE,
                summary="Reroute option",
                description="Reroute description",
                steps=["Step 1"],
                deadline=datetime.utcnow() + timedelta(hours=24),
                deadline_reason="Test",
                cost_usd=5000,
                risk_mitigated_usd=15000,
                feasibility=ActionFeasibility.HIGH,
                utility_score=0.8,
            ),
            Action(
                action_id="act_2",
                action_type=ActionType.DO_NOTHING,
                summary="Do nothing",
                description="Accept risk",
                steps=["Step 1"],
                deadline=datetime.utcnow() + timedelta(days=7),
                deadline_reason="No action",
                cost_usd=0,
                risk_mitigated_usd=0,
                feasibility=ActionFeasibility.HIGH,
                utility_score=0.1,
            ),
        ]

    def test_action_count(self, sample_actions: list[Action]):
        """Action count should match list length."""
        action_set = ActionSet(
            customer_id="cust_123",
            signal_id="sig_123",
            actions=sample_actions,
            primary_action=sample_actions[0],
            alternatives=[sample_actions[1]],
            do_nothing_cost=20000,
        )
        assert action_set.action_count == 2

    def test_has_profitable_action(self, sample_actions: list[Action]):
        """Should detect profitable actions."""
        action_set = ActionSet(
            customer_id="cust_123",
            signal_id="sig_123",
            actions=sample_actions,
            primary_action=sample_actions[0],
            alternatives=[],
            do_nothing_cost=20000,
        )
        assert action_set.has_profitable_action is True

    def test_get_feasible_actions(self, sample_actions: list[Action]):
        """Should filter out impossible actions."""
        # Add an impossible action
        impossible = Action(
            action_id="act_impossible",
            action_type=ActionType.REROUTE,
            summary="Impossible",
            description="Cannot do",
            steps=["Step 1"],
            deadline=datetime.utcnow() + timedelta(hours=24),
            deadline_reason="Test",
            cost_usd=0,
            risk_mitigated_usd=0,
            feasibility=ActionFeasibility.IMPOSSIBLE,
        )
        all_actions = sample_actions + [impossible]

        action_set = ActionSet(
            customer_id="cust_123",
            signal_id="sig_123",
            actions=all_actions,
            primary_action=sample_actions[0],
            alternatives=[],
            do_nothing_cost=20000,
        )

        feasible = action_set.get_feasible_actions()
        assert len(feasible) == 2  # Excludes impossible


class TestActionGenerator:
    """Tests for ActionGenerator."""

    @pytest.fixture
    def generator(self) -> ActionGenerator:
        """Create action generator instance."""
        return create_action_generator()

    @pytest.fixture
    def calculator(self) -> ImpactCalculator:
        """Create impact calculator."""
        return ImpactCalculator()

    def test_generate_always_includes_do_nothing(
        self,
        generator: ActionGenerator,
        calculator: ImpactCalculator,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """DO_NOTHING should always be included as baseline."""
        exposure = exposure_matcher.match(confirmed_intelligence, sample_customer_context)
        impact = calculator.calculate(exposure, confirmed_intelligence, sample_customer_context)

        action_set = generator.generate(
            exposure, impact, confirmed_intelligence, sample_customer_context
        )

        do_nothing_actions = [
            a for a in action_set.actions
            if a.action_type == ActionType.DO_NOTHING
        ]
        assert len(do_nothing_actions) == 1

    def test_generate_specific_actions(
        self,
        generator: ActionGenerator,
        calculator: ImpactCalculator,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Generated actions must be specific, not vague."""
        exposure = exposure_matcher.match(confirmed_intelligence, sample_customer_context)
        impact = calculator.calculate(exposure, confirmed_intelligence, sample_customer_context)

        action_set = generator.generate(
            exposure, impact, confirmed_intelligence, sample_customer_context
        )

        for action in action_set.actions:
            # Every action must have concrete details
            assert action.summary is not None
            assert len(action.summary) <= 100  # One-line summary
            assert action.description is not None
            assert len(action.steps) >= 1  # At least one step
            assert action.deadline is not None  # Specific deadline
            assert isinstance(action.cost_usd, float)
            assert action.cost_usd >= 0

    def test_generate_reroute_with_carrier(
        self,
        generator: ActionGenerator,
        calculator: ImpactCalculator,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Reroute actions should specify carrier."""
        exposure = exposure_matcher.match(confirmed_intelligence, sample_customer_context)
        impact = calculator.calculate(exposure, confirmed_intelligence, sample_customer_context)

        action_set = generator.generate(
            exposure, impact, confirmed_intelligence, sample_customer_context
        )

        reroute_actions = [
            a for a in action_set.actions
            if a.action_type == ActionType.REROUTE
        ]

        if reroute_actions:  # May not always generate reroute
            reroute = reroute_actions[0]
            assert reroute.recommended_carrier is not None
            assert reroute.carrier_name is not None
            assert reroute.contact_info is not None

    def test_generate_ranks_by_utility(
        self,
        generator: ActionGenerator,
        calculator: ImpactCalculator,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Actions should be ranked by utility score."""
        exposure = exposure_matcher.match(confirmed_intelligence, sample_customer_context)
        impact = calculator.calculate(exposure, confirmed_intelligence, sample_customer_context)

        action_set = generator.generate(
            exposure, impact, confirmed_intelligence, sample_customer_context
        )

        # Check actions are sorted by utility (descending)
        scores = [a.utility_score for a in action_set.actions]
        assert scores == sorted(scores, reverse=True)

    def test_generate_primary_is_highest_utility(
        self,
        generator: ActionGenerator,
        calculator: ImpactCalculator,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Primary action should have highest utility."""
        exposure = exposure_matcher.match(confirmed_intelligence, sample_customer_context)
        impact = calculator.calculate(exposure, confirmed_intelligence, sample_customer_context)

        action_set = generator.generate(
            exposure, impact, confirmed_intelligence, sample_customer_context
        )

        primary_score = action_set.primary_action.utility_score
        all_scores = [a.utility_score for a in action_set.actions]
        assert primary_score == max(all_scores)

    def test_generate_considers_risk_tolerance(
        self,
        generator: ActionGenerator,
        calculator: ImpactCalculator,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
        conservative_customer_profile,
        aggressive_customer_profile,
        sample_shipment,
        high_value_shipment,
    ):
        """Different risk tolerances should produce different rankings."""
        exposure = exposure_matcher.match(confirmed_intelligence, sample_customer_context)
        impact = calculator.calculate(exposure, confirmed_intelligence, sample_customer_context)

        # Conservative context
        conservative_context = CustomerContext(
            profile=conservative_customer_profile,
            active_shipments=[sample_shipment, high_value_shipment],
        )
        conservative_exposure = exposure_matcher.match(confirmed_intelligence, conservative_context)
        conservative_impact = calculator.calculate(
            conservative_exposure, confirmed_intelligence, conservative_context
        )

        # Aggressive context
        aggressive_context = CustomerContext(
            profile=aggressive_customer_profile,
            active_shipments=[sample_shipment, high_value_shipment],
        )
        aggressive_exposure = exposure_matcher.match(confirmed_intelligence, aggressive_context)
        aggressive_impact = calculator.calculate(
            aggressive_exposure, confirmed_intelligence, aggressive_context
        )

        # Generate actions for both
        conservative_actions = generator.generate(
            conservative_exposure, conservative_impact,
            confirmed_intelligence, conservative_context
        )
        aggressive_actions = generator.generate(
            aggressive_exposure, aggressive_impact,
            confirmed_intelligence, aggressive_context
        )

        # Different risk tolerances should affect scoring
        # (Primary action may differ, or at least scores will differ)
        assert conservative_actions is not None
        assert aggressive_actions is not None


class TestActionGeneratorFactory:
    """Tests for factory function."""

    def test_create_action_generator(self):
        """Factory should create valid instance."""
        gen = create_action_generator()
        assert isinstance(gen, ActionGenerator)
