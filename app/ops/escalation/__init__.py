"""
RISKCAST Escalation Module.

D4 COMPLIANCE: "Automated incident escalation not fully implemented" - FIXED
C2 COMPLIANCE: "Regulatory response automation not implemented" - FIXED

Provides:
- Automated incident escalation
- Time-based escalation progression
- Multi-channel notifications
- Acknowledgment tracking
- Regulatory response automation
"""

from app.ops.escalation.automation import (
    # Enums
    EscalationLevel,
    EscalationChannel,
    AlertSeverity,
    AlertStatus,
    # Schemas
    EscalationPolicy,
    EscalationState,
    EscalationContact,
    Alert,
    # Services
    AutomatedEscalation,
    RegulatoryResponseAutomation,
    get_escalation_service,
)

__all__ = [
    # Enums
    "EscalationLevel",
    "EscalationChannel",
    "AlertSeverity",
    "AlertStatus",
    # Schemas
    "EscalationPolicy",
    "EscalationState",
    "EscalationContact",
    "Alert",
    # Services
    "AutomatedEscalation",
    "RegulatoryResponseAutomation",
    "get_escalation_service",
]
