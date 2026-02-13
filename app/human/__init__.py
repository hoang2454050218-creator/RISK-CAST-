"""
RISKCAST Human-AI Collaboration Module.

This module enables human oversight of AI decisions:
- Override: Humans can override system recommendations with documented reasons
- Escalation: System escalates uncertain decisions to human review
- Feedback: Humans provide feedback to improve system accuracy
- Trust Metrics: Outcome-based trust calibration (C3 Compliance)

CRITICAL: All human interactions create immutable audit records.
"""

from app.human.schemas import (
    OverrideReason,
    OverrideRequest,
    OverrideResult,
    EscalationTrigger,
    EscalationRequest,
    EscalationResolution,
    FeedbackType,
    FeedbackSubmission,
    TrustMetrics,
)
from app.human.service import (
    HumanCollaborationService,
    EscalationConfig,
    create_human_collaboration_service,
)
from app.human.trust_metrics import (
    TrustCalibration,
    TrustAlert,
    TrustCalibrationReport,
    TrustMetricsCalculator,
    create_trust_metrics_calculator,
)

__all__ = [
    # Override schemas
    "OverrideReason",
    "OverrideRequest",
    "OverrideResult",
    # Escalation schemas
    "EscalationTrigger",
    "EscalationRequest",
    "EscalationResolution",
    # Feedback schemas
    "FeedbackType",
    "FeedbackSubmission",
    # Trust metrics (basic)
    "TrustMetrics",
    # Trust calibration (C3 Compliance)
    "TrustCalibration",
    "TrustAlert",
    "TrustCalibrationReport",
    "TrustMetricsCalculator",
    "create_trust_metrics_calculator",
    # Service
    "HumanCollaborationService",
    "EscalationConfig",
    "create_human_collaboration_service",
]
