"""Tests for Trade-off Analyzer.

Tests the TradeOffAnalyzer which answers:
"What if I don't act?"
"""

from datetime import datetime, timedelta

import pytest

from app.oracle.schemas import CorrelatedIntelligence
from app.riskcast.calculators.impact import ImpactCalculator
from app.riskcast.generators.action import ActionGenerator
from app.riskcast.generators.tradeoff import TradeOffAnalyzer, create_tradeoff_analyzer
from app.riskcast.matchers.exposure import ExposureMatcher
from app.riskcast.schemas.action import (
    Action,
    ActionFeasibility,
    ActionSet,
    ActionType,
    InactionConsequence,
    TimePoint,
    TradeOffAnalysis,
)
from app.riskcast.schemas.customer import CustomerContext


class TestTimePoint:
    """Tests for TimePoint model."""

    def test_create_deadline_timepoint(self):
        """Can create deadline time point."""
        tp = TimePoint(
            hours_from_now=24,
            timestamp=datetime.utcnow() + timedelta(hours=24),
            description="Booking deadline",
            do_nothing_cost=50000,
            reroute_cost=8500,
            what_changes="Reroute option closes",
            is_deadline=True,
            deadline_type="booking_closes",
        )
        assert tp.is_deadline is True
        assert tp.deadline_type == "booking_closes"

    def test_create_checkpoint_timepoint(self):
        """Can create checkpoint (non-deadline) time point."""
        tp = TimePoint(
            hours_from_now=6,
            timestamp=datetime.utcnow() + timedelta(hours=6),
            description="6 hour mark",
            do_nothing_cost=52000,
            reroute_cost=0,
            what_changes="Early warning - options still available",
            is_deadline=False,
        )
        assert tp.is_deadline is False


class TestInactionConsequence:
    """Tests for InactionConsequence model."""

    def test_cost_increase_calculations(self):
        """Should calculate cost increases correctly."""
        inaction = InactionConsequence(
            immediate_cost_usd=50000,
            cost_at_6h=55000,
            cost_at_24h=65000,
            cost_at_48h=75000,
            deadlines=[],
            worst_case_cost_usd=100000,
            worst_case_scenario="All shipments delayed 21+ days",
        )

        assert inaction.cost_increase_6h == 5000
        assert inaction.cost_increase_24h == 15000

    def test_cost_increase_percentage(self):
        """Should calculate percentage increase."""
        inaction = InactionConsequence(
            immediate_cost_usd=50000,
            cost_at_6h=55000,
            cost_at_24h=65000,
            cost_at_48h=75000,
            deadlines=[],
            worst_case_cost_usd=100000,
            worst_case_scenario="Test",
        )

        # 15000 / 50000 = 30%
        assert inaction.cost_increase_pct_24h == 30.0

    def test_has_point_of_no_return(self):
        """Should detect point of no return."""
        ponr = datetime.utcnow() + timedelta(hours=48)
        inaction = InactionConsequence(
            immediate_cost_usd=50000,
            cost_at_6h=55000,
            cost_at_24h=65000,
            cost_at_48h=75000,
            deadlines=[],
            point_of_no_return=ponr,
            point_of_no_return_reason="Booking window closes",
            worst_case_cost_usd=100000,
            worst_case_scenario="Test",
        )

        assert inaction.has_point_of_no_return is True
        assert inaction.hours_until_no_return is not None
        assert inaction.hours_until_no_return > 0


class TestTradeOffAnalysis:
    """Tests for TradeOffAnalysis model."""

    def test_time_to_decide_hours(self):
        """Should calculate hours to decide."""
        now = datetime.utcnow()
        analysis = TradeOffAnalysis(
            customer_id="cust_123",
            signal_id="sig_123",
            actions_compared=["act_1", "act_2"],
            recommended_action="act_1",
            recommended_reason="Best net benefit",
            inaction=InactionConsequence(
                immediate_cost_usd=50000,
                cost_at_6h=55000,
                cost_at_24h=65000,
                cost_at_48h=75000,
                deadlines=[],
                worst_case_cost_usd=100000,
                worst_case_scenario="Test",
            ),
            urgency="HOURS",
            time_to_decide=timedelta(hours=12),
            analysis_confidence=0.85,
        )

        assert analysis.time_to_decide_hours == 12.0

    def test_is_immediate(self):
        """Should detect immediate urgency."""
        analysis = TradeOffAnalysis(
            customer_id="cust_123",
            signal_id="sig_123",
            recommended_action="act_1",
            recommended_reason="Urgent action needed",
            inaction=InactionConsequence(
                immediate_cost_usd=50000,
                cost_at_6h=55000,
                cost_at_24h=65000,
                cost_at_48h=75000,
                deadlines=[],
                worst_case_cost_usd=100000,
                worst_case_scenario="Test",
            ),
            urgency="IMMEDIATE",
            time_to_decide=timedelta(hours=4),
            analysis_confidence=0.9,
        )

        assert analysis.is_immediate is True


