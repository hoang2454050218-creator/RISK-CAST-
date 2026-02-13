"""OMEN - Signal Engine.

OMEN is a SIGNAL ENGINE ONLY.
Outputs: signals, evidence, confidence (data quality), context.
NEVER outputs: risk_status, overall_risk, RiskLevel, decisions.
"""

from app.omen.schemas import (
    Chokepoint,
    SignalCategory,
    EvidenceSource,
    EvidenceItem,
    GeographicScope,
    TemporalScope,
    OmenSignal,
)
from app.omen.client import (
    OmenClient,
    OmenClientConfig,
    OmenAPIResponse,
    get_omen_client,
    create_omen_client,
)
from app.omen.service import (
    OmenService,
    SignalCache,
    get_omen_service,
    create_omen_service,
)

__all__ = [
    # Schemas
    "Chokepoint",
    "SignalCategory",
    "EvidenceSource",
    "EvidenceItem",
    "GeographicScope",
    "TemporalScope",
    "OmenSignal",
    # Client
    "OmenClient",
    "OmenClientConfig",
    "OmenAPIResponse",
    "get_omen_client",
    "create_omen_client",
    # Service
    "OmenService",
    "SignalCache",
    "get_omen_service",
    "create_omen_service",
]
