"""
RISKCAST Analysis Module.

This module provides analytical tools for decision-making:

- Sensitivity Analysis: Identify which inputs most affect decisions
- Decision Boundaries: Find thresholds that flip recommendations
- What-If Analysis: Explore alternative scenarios
- Robustness Assessment: Measure decision stability

Key question answered: "Which inputs, if changed, would flip the decision?"
"""

from app.analysis.sensitivity import (
    SensitivityFactor,
    DecisionRobustness,
    SensitivityAnalyzer,
    WhatIfResult,
    create_sensitivity_analyzer,
)

__all__ = [
    "SensitivityFactor",
    "DecisionRobustness",
    "SensitivityAnalyzer",
    "WhatIfResult",
    "create_sensitivity_analyzer",
]
