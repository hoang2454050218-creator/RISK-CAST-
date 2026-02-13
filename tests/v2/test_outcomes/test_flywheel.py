"""
Tests for Flywheel Learning Loop.

Covers:
- Prior updates from outcome data
- Insufficient data handling
- Calibration drift detection
- Learning summary
- Conservative shift limits
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import Outcome
from riskcast.outcomes.flywheel import FlywheelEngine


@pytest.fixture
def flywheel():
    return FlywheelEngine(
        learning_rate=0.3,
        max_shift=5.0,
        drift_threshold=0.15,
        min_outcomes=5,
    )


async def _insert_outcome(
    session: AsyncSession,
    company_id: str,
    entity_type: str,
    predicted_risk: float,
    materialized: bool,
    prediction_error: float = 0.1,
) -> Outcome:
    """Helper: insert an outcome for flywheel testing."""
    outcome = Outcome(
        id=uuid.uuid4(),
        decision_id=f"dec_{uuid.uuid4().hex[:16]}",
        company_id=company_id,
        entity_type=entity_type,
        entity_id=f"ent-{uuid.uuid4().hex[:8]}",
        predicted_risk_score=Decimal(str(predicted_risk)),
        predicted_confidence=Decimal("0.8"),
        predicted_loss_usd=Decimal("10000"),
        predicted_action="insure",
        outcome_type="loss_occurred" if materialized else "no_impact",
        actual_loss_usd=Decimal("5000") if materialized else Decimal("0"),
        actual_delay_days=Decimal("0"),
        action_taken="insure",
        action_followed_recommendation=True,
        risk_materialized=materialized,
        prediction_error=Decimal(str(prediction_error)),
        was_accurate=prediction_error < 0.15,
        value_generated_usd=Decimal("5000") if materialized else Decimal("10000"),
        recorded_at=datetime.now(timezone.utc),
    )
    session.add(outcome)
    await session.flush()
    return outcome


# ── Insufficient Data ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_insufficient_data_returns_defaults(db, company_a, flywheel):
    """With fewer than min_outcomes, priors stay at defaults."""
    cid = str(company_a.id)
    # Only 2 outcomes — below threshold of 5
    for _ in range(2):
        await _insert_outcome(db, cid, "order", 50.0, True)
    await db.commit()

    state = await flywheel.compute_updated_priors(
        db, cid, "order", default_alpha=2.0, default_beta=5.0
    )
    assert state.n_outcomes == 2
    assert state.updated_alpha == 2.0  # No change
    assert state.updated_beta == 5.0   # No change
    assert state.needs_recalibration is False


# ── Prior Updates with Outcome Data ───────────────────────────────────


@pytest.mark.asyncio
async def test_high_risk_rate_increases_alpha(db, company_a, flywheel):
    """If actual risk rate > prior rate, alpha should increase."""
    cid = str(company_a.id)
    # 8 out of 10 risks materialized — much higher than prior (2/7 ≈ 0.286)
    for _ in range(8):
        await _insert_outcome(db, cid, "route", 70.0, True)
    for _ in range(2):
        await _insert_outcome(db, cid, "route", 30.0, False)
    await db.commit()

    state = await flywheel.compute_updated_priors(
        db, cid, "route", default_alpha=2.0, default_beta=5.0
    )
    assert state.n_outcomes == 10
    assert state.n_materialized == 8
    assert state.updated_alpha > 2.0  # Alpha increased


@pytest.mark.asyncio
async def test_low_risk_rate_decreases_alpha(db, company_a, flywheel):
    """If actual risk rate < prior rate, alpha should decrease."""
    cid = str(company_a.id)
    # 1 out of 10 risks materialized — much lower than prior (2/7 ≈ 0.286)
    for _ in range(1):
        await _insert_outcome(db, cid, "customer", 20.0, True)
    for _ in range(9):
        await _insert_outcome(db, cid, "customer", 20.0, False)
    await db.commit()

    state = await flywheel.compute_updated_priors(
        db, cid, "customer", default_alpha=2.0, default_beta=5.0
    )
    assert state.n_outcomes == 10
    assert state.n_materialized == 1
    assert state.updated_alpha < 2.0  # Alpha decreased


# ── Shift Limits ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_max_shift_is_respected(db, company_a, flywheel):
    """Even with extreme data, shift should not exceed max_shift."""
    cid = str(company_a.id)
    # All risks materialized — extreme case
    for _ in range(20):
        await _insert_outcome(db, cid, "order", 90.0, True)
    await db.commit()

    state = await flywheel.compute_updated_priors(
        db, cid, "order", default_alpha=2.0, default_beta=5.0
    )
    # Max shift = 5.0
    assert state.updated_alpha <= 2.0 + 5.0
    assert state.updated_beta >= 0.5  # Never goes below 0.5


# ── Calibration Drift ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_no_drift_when_calibrated(db, company_a, flywheel):
    """If predictions match reality, drift should be low."""
    cid = str(company_a.id)
    # Predicted 70% risk, 7 out of 10 materialized → well calibrated
    for _ in range(7):
        await _insert_outcome(db, cid, "order", 70.0, True)
    for _ in range(3):
        await _insert_outcome(db, cid, "order", 70.0, False)
    await db.commit()

    state = await flywheel.compute_updated_priors(db, cid, "order")
    assert state.calibration_drift < 0.05
    assert state.needs_recalibration is False


@pytest.mark.asyncio
async def test_high_drift_triggers_recalibration(db, company_a, flywheel):
    """Large drift between predicted and actual → needs_recalibration."""
    cid = str(company_a.id)
    # Predicted 90% risk, but only 1 materialized → large drift
    for _ in range(1):
        await _insert_outcome(db, cid, "route", 90.0, True)
    for _ in range(9):
        await _insert_outcome(db, cid, "route", 90.0, False)
    await db.commit()

    state = await flywheel.compute_updated_priors(db, cid, "route")
    assert state.calibration_drift > 0.5
    assert state.needs_recalibration is True


# ── Learning Summary ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_learning_summary_empty(db, company_a, flywheel):
    """Empty state returns collecting_data status."""
    summary = await flywheel.get_learning_summary(db, str(company_a.id))
    assert summary["total_outcomes"] == 0
    assert summary["flywheel_status"] == "collecting_data"


@pytest.mark.asyncio
async def test_learning_summary_with_data(db, company_a, flywheel):
    """With enough outcomes, flywheel status should be 'learning'."""
    cid = str(company_a.id)
    for _ in range(10):
        await _insert_outcome(db, cid, "order", 60.0, True)
    await db.commit()

    summary = await flywheel.get_learning_summary(db, cid)
    assert summary["total_outcomes"] >= 10
    assert summary["flywheel_status"] == "learning"
    assert "entity_states" in summary


# ── Serialization ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_flywheel_state_serialization(db, company_a, flywheel):
    """FlywheelState.to_dict() should produce valid dict."""
    cid = str(company_a.id)
    for _ in range(5):
        await _insert_outcome(db, cid, "order", 50.0, True)
    await db.commit()

    state = await flywheel.compute_updated_priors(db, cid, "order")
    d = state.to_dict()
    assert "entity_key" in d
    assert "updated_prior" in d
    assert "original_prior" in d
    assert "needs_recalibration" in d
    assert isinstance(d["updated_prior"]["alpha"], float)
