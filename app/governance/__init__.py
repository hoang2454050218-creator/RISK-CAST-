"""
RISKCAST AI Governance Framework.

EU AI Act Compliant Governance for Decision Intelligence.

This module provides:
- AI Governance Policy enforcement
- Model Registry with Model Cards
- Bias detection and fairness monitoring (with production data - C4)
- Transparency and public documentation
- Ethical decision-making framework

Addresses audit gaps:
- C4.1 AI Governance: Policy enforcement, human oversight
- C4.2 Fairness & Bias: Bias detection, fairness metrics
- C4.3 Transparency: Model cards, public documentation
- C4.4 Ethical Decision-Making: Ethical assessment framework
- C4: Production data integration for bias detection (NEW)

EU AI Act Classification: LIMITED RISK
- Decision recommendation system (not autonomous)
- Human oversight required for high-value decisions
- Transparency obligations apply
"""

from app.governance.ai_policy import (
    AIRiskLevel,
    ModelPurpose,
    GovernancePolicy,
    PolicyEnforcer,
    PolicyViolation,
    PolicyComplianceReport,
    get_default_policy,
)

from app.governance.model_registry import (
    ModelStatus,
    ModelCard,
    ModelRegistry,
    get_model_registry,
)

from app.governance.bias_detection import (
    FairnessMetric,
    GroupFairnessReport,
    FairnessReport,
    BiasDetector,
    ProductionBiasDetector,
    create_production_bias_detector,
)

from app.governance.ethics import (
    EthicalPrinciple,
    EthicalCheck,
    EthicalAssessment,
    EthicsChecker,
)

from app.governance.transparency import (
    TransparencyLevel,
    PublicDocumentation,
    SystemCapabilities,
    TransparencyReport,
    TransparencyManager,
)

__all__ = [
    # AI Policy
    "AIRiskLevel",
    "ModelPurpose",
    "GovernancePolicy",
    "PolicyEnforcer",
    "PolicyViolation",
    "PolicyComplianceReport",
    "get_default_policy",
    # Model Registry
    "ModelStatus",
    "ModelCard",
    "ModelRegistry",
    "get_model_registry",
    # Bias Detection (including production - C4)
    "FairnessMetric",
    "GroupFairnessReport",
    "FairnessReport",
    "BiasDetector",
    "ProductionBiasDetector",
    "create_production_bias_detector",
    # Ethics
    "EthicalPrinciple",
    "EthicalCheck",
    "EthicalAssessment",
    "EthicsChecker",
    # Transparency
    "TransparencyLevel",
    "PublicDocumentation",
    "SystemCapabilities",
    "TransparencyReport",
    "TransparencyManager",
]
