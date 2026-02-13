"""RISKCAST - Decision Engine (THE MOAT).

RISKCAST transforms INFORMATION into DECISIONS.

Every output MUST answer 7 questions:
- Q1: What is happening? (Personalized event summary)
- Q2: When? (Timeline + urgency)
- Q3: How bad? ($ exposure + delay days)
- Q4: Why? (Causal chain + evidence)
- Q5: What to do? (Specific action + cost + deadline)
- Q6: Confidence? (Score + factors + caveats)
- Q7: If nothing? (Inaction cost + point of no return)

The MOAT is not algorithms - it's CUSTOMER DATA.
"""

from app.riskcast.service import (
    RiskCastService,
    create_riskcast_service,
    get_riskcast_service,
)

__all__ = [
    "RiskCastService",
    "create_riskcast_service",
    "get_riskcast_service",
]
