"""
Tests for Accuracy Calculator.

Covers:
- Brier score computation
- Mean Absolute Error
- Calibration drift (ECE)
- Confusion matrix (TP, TN, FP, FN, precision, recall, F1)
- Empty state handling
- Recommendation generation
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import Outcome
from riskcast.outcomes.accuracy import AccuracyCalculator


@pytest.fixture
def calculator():
    return AccuracyCalculator(accuracy_threshold=0.15)


async def _insert_outcome(
    session: AsyncSession,
    company_id: str,
    predicted_risk: float,
    materialized: bool,
    predicted_loss: float = 10000.0,
    actual_loss: float = 0.0,
    prediction_error: float = 0.0,
    was_accurate: bool = True,
) -> Outcome:
    """Helper: insert an outcome directly for testing."""
    outcome = Outcome(
        id=uuid.uuid4(),
        decision_id=f"dec_{uuid.uuid4().hex[:16]}",
        company_id=company_id,
        entity_type="order",
        entity_id=f"ord-{uuid.uuid4().hex[:8]}",
        predicted_risk_score=Decimal(str(predicted_risk)),
        predicted_confidence=Decimal("0.8"),
        predicted_loss_usd=Decimal(str(predicted_loss)),
        predicted_action="insure",
        outcome_type="loss_occurred" if materialized else "no_impact",
        actual_loss_usd=Decimal(str(actual_loss)),
        actual_delay_days=Decimal("0"),
        action_taken="insure",
        action_followed_recommendation=True,
        risk_materialized=materialized,
        prediction_error=Decimal(str(prediction_error)),
        was_accurate=was_accurate,
        value_generated_usd=Decimal("0"),
        recorded_at=datetime.now(timezone.utc),
    )
    session.add(outcome)
    await session.flush()
    return outcome


# ── Empty State ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_accuracy_report_empty(db, company_a, calculator):
    """No outcomes → graceful empty report."""
    report = await calculator.generate_report(db, str(company_a.id))
    assert report.total_outcomes == 0
    assert report.brier_score == 0.0
    assert "Not enough outcome data" in report.recommendation


# ── Brier Score ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_perfect_predictions(db, company_a, calculator):
    """Perfect predictions should give Brier score ≈ 0."""
    cid = str(company_a.id)
    # 5 correct high-risk predictions (risk = 100, materialized)
    for _ in range(5):
        await _insert_outcome(db, cid, 100.0, True)
    # 5 correct low-risk predictions (risk = 0, not materialized)
    for _ in range(5):
        await _insert_outcome(db, cid, 0.0, False)
    await db.commit()

    report = await calculator.generate_report(db, cid, days_back=365)
    assert report.total_outcomes == 10
    assert report.brier_score == 0.0


@pytest.mark.asyncio
async def test_worst_predictions(db, company_a, calculator):
    """Worst predictions (100% confident wrong) → Brier ≈ 1.0."""
    cid = str(company_a.id)
    # Predicted 100% risk but nothing happened
    for _ in range(5):
        await _insert_outcome(db, cid, 100.0, False)
    # Predicted 0% risk but loss occurred
    for _ in range(5):
        await _insert_outcome(db, cid, 0.0, True)
    await db.commit()

    report = await calculator.generate_report(db, cid, days_back=365)
    assert report.brier_score == 1.0


@pytest.mark.asyncio
async def test_moderate_predictions(db, company_a, calculator):
    """Moderate predictions → Brier between 0 and 0.5."""
    cid = str(company_a.id)
    # Mix of correct and incorrect
    for _ in range(5):
        await _insert_outcome(db, cid, 70.0, True)   # Correct
    for _ in range(3):
        await _insert_outcome(db, cid, 40.0, False)  # Correct
    for _ in range(2):
        await _insert_outcome(db, cid, 80.0, False)  # Wrong
    await db.commit()

    report = await calculator.generate_report(db, cid, days_back=365)
    assert 0.0 < report.brier_score < 0.5


# ── Confusion Matrix ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_confusion_matrix(db, company_a, calculator):
    """Verify TP, TN, FP, FN counts."""
    cid = str(company_a.id)

    # TP: High risk predicted (≥50), materialized
    for _ in range(3):
        await _insert_outcome(db, cid, 80.0, True)
    # TN: Low risk (<50), didn't materialize
    for _ in range(4):
        await _insert_outcome(db, cid, 20.0, False)
    # FP: High risk predicted, didn't materialize
    for _ in range(2):
        await _insert_outcome(db, cid, 70.0, False)
    # FN: Low risk predicted, materialized
    for _ in range(1):
        await _insert_outcome(db, cid, 30.0, True)
    await db.commit()

    report = await calculator.generate_report(db, cid, days_back=365)
    assert report.true_positives == 3
    assert report.true_negatives == 4
    assert report.false_positives == 2
    assert report.false_negatives == 1

    # Precision = TP / (TP + FP) = 3 / 5 = 0.6
    assert abs(report.precision - 0.6) < 0.01
    # Recall = TP / (TP + FN) = 3 / 4 = 0.75
    assert abs(report.recall - 0.75) < 0.01
    # F1 = 2 × 0.6 × 0.75 / (0.6 + 0.75) = 2/3
    assert abs(report.f1_score - 2/3) < 0.01


# ── Calibration Drift (ECE) ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_well_calibrated_low_drift(db, company_a, calculator):
    """Well-calibrated predictions → low ECE."""
    cid = str(company_a.id)
    # Predictions cluster around 70%, actual rate ≈ 70%
    for _ in range(7):
        await _insert_outcome(db, cid, 70.0, True)
    for _ in range(3):
        await _insert_outcome(db, cid, 70.0, False)
    await db.commit()

    report = await calculator.generate_report(db, cid, days_back=365)
    assert report.calibration_drift < 0.05  # Very low drift


@pytest.mark.asyncio
async def test_miscalibrated_high_drift(db, company_a, calculator):
    """Predictions say 90% risk but only 10% materialize → high ECE."""
    cid = str(company_a.id)
    # Predict 90% risk but only 1 in 10 materialized
    for _ in range(1):
        await _insert_outcome(db, cid, 90.0, True)
    for _ in range(9):
        await _insert_outcome(db, cid, 90.0, False)
    await db.commit()

    report = await calculator.generate_report(db, cid, days_back=365)
    assert report.calibration_drift > 0.5  # Large drift


# ── Recommendation ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_recommendation_insufficient_data(db, company_a, calculator):
    """Few outcomes → recommendation suggests more data."""
    cid = str(company_a.id)
    for _ in range(3):
        await _insert_outcome(db, cid, 50.0, True)
    await db.commit()

    report = await calculator.generate_report(db, cid, days_back=365)
    assert "Need at least 10" in report.recommendation


@pytest.mark.asyncio
async def test_accuracy_rate(db, company_a, calculator):
    """Verify accuracy rate counts."""
    cid = str(company_a.id)
    # 8 accurate, 2 inaccurate
    for _ in range(8):
        await _insert_outcome(
            db, cid, 50.0, True,
            prediction_error=0.05, was_accurate=True,
        )
    for _ in range(2):
        await _insert_outcome(
            db, cid, 50.0, False,
            prediction_error=0.50, was_accurate=False,
        )
    await db.commit()

    report = await calculator.generate_report(db, cid, days_back=365)
    assert report.accuracy_rate == 0.8
