"""
Signal Correlation Engine Tests.
"""

import pytest

from riskcast.engine.correlation import (
    CorrelationEngine,
    SignalObservation,
    CORRELATION_THRESHOLD,
)


class TestCorrelationDetection:
    """Test correlation analysis."""

    def setup_method(self):
        self.engine = CorrelationEngine()

    def test_empty_signals(self):
        """No signals → no correlations."""
        report = self.engine.analyze_correlations([])
        assert report.n_correlated_pairs == 0
        assert report.effective_signals == 0

    def test_single_signal(self):
        """Single signal → no correlations."""
        report = self.engine.analyze_correlations([
            SignalObservation("payment_risk", "order-1", 50.0, "2024-01-01"),
        ])
        assert report.n_correlated_pairs == 0

    def test_uncorrelated_signals(self):
        """Signals on different entities are uncorrelated."""
        signals = [
            SignalObservation("payment_risk", "order-1", 50.0, "2024-01-01"),
            SignalObservation("route_disruption", "order-2", 60.0, "2024-01-01"),
        ]
        report = self.engine.analyze_correlations(signals)
        assert report.n_correlated_pairs == 0

    def test_correlated_signals_detected(self):
        """Signals frequently co-occurring on same entity are correlated."""
        signals = []
        for i in range(10):
            entity = f"order-{i}"
            signals.append(SignalObservation("payment_risk", entity, 50.0, "2024-01-01"))
            signals.append(SignalObservation("order_risk", entity, 60.0, "2024-01-01"))
        report = self.engine.analyze_correlations(signals)
        assert report.n_correlated_pairs >= 1

    def test_correlation_threshold(self):
        """Only pairs above threshold are reported."""
        engine = CorrelationEngine(threshold=0.8)
        signals = []
        # 50% overlap — below 0.8 threshold
        for i in range(10):
            signals.append(SignalObservation("a", f"e-{i}", 50, "2024-01-01"))
        for i in range(5):  # Only 5 of 10 overlap
            signals.append(SignalObservation("b", f"e-{i}", 50, "2024-01-01"))
        for i in range(10, 15):  # 5 unique to b
            signals.append(SignalObservation("b", f"e-{i}", 50, "2024-01-01"))

        report = engine.analyze_correlations(signals)
        # Jaccard = 5/15 ≈ 0.33 — below 0.8
        assert report.n_correlated_pairs == 0


class TestCorrelationDiscount:
    """Test discount application."""

    def setup_method(self):
        self.engine = CorrelationEngine()

    def test_no_discount_without_correlations(self):
        """Without correlations, scores are unchanged."""
        report = self.engine.analyze_correlations([])
        scores = {"payment_risk": 50.0, "route_disruption": 40.0}
        adjusted = self.engine.apply_discount(scores, report)
        assert adjusted == scores

    def test_discount_reduces_weaker_signal(self):
        """Correlated pair → weaker signal is discounted."""
        signals = []
        for i in range(10):
            signals.append(SignalObservation("a", f"e-{i}", 80, "2024-01-01"))
            signals.append(SignalObservation("b", f"e-{i}", 30, "2024-01-01"))
        report = self.engine.analyze_correlations(signals)

        scores = {"a": 80.0, "b": 30.0}
        adjusted = self.engine.apply_discount(scores, report)

        # "a" is stronger → "b" should be discounted
        assert adjusted["a"] == 80.0
        if report.n_correlated_pairs > 0:
            assert adjusted["b"] < 30.0
