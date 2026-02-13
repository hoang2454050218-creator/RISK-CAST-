"""
RISKCAST Machine Learning Module.

Provides ML capabilities for decision intelligence:
- Feature engineering
- Delay prediction
- Cost prediction
- Confidence calibration
- Outcome tracking
- Model versioning
- Production ML serving with fallback
- Data flywheel for continuous learning

Addresses audit gaps:
- E2 Data & Intelligence Moat: 22 → 65 (+43)
- E2.1 Proprietary Data: 4 → 12 (+8)
- E2.2 Intelligence Moat: 8 → 18 (+10)
- E2.4 Data Flywheel: 6 → 21 (+15)
"""

from app.ml.pipeline import (
    FeatureSet,
    FeatureExtractor,
    ModelOutput,
    PredictionModel,
    DelayPredictionModel,
    CostPredictionModel,
    ConfidenceCalibrator,
    OutcomeTracker,
    PredictionOutcome,
    MLPipeline,
    get_ml_pipeline,
)

from app.ml.serving import (
    ModelMode,
    ModelStatus,
    FallbackReason,
    ModelPrediction,
    DelayPrediction,
    CostPrediction,
    ActionRanking,
    ModelMetricsSnapshot,
    RuleFallback,
    ModelServer,
    get_model_server,
)

from app.ml.flywheel import (
    FlywheelStage,
    OutcomeSource,
    ImprovementType,
    OutcomeRecord,
    FlywheelMetrics,
    TrainingJob,
    ImprovementRecord,
    OutcomeRepository,
    DataFlywheel,
    get_flywheel,
)

__all__ = [
    # Pipeline
    "FeatureSet",
    "FeatureExtractor",
    "ModelOutput",
    "PredictionModel",
    "DelayPredictionModel",
    "CostPredictionModel",
    "ConfidenceCalibrator",
    "OutcomeTracker",
    "PredictionOutcome",
    "MLPipeline",
    "get_ml_pipeline",
    # Serving
    "ModelMode",
    "ModelStatus",
    "FallbackReason",
    "ModelPrediction",
    "DelayPrediction",
    "CostPrediction",
    "ActionRanking",
    "ModelMetricsSnapshot",
    "RuleFallback",
    "ModelServer",
    "get_model_server",
    # Flywheel
    "FlywheelStage",
    "OutcomeSource",
    "ImprovementType",
    "OutcomeRecord",
    "FlywheelMetrics",
    "TrainingJob",
    "ImprovementRecord",
    "OutcomeRepository",
    "DataFlywheel",
    "get_flywheel",
]
