"""
Signal Fusion Engine Tests.
"""

import pytest
from hypothesis import given, settings as hyp_settings
from hypothesis import strategies as st

from riskcast.engine.fusion import SignalFusionEngine, SignalInput, FusedRiskScore


class TestSignalFusion:
    """Test weighted signal fusion."""

    def setup_method(self):
        self.engine = SignalFusionEngine()

    def test_empty_signals(self):
        """No signals → score is 0."""
        result = self.engine.fuse([])
        assert result.fused_score == 0.0
        assert result.n_signals == 0

    def test_single_signal(self):
        """Single signal → fused score equals signal score."""
        result = self.engine.fuse([
            SignalInput(signal_type="payment_risk", severity_score=75, confidence=0.9)
        ])
        assert abs(result.fused_score - 75.0) < 0.1
        assert result.n_signals == 1

    def test_confidence_weighting(self):
        """Low-confidence signals have less influence."""
        high_conf = self.engine.fuse([
            SignalInput(signal_type="payment_risk", severity_score=80, confidence=0.95),
            SignalInput(signal_type="route_disruption", severity_score=20, confidence=0.3),
        ])
        # Should be closer to 80 (high confidence) than to 50 (simple average)
        assert high_conf.fused_score > 50

    def test_factor_contributions_sum_to_100(self):
        """Factor contribution percentages sum to ~100%."""
        result = self.engine.fuse([
            SignalInput(signal_type="payment_risk", severity_score=60, confidence=0.8),
            SignalInput(signal_type="route_disruption", severity_score=40, confidence=0.7),
            SignalInput(signal_type="order_risk_composite", severity_score=50, confidence=0.6),
        ])
        total_pct = sum(f.pct_contribution for f in result.factors)
        assert 99 <= total_pct <= 101

    def test_dominant_factor(self):
        """Dominant factor is the one with highest contribution."""
        result = self.engine.fuse([
            SignalInput(signal_type="payment_risk", severity_score=90, confidence=0.9),
            SignalInput(signal_type="route_disruption", severity_score=10, confidence=0.5),
        ])
        assert result.dominant_factor is not None
        assert result.dominant_factor.signal_type == "payment_risk"

    def test_custom_weights(self):
        """Custom weights override defaults."""
        engine = SignalFusionEngine(weights={"a": 0.8, "b": 0.2})
        result = engine.fuse([
            SignalInput(signal_type="a", severity_score=100, confidence=1.0),
            SignalInput(signal_type="b", severity_score=0, confidence=1.0),
        ])
        # Should be heavily weighted toward signal "a"
        assert result.fused_score > 70

    def test_ci_bounds_valid(self):
        """CI lower <= fused_score <= CI upper."""
        result = self.engine.fuse([
            SignalInput(signal_type="payment_risk", severity_score=60, confidence=0.7),
        ])
        assert result.ci_lower <= result.fused_score <= result.ci_upper

    def test_update_weights_normalizes(self):
        """Updating weights normalizes them to sum to 1."""
        self.engine.update_weights({"payment_risk": 10, "route_disruption": 10})
        total = sum(self.engine.weights.values())
        assert abs(total - 1.0) < 0.01


class TestFusionPropertyBased:
    """Property-based tests for fusion."""

    @given(
        scores=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=20),
                st.floats(min_value=0, max_value=100),
                st.floats(min_value=0.01, max_value=1.0),
            ),
            min_size=1,
            max_size=10,
        )
    )
    @hyp_settings(max_examples=50)
    def test_fused_score_in_range(self, scores):
        """Fused score is always in [0, 100]."""
        engine = SignalFusionEngine()
        signals = [
            SignalInput(signal_type=s[0], severity_score=s[1], confidence=s[2])
            for s in scores
        ]
        result = engine.fuse(signals)
        assert 0 <= result.fused_score <= 100
