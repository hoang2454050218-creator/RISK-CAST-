"""RISKCAST Schemas - Data models for decision engine."""

from app.riskcast.schemas.customer import (
    CustomerContext,
    CustomerProfile,
    RiskTolerance,
    Shipment,
    ShipmentStatus,
)
from app.riskcast.schemas.impact import (
    CostBreakdown,
    DelayEstimate,
    ShipmentImpact,
    TotalImpact,
)
from app.riskcast.schemas.action import (
    Action,
    ActionFeasibility,
    ActionSet,
    ActionType,
    InactionConsequence,
    TimePoint,
    TradeOffAnalysis,
)
from app.riskcast.schemas.decision import (
    DecisionObject,
    Q1WhatIsHappening,
    Q2WhenWillItHappen,
    Q3HowBadIsIt,
    Q4WhyIsThisHappening,
    Q5WhatToDoNow,
    Q6HowConfident,
    Q7WhatIfNothing,
)

__all__ = [
    # Customer schemas
    "CustomerContext",
    "CustomerProfile",
    "RiskTolerance",
    "Shipment",
    "ShipmentStatus",
    # Impact schemas
    "CostBreakdown",
    "DelayEstimate",
    "ShipmentImpact",
    "TotalImpact",
    # Action schemas
    "Action",
    "ActionFeasibility",
    "ActionSet",
    "ActionType",
    "InactionConsequence",
    "TimePoint",
    "TradeOffAnalysis",
    # Decision schemas (Q1-Q7)
    "DecisionObject",
    "Q1WhatIsHappening",
    "Q2WhenWillItHappen",
    "Q3HowBadIsIt",
    "Q4WhyIsThisHappening",
    "Q5WhatToDoNow",
    "Q6HowConfident",
    "Q7WhatIfNothing",
]
