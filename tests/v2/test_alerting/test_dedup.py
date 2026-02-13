"""
Tests for Alert Deduplication & Cooldown.

Covers:
- Cooldown suppression
- Daily limit suppression
- Content dedup suppression
- No suppression for first alert
- Daily count reset
"""

import time
from datetime import datetime, timedelta, timezone

import pytest

from riskcast.alerting.dedup import DedupManager
from riskcast.alerting.schemas import (
    AlertChannel,
    AlertRecord,
    AlertSeverity,
    AlertStatus,
)


@pytest.fixture
def dedup():
    mgr = DedupManager()
    mgr.reset()
    return mgr


def _make_alert(
    rule_id: str = "rule_001",
    metric_value: float = 80.0,
    entity_id: str = "ent-1",
) -> AlertRecord:
    return AlertRecord(
        alert_id=f"alert_test_{rule_id}_{metric_value}",
        rule_id=rule_id,
        rule_name="Test Rule",
        company_id="comp-001",
        severity=AlertSeverity.HIGH,
        status=AlertStatus.PENDING,
        metric="risk_score",
        metric_value=metric_value,
        threshold=70.0,
        entity_type="order",
        entity_id=entity_id,
        title="Test",
        message="Test alert",
        channels=[AlertChannel.IN_APP],
        triggered_at=datetime.now(timezone.utc).isoformat(),
    )


# ── No Suppression ────────────────────────────────────────────────────


class TestNoSuppression:
    def test_first_alert_not_suppressed(self, dedup):
        alert = _make_alert()
        suppressed, reason = dedup.should_suppress(alert, cooldown_minutes=30, max_per_day=10)
        assert suppressed is False
        assert reason == ""

    def test_different_rules_not_suppressed(self, dedup):
        alert1 = _make_alert(rule_id="rule_001")
        dedup.record_fired(alert1)

        alert2 = _make_alert(rule_id="rule_002")
        suppressed, _ = dedup.should_suppress(alert2, 30, 10)
        assert suppressed is False


# ── Cooldown ──────────────────────────────────────────────────────────


class TestCooldown:
    def test_within_cooldown_suppressed(self, dedup):
        alert = _make_alert()
        dedup.record_fired(alert)

        # Same rule, within cooldown
        suppressed, reason = dedup.should_suppress(alert, cooldown_minutes=30, max_per_day=10)
        assert suppressed is True
        assert "Cooldown active" in reason

    def test_after_cooldown_not_suppressed(self, dedup):
        alert = _make_alert()
        # Simulate firing 31 minutes ago
        dedup._last_fired[alert.rule_id] = (
            datetime.now(timezone.utc) - timedelta(minutes=31)
        )

        suppressed, _ = dedup.should_suppress(alert, cooldown_minutes=30, max_per_day=10)
        assert suppressed is False


# ── Daily Limit ───────────────────────────────────────────────────────


class TestDailyLimit:
    def test_daily_limit_suppresses(self, dedup):
        # Simulate hitting daily limit with 10 different alerts
        for i in range(10):
            a = _make_alert(metric_value=80.0 + i, entity_id=f"ent-dl-{i}")
            dedup.record_fired(a)

        # Clear cooldown and content hashes so only daily limit applies
        dedup._last_fired.clear()
        dedup._content_hashes.clear()

        new_alert = _make_alert(metric_value=99.0, entity_id="ent-dl-new")
        suppressed, reason = dedup.should_suppress(new_alert, cooldown_minutes=0, max_per_day=10)
        assert suppressed is True
        assert "Daily limit" in reason

    def test_within_daily_limit(self, dedup):
        for i in range(5):
            a = _make_alert(metric_value=80.0 + i, entity_id=f"ent-wdl-{i}")
            dedup.record_fired(a)

        dedup._last_fired.clear()
        dedup._content_hashes.clear()

        new_alert = _make_alert(metric_value=99.0, entity_id="ent-wdl-new")
        suppressed, _ = dedup.should_suppress(new_alert, cooldown_minutes=0, max_per_day=10)
        assert suppressed is False


# ── Content Dedup ─────────────────────────────────────────────────────


class TestContentDedup:
    def test_same_content_suppressed(self, dedup):
        alert = _make_alert(entity_id="ent-cd-same")
        dedup.record_fired(alert)
        # Clear cooldown and daily count to isolate content dedup
        dedup._last_fired.clear()
        dedup._daily_counts.clear()

        # Same alert again — content hash matches
        alert2 = _make_alert(entity_id="ent-cd-same")
        suppressed, reason = dedup.should_suppress(alert2, cooldown_minutes=0, max_per_day=100)
        assert suppressed is True
        assert "Duplicate content" in reason

    def test_different_content_not_suppressed(self, dedup):
        alert1 = _make_alert(entity_id="ent-cd-1")
        dedup.record_fired(alert1)
        dedup._last_fired.clear()
        dedup._daily_counts.clear()

        alert2 = _make_alert(entity_id="ent-cd-2")
        suppressed, _ = dedup.should_suppress(alert2, cooldown_minutes=0, max_per_day=100)
        assert suppressed is False


# ── Utility ───────────────────────────────────────────────────────────


class TestUtility:
    def test_daily_count(self, dedup):
        alert = _make_alert()
        assert dedup.get_daily_count(alert.rule_id) == 0
        dedup.record_fired(alert)
        assert dedup.get_daily_count(alert.rule_id) == 1

    def test_reset(self, dedup):
        alert = _make_alert()
        dedup.record_fired(alert)
        dedup.reset()
        assert dedup.get_daily_count(alert.rule_id) == 0

    def test_daily_reset_on_new_day(self, dedup):
        alert = _make_alert()
        dedup.record_fired(alert)
        # Simulate day change
        dedup._count_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()
        assert dedup.get_daily_count(alert.rule_id) == 0  # Reset
