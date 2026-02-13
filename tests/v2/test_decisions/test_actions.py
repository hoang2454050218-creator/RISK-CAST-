"""
Action Generator Tests.
"""

import pytest

from riskcast.decisions.actions import ActionGenerator, ActionType
from riskcast.engine.risk_engine import RiskAssessment


def _make_assessment(risk_score: float, is_reliable: bool = True) -> RiskAssessment:
    return RiskAssessment(
        entity_type="order",
        entity_id="test-123",
        risk_score=risk_score,
        confidence=0.8,
        ci_lower=risk_score - 10,
        ci_upper=risk_score + 10,
        severity_label="low" if risk_score < 25 else "moderate" if risk_score < 50 else "high" if risk_score < 75 else "critical",
        is_reliable=is_reliable,
        needs_human_review=False,
        n_signals=5,
        n_active_signals=5,
        data_freshness="fresh",
        primary_driver="payment_risk",
        generated_at="2026-01-01T00:00:00Z",
    )


class TestActionGenerator:
    def setup_method(self):
        self.gen = ActionGenerator()

    def test_low_risk_only_monitor(self):
        """Low risk → only monitor action."""
        assessment = _make_assessment(10)
        actions = self.gen.generate_actions(assessment, exposure_usd=10000)
        types = {a.action_type for a in actions}
        assert ActionType.MONITOR in types
        assert ActionType.REROUTE not in types

    def test_moderate_risk_includes_insurance(self):
        """Moderate risk → includes insurance."""
        assessment = _make_assessment(35)
        actions = self.gen.generate_actions(assessment, exposure_usd=50000)
        types = {a.action_type for a in actions}
        assert ActionType.INSURE in types

    def test_high_risk_includes_reroute(self):
        """High risk → includes reroute."""
        assessment = _make_assessment(55)
        actions = self.gen.generate_actions(assessment, exposure_usd=100000)
        types = {a.action_type for a in actions}
        assert ActionType.REROUTE in types
        assert ActionType.DELAY in types

    def test_critical_risk_includes_escalation(self):
        """Critical risk → includes escalation."""
        assessment = _make_assessment(85)
        actions = self.gen.generate_actions(assessment, exposure_usd=200000)
        types = {a.action_type for a in actions}
        assert ActionType.ESCALATE in types

    def test_unreliable_assessment_includes_escalation(self):
        """Unreliable data → escalation regardless of score."""
        assessment = _make_assessment(30, is_reliable=False)
        actions = self.gen.generate_actions(assessment, exposure_usd=10000)
        types = {a.action_type for a in actions}
        assert ActionType.ESCALATE in types

    def test_actions_sorted_by_net_value(self):
        """Actions are sorted by net value (highest first)."""
        assessment = _make_assessment(60)
        actions = self.gen.generate_actions(assessment, exposure_usd=100000)
        for i in range(len(actions) - 1):
            assert actions[i].net_value >= actions[i + 1].net_value

    def test_all_actions_have_descriptions(self):
        """Every action has a non-empty description."""
        assessment = _make_assessment(70)
        actions = self.gen.generate_actions(assessment, exposure_usd=100000)
        for a in actions:
            assert len(a.description) > 0

    def test_insurance_cost_proportional(self):
        """Insurance cost scales with exposure."""
        assessment = _make_assessment(40)
        small = self.gen.generate_actions(assessment, exposure_usd=10000)
        large = self.gen.generate_actions(assessment, exposure_usd=1000000)
        ins_small = next(a for a in small if a.action_type == ActionType.INSURE)
        ins_large = next(a for a in large if a.action_type == ActionType.INSURE)
        assert ins_large.estimated_cost_usd > ins_small.estimated_cost_usd

    def test_monitor_always_present(self):
        """Monitor is always an option."""
        for score in [5, 30, 50, 70, 95]:
            assessment = _make_assessment(score)
            actions = self.gen.generate_actions(assessment, exposure_usd=50000)
            assert any(a.action_type == ActionType.MONITOR for a in actions)
