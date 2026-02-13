"""
Early Warning Detector — Trend detection and threshold crossing prediction.

Analyzes historical metric values to detect:
1. Rising/falling trends
2. Acceleration (rate of change is increasing)
3. Predicted threshold crossing time

Uses simple linear regression for trend detection and extrapolation.
All computations are traceable with data point counts and confidence.
"""

import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.alerting.schemas import (
    AlertSeverity,
    EarlyWarning,
    TrendDirection,
)
from riskcast.db.models import Outcome, Signal

logger = structlog.get_logger(__name__)

# Minimum data points for trend detection
MIN_DATA_POINTS: int = 3

# Confidence thresholds
HIGH_CONFIDENCE_THRESHOLD: float = 0.7
MEDIUM_CONFIDENCE_THRESHOLD: float = 0.4


class EarlyWarningDetector:
    """
    Detects early warning signals by analyzing metric trends.

    Pipeline:
    1. Collect historical data points for a metric
    2. Compute linear regression (slope + R²)
    3. Determine trend direction and confidence
    4. Predict when threshold will be crossed
    5. Generate early warning with recommendation
    """

    def __init__(self, min_data_points: int = MIN_DATA_POINTS):
        self.min_data_points = min_data_points

    def detect_from_values(
        self,
        values: list[tuple[float, float]],
        metric: str,
        threshold: float,
        company_id: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
    ) -> Optional[EarlyWarning]:
        """
        Detect early warning from a list of (timestamp_hours, value) pairs.

        Args:
            values: List of (hours_ago, metric_value) sorted oldest to newest
            metric: Name of the metric
            threshold: Alert threshold to predict crossing for
            company_id: Tenant company ID
            entity_type: Optional entity type filter
            entity_id: Optional entity ID

        Returns:
            EarlyWarning if a trend is detected, None if insufficient data
        """
        if len(values) < self.min_data_points:
            return None

        warning_id = f"ew_{uuid.uuid4().hex[:16]}"
        now = datetime.utcnow()

        # Current value is the latest
        current_value = values[-1][1]
        distance = threshold - current_value

        # ── Linear regression ─────────────────────────────────────────
        slope, intercept, r_squared = self._linear_regression(values)

        # ── Trend direction ───────────────────────────────────────────
        trend = self._determine_trend(slope, r_squared, values)

        # ── Predicted threshold crossing ──────────────────────────────
        crossing_hours = self._predict_crossing(
            slope, current_value, threshold, values[-1][0]
        )

        # ── Confidence ────────────────────────────────────────────────
        confidence = self._compute_confidence(r_squared, len(values))

        # ── Urgency ───────────────────────────────────────────────────
        urgency = self._determine_urgency(crossing_hours, distance, threshold)

        # ── Recommendation ────────────────────────────────────────────
        recommendation = self._generate_recommendation(
            metric, current_value, threshold, trend, crossing_hours
        )

        warning = EarlyWarning(
            warning_id=warning_id,
            company_id=company_id,
            metric=metric,
            entity_type=entity_type,
            entity_id=entity_id,
            current_value=round(current_value, 4),
            threshold=threshold,
            distance_to_threshold=round(distance, 4),
            trend_direction=trend,
            trend_slope=round(slope, 6),
            predicted_crossing_hours=round(crossing_hours, 1) if crossing_hours else None,
            confidence=round(confidence, 4),
            data_points_used=len(values),
            recommendation=recommendation,
            urgency=urgency,
            generated_at=now.isoformat(),
        )

        logger.info(
            "early_warning_detected",
            warning_id=warning_id,
            metric=metric,
            trend=trend.value,
            slope=round(slope, 6),
            crossing_hours=crossing_hours,
            confidence=round(confidence, 4),
        )

        return warning

    async def detect_risk_trends(
        self,
        session: AsyncSession,
        company_id: str,
        threshold: float = 70.0,
        days_back: int = 14,
    ) -> list[EarlyWarning]:
        """
        Detect risk score trends from outcome history.

        Looks at predicted_risk_score over time and detects
        entities where risk is trending toward the threshold.
        """
        cutoff = datetime.utcnow() - timedelta(days=days_back)

        # Get entity types with outcomes
        result = await session.execute(
            select(
                Outcome.entity_type,
                Outcome.entity_id,
            )
            .where(
                Outcome.company_id == company_id,
                Outcome.recorded_at >= cutoff,
            )
            .group_by(Outcome.entity_type, Outcome.entity_id)
            .having(func.count(Outcome.id) >= self.min_data_points)
        )
        entity_groups = result.all()

        warnings: list[EarlyWarning] = []
        for entity_type, entity_id in entity_groups:
            # Get risk scores over time for this entity
            scores_result = await session.execute(
                select(Outcome.recorded_at, Outcome.predicted_risk_score)
                .where(
                    Outcome.company_id == company_id,
                    Outcome.entity_type == entity_type,
                    Outcome.entity_id == entity_id,
                    Outcome.recorded_at >= cutoff,
                )
                .order_by(Outcome.recorded_at)
            )
            rows = scores_result.all()

            if len(rows) < self.min_data_points:
                continue

            # Convert to (hours_from_start, value) pairs
            base_time = rows[0][0]
            values = []
            for recorded_at, score in rows:
                hours = (recorded_at - base_time).total_seconds() / 3600.0
                values.append((hours, float(score)))

            warning = self.detect_from_values(
                values, "risk_score", threshold, company_id,
                entity_type, str(entity_id),
            )
            if warning and warning.trend_direction in (
                TrendDirection.RISING, TrendDirection.ACCELERATING
            ):
                warnings.append(warning)

        return warnings

    async def detect_signal_trends(
        self,
        session: AsyncSession,
        company_id: str,
        days_back: int = 7,
    ) -> list[EarlyWarning]:
        """
        Detect trends in signal severity over time.

        Groups signals by entity and looks for rising severity trends.
        """
        cutoff = datetime.utcnow() - timedelta(days=days_back)

        result = await session.execute(
            select(
                Signal.entity_type,
                Signal.entity_id,
            )
            .where(
                Signal.company_id == company_id,
                Signal.created_at >= cutoff,
                Signal.is_active.is_(True),
            )
            .group_by(Signal.entity_type, Signal.entity_id)
            .having(func.count(Signal.id) >= self.min_data_points)
        )
        entity_groups = result.all()

        warnings: list[EarlyWarning] = []
        for entity_type, entity_id in entity_groups:
            if not entity_type or not entity_id:
                continue

            scores_result = await session.execute(
                select(Signal.created_at, Signal.severity_score)
                .where(
                    Signal.company_id == company_id,
                    Signal.entity_type == entity_type,
                    Signal.entity_id == entity_id,
                    Signal.created_at >= cutoff,
                    Signal.severity_score.isnot(None),
                )
                .order_by(Signal.created_at)
            )
            rows = scores_result.all()

            if len(rows) < self.min_data_points:
                continue

            base_time = rows[0][0]
            values = []
            for created_at, score in rows:
                hours = (created_at - base_time).total_seconds() / 3600.0
                values.append((hours, float(score)))

            warning = self.detect_from_values(
                values, "signal_severity", 80.0, company_id,
                entity_type, str(entity_id),
            )
            if warning and warning.trend_direction in (
                TrendDirection.RISING, TrendDirection.ACCELERATING
            ):
                warnings.append(warning)

        return warnings

    def _linear_regression(
        self, values: list[tuple[float, float]]
    ) -> tuple[float, float, float]:
        """
        Simple linear regression: y = slope * x + intercept.

        Returns: (slope, intercept, r_squared)
        """
        n = len(values)
        if n < 2:
            return 0.0, 0.0, 0.0

        sum_x = sum(x for x, _ in values)
        sum_y = sum(y for _, y in values)
        sum_xy = sum(x * y for x, y in values)
        sum_x2 = sum(x * x for x, _ in values)
        sum_y2 = sum(y * y for _, y in values)

        denom = n * sum_x2 - sum_x ** 2
        if abs(denom) < 1e-12:
            return 0.0, sum_y / n, 0.0

        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n

        # R² (coefficient of determination)
        ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in values)
        mean_y = sum_y / n
        ss_tot = sum((y - mean_y) ** 2 for _, y in values)

        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 1e-12 else 0.0
        r_squared = max(0.0, min(1.0, r_squared))

        return slope, intercept, r_squared

    def _determine_trend(
        self,
        slope: float,
        r_squared: float,
        values: list[tuple[float, float]],
    ) -> TrendDirection:
        """Determine trend direction from slope and R²."""
        if r_squared < 0.3 or abs(slope) < 0.001:
            return TrendDirection.STABLE

        # Check for acceleration: second half slope vs first half slope
        if len(values) >= 6:
            mid = len(values) // 2
            first_half = values[:mid]
            second_half = values[mid:]
            s1, _, _ = self._linear_regression(first_half)
            s2, _, _ = self._linear_regression(second_half)

            if slope > 0 and s2 > s1 * 1.5:
                return TrendDirection.ACCELERATING

        if slope > 0:
            return TrendDirection.RISING
        else:
            return TrendDirection.FALLING

    def _predict_crossing(
        self,
        slope: float,
        current_value: float,
        threshold: float,
        current_time: float,
    ) -> Optional[float]:
        """
        Predict when the metric will cross the threshold.

        Returns hours until crossing, or None if not approaching.
        """
        if abs(slope) < 1e-9:
            return None

        distance = threshold - current_value
        hours_to_cross = distance / slope

        if hours_to_cross <= 0:
            # Already past threshold or moving away
            return None

        # Cap prediction at 30 days (720 hours)
        if hours_to_cross > 720:
            return None

        return hours_to_cross

    def _compute_confidence(self, r_squared: float, n_points: int) -> float:
        """Compute confidence in the trend prediction."""
        # Base confidence from R²
        base = r_squared

        # Boost for more data points (up to +0.2 for 20+ points)
        data_boost = min(0.2, (n_points - self.min_data_points) * 0.02)

        confidence = min(1.0, base + data_boost)
        return confidence

    def _determine_urgency(
        self,
        crossing_hours: Optional[float],
        distance: float,
        threshold: float,
    ) -> AlertSeverity:
        """Determine urgency level based on predicted crossing time."""
        if crossing_hours is None:
            return AlertSeverity.INFO

        if crossing_hours < 6:
            return AlertSeverity.CRITICAL
        elif crossing_hours < 24:
            return AlertSeverity.HIGH
        elif crossing_hours < 72:
            return AlertSeverity.WARNING
        else:
            return AlertSeverity.INFO

    def _generate_recommendation(
        self,
        metric: str,
        current: float,
        threshold: float,
        trend: TrendDirection,
        crossing_hours: Optional[float],
    ) -> str:
        """Generate a human-readable recommendation."""
        if trend == TrendDirection.STABLE:
            return f"{metric} is stable at {current:.2f}. No action needed."

        if trend == TrendDirection.FALLING:
            return f"{metric} is declining. Current: {current:.2f}. Monitor for stabilization."

        # Rising or accelerating
        parts = [f"{metric} is {trend.value} (current: {current:.2f}, threshold: {threshold:.2f})."]

        if crossing_hours is not None:
            if crossing_hours < 6:
                parts.append(f"URGENT: Predicted to breach threshold in {crossing_hours:.0f}h.")
                parts.append("Immediate action recommended.")
            elif crossing_hours < 24:
                parts.append(f"Expected to breach threshold in {crossing_hours:.0f}h.")
                parts.append("Plan mitigation actions today.")
            elif crossing_hours < 72:
                parts.append(f"May breach threshold in {crossing_hours:.0f}h ({crossing_hours/24:.1f} days).")
                parts.append("Schedule review and prepare contingency.")
            else:
                parts.append(f"Trending toward threshold (est. {crossing_hours/24:.0f} days).")
                parts.append("Monitor closely.")
        else:
            parts.append("Rising but not projected to cross threshold in near term.")

        return " ".join(parts)
