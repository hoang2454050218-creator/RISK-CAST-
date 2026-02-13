"""
Accuracy Calculator — Prediction vs Actual metrics.

Computes:
- Brier Score: mean squared error of probabilistic predictions
- Mean Absolute Error: average prediction error
- Calibration Drift: how far current model is from well-calibrated
- Confusion Matrix: TP, TN, FP, FN, precision, recall, F1
- Accuracy Rate: % of predictions within threshold

All metrics are computed from recorded outcomes.
"""

import math
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import Outcome
from riskcast.outcomes.schemas import AccuracyReport

logger = structlog.get_logger(__name__)

# Default: predictions within 15% considered accurate
DEFAULT_ACCURACY_THRESHOLD: float = 0.15

# Number of calibration bins for ECE
N_CALIBRATION_BINS: int = 10


class AccuracyCalculator:
    """
    Computes prediction accuracy metrics from recorded outcomes.

    All computations use real outcome data — no mocking.
    """

    def __init__(self, accuracy_threshold: float = DEFAULT_ACCURACY_THRESHOLD):
        self.accuracy_threshold = accuracy_threshold

    async def generate_report(
        self,
        session: AsyncSession,
        company_id: str,
        period: str = "last_30_days",
        days_back: int = 30,
    ) -> AccuracyReport:
        """
        Generate an accuracy report for a company.

        Args:
            session: Database session
            company_id: Tenant company ID
            period: Human-readable period label
            days_back: Number of days to look back

        Returns:
            AccuracyReport with all metrics
        """
        now = datetime.utcnow()

        # Fetch all outcomes in the period
        outcomes = await self._fetch_outcomes(session, company_id, days_back)

        total_outcomes = len(outcomes)

        # Count total decisions (outcomes + decisions without outcomes)
        total_decisions = await self._count_decisions(session, company_id, days_back)
        # Ensure total_decisions >= total_outcomes
        total_decisions = max(total_decisions, total_outcomes)

        coverage = total_outcomes / max(total_decisions, 1)

        if total_outcomes == 0:
            return AccuracyReport(
                period=period,
                generated_at=now.isoformat(),
                total_decisions=total_decisions,
                total_outcomes=0,
                coverage=0.0,
                brier_score=0.0,
                mean_absolute_error=0.0,
                accuracy_rate=0.0,
                calibration_drift=0.0,
                true_positives=0,
                true_negatives=0,
                false_positives=0,
                false_negatives=0,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                recommendation="Not enough outcome data to compute accuracy metrics. "
                               "Record at least 10 outcomes for meaningful results.",
            )

        # ── Brier Score ───────────────────────────────────────────────
        brier_score = self._compute_brier_score(outcomes)

        # ── Mean Absolute Error ───────────────────────────────────────
        mae = self._compute_mae(outcomes)

        # ── Accuracy Rate ─────────────────────────────────────────────
        accurate_count = sum(1 for o in outcomes if o.was_accurate)
        accuracy_rate = accurate_count / total_outcomes

        # ── Calibration Drift (ECE) ──────────────────────────────────
        calibration_drift = self._compute_ece(outcomes)

        # ── Confusion Matrix ──────────────────────────────────────────
        tp, tn, fp, fn = self._compute_confusion_matrix(outcomes)
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        f1_score = (
            2 * precision * recall / max(precision + recall, 1e-9)
        )

        # ── Recommendation ────────────────────────────────────────────
        recommendation = self._generate_recommendation(
            brier_score, accuracy_rate, calibration_drift, total_outcomes
        )

        report = AccuracyReport(
            period=period,
            generated_at=now.isoformat(),
            total_decisions=total_decisions,
            total_outcomes=total_outcomes,
            coverage=round(coverage, 4),
            brier_score=round(brier_score, 4),
            mean_absolute_error=round(mae, 4),
            accuracy_rate=round(accuracy_rate, 4),
            calibration_drift=round(calibration_drift, 4),
            true_positives=tp,
            true_negatives=tn,
            false_positives=fp,
            false_negatives=fn,
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1_score=round(f1_score, 4),
            recommendation=recommendation,
        )

        logger.info(
            "accuracy_report_generated",
            company_id=company_id,
            period=period,
            brier_score=round(brier_score, 4),
            accuracy_rate=round(accuracy_rate, 4),
            calibration_drift=round(calibration_drift, 4),
            total_outcomes=total_outcomes,
        )

        return report

    def _compute_brier_score(self, outcomes: list[Outcome]) -> float:
        """
        Compute Brier Score: mean squared error of probabilistic predictions.

        Brier = (1/N) × Σ (predicted_prob - actual_binary)²

        Lower is better. 0 = perfect, 0.25 = random (for binary), 1 = worst.
        """
        total = 0.0
        for o in outcomes:
            predicted_prob = float(o.predicted_risk_score) / 100.0  # Normalize to [0,1]
            actual_binary = 1.0 if o.risk_materialized else 0.0
            total += (predicted_prob - actual_binary) ** 2
        return total / max(len(outcomes), 1)

    def _compute_mae(self, outcomes: list[Outcome]) -> float:
        """Compute Mean Absolute Error of prediction errors."""
        if not outcomes:
            return 0.0
        total = sum(float(o.prediction_error) for o in outcomes)
        return total / len(outcomes)

    def _compute_ece(self, outcomes: list[Outcome]) -> float:
        """
        Compute Expected Calibration Error (ECE).

        Groups predictions into bins and measures how well-calibrated they are.
        A well-calibrated model: predicted probability ≈ actual frequency.
        """
        bins: dict[int, list[tuple[float, float]]] = {i: [] for i in range(N_CALIBRATION_BINS)}

        for o in outcomes:
            predicted_prob = float(o.predicted_risk_score) / 100.0
            actual_binary = 1.0 if o.risk_materialized else 0.0
            bin_idx = min(int(predicted_prob * N_CALIBRATION_BINS), N_CALIBRATION_BINS - 1)
            bins[bin_idx].append((predicted_prob, actual_binary))

        ece = 0.0
        n_total = len(outcomes)

        for bin_items in bins.values():
            if not bin_items:
                continue
            n_bin = len(bin_items)
            avg_predicted = sum(p for p, _ in bin_items) / n_bin
            avg_actual = sum(a for _, a in bin_items) / n_bin
            ece += (n_bin / n_total) * abs(avg_predicted - avg_actual)

        return ece

    def _compute_confusion_matrix(
        self, outcomes: list[Outcome]
    ) -> tuple[int, int, int, int]:
        """
        Compute confusion matrix values.

        TP: Predicted high risk (≥50), risk materialized
        TN: Predicted low risk (<50), risk did NOT materialize
        FP: Predicted high risk (≥50), risk did NOT materialize
        FN: Predicted low risk (<50), risk materialized
        """
        tp = tn = fp = fn = 0
        for o in outcomes:
            predicted_high = float(o.predicted_risk_score) >= 50.0
            materialized = o.risk_materialized
            if predicted_high and materialized:
                tp += 1
            elif not predicted_high and not materialized:
                tn += 1
            elif predicted_high and not materialized:
                fp += 1
            else:
                fn += 1
        return tp, tn, fp, fn

    def _generate_recommendation(
        self,
        brier_score: float,
        accuracy_rate: float,
        calibration_drift: float,
        n_outcomes: int,
    ) -> str:
        """Generate a human-readable recommendation based on metrics."""
        parts: list[str] = []

        if n_outcomes < 10:
            return (
                f"Only {n_outcomes} outcomes recorded. "
                "Need at least 10 for reliable metrics. Keep recording outcomes."
            )

        if brier_score < 0.1:
            parts.append("Brier score is excellent (<0.1) — predictions are well-calibrated.")
        elif brier_score < 0.2:
            parts.append("Brier score is good (<0.2) — minor calibration improvements possible.")
        else:
            parts.append(
                f"Brier score is {brier_score:.3f} — consider recalibrating the model."
            )

        if accuracy_rate >= 0.8:
            parts.append(f"Accuracy rate is strong at {accuracy_rate:.0%}.")
        elif accuracy_rate >= 0.6:
            parts.append(f"Accuracy rate is moderate at {accuracy_rate:.0%} — room for improvement.")
        else:
            parts.append(
                f"Accuracy rate is low at {accuracy_rate:.0%} — model retraining recommended."
            )

        if calibration_drift > 0.15:
            parts.append(
                f"Calibration drift is {calibration_drift:.3f} — flywheel re-calibration recommended."
            )

        return " ".join(parts)

    async def _fetch_outcomes(
        self,
        session: AsyncSession,
        company_id: str,
        days_back: int,
    ) -> list[Outcome]:
        """Fetch outcomes within the lookback period."""
        cutoff = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        from datetime import timedelta
        cutoff = cutoff - timedelta(days=days_back)

        result = await session.execute(
            select(Outcome).where(
                Outcome.company_id == company_id,
                Outcome.recorded_at >= cutoff,
            )
        )
        return list(result.scalars().all())

    async def _count_decisions(
        self,
        session: AsyncSession,
        company_id: str,
        days_back: int,
    ) -> int:
        """
        Count total decisions in the period.

        Uses outcomes count as a lower bound since we don't have a
        dedicated decisions table yet. Future: query decisions table.
        """
        cutoff = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        from datetime import timedelta
        cutoff = cutoff - timedelta(days=days_back)

        result = await session.execute(
            select(func.count(Outcome.id)).where(
                Outcome.company_id == company_id,
                Outcome.recorded_at >= cutoff,
            )
        )
        return result.scalar_one() or 0
