"""
RISKCAST Uncertainty Quantification Module.

This module implements proper probabilistic uncertainty propagation
for all numeric outputs in RISKCAST.

Key features:
- Distribution modeling (normal, beta, lognormal, empirical)
- Multiple confidence interval calculation (80%, 90%, 95%, 99%)
- Value at Risk (VaR) and Conditional VaR (CVaR/Expected Shortfall)
- Monte Carlo uncertainty propagation
- Bayesian calculations for combining uncertain inputs
- Confidence communication (translating uncertainty to actionable guidance)

Every numeric output has:
- Point estimate (best guess)
- Multiple confidence intervals (80%, 90%, 95%, 99%)
- VaR and CVaR for risk metrics
- Full distribution (for downstream calculations)

Addresses audit gaps:
- A2.2: Confidence Intervals - comprehensive CI coverage
- A4.4: Confidence Communication - actionable uncertainty guidance
"""

from app.uncertainty.bayesian import (
    Distribution,
    DistributionType,
    UncertainValue,
    BayesianCalculator,
    create_bayesian_calculator,
)

from app.uncertainty.communication import (
    UncertaintyLevel,
    ActConfidence,
    UncertaintyReducer,
    RiskAdjustedRecommendations,
    ConfidenceGuidance,
    ConfidenceCommunicator,
)

__all__ = [
    # Bayesian module
    "Distribution",
    "DistributionType",
    "UncertainValue",
    "BayesianCalculator",
    "create_bayesian_calculator",
    # Communication module (A4.4)
    "UncertaintyLevel",
    "ActConfidence",
    "UncertaintyReducer",
    "RiskAdjustedRecommendations",
    "ConfidenceGuidance",
    "ConfidenceCommunicator",
]
