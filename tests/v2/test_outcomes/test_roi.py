"""
Tests for ROI Calculator.

Covers:
- Empty state handling
- Total predicted vs actual loss
- Net value generated
- ROI ratio
- Recommendation follow rate
- Action effectiveness
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import Outcome
from riskcast.outcomes.roi import ROICalculator


@pytest.fixture
def roi():
    return ROICalculator()


async def _insert_outcome(
    session: AsyncSession,
    company_id: str,
    predicted_loss: float,
    actual_loss: float,
    action_followed: bool,
    value_generated: float,
) -> None:
    """Helper: insert an outcome for ROI testing."""
    outcome = Outcome(
        id=uuid.uuid4(),
        decision_id=f"dec_{uuid.uuid4().hex[:16]}",
        company_id=company_id,
        entity_type="order",
        entity_id=f"ord-{uuid.uuid4().hex[:8]}",
        predicted_risk_score=Decimal("60"),
        predicted_confidence=Decimal("0.8"),
        predicted_loss_usd=Decimal(str(predicted_loss)),
        predicted_action="insure",
        outcome_type="loss_occurred" if actual_loss > 0 else "no_impact",
        actual_loss_usd=Decimal(str(actual_loss)),
        actual_delay_days=Decimal("0"),
        action_taken="insure" if action_followed else "",
        action_followed_recommendation=action_followed,
        risk_materialized=actual_loss > 0,
        prediction_error=Decimal("0.1"),
        was_accurate=True,
        value_generated_usd=Decimal(str(value_generated)),
        recorded_at=datetime.now(timezone.utc),
    )
    session.add(outcome)
    await session.flush()


# ── Empty State ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_roi_empty(db, company_a, roi):
    """No outcomes → graceful empty report."""
    report = await roi.generate_report(db, str(company_a.id))
    assert report.total_decisions == 0
    assert report.net_value_generated_usd == 0.0
    assert report.roi_ratio == 0.0
    assert "No outcomes recorded" in report.recommendation


# ── Value Tracking ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_positive_value_generation(db, company_a, roi):
    """Actions that avoid loss generate positive value."""
    cid = str(company_a.id)
    # 5 decisions, followed, avoided loss ($50k each → $250k total value)
    for _ in range(5):
        await _insert_outcome(db, cid, 50000.0, 0.0, True, 50000.0)
    await db.commit()

    report = await roi.generate_report(db, cid, days_back=365)
    assert report.decisions_with_outcomes == 5
    assert report.net_value_generated_usd == 250000.0
    assert report.total_predicted_loss_usd == 250000.0
    assert report.total_actual_loss_usd == 0.0


@pytest.mark.asyncio
async def test_negative_value_when_ignored(db, company_a, roi):
    """Not following recommendations + loss occurring → negative value."""
    cid = str(company_a.id)
    # 5 decisions, not followed, loss occurred ($30k each → -$150k total value)
    for _ in range(5):
        await _insert_outcome(db, cid, 40000.0, 30000.0, False, -30000.0)
    await db.commit()

    report = await roi.generate_report(db, cid, days_back=365)
    assert report.net_value_generated_usd == -150000.0


@pytest.mark.asyncio
async def test_mixed_outcomes(db, company_a, roi):
    """Mix of positive and negative outcomes."""
    cid = str(company_a.id)
    # 3 wins (followed, $50k value each)
    for _ in range(3):
        await _insert_outcome(db, cid, 50000.0, 0.0, True, 50000.0)
    # 2 losses (not followed, -$20k each)
    for _ in range(2):
        await _insert_outcome(db, cid, 30000.0, 20000.0, False, -20000.0)
    await db.commit()

    report = await roi.generate_report(db, cid, days_back=365)
    assert report.net_value_generated_usd == 110000.0  # 150k - 40k


# ── Follow Rate ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_follow_rate(db, company_a, roi):
    """Recommendation follow rate computed correctly."""
    cid = str(company_a.id)
    # 7 followed, 3 not followed
    for _ in range(7):
        await _insert_outcome(db, cid, 10000.0, 0.0, True, 10000.0)
    for _ in range(3):
        await _insert_outcome(db, cid, 10000.0, 5000.0, False, -5000.0)
    await db.commit()

    report = await roi.generate_report(db, cid, days_back=365)
    assert abs(report.recommendation_follow_rate - 0.7) < 0.01


# ── Action Effectiveness ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_action_effectiveness(db, company_a, roi):
    """Count actions that helped vs didn't help."""
    cid = str(company_a.id)
    # 4 followed + positive value
    for _ in range(4):
        await _insert_outcome(db, cid, 20000.0, 0.0, True, 20000.0)
    # 2 followed but still lost (value = 0 or negative)
    for _ in range(2):
        await _insert_outcome(db, cid, 20000.0, 20000.0, True, 0.0)
    await db.commit()

    report = await roi.generate_report(db, cid, days_back=365)
    assert report.actions_that_helped == 4
    assert report.actions_that_didnt_help == 2


# ── ROI Ratio ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_roi_ratio_positive(db, company_a, roi):
    """Positive ROI when net value exceeds action cost."""
    cid = str(company_a.id)
    for _ in range(10):
        await _insert_outcome(db, cid, 100000.0, 0.0, True, 100000.0)
    await db.commit()

    report = await roi.generate_report(db, cid, days_back=365)
    assert report.roi_ratio > 1.0  # Positive ROI
    assert report.total_action_cost_usd > 0  # Action cost estimated


# ── Recommendation Text ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_recommendation_insufficient_data(db, company_a, roi):
    """Few outcomes → recommendation asks for more data."""
    cid = str(company_a.id)
    for _ in range(3):
        await _insert_outcome(db, cid, 10000.0, 0.0, True, 10000.0)
    await db.commit()

    report = await roi.generate_report(db, cid, days_back=365)
    assert "Only 3 outcomes" in report.recommendation
