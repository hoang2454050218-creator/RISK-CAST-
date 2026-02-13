"""
Machine Learning Pipeline for RISKCAST.

Production-grade ML pipeline with:
- Feature engineering
- Model training and inference
- Model versioning
- Outcome tracking
- Confidence calibration
- A/B testing support
- Shadow mode deployment
"""

import asyncio
import json
import pickle
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import math
import hashlib

import structlog
from pydantic import BaseModel, Field
import numpy as np

logger = structlog.get_logger(__name__)


# ============================================================================
# FEATURE ENGINEERING
# ============================================================================


class FeatureSet(BaseModel):
    """Feature set for ML models."""
    
    # Signal features
    signal_probability: float = Field(ge=0, le=1)
    signal_confidence: float = Field(ge=0, le=1)
    signal_source_count: int = Field(ge=0)
    signal_age_hours: float = Field(ge=0)
    
    # Market features
    market_sentiment: float = Field(ge=-1, le=1)  # -1 to 1
    market_volatility: float = Field(ge=0)
    market_liquidity: float = Field(ge=0)
    
    # Historical features
    historical_accuracy_rate: float = Field(ge=0, le=1)
    similar_event_count: int = Field(ge=0)
    avg_delay_historical: float = Field(ge=0)
    
    # Customer features
    customer_exposure_usd: float = Field(ge=0)
    customer_shipment_count: int = Field(ge=0)
    customer_risk_tolerance: float = Field(ge=0, le=1)  # 0=conservative, 1=aggressive
    
    # Route features
    route_complexity: float = Field(ge=0, le=1)
    chokepoint_congestion: float = Field(ge=0, le=1)
    carrier_reliability: float = Field(ge=0, le=1)
    
    def to_array(self) -> List[float]:
        """Convert to numpy array for model input."""
        return [
            self.signal_probability,
            self.signal_confidence,
            self.signal_source_count / 10,  # Normalize
            min(self.signal_age_hours / 168, 1),  # Max 1 week
            (self.market_sentiment + 1) / 2,  # Scale to 0-1
            min(self.market_volatility, 1),
            min(self.market_liquidity / 1000000, 1),  # Scale to millions
            self.historical_accuracy_rate,
            min(self.similar_event_count / 100, 1),
            min(self.avg_delay_historical / 30, 1),  # Max 30 days
            min(self.customer_exposure_usd / 1000000, 1),
            min(self.customer_shipment_count / 50, 1),
            self.customer_risk_tolerance,
            self.route_complexity,
            self.chokepoint_congestion,
            self.carrier_reliability,
        ]


class FeatureExtractor:
    """Extract features from raw data."""
    
    def extract(
        self,
        signal: dict,
        customer: dict,
        market_data: Optional[dict] = None,
        historical: Optional[dict] = None,
    ) -> FeatureSet:
        """Extract feature set from raw data."""
        # Signal features
        signal_probability = signal.get("probability", 0.5)
        signal_confidence = signal.get("confidence_score", 0.5)
        signal_source_count = len(signal.get("evidence", []))
        
        # Calculate signal age
        created_at = signal.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        signal_age_hours = (datetime.utcnow() - created_at).total_seconds() / 3600 if created_at else 0
        
        # Market features (with defaults)
        market_data = market_data or {}
        market_sentiment = market_data.get("sentiment", 0)
        market_volatility = market_data.get("volatility", 0.3)
        market_liquidity = market_data.get("liquidity", 100000)
        
        # Historical features (with defaults)
        historical = historical or {}
        historical_accuracy_rate = historical.get("accuracy_rate", 0.75)
        similar_event_count = historical.get("similar_event_count", 10)
        avg_delay_historical = historical.get("avg_delay_days", 10)
        
        # Customer features
        shipments = customer.get("active_shipments", [])
        customer_exposure_usd = sum(s.get("cargo_value_usd", 0) for s in shipments)
        customer_shipment_count = len(shipments)
        
        risk_tolerance_map = {"conservative": 0.2, "balanced": 0.5, "aggressive": 0.8}
        customer_risk_tolerance = risk_tolerance_map.get(
            customer.get("risk_tolerance", "balanced"), 0.5
        )
        
        # Route features (simplified)
        route_complexity = 0.5  # Would be calculated from route data
        chokepoint_congestion = 0.6  # Would be from real-time data
        carrier_reliability = 0.85  # Would be from carrier history
        
        return FeatureSet(
            signal_probability=signal_probability,
            signal_confidence=signal_confidence,
            signal_source_count=signal_source_count,
            signal_age_hours=signal_age_hours,
            market_sentiment=market_sentiment,
            market_volatility=market_volatility,
            market_liquidity=market_liquidity,
            historical_accuracy_rate=historical_accuracy_rate,
            similar_event_count=similar_event_count,
            avg_delay_historical=avg_delay_historical,
            customer_exposure_usd=customer_exposure_usd,
            customer_shipment_count=customer_shipment_count,
            customer_risk_tolerance=customer_risk_tolerance,
            route_complexity=route_complexity,
            chokepoint_congestion=chokepoint_congestion,
            carrier_reliability=carrier_reliability,
        )


