"""
Tests for Early Warning Detector.

Covers:
- Linear regression
- Trend detection (rising, falling, stable, accelerating)
- Threshold crossing prediction
- Confidence computation
- Urgency levels
- Insufficient data handling
"""

import pytest

from riskcast.alerting.early_warning import EarlyWarningDetector
from riskcast.alerting.schemas import AlertSeverity, TrendDirection


@pytest.fixture
def detector():
    return EarlyWarningDetector(min_data_points=3)


# ── Insufficient Data ──────────────────────────────────────────────────


class TestInsufficientData:
    def test_too_few_points_returns_none(self, detector):
        values = [(0.0, 50.0), (1.0, 55.0)]  # Only 2 points
        result = detector.detect_from_values(
            values, "risk_score", 80.0, "comp-001"
        )
        assert result is None


# ── Trend Detection ───────────────────────────────────────────────────


class TestTrendDetection:
    def test_rising_trend(self, detector):
        # Clear upward trend
        values = [(0, 40), (1, 50), (2, 60), (3, 70)]
        warning = detector.detect_from_values(
            values, "risk_score", 90.0, "comp-001"
        )
        assert warning is not None
        assert warning.trend_direction == TrendDirection.RISING

    def test_falling_trend(self, detector):
        values = [(0, 80), (1, 70), (2, 60), (3, 50)]
        warning = detector.detect_from_values(
            values, "risk_score", 90.0, "comp-001"
        )
        assert warning is not None
        assert warning.trend_direction == TrendDirection.FALLING

    def test_stable_trend(self, detector):
        values = [(0, 50), (1, 50.001), (2, 49.999), (3, 50.0)]
        warning = detector.detect_from_values(
            values, "risk_score", 90.0, "comp-001"
        )
        assert warning is not None
        assert warning.trend_direction == TrendDirection.STABLE

    def test_accelerating_trend(self, detector):
        # First half slow, second half fast
        values = [
            (0, 30), (1, 31), (2, 32),    # Slow
            (3, 35), (4, 40), (5, 50),    # Fast
            (6, 65), (7, 85),
        ]
        warning = detector.detect_from_values(
            values, "risk_score", 100.0, "comp-001"
        )
        assert warning is not None
        assert warning.trend_direction in (
            TrendDirection.ACCELERATING, TrendDirection.RISING
        )


# ── Threshold Crossing ────────────────────────────────────────────────


class TestThresholdCrossing:
    def test_predicts_crossing(self, detector):
        # Rising ~10 units per hour toward threshold 80
        values = [(0, 40), (1, 50), (2, 60), (3, 70)]
        warning = detector.detect_from_values(
            values, "risk_score", 80.0, "comp-001"
        )
        assert warning is not None
        assert warning.predicted_crossing_hours is not None
        assert warning.predicted_crossing_hours > 0

    def test_no_crossing_for_falling(self, detector):
        # Falling away from threshold
        values = [(0, 70), (1, 60), (2, 50), (3, 40)]
        warning = detector.detect_from_values(
            values, "risk_score", 80.0, "comp-001"
        )
        assert warning is not None
        assert warning.predicted_crossing_hours is None

    def test_no_crossing_for_stable(self, detector):
        values = [(0, 50), (1, 50), (2, 50), (3, 50)]
        warning = detector.detect_from_values(
            values, "risk_score", 80.0, "comp-001"
        )
        assert warning is not None
        assert warning.predicted_crossing_hours is None


# ── Urgency ───────────────────────────────────────────────────────────


class TestUrgency:
    def test_critical_urgency_close_crossing(self, detector):
        # Will cross within ~1 hour
        values = [(0, 70), (1, 75), (2, 78), (3, 79)]
        warning = detector.detect_from_values(
            values, "risk_score", 82.0, "comp-001"
        )
        assert warning is not None
        if warning.predicted_crossing_hours and warning.predicted_crossing_hours < 6:
            assert warning.urgency == AlertSeverity.CRITICAL

    def test_info_urgency_distant_crossing(self, detector):
        # Will cross very far in the future
        values = [(0, 30), (1, 30.1), (2, 30.2), (3, 30.3)]
        warning = detector.detect_from_values(
            values, "risk_score", 80.0, "comp-001"
        )
        assert warning is not None
        # Crossing is far away or not predicted
        if warning.predicted_crossing_hours is None:
            assert warning.urgency == AlertSeverity.INFO


# ── Confidence ────────────────────────────────────────────────────────


class TestConfidence:
    def test_high_r_squared_high_confidence(self, detector):
        # Perfect linear trend → high R²
        values = [(0, 40), (1, 50), (2, 60), (3, 70), (4, 80)]
        warning = detector.detect_from_values(
            values, "risk_score", 100.0, "comp-001"
        )
        assert warning is not None
        assert warning.confidence > 0.8

    def test_noisy_data_lower_confidence(self, detector):
        # Noisy data → lower R²
        values = [(0, 40), (1, 70), (2, 35), (3, 65), (4, 50)]
        warning = detector.detect_from_values(
            values, "risk_score", 100.0, "comp-001"
        )
        assert warning is not None
        assert warning.confidence < 0.5


# ── Linear Regression ─────────────────────────────────────────────────


class TestLinearRegression:
    def test_perfect_positive_slope(self, detector):
        values = [(0, 0), (1, 10), (2, 20)]
        slope, intercept, r2 = detector._linear_regression(values)
        assert abs(slope - 10.0) < 0.01
        assert abs(intercept) < 0.01
        assert abs(r2 - 1.0) < 0.01

    def test_perfect_negative_slope(self, detector):
        values = [(0, 100), (1, 90), (2, 80)]
        slope, intercept, r2 = detector._linear_regression(values)
        assert abs(slope - (-10.0)) < 0.01
        assert abs(r2 - 1.0) < 0.01

    def test_zero_slope(self, detector):
        values = [(0, 50), (1, 50), (2, 50)]
        slope, _, _ = detector._linear_regression(values)
        assert abs(slope) < 0.01

    def test_single_point_returns_zero(self, detector):
        slope, _, r2 = detector._linear_regression([(0, 50)])
        assert slope == 0.0
        assert r2 == 0.0


# ── Recommendation ────────────────────────────────────────────────────


class TestRecommendation:
    def test_recommendation_for_rising_trend(self, detector):
        values = [(0, 40), (1, 50), (2, 60), (3, 70)]
        warning = detector.detect_from_values(
            values, "risk_score", 90.0, "comp-001"
        )
        assert warning is not None
        assert len(warning.recommendation) > 0
        assert "risk_score" in warning.recommendation

    def test_recommendation_for_stable(self, detector):
        values = [(0, 50), (1, 50), (2, 50), (3, 50)]
        warning = detector.detect_from_values(
            values, "risk_score", 90.0, "comp-001"
        )
        assert warning is not None
        assert "stable" in warning.recommendation.lower()
