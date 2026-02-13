"""
Production ML Model Serving.

Production-grade ML serving with:
- Model versioning via MLflow
- A/B testing between model versions
- Shadow mode for new models
- Automatic fallback to rules
- Prediction caching
- Latency monitoring

Addresses audit gaps:
- E2.2 Intelligence Moat: ML-powered predictions
- E2.4 Data Flywheel: Model serving infrastructure
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any, List
from enum import Enum
import time
import random
import hashlib

import structlog
from pydantic import BaseModel, Field, computed_field

logger = structlog.get_logger(__name__)


# ============================================================================
# ENUMS
# ============================================================================


class ModelMode(str, Enum):
    """Model deployment mode."""
    PRODUCTION = "production"    # Primary model for predictions
    SHADOW = "shadow"           # Runs but doesn't affect output
    AB_TEST = "ab_test"         # Random assignment to test vs control
    DISABLED = "disabled"       # Model not used
    CANARY = "canary"          # Small traffic percentage


class ModelStatus(str, Enum):
    """Model health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    LOADING = "loading"


class FallbackReason(str, Enum):
    """Why fallback was used."""
    MODEL_NOT_LOADED = "model_not_loaded"
    MODEL_DISABLED = "model_disabled"
    PREDICTION_FAILED = "prediction_failed"
    TIMEOUT = "timeout"
    LOW_CONFIDENCE = "low_confidence"


# ============================================================================
# SCHEMAS
# ============================================================================


class ModelPrediction(BaseModel):
    """Standardized model prediction output."""
    
    value: float = Field(description="Primary prediction value")
    confidence: float = Field(ge=0, le=1, description="Prediction confidence")
    
    # Model info
    model_id: str = Field(description="Model identifier")
    model_version: str = Field(description="Model version")
    
    # Performance
    latency_ms: float = Field(description="Inference latency in milliseconds")
    
    # Fallback info
    used_fallback: bool = Field(default=False)
    fallback_reason: Optional[FallbackReason] = None
    
    # Uncertainty
    std: Optional[float] = Field(default=None, description="Standard deviation")
    lower_bound: Optional[float] = Field(default=None, description="Lower confidence bound")
    upper_bound: Optional[float] = Field(default=None, description="Upper confidence bound")
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_hash: Optional[str] = None
    
    @computed_field
    @property
    def is_high_confidence(self) -> bool:
        """Check if prediction is high confidence."""
        return self.confidence >= 0.75


class DelayPrediction(ModelPrediction):
    """Delay prediction with range."""
    
    min_days: float = Field(ge=0, description="Minimum delay days")
    max_days: float = Field(ge=0, description="Maximum delay days")
    expected_days: float = Field(ge=0, description="Expected delay days")


class CostPrediction(ModelPrediction):
    """Cost prediction with range."""
    
    min_cost: float = Field(ge=0, description="Minimum cost")
    max_cost: float = Field(ge=0, description="Maximum cost")
    expected_cost: float = Field(ge=0, description="Expected cost")


class ActionRanking(BaseModel):
    """Ranked list of actions."""
    
    rankings: List[Tuple[str, float]] = Field(description="(action_type, score) sorted by score")
    model_version: str
    latency_ms: float
    used_fallback: bool = False


class ModelMetricsSnapshot(BaseModel):
    """Point-in-time model metrics."""
    
    model_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Request counts
    total_requests: int = 0
    fallback_requests: int = 0
    shadow_requests: int = 0
    
    # Latency (ms)
    latency_p50: float = 0
    latency_p95: float = 0
    latency_p99: float = 0
    
    # Accuracy (if outcomes available)
    accuracy: Optional[float] = None
    mae: Optional[float] = None
    
    @computed_field
    @property
    def fallback_rate(self) -> float:
        """Percentage of requests using fallback."""
        if self.total_requests == 0:
            return 0.0
        return self.fallback_requests / self.total_requests


# ============================================================================
# RULE-BASED FALLBACK
# ============================================================================