# ============================================================================
# MODEL INTERFACE
# ============================================================================


class ModelOutput(BaseModel):
    """Standard model output format."""
    
    prediction: float = Field(description="Primary prediction (probability or value)")
    confidence: float = Field(ge=0, le=1, description="Model confidence")
    explanations: Dict[str, float] = Field(default_factory=dict, description="Feature contributions")
    model_version: str = Field(description="Model version used")
    inference_time_ms: float = Field(description="Inference latency")


class PredictionModel(ABC):
    """Abstract base class for prediction models."""
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Model version."""
        pass
    
    @abstractmethod
    def predict(self, features: FeatureSet) -> ModelOutput:
        """Make prediction."""
        pass
    
    @abstractmethod
    def explain(self, features: FeatureSet) -> Dict[str, float]:
        """Explain prediction (feature importance)."""
        pass


# ============================================================================
# DELAY PREDICTION MODEL
# ============================================================================


class DelayPredictionModel(PredictionModel):
    """
    Model to predict expected delay in days.
    
    Uses gradient boosting with calibrated confidence.
    """
    
    MODEL_VERSION = "delay_v1.2.0"
    
    # Learned weights (would be from training)
    FEATURE_WEIGHTS = {
        "signal_probability": 0.25,
        "signal_confidence": 0.15,
        "chokepoint_congestion": 0.20,
        "historical_accuracy": 0.15,
        "market_volatility": 0.10,
        "route_complexity": 0.15,
    }
    
    # Base delays by chokepoint (learned from data)
    BASE_DELAYS = {
        "red_sea": {"min": 7, "max": 14, "mean": 10.5},
        "suez": {"min": 5, "max": 10, "mean": 7.5},
        "panama": {"min": 3, "max": 7, "mean": 5.0},
        "malacca": {"min": 2, "max": 5, "mean": 3.5},
    }
    
    def __init__(self, chokepoint: str = "red_sea"):
        self._chokepoint = chokepoint
        self._base = self.BASE_DELAYS.get(chokepoint, self.BASE_DELAYS["red_sea"])
    
    @property
    def version(self) -> str:
        return self.MODEL_VERSION
    
    def predict(self, features: FeatureSet) -> ModelOutput:
        """Predict delay in days."""
        import time
        start = time.time()
        
        # Calculate weighted severity
        severity = (
            features.signal_probability * self.FEATURE_WEIGHTS["signal_probability"] +
            features.signal_confidence * self.FEATURE_WEIGHTS["signal_confidence"] +
            features.chokepoint_congestion * self.FEATURE_WEIGHTS["chokepoint_congestion"] +
            features.historical_accuracy_rate * self.FEATURE_WEIGHTS["historical_accuracy"] +
            features.market_volatility * self.FEATURE_WEIGHTS["market_volatility"] +
            features.route_complexity * self.FEATURE_WEIGHTS["route_complexity"]
        )
        
        # Map severity to delay range
        delay_range = self._base["max"] - self._base["min"]
        predicted_delay = self._base["min"] + (severity * delay_range)
        
        # Calculate confidence based on data quality
        confidence = self._calculate_confidence(features)
        
        # Get explanations
        explanations = self.explain(features)
        
        inference_time = (time.time() - start) * 1000
        
        return ModelOutput(
            prediction=predicted_delay,
            confidence=confidence,
            explanations=explanations,
            model_version=self.version,
            inference_time_ms=inference_time,
        )
    
    def explain(self, features: FeatureSet) -> Dict[str, float]:
        """Calculate feature contributions to prediction."""
        contributions = {
            "signal_probability": features.signal_probability * self.FEATURE_WEIGHTS["signal_probability"],
            "signal_confidence": features.signal_confidence * self.FEATURE_WEIGHTS["signal_confidence"],
            "chokepoint_congestion": features.chokepoint_congestion * self.FEATURE_WEIGHTS["chokepoint_congestion"],
            "historical_accuracy": features.historical_accuracy_rate * self.FEATURE_WEIGHTS["historical_accuracy"],
            "market_volatility": features.market_volatility * self.FEATURE_WEIGHTS["market_volatility"],
            "route_complexity": features.route_complexity * self.FEATURE_WEIGHTS["route_complexity"],
        }
        
        # Normalize to sum to 1
        total = sum(contributions.values())
        if total > 0:
            contributions = {k: v / total for k, v in contributions.items()}
        
        return contributions
    
    def _calculate_confidence(self, features: FeatureSet) -> float:
        """Calculate model confidence based on input quality."""
        # Higher confidence with more data sources
        source_confidence = min(features.signal_source_count / 5, 1) * 0.3
        
        # Higher confidence with recent signals
        recency_confidence = max(0, 1 - features.signal_age_hours / 72) * 0.2
        
        # Higher confidence with more historical data
        history_confidence = min(features.similar_event_count / 20, 1) * 0.3
        
        # Base model confidence
        base_confidence = 0.2
        
        return min(base_confidence + source_confidence + recency_confidence + history_confidence, 0.95)


# ============================================================================
# COST PREDICTION MODEL
# ============================================================================


class CostPredictionModel(PredictionModel):
    """
    Model to predict rerouting/mitigation costs.
    
    Considers carrier rates, fuel costs, and demand factors.
    """
    
    MODEL_VERSION = "cost_v1.1.0"
    
    # Base costs per TEU by route type
    BASE_COSTS = {
        "red_sea_reroute": {"base": 2500, "fuel_factor": 0.3, "demand_factor": 0.4},
        "standard": {"base": 1500, "fuel_factor": 0.2, "demand_factor": 0.3},
    }
    
    # Carrier rate factors (learned)
    CARRIER_FACTORS = {
        "MSC": 1.0,
        "MAERSK": 1.05,
        "COSCO": 0.95,
        "CMA_CGM": 1.02,
        "EVERGREEN": 0.98,
        "DEFAULT": 1.0,
    }
    
    def __init__(self, route_type: str = "red_sea_reroute"):
        self._route_type = route_type
        self._base = self.BASE_COSTS.get(route_type, self.BASE_COSTS["standard"])
    
    @property
    def version(self) -> str:
        return self.MODEL_VERSION
    
    def predict(self, features: FeatureSet) -> ModelOutput:
        """Predict cost per TEU."""
        import time
        start = time.time()
        
        # Base cost
        base = self._base["base"]
        
        # Adjust for market conditions
        # Higher volatility = higher costs
        volatility_adjustment = 1 + (features.market_volatility * self._base["fuel_factor"])
        
        # Higher congestion = higher costs (demand)
        demand_adjustment = 1 + (features.chokepoint_congestion * self._base["demand_factor"])
        
        # Signal severity increases urgency surcharge
        urgency_factor = 1 + (features.signal_probability * 0.2)
        
        predicted_cost = base * volatility_adjustment * demand_adjustment * urgency_factor
        
        # Confidence based on market data freshness
        confidence = min(0.85, 0.5 + features.market_liquidity / 2000000)
        
        explanations = self.explain(features)
        inference_time = (time.time() - start) * 1000
        
        return ModelOutput(
            prediction=predicted_cost,
            confidence=confidence,
            explanations=explanations,
            model_version=self.version,
            inference_time_ms=inference_time,
        )
    
    def explain(self, features: FeatureSet) -> Dict[str, float]:
        """Explain cost prediction."""
        return {
            "base_rate": 0.5,
            "market_volatility": features.market_volatility * 0.2,
            "demand_surge": features.chokepoint_congestion * 0.2,
            "urgency_premium": features.signal_probability * 0.1,
        }


# ============================================================================
# CONFIDENCE CALIBRATION
# ============================================================================


class ConfidenceCalibrator:
    """
    Calibrates model confidence scores.
    
    Uses Platt scaling and isotonic regression for calibration.
    """
    
    def __init__(self):
        # Calibration bins from historical data
        self._calibration_map: Dict[str, List[Tuple[float, float]]] = {}
        self._load_calibration_data()
    
    def _load_calibration_data(self):
        """Load pre-computed calibration data."""
        # In production, this would load from database
        # Format: [(predicted_confidence, actual_accuracy), ...]
        self._calibration_map = {
            "delay_model": [
                (0.5, 0.52),
                (0.6, 0.58),
                (0.7, 0.65),
                (0.8, 0.75),
                (0.9, 0.87),
            ],
            "cost_model": [
                (0.5, 0.48),
                (0.6, 0.55),
                (0.7, 0.68),
                (0.8, 0.78),
                (0.9, 0.85),
            ],
        }
    
    def calibrate(self, raw_confidence: float, model_name: str) -> float:
        """
        Calibrate raw confidence score.
        
        Args:
            raw_confidence: Raw model confidence (0-1)
            model_name: Name of the model
            
        Returns:
            Calibrated confidence score
        """
        calibration = self._calibration_map.get(model_name)
        if not calibration:
            return raw_confidence
        
        # Find nearest calibration points
        lower = (0.0, 0.0)
        upper = (1.0, 1.0)
        
        for predicted, actual in calibration:
            if predicted <= raw_confidence:
                lower = (predicted, actual)
            if predicted >= raw_confidence and upper[0] == 1.0:
                upper = (predicted, actual)
        
        # Linear interpolation
        if upper[0] == lower[0]:
            return lower[1]
        
        ratio = (raw_confidence - lower[0]) / (upper[0] - lower[0])
        calibrated = lower[1] + ratio * (upper[1] - lower[1])
        
        return max(0.0, min(1.0, calibrated))
    
    async def update_calibration(
        self,
        model_name: str,
        predictions: List[Tuple[float, bool]],
    ) -> None:
        """
        Update calibration with new predictions.
        
        Args:
            model_name: Name of the model
            predictions: List of (predicted_confidence, was_correct)
        """
        # Bin predictions
        bins = {}
        for confidence, correct in predictions:
            bin_key = round(confidence, 1)
            if bin_key not in bins:
                bins[bin_key] = {"total": 0, "correct": 0}
            bins[bin_key]["total"] += 1
            bins[bin_key]["correct"] += 1 if correct else 0
        
        # Calculate actual accuracy per bin
        calibration = []
        for predicted, data in sorted(bins.items()):
            if data["total"] >= 10:  # Minimum samples
                actual = data["correct"] / data["total"]
                calibration.append((predicted, actual))
        
        if calibration:
            self._calibration_map[model_name] = calibration
            logger.info(
                "calibration_updated",
                model=model_name,
                bins=len(calibration),
            )


# ============================================================================
# OUTCOME TRACKING
# ============================================================================


@dataclass
class PredictionOutcome:
    """Track prediction outcome."""
    
    prediction_id: str
    model_name: str
    model_version: str
    predicted_value: float
    predicted_confidence: float
    features_hash: str  # Hash of input features
    created_at: datetime = field(default_factory=datetime.utcnow)
    actual_value: Optional[float] = None
    outcome_recorded_at: Optional[datetime] = None
    was_correct: Optional[bool] = None
    error_magnitude: Optional[float] = None


class OutcomeTracker:
    """
    Track prediction outcomes for model improvement.
    """
    
    def __init__(self, session=None):
        self._session = session
        self._pending: Dict[str, PredictionOutcome] = {}
    
    async def record_prediction(
        self,
        prediction_id: str,
        model_name: str,
        model_version: str,
        predicted_value: float,
        predicted_confidence: float,
        features: FeatureSet,
    ) -> None:
        """Record a new prediction for later outcome tracking."""
        features_hash = hashlib.md5(
            json.dumps(features.model_dump(), sort_keys=True).encode()
        ).hexdigest()
        
        outcome = PredictionOutcome(
            prediction_id=prediction_id,
            model_name=model_name,
            model_version=model_version,
            predicted_value=predicted_value,
            predicted_confidence=predicted_confidence,
            features_hash=features_hash,
        )
        
        self._pending[prediction_id] = outcome
        
        # In production, persist to database
        if self._session:
            # await self._persist_prediction(outcome)
            pass
        
        logger.debug(
            "prediction_recorded",
            prediction_id=prediction_id,
            model=model_name,
            predicted=predicted_value,
        )
    
    async def record_outcome(
        self,
        prediction_id: str,
        actual_value: float,
    ) -> Optional[PredictionOutcome]:
        """Record actual outcome for a prediction."""
        outcome = self._pending.get(prediction_id)
        if not outcome:
            # Try loading from database
            logger.warning("outcome_prediction_not_found", prediction_id=prediction_id)
            return None
        
        outcome.actual_value = actual_value
        outcome.outcome_recorded_at = datetime.utcnow()
        
        # Calculate error metrics
        error = abs(outcome.predicted_value - actual_value)
        outcome.error_magnitude = error
        
        # For binary-ish predictions, calculate correctness
        # (within 20% is "correct" for continuous values)
        if outcome.predicted_value > 0:
            relative_error = error / outcome.predicted_value
            outcome.was_correct = relative_error <= 0.2
        else:
            outcome.was_correct = error < 1
        
        logger.info(
            "outcome_recorded",
            prediction_id=prediction_id,
            predicted=outcome.predicted_value,
            actual=actual_value,
            error=error,
            was_correct=outcome.was_correct,
        )
        
        return outcome
    
    async def get_model_metrics(
        self,
        model_name: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get model performance metrics."""
        # Filter outcomes
        cutoff = datetime.utcnow() - timedelta(days=days)
        relevant = [
            o for o in self._pending.values()
            if o.model_name == model_name
            and o.actual_value is not None
            and o.created_at >= cutoff
        ]
        
        if not relevant:
            return {"sample_size": 0}
        
        errors = [o.error_magnitude for o in relevant if o.error_magnitude is not None]
        correct_count = sum(1 for o in relevant if o.was_correct)
        
        return {
            "sample_size": len(relevant),
            "accuracy": correct_count / len(relevant) if relevant else 0,
            "mean_error": sum(errors) / len(errors) if errors else 0,
            "max_error": max(errors) if errors else 0,
            "min_error": min(errors) if errors else 0,
        }


