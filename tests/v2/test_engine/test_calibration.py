"""
Calibration Engine Tests.
"""

import pytest

from riskcast.engine.calibration import (
    CalibrationEngine,
    PlattScaler,
    N_CALIBRATION_BINS,
    MIN_SAMPLES_FOR_CALIBRATION,
)


class TestCalibrationAssessment:
    """Test calibration assessment metrics."""

    def setup_method(self):
        self.engine = CalibrationEngine()

    def test_empty_predictions(self):
        """Empty predictions return default report."""
        report = self.engine.assess([], [])
        assert report.n_predictions == 0
        assert report.ece == 0.0

    def test_perfect_calibration(self):
        """Perfectly calibrated predictions have ECE ≈ 0."""
        # Group of 0.2 predictions where 20% are 1
        predicted = [0.2] * 100
        actual = [1] * 20 + [0] * 80
        report = self.engine.assess(predicted, actual)
        assert report.ece < 0.05

    def test_overconfident_detection(self):
        """Detects overconfident predictions."""
        # Predict 0.9 but only 50% are actually 1
        predicted = [0.9] * 100
        actual = [1] * 50 + [0] * 50
        report = self.engine.assess(predicted, actual)
        assert report.ece > 0.1
        assert report.overconfident

    def test_brier_score_range(self):
        """Brier score is in [0, 1]."""
        predicted = [0.7] * 50 + [0.3] * 50
        actual = [1] * 50 + [0] * 50
        report = self.engine.assess(predicted, actual)
        assert 0 <= report.brier_score <= 1

    def test_bins_count(self):
        """Report has the correct number of bins."""
        predicted = [i / 100 for i in range(100)]
        actual = [1 if i > 50 else 0 for i in range(100)]
        report = self.engine.assess(predicted, actual)
        assert len(report.bins) == N_CALIBRATION_BINS

    def test_bin_gap_non_negative(self):
        """All bin gaps are non-negative."""
        predicted = [0.5] * 100
        actual = [1] * 50 + [0] * 50
        report = self.engine.assess(predicted, actual)
        for b in report.bins:
            assert b.gap >= 0

    def test_recommendation_provided(self):
        """Every report has a recommendation."""
        predicted = [0.5] * 100
        actual = [1] * 50 + [0] * 50
        report = self.engine.assess(predicted, actual)
        assert len(report.recommendation) > 0


class TestPlattScaler:
    """Test Platt Scaling."""

    def test_unfitted_returns_raw(self):
        """Unfitted scaler returns the raw probability."""
        scaler = PlattScaler()
        assert scaler.calibrate(0.7) == 0.7

    def test_fit_updates_parameters(self):
        """Fitting updates A and B parameters."""
        scaler = PlattScaler()
        predicted = [0.1 * i for i in range(10)] * 5  # 50 samples
        actual = [1 if p > 0.5 else 0 for p in predicted]
        scaler.fit(predicted, actual)
        assert scaler.is_fitted

    def test_calibrate_returns_valid_probability(self):
        """Calibrated output is in [0, 1]."""
        scaler = PlattScaler()
        predicted = [0.1 * i for i in range(10)] * 5
        actual = [1 if p > 0.5 else 0 for p in predicted]
        scaler.fit(predicted, actual)
        for p in [0.0, 0.1, 0.5, 0.9, 1.0]:
            result = scaler.calibrate(p)
            assert 0 <= result <= 1

    def test_insufficient_data_skips_fit(self):
        """Too few samples → scaler not fitted."""
        scaler = PlattScaler()
        scaler.fit([0.5] * 5, [1] * 5)  # Only 5, need 30
        assert not scaler.is_fitted
