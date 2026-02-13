"""
Escalation Rules Tests.
"""

import pytest

from riskcast.decisions.escalation import EscalationEngine
from riskcast.engine.risk_engine import RiskAssessment


def _assessment(
    risk_score: float = 50,
    confidence: float = 0.8,
    is_reliable: bool = True,
    disagreement: float = 5.0,
) -> RiskAssessment:
    return RiskAssessment(
        entity_type="order",
        entity_id="test-123",
        risk_score=risk_score,
        confidence=confidence,
        ci_lower=risk_score - 10,
        ci_upper=risk_score + 10,
        severity_label="moderate",
        is_reliable=is_reliable,
        needs_human_review=False,
        n_signals=5,
        n_active_signals=5,
        data_freshness="fresh",
        primary_driver="payment_risk",
        algorithm_trace={"ensemble_disagreement": disagreement},
        generated_at="2026-01-01T00:00:00Z",
    )


class TestEscalationEngine:
    def setup_method(self):
        self.engine = EscalationEngine()

    def test_no_escalation_when_safe(self):
        """Low risk, high confidence → no escalation."""
        needs, rules, reason = self.engine.evaluate(
            _assessment(risk_score=30, confidence=0.9), exposure_usd=50000
        )
        assert not needs
        triggered = [r for r in rules if r.triggered]
        assert len(triggered) == 0

    def test_high_exposure_triggers(self):
        """High exposure → escalation."""
        needs, rules, reason = self.engine.evaluate(
            _assessment(), exposure_usd=500000
        )
        assert needs
        assert any(r.rule_name == "high_exposure" and r.triggered for r in rules)

    def test_low_confidence_triggers(self):
        """Low confidence → escalation."""
        needs, rules, reason = self.engine.evaluate(
            _assessment(confidence=0.3), exposure_usd=50000
        )
        assert needs
        assert any(r.rule_name == "low_confidence" and r.triggered for r in rules)

    def test_critical_risk_triggers(self):
        """Critical risk score → escalation."""
        needs, rules, reason = self.engine.evaluate(
            _assessment(risk_score=90), exposure_usd=50000
        )
        assert needs
        assert any(r.rule_name == "critical_risk_score" and r.triggered for r in rules)

    def test_model_disagreement_triggers(self):
        """High model disagreement → escalation."""
        needs, rules, reason = self.engine.evaluate(
            _assessment(disagreement=20.0), exposure_usd=50000
        )
        assert needs
        assert any(r.rule_name == "model_disagreement" and r.triggered for r in rules)

    def test_insufficient_data_triggers(self):
        """Insufficient data → escalation."""
        needs, rules, reason = self.engine.evaluate(
            _assessment(is_reliable=False), exposure_usd=50000
        )
        assert needs
        assert any(r.rule_name == "insufficient_data" and r.triggered for r in rules)

    def test_multiple_rules_can_trigger(self):
        """Multiple rules can trigger simultaneously."""
        needs, rules, reason = self.engine.evaluate(
            _assessment(risk_score=90, confidence=0.3, is_reliable=False),
            exposure_usd=500000,
        )
        triggered = [r for r in rules if r.triggered]
        assert len(triggered) >= 3

    def test_reason_summary_contains_rule_names(self):
        """Reason summary lists triggered rule names."""
        needs, rules, reason = self.engine.evaluate(
            _assessment(risk_score=90), exposure_usd=50000
        )
        assert "critical_risk_score" in reason

    def test_custom_thresholds(self):
        """Custom thresholds override defaults."""
        engine = EscalationEngine(exposure_threshold=1_000_000)
        needs, _, _ = engine.evaluate(
            _assessment(), exposure_usd=500000
        )
        # 500K < 1M threshold → no escalation from exposure
        triggered_exposure = False
        _, rules, _ = engine.evaluate(_assessment(), exposure_usd=500000)
        for r in rules:
            if r.rule_name == "high_exposure":
                triggered_exposure = r.triggered
        assert not triggered_exposure
