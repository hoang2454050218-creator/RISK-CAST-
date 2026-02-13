"""
Tests for Alert Engine.

Covers:
- Rule evaluation with all operators
- Entity type filtering
- Inactive rule skipping
- Multi-rule evaluation
- Alert message generation
"""

import pytest

from riskcast.alerting.engine import AlertEngine
from riskcast.alerting.schemas import (
    AlertChannel,
    AlertRule,
    AlertSeverity,
    AlertStatus,
    RuleOperator,
)


@pytest.fixture
def engine():
    return AlertEngine()


def _make_rule(
    metric: str = "risk_score",
    operator: RuleOperator = RuleOperator.GT,
    threshold: float = 70.0,
    severity: AlertSeverity = AlertSeverity.HIGH,
    entity_type: str | None = None,
    is_active: bool = True,
) -> AlertRule:
    return AlertRule(
        rule_id="rule_test_001",
        rule_name="Test Risk Alert",
        description="Fires when risk score exceeds threshold",
        company_id="comp-001",
        is_active=is_active,
        metric=metric,
        operator=operator,
        threshold=threshold,
        entity_type=entity_type,
        severity=severity,
        channels=[AlertChannel.IN_APP],
        cooldown_minutes=30,
        max_per_day=10,
    )


# ── Operator Tests ─────────────────────────────────────────────────────


class TestOperators:
    def test_gt_fires(self, engine):
        rule = _make_rule(operator=RuleOperator.GT, threshold=70.0)
        alert = engine.evaluate_rule(rule, 75.0)
        assert alert is not None
        assert alert.metric_value == 75.0

    def test_gt_does_not_fire(self, engine):
        rule = _make_rule(operator=RuleOperator.GT, threshold=70.0)
        assert engine.evaluate_rule(rule, 70.0) is None
        assert engine.evaluate_rule(rule, 50.0) is None

    def test_gte_fires(self, engine):
        rule = _make_rule(operator=RuleOperator.GTE, threshold=70.0)
        assert engine.evaluate_rule(rule, 70.0) is not None
        assert engine.evaluate_rule(rule, 80.0) is not None

    def test_gte_does_not_fire(self, engine):
        rule = _make_rule(operator=RuleOperator.GTE, threshold=70.0)
        assert engine.evaluate_rule(rule, 69.9) is None

    def test_lt_fires(self, engine):
        rule = _make_rule(metric="confidence", operator=RuleOperator.LT, threshold=0.3)
        alert = engine.evaluate_rule(rule, 0.2)
        assert alert is not None

    def test_lt_does_not_fire(self, engine):
        rule = _make_rule(metric="confidence", operator=RuleOperator.LT, threshold=0.3)
        assert engine.evaluate_rule(rule, 0.3) is None

    def test_lte_fires(self, engine):
        rule = _make_rule(operator=RuleOperator.LTE, threshold=30.0)
        assert engine.evaluate_rule(rule, 30.0) is not None

    def test_eq_fires(self, engine):
        rule = _make_rule(operator=RuleOperator.EQ, threshold=50.0)
        assert engine.evaluate_rule(rule, 50.0) is not None

    def test_neq_fires(self, engine):
        rule = _make_rule(operator=RuleOperator.NEQ, threshold=50.0)
        assert engine.evaluate_rule(rule, 51.0) is not None
        assert engine.evaluate_rule(rule, 50.0) is None


# ── Rule Filtering ─────────────────────────────────────────────────────


class TestFiltering:
    def test_inactive_rule_skipped(self, engine):
        rule = _make_rule(is_active=False)
        assert engine.evaluate_rule(rule, 90.0) is None

    def test_entity_type_filter_matches(self, engine):
        rule = _make_rule(entity_type="order")
        alert = engine.evaluate_rule(rule, 80.0, entity_type="order")
        assert alert is not None

    def test_entity_type_filter_rejects(self, engine):
        rule = _make_rule(entity_type="order")
        assert engine.evaluate_rule(rule, 80.0, entity_type="customer") is None

    def test_no_entity_type_matches_all(self, engine):
        rule = _make_rule(entity_type=None)
        assert engine.evaluate_rule(rule, 80.0, entity_type="customer") is not None
        assert engine.evaluate_rule(rule, 80.0, entity_type="order") is not None


# ── Multi-Rule Evaluation ──────────────────────────────────────────────


class TestMultiRule:
    def test_multiple_rules_partial_fire(self, engine):
        rules = [
            _make_rule(metric="risk_score", operator=RuleOperator.GT, threshold=70.0),
            AlertRule(
                rule_id="rule_test_002",
                rule_name="Low Confidence",
                description="Fires on low confidence",
                company_id="comp-001",
                metric="confidence",
                operator=RuleOperator.LT,
                threshold=0.5,
                severity=AlertSeverity.WARNING,
                channels=[AlertChannel.IN_APP],
                cooldown_minutes=30,
                max_per_day=10,
            ),
        ]
        metrics = {"risk_score": 80.0, "confidence": 0.7}
        fired = engine.evaluate_rules(rules, metrics)
        # risk_score > 70 fires, confidence < 0.5 does NOT fire
        assert len(fired) == 1
        assert fired[0].metric == "risk_score"

    def test_all_rules_fire(self, engine):
        rules = [
            _make_rule(metric="risk_score", operator=RuleOperator.GT, threshold=70.0),
            AlertRule(
                rule_id="rule_test_003",
                rule_name="High Exposure",
                description="",
                company_id="comp-001",
                metric="exposure_usd",
                operator=RuleOperator.GTE,
                threshold=100000.0,
                severity=AlertSeverity.CRITICAL,
                channels=[AlertChannel.WEBHOOK],
                cooldown_minutes=10,
                max_per_day=5,
            ),
        ]
        metrics = {"risk_score": 90.0, "exposure_usd": 500000.0}
        fired = engine.evaluate_rules(rules, metrics)
        assert len(fired) == 2

    def test_missing_metric_skipped(self, engine):
        rule = _make_rule(metric="nonexistent")
        fired = engine.evaluate_rules([rule], {"risk_score": 80.0})
        assert len(fired) == 0


# ── Alert Message ──────────────────────────────────────────────────────


class TestAlertMessage:
    def test_alert_has_title(self, engine):
        rule = _make_rule(severity=AlertSeverity.CRITICAL)
        alert = engine.evaluate_rule(rule, 95.0)
        assert "[CRITICAL]" in alert.title
        assert "95.00" in alert.title

    def test_alert_has_message(self, engine):
        rule = _make_rule()
        alert = engine.evaluate_rule(rule, 80.0, entity_type="order", entity_id="o-1")
        assert "risk_score" in alert.message
        assert "order" in alert.message

    def test_alert_status_is_pending(self, engine):
        rule = _make_rule()
        alert = engine.evaluate_rule(rule, 80.0)
        assert alert.status == AlertStatus.PENDING
