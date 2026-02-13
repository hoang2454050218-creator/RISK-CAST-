"""
Ensemble Aggregation Engine Tests.
"""

import pytest
from hypothesis import given, settings as hyp_settings
from hypothesis import strategies as st

from riskcast.engine.ensemble import (
    EnsembleEngine,
    ModelPrediction,
    DISAGREEMENT_THRESHOLD,
    HIGH_DISAGREEMENT_THRESHOLD,
)


class TestEnsembleAggregation:
    """Test ensemble risk aggregation."""

    def setup_method(self):
        self.engine = EnsembleEngine()

    def test_empty_predictions(self):
        """No models → zero score."""
        result = self.engine.aggregate([])
        assert result.ensemble_score == 0.0
        assert result.n_models == 0

    def test_single_model(self):
        """Single model → ensemble = model."""
        result = self.engine.aggregate([
            ModelPrediction("bayesian", 65.0, 0.8),
        ])
        assert abs(result.ensemble_score - 65.0) < 0.1
        assert result.n_models == 1

    def test_agreeing_models(self):
        """Agreeing models → low disagreement."""
        result = self.engine.aggregate([
            ModelPrediction("bayesian", 60.0, 0.8),
            ModelPrediction("fusion", 62.0, 0.9),
        ])
        assert result.disagreement < DISAGREEMENT_THRESHOLD
        assert result.disagreement_level == "low"
        assert not result.needs_human_review

    def test_disagreeing_models(self):
        """Highly disagreeing models → human review flag."""
        result = self.engine.aggregate([
            ModelPrediction("bayesian", 20.0, 0.8),
            ModelPrediction("fusion", 80.0, 0.9),
        ])
        assert result.disagreement > DISAGREEMENT_THRESHOLD
        assert result.needs_human_review

    def test_confidence_weighted(self):
        """Higher confidence model has more influence."""
        result = self.engine.aggregate([
            ModelPrediction("low_conf", 30.0, 0.3),
            ModelPrediction("high_conf", 80.0, 0.95),
        ])
        # Should be closer to 80 (high confidence model)
        assert result.ensemble_score > 55

    def test_dominant_model(self):
        """Dominant model is the one with highest confidence."""
        result = self.engine.aggregate([
            ModelPrediction("model_a", 50.0, 0.6),
            ModelPrediction("model_b", 50.0, 0.9),
        ])
        assert result.dominant_model == "model_b"

    def test_ci_bounds(self):
        """CI lower <= score <= CI upper."""
        result = self.engine.aggregate([
            ModelPrediction("a", 50.0, 0.8),
            ModelPrediction("b", 60.0, 0.7),
        ])
        assert result.ci_lower <= result.ensemble_score <= result.ci_upper


class TestEnsemblePropertyBased:
    """Property-based tests."""

    @given(
        predictions=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=10),
                st.floats(min_value=0, max_value=100),
                st.floats(min_value=0.01, max_value=1.0),
            ),
            min_size=1,
            max_size=5,
        )
    )
    @hyp_settings(max_examples=50)
    def test_ensemble_score_in_range(self, predictions):
        """Ensemble score is always in [0, 100]."""
        engine = EnsembleEngine()
        preds = [
            ModelPrediction(name, score, conf)
            for name, score, conf in predictions
        ]
        result = engine.aggregate(preds)
        assert 0 <= result.ensemble_score <= 100

    @given(
        predictions=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=10),
                st.floats(min_value=0, max_value=100),
                st.floats(min_value=0.01, max_value=1.0),
            ),
            min_size=2,
            max_size=5,
        )
    )
    @hyp_settings(max_examples=50)
    def test_disagreement_non_negative(self, predictions):
        """Disagreement is always non-negative."""
        engine = EnsembleEngine()
        preds = [
            ModelPrediction(name, score, conf)
            for name, score, conf in predictions
        ]
        result = engine.aggregate(preds)
        assert result.disagreement >= 0
