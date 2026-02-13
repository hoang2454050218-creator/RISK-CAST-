"""
Counterfactual Analysis Tests.
"""

import pytest

from riskcast.decisions.counterfactual import CounterfactualEngine
from riskcast.engine.risk_engine import RiskAssessment


def _assessment(risk_score: float = 50) -> RiskAssessment:
    return RiskAssessment(
        entity_type="order",
        entity_id="test-123",
        risk_score=risk_score,
        confidence=0.8,
        ci_lower=risk_score - 10,
        ci_upper=risk_score + 10,
        severity_label="moderate",
        is_reliable=True,
        needs_human_review=False,
        n_signals=5,
        n_active_signals=5,
        data_freshness="fresh",
        primary_driver="payment_risk",
        generated_at="2026-01-01T00:00:00Z",
    )


class TestCounterfactualEngine:
    def setup_method(self):
        self.engine = CounterfactualEngine()

    def test_generates_base_scenarios(self):
        """Always generates at least 3 base scenarios."""
        scenarios = self.engine.generate_scenarios(_assessment(50), 100000)
        assert len(scenarios) >= 3

    def test_cascade_scenario_for_high_risk(self):
        """High risk (>=60) includes cascade failure scenario."""
        scenarios = self.engine.generate_scenarios(_assessment(75), 100000)
        names = {s.scenario_name for s in scenarios}
        assert "Cascade Failure" in names

    def test_no_cascade_for_low_risk(self):
        """Low risk (<60) excludes cascade failure."""
        scenarios = self.engine.generate_scenarios(_assessment(40), 100000)
        names = {s.scenario_name for s in scenarios}
        assert "Cascade Failure" not in names

    def test_probabilities_valid(self):
        """All probabilities are in [0, 1]."""
        scenarios = self.engine.generate_scenarios(_assessment(70), 200000)
        for s in scenarios:
            assert 0 <= s.probability <= 1

    def test_expected_loss_non_negative(self):
        """Expected loss is non-negative."""
        scenarios = self.engine.generate_scenarios(_assessment(50), 100000)
        for s in scenarios:
            assert s.expected_loss >= 0

    def test_risk_materializes_has_mitigation(self):
        """Risk materializes scenario is mitigable."""
        scenarios = self.engine.generate_scenarios(_assessment(60), 100000)
        risk_mat = next(s for s in scenarios if s.scenario_name == "Risk Materializes")
        assert risk_mat.mitigation_available

    def test_exposure_scales_expected_loss(self):
        """Higher exposure → higher expected loss."""
        low = self.engine.generate_scenarios(_assessment(50), 10000)
        high = self.engine.generate_scenarios(_assessment(50), 1000000)
        loss_low = sum(s.expected_loss for s in low)
        loss_high = sum(s.expected_loss for s in high)
        assert loss_high > loss_low
