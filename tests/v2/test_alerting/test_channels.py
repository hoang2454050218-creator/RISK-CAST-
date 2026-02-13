"""
Tests for Alert Channels.

Covers:
- InAppDispatcher always succeeds
- WebhookDispatcher SSRF protection
- WebhookDispatcher missing URL handling
- EmailDispatcher missing config handling
- ChannelRouter multi-channel dispatch
"""

from datetime import datetime, timezone

import pytest

from riskcast.alerting.channels import (
    ChannelRouter,
    EmailDispatcher,
    InAppDispatcher,
    WebhookDispatcher,
)
from riskcast.alerting.schemas import (
    AlertChannel,
    AlertRecord,
    AlertSeverity,
    AlertStatus,
)


def _make_alert() -> AlertRecord:
    return AlertRecord(
        alert_id="alert_ch_001",
        rule_id="rule_001",
        rule_name="Test Rule",
        company_id="comp-001",
        severity=AlertSeverity.HIGH,
        status=AlertStatus.PENDING,
        metric="risk_score",
        metric_value=85.0,
        threshold=70.0,
        entity_type="order",
        entity_id="ord-1",
        title="[HIGH] Test Alert",
        message="Test alert message",
        channels=[AlertChannel.IN_APP, AlertChannel.WEBHOOK],
        triggered_at=datetime.now(timezone.utc).isoformat(),
    )


# ── InApp ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_in_app_always_succeeds():
    dispatcher = InAppDispatcher()
    result = await dispatcher.dispatch(_make_alert(), {})
    assert result["success"] is True


# ── Webhook ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_webhook_missing_url():
    dispatcher = WebhookDispatcher()
    result = await dispatcher.dispatch(_make_alert(), {})
    assert result["success"] is False
    assert "No webhook URL" in result["detail"]


@pytest.mark.asyncio
async def test_webhook_ssrf_blocked():
    dispatcher = WebhookDispatcher()
    # Internal IP — should be blocked by SSRF protection
    result = await dispatcher.dispatch(
        _make_alert(), {"url": "http://169.254.169.254/metadata"}
    )
    assert result["success"] is False
    assert "SSRF" in result["detail"] or "blocked" in result["detail"].lower() or "not allowed" in result["detail"].lower()


# ── Email ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_email_missing_recipients():
    dispatcher = EmailDispatcher()
    result = await dispatcher.dispatch(_make_alert(), {"smtp_host": "smtp.test.com"})
    assert result["success"] is False
    assert "No recipient" in result["detail"]


@pytest.mark.asyncio
async def test_email_missing_smtp_host():
    dispatcher = EmailDispatcher()
    result = await dispatcher.dispatch(_make_alert(), {"to_emails": ["test@test.com"]})
    assert result["success"] is False
    assert "No SMTP host" in result["detail"]


# ── Channel Router ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_channel_router_dispatches_in_app():
    router = ChannelRouter()
    alert = AlertRecord(
        alert_id="alert_router_001",
        rule_id="rule_001",
        rule_name="Test",
        company_id="comp-001",
        severity=AlertSeverity.WARNING,
        status=AlertStatus.PENDING,
        metric="risk_score",
        metric_value=75.0,
        threshold=70.0,
        title="Test",
        message="Test",
        channels=[AlertChannel.IN_APP],
        triggered_at=datetime.now(timezone.utc).isoformat(),
    )
    results = await router.dispatch_alert(alert, {"in_app": {}})
    assert "in_app" in results
    assert results["in_app"]["success"] is True


@pytest.mark.asyncio
async def test_channel_router_handles_missing_config():
    router = ChannelRouter()
    alert = AlertRecord(
        alert_id="alert_router_002",
        rule_id="rule_001",
        rule_name="Test",
        company_id="comp-001",
        severity=AlertSeverity.WARNING,
        status=AlertStatus.PENDING,
        metric="risk_score",
        metric_value=75.0,
        threshold=70.0,
        title="Test",
        message="Test",
        channels=[AlertChannel.WEBHOOK],
        triggered_at=datetime.now(timezone.utc).isoformat(),
    )
    results = await router.dispatch_alert(alert, {})
    assert "webhook" in results
    assert results["webhook"]["success"] is False  # No URL configured