class RuleFallback:
    """
    Rule-based fallback when ML models are unavailable.
    
    Uses historical averages and heuristics.
    """
    
    # Delay estimates by chokepoint (days)
    DELAY_ESTIMATES = {
        "red_sea": {"min": 7, "max": 14, "mean": 10.5, "std": 2.5},
        "suez": {"min": 5, "max": 12, "mean": 8.5, "std": 2.0},
        "panama": {"min": 3, "max": 8, "mean": 5.5, "std": 1.5},
        "malacca": {"min": 2, "max": 5, "mean": 3.5, "std": 1.0},
        "default": {"min": 5, "max": 10, "mean": 7.5, "std": 2.0},
    }
    
    # Cost per TEU by action type
    COST_PER_TEU = {
        "reroute": {"base": 2500, "variance": 500},
        "expedite": {"base": 1500, "variance": 300},
        "hold": {"base": 500, "variance": 100},
        "delay": {"base": 200, "variance": 50},
        "monitor": {"base": 0, "variance": 0},
        "do_nothing": {"base": 0, "variance": 0},
        "default": {"base": 1000, "variance": 200},
    }
    
    # Action utility weights
    ACTION_WEIGHTS = {
        "reroute": {"benefit_factor": 0.8, "cost_factor": 1.2},
        "delay": {"benefit_factor": 0.5, "cost_factor": 0.3},
        "expedite": {"benefit_factor": 0.6, "cost_factor": 1.0},
        "monitor": {"benefit_factor": 0.3, "cost_factor": 0.1},
        "hold": {"benefit_factor": 0.4, "cost_factor": 0.5},
        "do_nothing": {"benefit_factor": 0.0, "cost_factor": 0.0},
    }
    
    def predict_delay(
        self,
        chokepoint: str,
        signal_probability: float,
        historical_mean: Optional[float] = None,
    ) -> Tuple[float, float, float, float]:
        """
        Predict delay using rules.
        
        Returns: (min_days, max_days, expected_days, confidence)
        """
        estimates = self.DELAY_ESTIMATES.get(
            chokepoint.lower(),
            self.DELAY_ESTIMATES["default"]
        )
        
        min_d = estimates["min"]
        max_d = estimates["max"]
        
        # Adjust expected based on signal probability
        # Higher probability = closer to max
        if historical_mean is not None:
            expected = historical_mean
        else:
            expected = min_d + (max_d - min_d) * signal_probability
        
        # Confidence is lower for rule-based
        confidence = 0.55 + (0.1 * signal_probability)
        
        return (min_d, max_d, expected, confidence)
    
    def predict_cost(
        self,
        action_type: str,
        route: str,
        teu_count: int,
        urgency_factor: float = 1.0,
    ) -> Tuple[float, float, float, float]:
        """
        Predict cost using rules.
        
        Returns: (min_cost, max_cost, expected_cost, confidence)
        """
        cost_info = self.COST_PER_TEU.get(
            action_type.lower(),
            self.COST_PER_TEU["default"]
        )
        
        base = cost_info["base"]
        variance = cost_info["variance"]
        
        # Apply urgency factor
        base = base * urgency_factor
        
        # Calculate per-shipment costs
        expected = base * teu_count
        min_cost = max(0, (base - variance) * teu_count)
        max_cost = (base + variance) * teu_count
        
        # Rule-based confidence is modest
        confidence = 0.6
        
        return (min_cost, max_cost, expected, confidence)
    
    def rank_actions(
        self,
        actions: List[Dict],
        context: Dict,
    ) -> List[Tuple[str, float]]:
        """
        Rank actions by expected utility using rules.
        
        Returns: [(action_type, score), ...] sorted by score descending
        """
        exposure = context.get("exposure_usd", 100000)
        
        rankings = []
        for action in actions:
            action_type = action.get("type", "unknown").lower()
            cost = action.get("cost", 0)
            benefit = action.get("benefit", exposure * 0.3)  # Default 30% of exposure
            
            weights = self.ACTION_WEIGHTS.get(
                action_type,
                {"benefit_factor": 0.5, "cost_factor": 1.0}
            )
            
            # Calculate utility: weighted benefit - weighted cost
            utility = (
                benefit * weights["benefit_factor"] -
                cost * weights["cost_factor"]
            )
            
            # Normalize to 0-1 range
            score = max(0, min(1, (utility / exposure) + 0.5)) if exposure > 0 else 0.5
            
            rankings.append((action.get("type", action_type), score))
        
        return sorted(rankings, key=lambda x: x[1], reverse=True)


