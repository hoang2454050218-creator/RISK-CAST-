"""
Property-Based Tests for Algorithms.

Uses Hypothesis to test invariants that must hold for ALL inputs:
- Bayesian: posterior bounds, monotonicity
- Fusion: output bounds
- Temporal: decay weight bounds
- Ensemble: aggregation bounds
- Calibration: metric bounds
"""

from datetime import datetime, timedelta, timezone

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from riskcast.engine.bayesian import BayesianRiskEngine
from riskcast.engine.calibration import CalibrationEngine
from riskcast.engine.ensemble import EnsembleEngine, ModelPrediction
from riskcast.engine.fusion import SignalFusionEngine, SignalInput
from riskcast.engine.temporal import TemporalDecayEngine


# ── Bayesian Properties ───────────────────────────────────────────────


class TestBayesianProperties:
    @given(
        successes=st.integers(min_value=0, max_value=1000),
        failures=st.integers(min_value=0, max_value=1000),
    )
    @settings(max_examples=50)
    def test_posterior_mean_bounded(self, successes, failures):
        """Posterior mean must always be in [0, 1]."""
        engine = BayesianRiskEngine()
        result = engine.beta_update(successes=successes, failures=failures)
        assert 0.0 <= result.mean <= 1.0

    @given(
        successes=st.integers(min_value=0, max_value=1000),
        failures=st.integers(min_value=0, max_value=1000),
    )
    @settings(max_examples=50)
    def test_credible_interval_ordered(self, successes, failures):
        """Lower CI bound <= mean <= upper CI bound."""
        engine = BayesianRiskEngine()
        result = engine.beta_update(successes=successes, failures=failures)
        assert result.ci_lower <= result.mean <= result.ci_upper

    @given(
        n=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=30)
    def test_more_successes_higher_mean(self, n):
        """More successes (holding failures constant) → higher mean."""
        engine = BayesianRiskEngine()
        low = engine.beta_update(successes=n, failures=n)
        high = engine.beta_update(successes=n * 2, failures=n)
        assert high.mean >= low.mean


# ── Fusion Properties ─────────────────────────────────────────────────


class TestFusionProperties:
    @given(
        severity=st.floats(min_value=0, max_value=100),
        confidence=st.floats(min_value=0.01, max_value=1.0),
    )
    @settings(max_examples=50)
    def test_fused_score_bounded(self, severity, confidence):
        """Fused score must be in [0, 100]."""
        assume(not (severity != severity))  # Skip NaN
        assume(not (confidence != confidence))
        engine = SignalFusionEngine()
        result = engine.fuse([
            SignalInput(signal_type="test", severity_score=severity, confidence=confidence),
        ])
        assert 0 <= result.fused_score <= 100

    @given(
        n=st.integers(min_value=2, max_value=10),
        sev=st.floats(min_value=10, max_value=90),
    )
    @settings(max_examples=30)
    def test_more_signals_reasonable(self, n, sev):
        """Adding more signals produces a valid fused score."""
        assume(not (sev != sev))
        engine = SignalFusionEngine()
        result = engine.fuse([
            SignalInput(signal_type=f"test_{i}", severity_score=sev, confidence=0.8)
            for i in range(n)
        ])
        assert 0 <= result.fused_score <= 100
        assert result.n_signals == n


# ── Temporal Decay Properties ─────────────────────────────────────────


class TestTemporalProperties:
    @given(
        age_hours=st.floats(min_value=0, max_value=10000),
    )
    @settings(max_examples=50)
    def test_decay_bounded(self, age_hours):
        """Decay weight must be in [0, 1]."""
        assume(not (age_hours != age_hours))
        engine = TemporalDecayEngine()
        now = datetime.now(timezone.utc)
        ts = now - timedelta(hours=age_hours)
        result = engine.compute_decay("supply_chain_disruption", 50.0, ts, now=now)
        assert 0.0 <= result.decay_weight <= 1.0

    @given(
        age1=st.floats(min_value=0, max_value=5000),
        age2=st.floats(min_value=0, max_value=5000),
    )
    @settings(max_examples=50)
    def test_decay_monotonic(self, age1, age2):
        """Older signals should have equal or lower weight."""
        assume(not (age1 != age1 or age2 != age2))
        engine = TemporalDecayEngine()
        now = datetime.now(timezone.utc)
        ts1 = now - timedelta(hours=age1)
        ts2 = now - timedelta(hours=age2)
        w1 = engine.compute_decay("test", 50.0, ts1, now=now).decay_weight
        w2 = engine.compute_decay("test", 50.0, ts2, now=now).decay_weight
        if age1 <= age2:
            assert w1 >= w2 - 1e-10  # Allow tiny float error


# ── Ensemble Properties ───────────────────────────────────────────────


class TestEnsembleProperties:
    @given(
        scores=st.lists(
            st.floats(min_value=0, max_value=100),
            min_size=1,
            max_size=10,
        ),
    )
    @settings(max_examples=50)
    def test_aggregated_bounded(self, scores):
        """Aggregated score must be within a reasonable range of individual predictions."""
        assume(all(s == s for s in scores))  # No NaN
        engine = EnsembleEngine()
        predictions = [
            ModelPrediction(model_name=f"m{i}", risk_score=s, confidence=0.8)
            for i, s in enumerate(scores)
        ]
        result = engine.aggregate(predictions)
        # Allow small rounding tolerance (ensemble rounds to 2 decimal places)
        assert min(scores) - 0.1 <= result.ensemble_score <= max(scores) + 0.1

    @given(
        score=st.floats(min_value=0, max_value=100),
    )
    @settings(max_examples=30)
    def test_single_model_no_disagreement(self, score):
        """Single model → no disagreement."""
        assume(score == score)  # No NaN
        engine = EnsembleEngine()
        result = engine.aggregate([
            ModelPrediction(model_name="solo", risk_score=score, confidence=0.9),
        ])
        assert result.needs_human_review is False


# ── Calibration Properties ────────────────────────────────────────────


class TestCalibrationProperties:
    @given(
        predicted=st.lists(
            st.floats(min_value=0, max_value=1),
            min_size=2,
            max_size=50,
        ),
        actual=st.lists(
            st.integers(min_value=0, max_value=1),
            min_size=2,
            max_size=50,
        ),
    )
    @settings(max_examples=30)
    def test_ece_bounded(self, predicted, actual):
        """ECE must be in [0, 1]."""
        assume(all(p == p for p in predicted))
        n = min(len(predicted), len(actual))
        assume(n >= 2)
        predicted = predicted[:n]
        actual = actual[:n]

        engine = CalibrationEngine()
        report = engine.assess(predicted, actual)
        assert 0.0 <= report.ece <= 1.0 + 1e-6