class TestTradeOffAnalyzer:
    """Tests for TradeOffAnalyzer."""

    @pytest.fixture
    def analyzer(self) -> TradeOffAnalyzer:
        """Create trade-off analyzer instance."""
        return create_tradeoff_analyzer()

    @pytest.fixture
    def calculator(self) -> ImpactCalculator:
        """Create impact calculator."""
        return ImpactCalculator()

    @pytest.fixture
    def generator(self) -> ActionGenerator:
        """Create action generator."""
        return ActionGenerator()

    def test_analyze_produces_specific_costs(
        self,
        analyzer: TradeOffAnalyzer,
        calculator: ImpactCalculator,
        generator: ActionGenerator,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Analysis must produce specific cost numbers at time points."""
        exposure = exposure_matcher.match(confirmed_intelligence, sample_customer_context)
        impact = calculator.calculate(exposure, confirmed_intelligence, sample_customer_context)
        actions = generator.generate(exposure, impact, confirmed_intelligence, sample_customer_context)

        analysis = analyzer.analyze(actions, impact, exposure, confirmed_intelligence)

        # Must have specific numbers, not vague
        inaction = analysis.inaction
        assert isinstance(inaction.immediate_cost_usd, float)
        assert isinstance(inaction.cost_at_6h, float)
        assert isinstance(inaction.cost_at_24h, float)
        assert isinstance(inaction.cost_at_48h, float)

    def test_analyze_cost_escalation(
        self,
        analyzer: TradeOffAnalyzer,
        calculator: ImpactCalculator,
        generator: ActionGenerator,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Costs should escalate over time."""
        exposure = exposure_matcher.match(confirmed_intelligence, sample_customer_context)
        impact = calculator.calculate(exposure, confirmed_intelligence, sample_customer_context)
        actions = generator.generate(exposure, impact, confirmed_intelligence, sample_customer_context)

        analysis = analyzer.analyze(actions, impact, exposure, confirmed_intelligence)

        inaction = analysis.inaction
        # Costs should increase over time
        assert inaction.cost_at_6h >= inaction.immediate_cost_usd
        assert inaction.cost_at_24h >= inaction.cost_at_6h
        assert inaction.cost_at_48h >= inaction.cost_at_24h

    def test_analyze_includes_deadlines(
        self,
        analyzer: TradeOffAnalyzer,
        calculator: ImpactCalculator,
        generator: ActionGenerator,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Analysis should include deadline timeline."""
        exposure = exposure_matcher.match(confirmed_intelligence, sample_customer_context)
        impact = calculator.calculate(exposure, confirmed_intelligence, sample_customer_context)
        actions = generator.generate(exposure, impact, confirmed_intelligence, sample_customer_context)

        analysis = analyzer.analyze(actions, impact, exposure, confirmed_intelligence)

        # Should have some deadlines
        # (may be action deadlines or standard checkpoints)
        assert analysis.inaction.deadlines is not None

    def test_analyze_urgency_levels(
        self,
        analyzer: TradeOffAnalyzer,
        calculator: ImpactCalculator,
        generator: ActionGenerator,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Analysis should determine urgency level."""
        exposure = exposure_matcher.match(confirmed_intelligence, sample_customer_context)
        impact = calculator.calculate(exposure, confirmed_intelligence, sample_customer_context)
        actions = generator.generate(exposure, impact, confirmed_intelligence, sample_customer_context)

        analysis = analyzer.analyze(actions, impact, exposure, confirmed_intelligence)

        # Urgency should be one of the defined levels
        assert analysis.urgency in ["IMMEDIATE", "HOURS", "DAYS", "WEEKS"]

    def test_analyze_recommended_action(
        self,
        analyzer: TradeOffAnalyzer,
        calculator: ImpactCalculator,
        generator: ActionGenerator,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Analysis should recommend an action with reason."""
        exposure = exposure_matcher.match(confirmed_intelligence, sample_customer_context)
        impact = calculator.calculate(exposure, confirmed_intelligence, sample_customer_context)
        actions = generator.generate(exposure, impact, confirmed_intelligence, sample_customer_context)

        analysis = analyzer.analyze(actions, impact, exposure, confirmed_intelligence)

        # Should have recommended action
        assert analysis.recommended_action is not None
        assert analysis.recommended_reason is not None
        assert len(analysis.recommended_reason) > 0

    def test_analyze_worst_case(
        self,
        analyzer: TradeOffAnalyzer,
        calculator: ImpactCalculator,
        generator: ActionGenerator,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Analysis should include worst case scenario."""
        exposure = exposure_matcher.match(confirmed_intelligence, sample_customer_context)
        impact = calculator.calculate(exposure, confirmed_intelligence, sample_customer_context)
        actions = generator.generate(exposure, impact, confirmed_intelligence, sample_customer_context)

        analysis = analyzer.analyze(actions, impact, exposure, confirmed_intelligence)

        # Worst case should be defined
        assert analysis.inaction.worst_case_cost_usd >= analysis.inaction.immediate_cost_usd
        assert analysis.inaction.worst_case_scenario is not None

    def test_analyze_confidence(
        self,
        analyzer: TradeOffAnalyzer,
        calculator: ImpactCalculator,
        generator: ActionGenerator,
        exposure_matcher: ExposureMatcher,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Analysis should have confidence score."""
        exposure = exposure_matcher.match(confirmed_intelligence, sample_customer_context)
        impact = calculator.calculate(exposure, confirmed_intelligence, sample_customer_context)
        actions = generator.generate(exposure, impact, confirmed_intelligence, sample_customer_context)

        analysis = analyzer.analyze(actions, impact, exposure, confirmed_intelligence)

        assert 0.0 <= analysis.analysis_confidence <= 1.0


class TestTradeOffAnalyzerFactory:
    """Tests for factory function."""

    def test_create_tradeoff_analyzer(self):
        """Factory should create valid instance."""
        analyzer = create_tradeoff_analyzer()
        assert isinstance(analyzer, TradeOffAnalyzer)
