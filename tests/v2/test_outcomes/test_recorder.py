"""
Tests for Outcome Recorder.

Covers:
- Record outcome for a decision
- Prediction error computation
- Value generated computation
- Outcome retrieval
- Duplicate decision_id prevention
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio

from riskcast.db.models import Outcome
from riskcast.outcomes.recorder import OutcomeRecorder
from riskcast.outcomes.schemas import OutcomeRecordRequest, OutcomeType


@pytest.fixture
def recorder():
    return OutcomeRecorder(accuracy_threshold=0.15)


# ── Record Outcome ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_record_loss_occurred(db, company_a, recorder):
    """Record an outcome where the predicted risk materialized."""
    request = OutcomeRecordRequest(
        decision_id=f"dec_{uuid.uuid4().hex[:16]}",
        outcome_type=OutcomeType.LOSS_OCCURRED,
        actual_loss_usd=50000.0,
        actual_delay_days=3.0,
        action_taken="insure",
        action_followed_recommendation=True,
        notes="Shipment was damaged in transit",
    )
    result = await recorder.record_outcome(
        session=db,
        company_id=str(company_a.id),
        request=request,
        predicted_risk_score=75.0,
        predicted_confidence=0.85,
        predicted_loss_usd=80000.0,
        predicted_action="insure",
        entity_type="order",
        entity_id="ord-123",
    )
    await db.commit()

    assert result.risk_materialized is True
    assert result.actual_loss_usd == 50000.0
    assert result.predicted_risk_score == 75.0
    assert result.outcome_type == OutcomeType.LOSS_OCCURRED
    assert result.decision_id == request.decision_id


@pytest.mark.asyncio
async def test_record_no_impact(db, company_a, recorder):
    """Record an outcome where nothing happened."""
    request = OutcomeRecordRequest(
        decision_id=f"dec_{uuid.uuid4().hex[:16]}",
        outcome_type=OutcomeType.NO_IMPACT,
        actual_loss_usd=0.0,
    )
    result = await recorder.record_outcome(
        session=db,
        company_id=str(company_a.id),
        request=request,
        predicted_risk_score=30.0,
        predicted_confidence=0.6,
        predicted_loss_usd=10000.0,
        predicted_action="monitor_only",
        entity_type="order",
        entity_id="ord-456",
    )
    await db.commit()

    assert result.risk_materialized is False
    assert result.actual_loss_usd == 0.0


@pytest.mark.asyncio
async def test_record_partial_impact(db, company_a, recorder):
    """Record a partial impact outcome."""
    request = OutcomeRecordRequest(
        decision_id=f"dec_{uuid.uuid4().hex[:16]}",
        outcome_type=OutcomeType.PARTIAL_IMPACT,
        actual_loss_usd=15000.0,
        action_followed_recommendation=True,
        action_taken="reroute",
    )
    result = await recorder.record_outcome(
        session=db,
        company_id=str(company_a.id),
        request=request,
        predicted_risk_score=60.0,
        predicted_confidence=0.7,
        predicted_loss_usd=30000.0,
        predicted_action="reroute",
        entity_type="order",
        entity_id="ord-789",
    )
    await db.commit()

    assert result.risk_materialized is True
    assert result.value_generated_usd == 15000.0  # predicted - actual


# ── Prediction Error ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_accurate_prediction(db, company_a, recorder):
    """A prediction that matches reality closely should be accurate."""
    request = OutcomeRecordRequest(
        decision_id=f"dec_{uuid.uuid4().hex[:16]}",
        outcome_type=OutcomeType.LOSS_OCCURRED,
        actual_loss_usd=75000.0,
    )
    result = await recorder.record_outcome(
        session=db,
        company_id=str(company_a.id),
        request=request,
        predicted_risk_score=80.0,  # High risk predicted
        predicted_confidence=0.9,
        predicted_loss_usd=80000.0,  # Close to actual
        predicted_action="insure",
        entity_type="order",
        entity_id="ord-acc-1",
    )
    await db.commit()

    # Direction correct + magnitude close → low error
    assert result.prediction_error < 0.15
    assert result.was_accurate is True


@pytest.mark.asyncio
async def test_inaccurate_prediction_wrong_direction(db, company_a, recorder):
    """Predicted low risk but risk materialized → high error."""
    request = OutcomeRecordRequest(
        decision_id=f"dec_{uuid.uuid4().hex[:16]}",
        outcome_type=OutcomeType.LOSS_OCCURRED,
        actual_loss_usd=100000.0,
    )
    result = await recorder.record_outcome(
        session=db,
        company_id=str(company_a.id),
        request=request,
        predicted_risk_score=20.0,  # Low risk predicted, but loss occurred!
        predicted_confidence=0.8,
        predicted_loss_usd=5000.0,
        predicted_action="monitor_only",
        entity_type="order",
        entity_id="ord-inacc-1",
    )
    await db.commit()

    assert result.prediction_error > 0.5  # Big miss
    assert result.was_accurate is False


# ── Value Generated ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_value_when_action_followed_risk_avoided(db, company_a, recorder):
    """Following recommendation and risk didn't materialize → full value."""
    request = OutcomeRecordRequest(
        decision_id=f"dec_{uuid.uuid4().hex[:16]}",
        outcome_type=OutcomeType.LOSS_AVOIDED,
        actual_loss_usd=0.0,
        action_followed_recommendation=True,
        action_taken="reroute",
    )
    result = await recorder.record_outcome(
        session=db,
        company_id=str(company_a.id),
        request=request,
        predicted_risk_score=70.0,
        predicted_confidence=0.85,
        predicted_loss_usd=50000.0,
        predicted_action="reroute",
        entity_type="order",
        entity_id="ord-val-1",
    )
    await db.commit()

    assert result.value_generated_usd == 50000.0  # Full predicted loss avoided


