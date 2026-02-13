"""
Tests for Outcome API endpoints.

Covers:
- POST /api/v1/outcomes/record
- GET  /api/v1/outcomes
- GET  /api/v1/outcomes/accuracy
- GET  /api/v1/outcomes/roi
- GET  /api/v1/outcomes/flywheel
- GET  /api/v1/outcomes/flywheel/priors
- GET  /api/v1/outcomes/{decision_id}
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.api.deps import get_db
from riskcast.db.models import Outcome
from riskcast.main import app


@pytest_asyncio.fixture
async def client(session_factory, admin_user, admin_token):
    """
    Authenticated async test client with DB dependency override.

    Overrides the app's get_db to use the test in-memory session factory,
    so the API sees the same data as the test fixtures.
    """

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


@pytest_asyncio.fixture
async def seeded_outcomes(session_factory, company_a):
    """Insert 10 outcomes for testing API endpoints."""
    async with session_factory() as session:
        for i in range(10):
            materialized = i < 6  # 6 materialized, 4 didn't
            outcome = Outcome(
                id=uuid.uuid4(),
                decision_id=f"dec_api_{uuid.uuid4().hex[:12]}",
                company_id=str(company_a.id),
                entity_type="order",
                entity_id=f"ord-api-{i}",
                predicted_risk_score=Decimal(str(60 + i * 3)),
                predicted_confidence=Decimal("0.8"),
                predicted_loss_usd=Decimal(str(10000 + i * 5000)),
                predicted_action="insure",
                outcome_type="loss_occurred" if materialized else "no_impact",
                actual_loss_usd=Decimal(str(5000 * i)) if materialized else Decimal("0"),
                actual_delay_days=Decimal("0"),
                action_taken="insure" if i % 2 == 0 else "",
                action_followed_recommendation=(i % 2 == 0),
                risk_materialized=materialized,
                prediction_error=Decimal(str(0.05 + i * 0.02)),
                was_accurate=(0.05 + i * 0.02) < 0.15,
                value_generated_usd=Decimal(str(5000 if i % 2 == 0 else -2000)),
                recorded_at=datetime.now(timezone.utc),
            )
            session.add(outcome)
        await session.commit()


# ── Record Outcome API ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_record_outcome_endpoint(client):
    """POST /api/v1/outcomes/record creates an outcome."""
    decision_id = f"dec_{uuid.uuid4().hex[:16]}"
    body = {
        "outcome": {
            "decision_id": decision_id,
            "outcome_type": "loss_occurred",
            "actual_loss_usd": 25000.0,
            "actual_delay_days": 1.5,
            "action_taken": "insure",
            "action_followed_recommendation": True,
            "notes": "Test outcome",
        },
        "predicted_risk_score": 72.0,
        "predicted_confidence": 0.85,
        "predicted_loss_usd": 30000.0,
        "predicted_action": "insure",
        "entity_type": "order",
        "entity_id": "ord-test-api",
    }
    response = await client.post("/api/v1/outcomes/record", json=body)
    assert response.status_code == 200, f"Response: {response.text}"
    data = response.json()
    assert data["decision_id"] == decision_id
    assert data["risk_materialized"] is True
    assert data["actual_loss_usd"] == 25000.0


# ── List Outcomes API ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_outcomes_endpoint(client, seeded_outcomes):
    """GET /api/v1/outcomes returns list of outcomes."""
    response = await client.get("/api/v1/outcomes")
    assert response.status_code == 200, f"Response: {response.text}"
    data = response.json()
    assert "outcomes" in data
    assert data["total"] >= 0


# ── Accuracy Report API ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_accuracy_report_endpoint(client, seeded_outcomes):
    """GET /api/v1/outcomes/accuracy returns accuracy metrics."""
    response = await client.get("/api/v1/outcomes/accuracy", params={"days_back": 365})
    assert response.status_code == 200, f"Response: {response.text}"
    data = response.json()
    assert "brier_score" in data
    assert "precision" in data
    assert "recall" in data
    assert "f1_score" in data
    assert "calibration_drift" in data
    assert "recommendation" in data


# ── ROI Report API ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_roi_report_endpoint(client, seeded_outcomes):
    """GET /api/v1/outcomes/roi returns ROI metrics."""
    response = await client.get("/api/v1/outcomes/roi", params={"days_back": 365})
    assert response.status_code == 200, f"Response: {response.text}"
    data = response.json()
    assert "net_value_generated_usd" in data
    assert "roi_ratio" in data
    assert "recommendation_follow_rate" in data
    assert "recommendation" in data


# ── Flywheel Status API ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_flywheel_status_endpoint(client, seeded_outcomes):
    """GET /api/v1/outcomes/flywheel returns learning status."""
    response = await client.get("/api/v1/outcomes/flywheel")
    assert response.status_code == 200, f"Response: {response.text}"
    data = response.json()
    assert "total_outcomes" in data
    assert "flywheel_status" in data
    assert "entity_states" in data


# ── Flywheel Priors API ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_flywheel_priors_endpoint(client, seeded_outcomes):
    """GET /api/v1/outcomes/flywheel/priors returns updated priors."""
    response = await client.get(
        "/api/v1/outcomes/flywheel/priors",
        params={"entity_type": "order", "days_back": 365},
    )
    assert response.status_code == 200, f"Response: {response.text}"
    data = response.json()
    assert "entity_key" in data
    assert "updated_prior" in data
    assert "original_prior" in data
    assert "needs_recalibration" in data


# ── Get Outcome By Decision ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_outcome_by_decision_not_found(client):
    """GET /api/v1/outcomes/{decision_id} returns 404 if not found."""
    response = await client.get("/api/v1/outcomes/dec_nonexistent")
    assert response.status_code == 404