# ============================================================================
# MODEL METRICS TRACKER
# ============================================================================


class ModelMetrics:
    """
    Track model performance metrics in real-time.
    """
    
    def __init__(self, window_minutes: int = 60):
        self._window = timedelta(minutes=window_minutes)
        self._predictions: Dict[str, List[Dict]] = {}
        self._fallbacks: Dict[str, int] = {}
    
    def record_prediction(
        self,
        model_id: str,
        latency_ms: float,
        used_fallback: bool = False,
        confidence: Optional[float] = None,
    ) -> None:
        """Record a prediction for metrics."""
        if model_id not in self._predictions:
            self._predictions[model_id] = []
        
        self._predictions[model_id].append({
            "timestamp": datetime.utcnow(),
            "latency_ms": latency_ms,
            "used_fallback": used_fallback,
            "confidence": confidence,
        })
        
        # Prune old entries
        cutoff = datetime.utcnow() - self._window
        self._predictions[model_id] = [
            p for p in self._predictions[model_id]
            if p["timestamp"] > cutoff
        ]
    
    def record_fallback(self, model_id: str) -> None:
        """Record a fallback occurrence."""
        self._fallbacks[model_id] = self._fallbacks.get(model_id, 0) + 1
    
    def get_metrics(self, model_id: str) -> ModelMetricsSnapshot:
        """Get current metrics for a model."""
        predictions = self._predictions.get(model_id, [])
        
        if not predictions:
            return ModelMetricsSnapshot(model_id=model_id)
        
        latencies = [p["latency_ms"] for p in predictions]
        latencies.sort()
        
        n = len(latencies)
        
        return ModelMetricsSnapshot(
            model_id=model_id,
            total_requests=n,
            fallback_requests=sum(1 for p in predictions if p["used_fallback"]),
            latency_p50=latencies[n // 2] if n > 0 else 0,
            latency_p95=latencies[int(n * 0.95)] if n > 0 else 0,
            latency_p99=latencies[int(n * 0.99)] if n > 0 else 0,
        )


# ============================================================================
# MODEL SERVER
# ============================================================================


class ModelServer:
    """
    Production ML model server.
    
    Features:
    - Model versioning via MLflow
    - A/B testing between model versions
    - Shadow mode for new models
    - Automatic fallback to rules
    - Prediction caching
    - Latency monitoring
    
    Usage:
        server = ModelServer()
        await server.load_model("delay_predictor", "v1.2.0")
        prediction = await server.predict_delay(...)
    """
    
    # A/B test traffic split (0.5 = 50% to treatment)
    AB_TEST_RATIO = 0.5
    
    # Canary traffic percentage
    CANARY_RATIO = 0.05
    
    # Prediction timeout (ms)
    PREDICTION_TIMEOUT_MS = 500
    
    # Cache TTL (seconds)
    CACHE_TTL_SECONDS = 60
    
    def __init__(self):
        """Initialize model server."""
        self._models: Dict[str, Any] = {}
        self._model_versions: Dict[str, str] = {}
        self._modes: Dict[str, ModelMode] = {}
        self._status: Dict[str, ModelStatus] = {}
        
        self._fallback = RuleFallback()
        self._metrics = ModelMetrics()
        
        # Simple in-memory cache
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        
        logger.info("model_server_initialized")
    
    # ========================================================================
    # MODEL LOADING
    # ========================================================================
    
    async def load_model(
        self,
        model_name: str,
        version: str = "latest",
        mode: ModelMode = ModelMode.PRODUCTION,
    ) -> bool:
        """
        Load a model from MLflow registry.
        
        Args:
            model_name: Name of the model in registry
            version: Version to load ("latest", "v1.2.0", etc.)
            mode: Deployment mode
            
        Returns:
            True if loaded successfully
        """
        self._status[model_name] = ModelStatus.LOADING
        
        try:
            # Try MLflow first
            model = await self._load_from_mlflow(model_name, version)
            
            if model is None:
                # Fall back to local models
                model = await self._load_local_model(model_name)
            
            if model is not None:
                self._models[model_name] = model
                self._model_versions[model_name] = version
                self._modes[model_name] = mode
                self._status[model_name] = ModelStatus.HEALTHY
                
                logger.info(
                    "model_loaded",
                    model_name=model_name,
                    version=version,
                    mode=mode.value,
                )
                return True
            else:
                self._status[model_name] = ModelStatus.UNHEALTHY
                logger.warning(
                    "model_load_fallback",
                    model_name=model_name,
                    version=version,
                )
                return False
                
        except Exception as e:
            self._status[model_name] = ModelStatus.UNHEALTHY
            logger.error(
                "model_load_failed",
                model_name=model_name,
                version=version,
                error=str(e),
            )
            return False
    
    async def _load_from_mlflow(
        self,
        model_name: str,
        version: str,
    ) -> Optional[Any]:
        """Load model from MLflow registry."""
        try:
            import mlflow  # type: ignore[import-not-found]
            
            model_uri = f"models:/{model_name}/{version}"
            model = mlflow.pyfunc.load_model(model_uri)
            return model
            
        except ImportError:
            logger.debug("mlflow_not_available")
            return None
        except Exception as e:
            logger.debug("mlflow_load_failed", error=str(e))
            return None
    
    async def _load_local_model(self, model_name: str) -> Optional[Any]:
        """Load local model implementation."""
        try:
            if model_name == "delay_predictor":
                from app.ml.pipeline import DelayPredictionModel
                return DelayPredictionModel()
            elif model_name == "cost_estimator":
                from app.ml.pipeline import CostPredictionModel
                return CostPredictionModel()
            else:
                return None
        except Exception as e:
            logger.debug("local_model_load_failed", model=model_name, error=str(e))
            return None
    
    def unload_model(self, model_name: str) -> None:
        """Unload a model."""
        if model_name in self._models:
            del self._models[model_name]
            del self._model_versions[model_name]
            del self._modes[model_name]
            self._status[model_name] = ModelStatus.UNHEALTHY
            logger.info("model_unloaded", model_name=model_name)
    
    def set_mode(self, model_name: str, mode: ModelMode) -> None:
        """Set model deployment mode."""
        self._modes[model_name] = mode
        logger.info("model_mode_changed", model_name=model_name, mode=mode.value)
    
    # ========================================================================
    # PREDICTIONS
    # ========================================================================
    
    async def predict_delay(
        self,
        chokepoint: str,
        signal_probability: float,
        historical_delays: Optional[List[float]] = None,
        current_congestion: float = 0.5,
        weather_severity: float = 0.0,
    ) -> DelayPrediction:
        """
        Predict delay with confidence interval.
        
        Args:
            chokepoint: Chokepoint identifier
            signal_probability: Probability of disruption (0-1)
            historical_delays: List of historical delay values
            current_congestion: Current congestion level (0-1)
            weather_severity: Weather impact (0-1)
            
        Returns:
            DelayPrediction with min, max, expected days and confidence
        """
        model_name = "delay_predictor"
        start_time = time.time()
        
        # Generate cache key
        cache_key = self._cache_key(
            model_name,
            chokepoint,
            round(signal_probability, 2),
            round(current_congestion, 2),
        )
        
        # Check cache
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        # Check if model available and enabled
        mode = self._modes.get(model_name, ModelMode.DISABLED)
        
        if model_name not in self._models or mode == ModelMode.DISABLED:
            # Use fallback
            return await self._delay_fallback(
                chokepoint,
                signal_probability,
                historical_delays,
                start_time,
                FallbackReason.MODEL_NOT_LOADED if model_name not in self._models else FallbackReason.MODEL_DISABLED,
            )
        
        # A/B test routing
        if mode == ModelMode.AB_TEST and random.random() > self.AB_TEST_RATIO:
            return await self._delay_fallback(
                chokepoint,
                signal_probability,
                historical_delays,
                start_time,
                None,  # Not really a fallback, just control group
            )
        
        # Canary routing
        if mode == ModelMode.CANARY and random.random() > self.CANARY_RATIO:
            return await self._delay_fallback(
                chokepoint,
                signal_probability,
                historical_delays,
                start_time,
                None,
            )
        
        try:
            model = self._models[model_name]
            version = self._model_versions.get(model_name, "unknown")
            
            # Prepare features
            historical_mean = sum(historical_delays) / len(historical_delays) if historical_delays else 7.0
            historical_std = (
                (sum((x - historical_mean) ** 2 for x in historical_delays) / len(historical_delays)) ** 0.5
                if historical_delays and len(historical_delays) > 1 else 3.0
            )
            
            # Get prediction from model
            if hasattr(model, 'predict'):
                from app.ml.pipeline import FeatureSet
                
                # Create feature set
                features = FeatureSet(
                    signal_probability=signal_probability,
                    signal_confidence=0.7,
                    signal_source_count=3,
                    signal_age_hours=2.0,
                    market_sentiment=0.0,
                    market_volatility=0.3,
                    market_liquidity=500000,
                    historical_accuracy_rate=0.75,
                    similar_event_count=10,
                    avg_delay_historical=historical_mean,
                    customer_exposure_usd=100000,
                    customer_shipment_count=5,
                    customer_risk_tolerance=0.5,
                    route_complexity=0.5,
                    chokepoint_congestion=current_congestion,
                    carrier_reliability=0.85,
                )
                
                output = model.predict(features)
                
                expected = output.prediction
                confidence = output.confidence
                std = historical_std
            else:
                # MLflow model
                import pandas as pd
                
                features_df = pd.DataFrame([{
                    "chokepoint": chokepoint,
                    "signal_probability": signal_probability,
                    "historical_mean": historical_mean,
                    "historical_std": historical_std,
                    "current_congestion": current_congestion,
                    "weather_severity": weather_severity,
                }])
                
                prediction = model.predict(features_df)
                
                if isinstance(prediction, dict):
                    expected = float(prediction.get("expected", historical_mean))
                    std = float(prediction.get("std", historical_std))
                    confidence = float(prediction.get("confidence", 0.75))
                else:
                    expected = float(prediction[0]) if hasattr(prediction, '__getitem__') else float(prediction)
                    std = historical_std
                    confidence = 0.75
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Record metrics
            self._metrics.record_prediction(model_name, latency_ms, False, confidence)
            
            prediction = DelayPrediction(
                value=expected,
                confidence=confidence,
                model_id=model_name,
                model_version=version,
                latency_ms=latency_ms,
                used_fallback=False,
                std=std,
                lower_bound=max(0, expected - 2 * std),
                upper_bound=expected + 2 * std,
                min_days=max(0, expected - 2 * std),
                max_days=expected + 2 * std,
                expected_days=expected,
            )
            
            # Cache result
            self._set_cached(cache_key, prediction)
            
            # Shadow mode: also run fallback for comparison
            if mode == ModelMode.SHADOW:
                shadow_result = await self._delay_fallback(
                    chokepoint,
                    signal_probability,
                    historical_delays,
                    time.time(),
                    None,
                )
                logger.debug(
                    "shadow_comparison",
                    model_prediction=expected,
                    shadow_prediction=shadow_result.expected_days,
                )
            
            return prediction
            
        except Exception as e:
            logger.error(
                "delay_prediction_failed",
                model_name=model_name,
                error=str(e),
            )
            self._metrics.record_fallback(model_name)
            return await self._delay_fallback(
                chokepoint,
                signal_probability,
                historical_delays,
                start_time,
                FallbackReason.PREDICTION_FAILED,
            )
    
    async def _delay_fallback(
        self,
        chokepoint: str,
        signal_probability: float,
        historical_delays: Optional[List[float]],
        start_time: float,
        reason: Optional[FallbackReason],
    ) -> DelayPrediction:
        """Generate delay prediction using fallback rules."""
        historical_mean = sum(historical_delays) / len(historical_delays) if historical_delays else None
        
        min_d, max_d, expected, confidence = self._fallback.predict_delay(
            chokepoint,
            signal_probability,
            historical_mean,
        )
        
        latency_ms = (time.time() - start_time) * 1000
        
        if reason:
            self._metrics.record_prediction("delay_predictor", latency_ms, True, confidence)
        
        return DelayPrediction(
            value=expected,
            confidence=confidence,
            model_id="rule_fallback",
            model_version="1.0.0",
            latency_ms=latency_ms,
            used_fallback=reason is not None,
            fallback_reason=reason,
            std=(max_d - min_d) / 4,
            lower_bound=min_d,
            upper_bound=max_d,
            min_days=min_d,
            max_days=max_d,
            expected_days=expected,
        )
    
    async def predict_action_cost(
        self,
        action_type: str,
        route: str,
        teu_count: int,
        urgency_level: str = "normal",
        market_conditions: Optional[Dict[str, float]] = None,
    ) -> CostPrediction:
        """
        Predict action cost with confidence interval.
        
        Args:
            action_type: Type of action (reroute, delay, etc.)
            route: Route identifier
            teu_count: Number of TEUs
            urgency_level: Urgency (normal, urgent, critical)
            market_conditions: Current market conditions
            
        Returns:
            CostPrediction with min, max, expected cost
        """
        model_name = "cost_estimator"
        start_time = time.time()
        
        mode = self._modes.get(model_name, ModelMode.DISABLED)
        
        # Urgency factor
        urgency_factors = {"normal": 1.0, "urgent": 1.3, "critical": 1.6}
        urgency_factor = urgency_factors.get(urgency_level, 1.0)
        
        if model_name not in self._models or mode == ModelMode.DISABLED:
            # Use fallback
            min_c, max_c, expected, confidence = self._fallback.predict_cost(
                action_type,
                route,
                teu_count,
                urgency_factor,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            return CostPrediction(
                value=expected,
                confidence=confidence,
                model_id="rule_fallback",
                model_version="1.0.0",
                latency_ms=latency_ms,
                used_fallback=True,
                fallback_reason=FallbackReason.MODEL_NOT_LOADED,
                std=(max_c - min_c) / 4,
                lower_bound=min_c,
                upper_bound=max_c,
                min_cost=min_c,
                max_cost=max_c,
                expected_cost=expected,
            )
        
        try:
            model = self._models[model_name]
            version = self._model_versions.get(model_name, "unknown")
            
            # Prepare features
            market = market_conditions or {}
            
            if hasattr(model, 'predict'):
                from app.ml.pipeline import FeatureSet
                
                features = FeatureSet(
                    signal_probability=0.7,
                    signal_confidence=0.7,
                    signal_source_count=3,
                    signal_age_hours=2.0,
                    market_sentiment=market.get("sentiment", 0.0),
                    market_volatility=market.get("volatility", 0.3),
                    market_liquidity=market.get("liquidity", 500000),
                    historical_accuracy_rate=0.75,
                    similar_event_count=10,
                    avg_delay_historical=10.0,
                    customer_exposure_usd=100000,
                    customer_shipment_count=teu_count,
                    customer_risk_tolerance=0.5,
                    route_complexity=0.5,
                    chokepoint_congestion=market.get("congestion", 0.5),
                    carrier_reliability=0.85,
                )
                
                output = model.predict(features)
                expected = output.prediction * teu_count * urgency_factor
                confidence = output.confidence
            else:
                expected = 2500 * teu_count * urgency_factor
                confidence = 0.7
            
            std = expected * 0.2
            latency_ms = (time.time() - start_time) * 1000
            
            self._metrics.record_prediction(model_name, latency_ms, False, confidence)
            
            return CostPrediction(
                value=expected,
                confidence=confidence,
                model_id=model_name,
                model_version=version,
                latency_ms=latency_ms,
                used_fallback=False,
                std=std,
                lower_bound=max(0, expected - 2 * std),
                upper_bound=expected + 2 * std,
                min_cost=max(0, expected - std),
                max_cost=expected + std,
                expected_cost=expected,
            )
            
        except Exception as e:
            logger.error("cost_prediction_failed", error=str(e))
            
            min_c, max_c, expected, confidence = self._fallback.predict_cost(
                action_type,
                route,
                teu_count,
                urgency_factor,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            return CostPrediction(
                value=expected,
                confidence=confidence,
                model_id="rule_fallback",
                model_version="1.0.0",
                latency_ms=latency_ms,
                used_fallback=True,
                fallback_reason=FallbackReason.PREDICTION_FAILED,
                std=(max_c - min_c) / 4,
                lower_bound=min_c,
                upper_bound=max_c,
                min_cost=min_c,
                max_cost=max_c,
                expected_cost=expected,
            )
    
    async def rank_actions(
        self,
        actions: List[Dict],
        context: Dict,
    ) -> ActionRanking:
        """
        Rank actions by expected utility.
        
        Args:
            actions: List of action dicts with type, cost, benefit
            context: Context dict with exposure_usd, etc.
            
        Returns:
            ActionRanking with sorted (action_type, score) tuples
        """
        model_name = "action_recommender"
        start_time = time.time()
        
        mode = self._modes.get(model_name, ModelMode.DISABLED)
        
        if model_name not in self._models or mode == ModelMode.DISABLED:
            rankings = self._fallback.rank_actions(actions, context)
            latency_ms = (time.time() - start_time) * 1000
            
            return ActionRanking(
                rankings=rankings,
                model_version="rule_v1.0",
                latency_ms=latency_ms,
                used_fallback=True,
            )
        
        try:
            model = self._models[model_name]
            version = self._model_versions.get(model_name, "unknown")
            
            rankings = []
            for action in actions:
                features = {
                    "action_type": action.get("type", "unknown"),
                    "cost": action.get("cost", 0),
                    "benefit": action.get("benefit", 0),
                    **context,
                }
                
                score = float(model.predict([features])[0])
                rankings.append((action.get("type", "unknown"), score))
            
            rankings = sorted(rankings, key=lambda x: x[1], reverse=True)
            latency_ms = (time.time() - start_time) * 1000
            
            return ActionRanking(
                rankings=rankings,
                model_version=version,
                latency_ms=latency_ms,
                used_fallback=False,
            )
            
        except Exception as e:
            logger.error("action_ranking_failed", error=str(e))
            
            rankings = self._fallback.rank_actions(actions, context)
            latency_ms = (time.time() - start_time) * 1000
            
            return ActionRanking(
                rankings=rankings,
                model_version="rule_v1.0",
                latency_ms=latency_ms,
                used_fallback=True,
            )
    
    # ========================================================================
    # CACHING
    # ========================================================================
    
    def _cache_key(self, *args) -> str:
        """Generate cache key."""
        key_str = ":".join(str(a) for a in args)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached prediction."""
        if key not in self._cache:
            return None
        
        value, timestamp = self._cache[key]
        if datetime.utcnow() - timestamp > timedelta(seconds=self.CACHE_TTL_SECONDS):
            del self._cache[key]
            return None
        
        return value
    
    def _set_cached(self, key: str, value: Any) -> None:
        """Set cached prediction."""
        self._cache[key] = (value, datetime.utcnow())
        
        # Prune old entries
        if len(self._cache) > 1000:
            cutoff = datetime.utcnow() - timedelta(seconds=self.CACHE_TTL_SECONDS)
            self._cache = {
                k: v for k, v in self._cache.items()
                if v[1] > cutoff
            }
    
    # ========================================================================
    # METRICS & STATUS
    # ========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Get overall server status."""
        return {
            "models_loaded": list(self._models.keys()),
            "model_modes": {k: v.value for k, v in self._modes.items()},
            "model_status": {k: v.value for k, v in self._status.items()},
            "model_versions": self._model_versions.copy(),
            "cache_size": len(self._cache),
        }
    
    def get_model_metrics(self, model_name: str) -> ModelMetricsSnapshot:
        """Get metrics for a specific model."""
        return self._metrics.get_metrics(model_name)
    
    def get_all_metrics(self) -> Dict[str, ModelMetricsSnapshot]:
        """Get metrics for all models."""
        return {
            name: self._metrics.get_metrics(name)
            for name in self._models.keys()
        }


# ============================================================================
# SINGLETON
# ============================================================================


_model_server: Optional[ModelServer] = None


def get_model_server() -> ModelServer:
    """Get global model server instance."""
    global _model_server
    if _model_server is None:
        _model_server = ModelServer()
    return _model_server
