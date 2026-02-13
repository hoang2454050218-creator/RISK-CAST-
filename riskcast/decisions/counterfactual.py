"""
Counterfactual Analysis — What-if scenario engine.

Generates scenarios:
- What if risk materializes? (worst case)
- What if conditions improve? (best case)
- What if we take the recommended action?
- What if we do nothing?
"""

import structlog

from riskcast.decisions.schemas import CounterfactualScenario
from riskcast.engine.risk_engine import RiskAssessment

logger = structlog.get_logger(__name__)


class CounterfactualEngine:
    """Generate what-if scenarios for a risk assessment."""

    def generate_scenarios(
        self,
        assessment: RiskAssessment,
        exposure_usd: float = 0.0,
    ) -> list[CounterfactualScenario]:
        """Generate counterfactual scenarios."""
        scenarios: list[CounterfactualScenario] = []
        risk_prob = assessment.risk_score / 100
        severity = assessment.risk_score

        # Scenario 1: Risk materializes fully
        scenarios.append(CounterfactualScenario(
            scenario_name="Risk Materializes",
            description=(
                f"The identified risk fully materializes. "
                f"Expected impact: severity {severity:.0f}/100."
            ),
            probability=risk_prob,
            impact_if_occurs=min(100, severity * 1.2),
            expected_loss=round(exposure_usd * risk_prob, 2),
            mitigation_available=True,
        ))

        # Scenario 2: Conditions improve
        scenarios.append(CounterfactualScenario(
            scenario_name="Conditions Improve",
            description="External conditions improve, reducing the risk significantly.",
            probability=round(max(0.05, 1 - risk_prob - 0.1), 4),
            impact_if_occurs=max(0, severity * 0.3),
            expected_loss=round(exposure_usd * max(0.05, 1 - risk_prob - 0.1) * 0.1, 2),
            mitigation_available=False,
        ))

        # Scenario 3: Partial impact
        scenarios.append(CounterfactualScenario(
            scenario_name="Partial Impact",
            description="Risk partially materializes with moderate consequences.",
            probability=round(min(0.5, risk_prob * 1.5), 4),
            impact_if_occurs=severity * 0.6,
            expected_loss=round(exposure_usd * min(0.5, risk_prob * 1.5) * 0.3, 2),
            mitigation_available=True,
        ))

        # Scenario 4: Cascade failure (if high risk)
        if assessment.risk_score >= 60:
            scenarios.append(CounterfactualScenario(
                scenario_name="Cascade Failure",
                description=(
                    "Risk triggers a cascade of related failures "
                    "(e.g., port closure → supply chain disruption → customer loss)."
                ),
                probability=round(risk_prob * 0.3, 4),
                impact_if_occurs=min(100, severity * 2),
                expected_loss=round(exposure_usd * risk_prob * 0.3 * 1.5, 2),
                mitigation_available=True,
            ))

        return scenarios
