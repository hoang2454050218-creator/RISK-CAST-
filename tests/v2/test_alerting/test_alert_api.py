"""
Tests for Alert API endpoints.

Covers:
- POST /api/v1/alerts/rules (create rule)
- GET  /api/v1/alerts/rules (list rules)
- DELETE /api/v1/alerts/rules/{rule_id}
- POST /api/v1/alerts/evaluate (evaluate rules)
- GET  /api/v1/alerts (list alerts)
- POST /api/v1/alerts/{alert_id}/acknowledge
- GET  /api/v1/alerts/early-warnings
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from riskcast.api.deps import get_db
from riskcast.db.models import Alert, AlertRuleModel
from riskcast.main import app


@pytest_asyncio.fixture
async def client(session_factory, admin_user, admin_token):
    """Authenticated async test client with DB dependency override."""

    async def _override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {admin_token}"},
    ) as c:
        yield c
    app.dependency_overrides.clear()


# ── Rule CRUD ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_alert_rule(client):
    """POST /api/v1/alerts/rules creates a rule."""
    body = {
        "rule_name": "High Risk Alert",
        "description": "Alert when risk score exceeds 80",
        "metric": "risk_score",
        "operator": "gt",
        "threshold": 80.0,
        "severity": "high",
        "channels": ["in_app"],
        "cooldown_minutes": 15,
        "max_per_day": 20,
    }
    response = await client.post("/api/v1/alerts/rules", json=body)
    assert response.status_code == 200, f"Response: {response.text}"
    data = response.json()
    assert data["rule_name"] == "High Risk Alert"
    assert data["metric"] == "risk_score"
    assert data["operator"] == "gt"
    assert data["threshold"] == 80.0
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_list_alert_rules(client):
    """GET /api/v1/alerts/rules returns rules."""
    # Create a rule first
    await client.post("/api/v1/alerts/rules", json={
        "rule_name": "Test Rule",
        "metric": "confidence",
        "operator": "lt",
        "threshold": 0.3,
    })
    response = await client.get("/api/v1/alerts/rules")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_delete_alert_rule(client):
    """DELETE /api/v1/alerts/rules/{rule_id} deletes a rule."""
    # Create a rule
    create_resp = await client.post("/api/v1/alerts/rules", json={
        "rule_name": "Delete Me",
        "metric": "risk_score",
        "operator": "gt",
        "threshold": 90.0,
    })
    rule_id = create_resp.json()["rule_id"]

    # Delete it
    del_resp = await client.delete(f"/api/v1/alerts/rules/{rule_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True

    # Verify gone
    del_again = await client.delete(f"/api/v1/alerts/rules/{rule_id}")
    assert del_again.status_code == 404


# ── Evaluate Rules ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_evaluate_triggers_alert(client):
    """POST /api/v1/alerts/evaluate fires alerts when rules match."""
    # Create a rule
    await client.post("/api/v1/alerts/rules", json={
        "rule_name": "Eval Test Rule",
        "metric": "risk_score",
        "operator": "gte",
        "threshold": 70.0,
        "channels": ["in_app"],
        "cooldown_minutes": 0,
        "max_per_day": 100,
    })

    # Evaluate with a metric that triggers
    eval_resp = await client.post("/api/v1/alerts/evaluate", json={
        "metrics": {"risk_score": 85.0},
        "entity_type": "order",
        "entity_id": "ord-eval-1",
    })
    assert eval_resp.status_code == 200, f"Response: {eval_resp.text}"
    data = eval_resp.json()
    assert len(data) >= 1
    assert data[0]["metric_value"] == 85.0


@pytest.mark.asyncio
async def test_evaluate_no_trigger(client):
    """POST /api/v1/alerts/evaluate returns empty when no rules match."""
    # Create a rule with high threshold
    await client.post("/api/v1/alerts/rules", json={
        "rule_name": "No Trigger Rule",
        "metric": "risk_score",
        "operator": "gt",
        "threshold": 99.0,
    })

    eval_resp = await client.post("/api/v1/alerts/evaluate", json={
        "metrics": {"risk_score": 50.0},
    })
    assert eval_resp.status_code == 200
    data = eval_resp.json()
    # The "No Trigger Rule" should not fire (50 < 99)
    no_trigger_alerts = [a for a in data if a["rule_name"] == "No Trigger Rule"]
    assert len(no_trigger_alerts) == 0


# ── Alert History ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_alerts(client):
    """GET /api/v1/alerts returns alert history."""
    response = await client.get("/api/v1/alerts")
    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data
    assert "total" in data


# ── Acknowledge ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_acknowledge_nonexistent_alert(client):
    """POST /api/v1/alerts/{alert_id}/acknowledge returns 404 for unknown."""
    response = await client.post("/api/v1/alerts/alert_nonexistent/acknowledge")
    assert response.status_code == 404


# ── Early Warnings ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_early_warnings_endpoint(client):
    """GET /api/v1/alerts/early-warnings returns warnings."""
    response = await client.get("/api/v1/alerts/early-warnings")
    assert response.status_code == 200
    data = response.json()
    assert "warnings" in data
    assert "total" in data