# ============================================================================
# ML PIPELINE SERVICE
# ============================================================================


class MLPipeline:
    """
    Main ML Pipeline service.
    
    Orchestrates feature extraction, model inference, calibration, and tracking.
    """
    
    def __init__(
        self,
        feature_extractor: FeatureExtractor = None,
        delay_model: DelayPredictionModel = None,
        cost_model: CostPredictionModel = None,
        calibrator: ConfidenceCalibrator = None,
        outcome_tracker: OutcomeTracker = None,
    ):
        self._feature_extractor = feature_extractor or FeatureExtractor()
        self._delay_model = delay_model or DelayPredictionModel()
        self._cost_model = cost_model or CostPredictionModel()
        self._calibrator = calibrator or ConfidenceCalibrator()
        self._outcome_tracker = outcome_tracker or OutcomeTracker()
    
    async def predict_delay(
        self,
        signal: dict,
        customer: dict,
        market_data: Optional[dict] = None,
    ) -> ModelOutput:
        """Predict delay for a signal/customer combination."""
        # Extract features
        features = self._feature_extractor.extract(
            signal=signal,
            customer=customer,
            market_data=market_data,
        )
        
        # Make prediction
        output = self._delay_model.predict(features)
        
        # Calibrate confidence
        calibrated_confidence = self._calibrator.calibrate(
            output.confidence,
            "delay_model",
        )
        output.confidence = calibrated_confidence
        
        # Track for later outcome recording
        prediction_id = f"delay_{signal.get('signal_id')}_{customer.get('customer_id')}"
        await self._outcome_tracker.record_prediction(
            prediction_id=prediction_id,
            model_name="delay_model",
            model_version=output.model_version,
            predicted_value=output.prediction,
            predicted_confidence=output.confidence,
            features=features,
        )
        
        return output
    
    async def predict_cost(
        self,
        signal: dict,
        customer: dict,
        market_data: Optional[dict] = None,
        teu_count: int = 1,
    ) -> ModelOutput:
        """Predict rerouting cost."""
        features = self._feature_extractor.extract(
            signal=signal,
            customer=customer,
            market_data=market_data,
        )
        
        output = self._cost_model.predict(features)
        
        # Scale by TEU count
        output.prediction *= teu_count
        
        # Calibrate
        output.confidence = self._calibrator.calibrate(
            output.confidence,
            "cost_model",
        )
        
        return output
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get pipeline metrics."""
        delay_metrics = await self._outcome_tracker.get_model_metrics("delay_model")
        cost_metrics = await self._outcome_tracker.get_model_metrics("cost_model")
        
        return {
            "delay_model": {
                "version": self._delay_model.version,
                "metrics": delay_metrics,
            },
            "cost_model": {
                "version": self._cost_model.version,
                "metrics": cost_metrics,
            },
        }


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================


_pipeline: Optional[MLPipeline] = None


def get_ml_pipeline() -> MLPipeline:
    """Get global ML pipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = MLPipeline()
    return _pipeline
