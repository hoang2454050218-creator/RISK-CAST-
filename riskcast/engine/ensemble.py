"""
Ensemble Risk Aggregation Engine.

Combines multiple risk models (Bayesian, weighted fusion, etc.)
into a final score with disagreement detection.

When models disagree significantly, the system flags it as
"high uncertainty" and recommends human review.
"""

import math
import statistics
from dataclasses import dataclass, field
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────

DISAGREEMENT_THRESHOLD: float = 15.0  # Models disagree if std > this
HIGH_DISAGREEMENT_THRESHOLD: float = 25.0  # Flag for human review


@dataclass(frozen=True)
class ModelPrediction:
    """A single model's risk prediction."""
    model_name: str
    risk_score: float        # 0-100
    confidence: float        # 0-1
    weight: float = 1.0      # Model weight in ensemble


@dataclass(frozen=True)
class EnsembleResult:
    """
    Output of ensemble aggregation.

    Includes disagreement detection and human-review flag.
    """
    ensemble_score: float           # Final aggregated score (0-100)
    ensemble_confidence: float      # Aggregated confidence (0-1)
    ci_lower: float
    ci_upper: float
    n_models: int
    model_scores: dict[str, float]  # Per-model scores
    disagreement: float             # Standard deviation of model scores
    disagreement_level: str         # "low" | "moderate" | "high"
    needs_human_review: bool        # True if high disagreement
    dominant_model: str             # Model with highest confidence
    factors: list[dict] = field(default_factory=list)
    algorithm: str = "weighted_ensemble"


class EnsembleEngine:
    """
    Combine multiple risk models using weighted averaging with
    confidence-based weighting and disagreement detection.
    """

    def __init__(
        self,
        disagreement_threshold: float = DISAGREEMENT_THRESHOLD,
        high_disagreement_threshold: float = HIGH_DISAGREEMENT_THRESHOLD,
    ):
        self.disagreement_threshold = disagreement_threshold
        self.high_disagreement_threshold = high_disagreement_threshold

    def aggregate(self, predictions: list[ModelPrediction]) -> EnsembleResult:
        """
        Aggregate multiple model predictions.

        Weighting: w_i × confidence_i
        Final = Σ(w_i × c_i × score_i) / Σ(w_i × c_i)
        """
        if not predictions:
            return EnsembleResult(
                ensemble_score=0.0,
                ensemble_confidence=0.0,
                ci_lower=0.0,
                ci_upper=0.0,
                n_models=0,
                model_scores={},
                disagreement=0.0,
                disagreement_level="low",
                needs_human_review=False,
                dominant_model="none",
            )

        # Weighted average by confidence
        total_weight = sum(p.weight * p.confidence for p in predictions)
        if total_weight > 0:
            ensemble_score = sum(
                p.weight * p.confidence * p.risk_score for p in predictions
            ) / total_weight
        else:
            ensemble_score = statistics.mean(p.risk_score for p in predictions)

        # Ensemble confidence
        conf_weights = sum(p.weight for p in predictions)
        if conf_weights > 0:
            ensemble_confidence = sum(
                p.weight * p.confidence for p in predictions
            ) / conf_weights
        else:
            ensemble_confidence = 0.0

        # Model disagreement
        scores = [p.risk_score for p in predictions]
        if len(scores) > 1:
            disagreement = statistics.stdev(scores)
        else:
            disagreement = 0.0

        # Classify disagreement
        if disagreement >= self.high_disagreement_threshold:
            disagreement_level = "high"
        elif disagreement >= self.disagreement_threshold:
            disagreement_level = "moderate"
        else:
            disagreement_level = "low"

        needs_human_review = disagreement_level == "high"

        # Confidence interval from model spread
        if len(scores) > 1:
            ci_lower = max(0, ensemble_score - 2 * disagreement)
            ci_upper = min(100, ensemble_score + 2 * disagreement)
        else:
            # Single model — use its confidence for uncertainty
            unc = scores[0] * (1 - predictions[0].confidence)
            ci_lower = max(0, ensemble_score - unc)
            ci_upper = min(100, ensemble_score + unc)

        # Dominant model (highest confidence)
        dominant = max(predictions, key=lambda p: p.confidence)
        model_scores = {p.model_name: round(p.risk_score, 2) for p in predictions}

        if needs_human_review:
            logger.warning(
                "ensemble_high_disagreement",
                disagreement=round(disagreement, 2),
                model_scores=model_scores,
            )

        return EnsembleResult(
            ensemble_score=round(ensemble_score, 2),
            ensemble_confidence=round(ensemble_confidence, 4),
            ci_lower=round(ci_lower, 2),
            ci_upper=round(ci_upper, 2),
            n_models=len(predictions),
            model_scores=model_scores,
            disagreement=round(disagreement, 2),
            disagreement_level=disagreement_level,
            needs_human_review=needs_human_review,
            dominant_model=dominant.model_name,
        )
