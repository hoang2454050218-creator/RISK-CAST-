"""
Escalation Rules — determines when a decision needs human review.

Rules are configurable per company. Each rule has a threshold.
When ANY rule triggers, the decision is escalated.
"""

import structlog

from riskcast.decisions.schemas import EscalationRule, SeverityLevel
from riskcast.engine.risk_engine import RiskAssessment

logger = structlog.get_logger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────

EXPOSURE_THRESHOLD_USD: float = 200_000.0
CONFIDENCE_FLOOR: float = 0.5
RISK_SCORE_CEILING: float = 80.0
DISAGREEMENT_THRESHOLD: float = 15.0


class EscalationEngine:
    """Evaluate escalation rules for a decision."""

    def __init__(
        self,
        exposure_threshold: float = EXPOSURE_THRESHOLD_USD,
        confidence_floor: float = CONFIDENCE_FLOOR,
        risk_score_ceiling: float = RISK_SCORE_CEILING,
        disagreement_threshold: float = DISAGREEMENT_THRESHOLD,
    ):
        self.exposure_threshold = exposure_threshold
        self.confidence_floor = confidence_floor
        self.risk_score_ceiling = risk_score_ceiling
        self.disagreement_threshold = disagreement_threshold

    def evaluate(
        self,
        assessment: RiskAssessment,
        exposure_usd: float = 0.0,
    ) -> tuple[bool, list[EscalationRule], str]:
        """
        Evaluate all escalation rules.

        Returns:
            (needs_escalation, triggered_rules, reason_summary)
        """
        rules: list[EscalationRule] = []

        # Rule 1: High exposure
        r1 = EscalationRule(
            rule_name="high_exposure",
            triggered=exposure_usd >= self.exposure_threshold,
            reason=f"Exposure ${exposure_usd:,.0f} exceeds threshold ${self.exposure_threshold:,.0f}",
            threshold=self.exposure_threshold,
            actual_value=exposure_usd,
        )
        rules.append(r1)

        # Rule 2: Low confidence
        r2 = EscalationRule(
            rule_name="low_confidence",
            triggered=assessment.confidence < self.confidence_floor,
            reason=f"Confidence {assessment.confidence:.2f} is below floor {self.confidence_floor:.2f}",
            threshold=self.confidence_floor,
            actual_value=assessment.confidence,
        )
        rules.append(r2)

        # Rule 3: Critical risk score
        r3 = EscalationRule(
            rule_name="critical_risk_score",
            triggered=assessment.risk_score >= self.risk_score_ceiling,
            reason=f"Risk score {assessment.risk_score:.0f} exceeds ceiling {self.risk_score_ceiling:.0f}",
            threshold=self.risk_score_ceiling,
            actual_value=assessment.risk_score,
        )
        rules.append(r3)

        # Rule 4: Model disagreement
        disagreement = assessment.algorithm_trace.get("ensemble_disagreement", 0.0)
        r4 = EscalationRule(
            rule_name="model_disagreement",
            triggered=disagreement >= self.disagreement_threshold,
            reason=f"Model disagreement {disagreement:.1f} exceeds threshold {self.disagreement_threshold:.1f}",
            threshold=self.disagreement_threshold,
            actual_value=disagreement,
        )
        rules.append(r4)

        # Rule 5: Insufficient data
        r5 = EscalationRule(
            rule_name="insufficient_data",
            triggered=not assessment.is_reliable,
            reason="Assessment is based on insufficient data",
            threshold=None,
            actual_value=float(assessment.n_signals),
        )
        rules.append(r5)

        triggered = [r for r in rules if r.triggered]
        needs_escalation = len(triggered) > 0

        if triggered:
            reasons = "; ".join(r.rule_name for r in triggered)
            reason_summary = f"Escalated: {reasons}"
        else:
            reason_summary = "No escalation rules triggered"

        if needs_escalation:
            logger.info(
                "decision_escalated",
                entity=f"{assessment.entity_type}/{assessment.entity_id}",
                rules=[r.rule_name for r in triggered],
            )

        return needs_escalation, rules, reason_summary