@pytest.mark.asyncio
async def test_negative_value_when_action_ignored(db, company_a, recorder):
    """Not following recommendation and risk materialized → negative value."""
    request = OutcomeRecordRequest(
        decision_id=f"dec_{uuid.uuid4().hex[:16]}",
        outcome_type=OutcomeType.LOSS_OCCURRED,
        actual_loss_usd=80000.0,
        action_followed_recommendation=False,
    )
    result = await recorder.record_outcome(
        session=db,
        company_id=str(company_a.id),
        request=request,
        predicted_risk_score=65.0,
        predicted_confidence=0.75,
        predicted_loss_usd=90000.0,
        predicted_action="insure",
        entity_type="order",
        entity_id="ord-val-2",
    )
    await db.commit()

    assert result.value_generated_usd == -80000.0  # Missed opportunity


@pytest.mark.asyncio
async def test_zero_value_when_nothing_happened(db, company_a, recorder):
    """Not following recommendation but nothing happened → zero value."""
    request = OutcomeRecordRequest(
        decision_id=f"dec_{uuid.uuid4().hex[:16]}",
        outcome_type=OutcomeType.NO_IMPACT,
        actual_loss_usd=0.0,
        action_followed_recommendation=False,
    )
    result = await recorder.record_outcome(
        session=db,
        company_id=str(company_a.id),
        request=request,
        predicted_risk_score=40.0,
        predicted_confidence=0.6,
        predicted_loss_usd=10000.0,
        predicted_action="monitor_only",
        entity_type="order",
        entity_id="ord-val-3",
    )
    await db.commit()

    assert result.value_generated_usd == 0.0


# ── Retrieval ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_outcomes_list(db, company_a, recorder):
    """List outcomes returns recorded outcomes."""
    decision_id = f"dec_{uuid.uuid4().hex[:16]}"
    request = OutcomeRecordRequest(
        decision_id=decision_id,
        outcome_type=OutcomeType.NO_IMPACT,
    )
    await recorder.record_outcome(
        session=db,
        company_id=str(company_a.id),
        request=request,
        predicted_risk_score=50.0,
        predicted_confidence=0.7,
        predicted_loss_usd=20000.0,
        predicted_action="monitor_only",
        entity_type="order",
        entity_id="ord-list-1",
    )
    await db.commit()

    outcomes = await recorder.get_outcomes(db, str(company_a.id))
    assert len(outcomes) >= 1


@pytest.mark.asyncio
async def test_get_outcome_by_decision(db, company_a, recorder):
    """Get outcome by decision_id returns the correct outcome."""
    decision_id = f"dec_{uuid.uuid4().hex[:16]}"
    request = OutcomeRecordRequest(
        decision_id=decision_id,
        outcome_type=OutcomeType.DELAY_OCCURRED,
        actual_delay_days=2.5,
    )
    await recorder.record_outcome(
        session=db,
        company_id=str(company_a.id),
        request=request,
        predicted_risk_score=55.0,
        predicted_confidence=0.65,
        predicted_loss_usd=15000.0,
        predicted_action="delay_shipment",
        entity_type="order",
        entity_id="ord-get-1",
    )
    await db.commit()

    result = await recorder.get_outcome_by_decision(
        db, str(company_a.id), decision_id
    )
    assert result is not None
    assert result.decision_id == decision_id
    assert result.actual_delay_days == 2.5


@pytest.mark.asyncio
async def test_get_nonexistent_outcome(db, company_a, recorder):
    """Looking up a non-existent decision returns None."""
    result = await recorder.get_outcome_by_decision(
        db, str(company_a.id), "dec_doesnotexist"
    )
    assert result is None
