"""
Tests for ML serving infrastructure.

Tests:
- test_ml_prediction_with_fallback(): ML prediction falls back to rules when model unavailable
- test_model_server_caching(): Predictions are cached correctly
- test_model_metrics_tracking(): Metrics are tracked properly
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.ml.serving import (
    ModelServer,
    RuleFallback,
    ModelMode,
    ModelStatus,
    FallbackReason,
    get_model_server,
    DelayPrediction,
    CostPrediction,
    ActionRanking,
)


# ============================================================================
# RULE FALLBACK TESTS
# ============================================================================


class TestRuleFallback:
    """Tests for rule-based fallback predictions."""
    
    def test_delay_prediction_high_probability(self):
        """High probability signals should predict longer delays."""
        fallback = RuleFallback()
        
        result = fallback.predict_delay(
            chokepoint="red_sea",
            signal_probability=0.9,
            historical_delays=[5, 7, 10, 12],
            current_congestion=0.8,
        )
        
        # High probability + high congestion = significant delay
        assert result["delay_days"] >= 7
        assert "historical_average" in result
        assert result["congestion_factor"] >= 1.0
    
    def test_delay_prediction_low_probability(self):
        """Low probability signals should predict minimal delays."""
        fallback = RuleFallback()
        
        result = fallback.predict_delay(
            chokepoint="red_sea",
            signal_probability=0.1,
            historical_delays=None,
            current_congestion=0.3,
        )
        
        # Low probability = minimal delay
        assert result["delay_days"] <= 5
    
    def test_delay_prediction_with_weather(self):
        """Weather severity should increase delay predictions."""
        fallback = RuleFallback()
        
        base_result = fallback.predict_delay(
            chokepoint="red_sea",
            signal_probability=0.5,
            weather_severity=0.0,
        )
        
        weather_result = fallback.predict_delay(
            chokepoint="red_sea",
            signal_probability=0.5,
            weather_severity=0.9,
        )
        
        assert weather_result["delay_days"] > base_result["delay_days"]
    
    def test_cost_prediction_basic(self):
        """Cost prediction should include base and per-teu costs."""
        fallback = RuleFallback()
        
        result = fallback.predict_cost(
            action_type="reroute",
            teu_count=5,
            delay_days=10,
            cargo_value_usd=100000,
        )
        
        assert result["total_cost_usd"] > 0
        assert result["cost_per_teu"] > 0
        assert "holding_cost" in result
    
    def test_cost_prediction_delay_action(self):
        """Delay action should calculate holding costs."""
        fallback = RuleFallback()
        
        result = fallback.predict_cost(
            action_type="delay",
            teu_count=5,
            delay_days=14,
            cargo_value_usd=200000,
        )
        
        # Holding cost = value * 0.001 * days * TEU factor
        assert result["holding_cost"] > 0
        assert result["total_cost_usd"] > 0
    
    def test_action_ranking(self):
        """Actions should be ranked by expected value."""
        fallback = RuleFallback()
        
        result = fallback.rank_actions(
            exposure_usd=100000,
            signal_probability=0.6,
            available_actions=["reroute", "delay", "monitor", "do_nothing"],
        )
        
        assert len(result["ranked_actions"]) == 4
        assert all("action" in r for r in result["ranked_actions"])
        assert all("score" in r for r in result["ranked_actions"])
        assert all("reasoning" in r for r in result["ranked_actions"])
        
        # Actions should be sorted by score descending
        scores = [r["score"] for r in result["ranked_actions"]]
        assert scores == sorted(scores, reverse=True)


# ============================================================================
# MODEL SERVER TESTS
# ============================================================================


class TestModelServer:
    """Tests for the ML model server."""
    
    @pytest.fixture
    def model_server(self):
        """Create a fresh model server instance."""
        # Reset singleton for testing
        import app.ml.serving as serving
        serving._model_server = None
        return ModelServer()
    
    @pytest.mark.asyncio
    async def test_ml_prediction_with_fallback(self, model_server):
        """
        Test that ML prediction falls back to rules when model unavailable.
        
        This is a required test from acceptance criteria.
        """
        # No models loaded - should use fallback
        prediction = await model_server.predict_delay(
            chokepoint="red_sea",
            signal_probability=0.7,
            historical_delays=[5, 10, 15],
            current_congestion=0.6,
        )
        
        # Should return valid prediction
        assert isinstance(prediction, DelayPrediction)
        assert prediction.delay_days_mean > 0
        
        # Should indicate fallback was used
        assert prediction.used_fallback is True
        assert prediction.fallback_reason in [
            FallbackReason.MODEL_NOT_LOADED,
            FallbackReason.MODEL_DISABLED,
        ]
        
        # Should have rule-based model version
        assert "rule" in prediction.model_version.lower()
    
    @pytest.mark.asyncio
    async def test_cost_prediction_with_fallback(self, model_server):
        """Cost prediction should fallback gracefully."""
        prediction = await model_server.predict_cost(
            action_type="reroute",
            teu_count=10,
            delay_days=7.0,
            cargo_value_usd=500000,
        )
        
        assert isinstance(prediction, CostPrediction)
        assert prediction.total_cost_usd > 0
        assert prediction.cost_per_teu > 0
        assert prediction.used_fallback is True
    
    @pytest.mark.asyncio
    async def test_action_ranking_with_fallback(self, model_server):
        """Action ranking should fallback gracefully."""
        ranking = await model_server.rank_actions(
            exposure_usd=200000,
            signal_probability=0.8,
            available_actions=["reroute", "delay", "monitor"],
        )
        
        assert isinstance(ranking, ActionRanking)
        assert len(ranking.ranked_actions) == 3
        assert ranking.used_fallback is True
        
        # Best action should have highest score
        assert ranking.best_action in ["reroute", "delay", "monitor"]
        assert ranking.best_score > 0
    
    @pytest.mark.asyncio
    async def test_prediction_caching(self, model_server):
        """Predictions should be cached for identical inputs."""
        # First prediction
        prediction1 = await model_server.predict_delay(
            chokepoint="red_sea",
            signal_probability=0.5,
            current_congestion=0.5,
        )
        
        # Second prediction with same inputs
        prediction2 = await model_server.predict_delay(
            chokepoint="red_sea",
            signal_probability=0.5,
            current_congestion=0.5,
        )
        
        # Should return cached result (same delay_days)
        assert prediction1.delay_days_mean == prediction2.delay_days_mean
    
    @pytest.mark.asyncio
    async def test_different_inputs_not_cached(self, model_server):
        """Different inputs should produce different predictions."""
        prediction1 = await model_server.predict_delay(
            chokepoint="red_sea",
            signal_probability=0.2,
            current_congestion=0.3,
        )
        
        prediction2 = await model_server.predict_delay(
            chokepoint="red_sea",
            signal_probability=0.9,
            current_congestion=0.9,
        )
        
        # High probability/congestion should produce longer delay
        assert prediction2.delay_days_mean > prediction1.delay_days_mean
    
    def test_model_status_without_models(self, model_server):
        """Model status should indicate no models loaded."""
        status = model_server.get_model_status()
        
        assert "delay_predictor" in status
        assert "cost_predictor" in status
        assert "action_ranker" in status
        
        for model_status in status.values():
            assert model_status.status == ModelStatus.NOT_LOADED
    
    @pytest.mark.asyncio
    async def test_model_metrics(self, model_server):
        """Model metrics should be tracked."""
        # Make some predictions
        await model_server.predict_delay(
            chokepoint="red_sea",
            signal_probability=0.5,
        )
        await model_server.predict_cost(
            action_type="reroute",
            teu_count=5,
        )
        
        metrics = model_server.get_metrics_snapshot()
        
        assert "delay_predictor" in metrics
        assert "cost_predictor" in metrics
    
    def test_set_model_mode(self, model_server):
        """Model mode can be set."""
        model_server.set_model_mode("delay_predictor", ModelMode.DISABLED)
        
        status = model_server.get_model_status()
        assert status["delay_predictor"].mode == ModelMode.DISABLED
    
    def test_clear_cache(self, model_server):
        """Cache can be cleared."""
        # This should not raise
        model_server.clear_cache()


# ============================================================================
# SINGLETON TESTS
# ============================================================================


class TestModelServerSingleton:
    """Tests for model server singleton behavior."""
    
    def test_singleton_returns_same_instance(self):
        """get_model_server should return same instance."""
        # Reset singleton
        import app.ml.serving as serving
        serving._model_server = None
        
        server1 = get_model_server()
        server2 = get_model_server()
        
        assert server1 is server2
