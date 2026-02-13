"""ORACLE - Reality Engine.

ORACLE provides ground truth about what IS happening:
- AIS vessel tracking
- Freight rates
- Port congestion
- Chokepoint health

And correlates OMEN predictions with reality.
"""

from app.oracle.schemas import (
    CorrelationStatus,
    ChokepointHealth,
    VesselMovement,
    RealitySnapshot,
    CorrelatedIntelligence,
)
from app.oracle.ais import AISClient, AISConfig, AISProvider, get_ais_client
from app.oracle.freight import (
    FreightRateClient,
    FreightRateData,
    FreightRateSnapshot,
    FreightRoute,
    get_freight_client,
)
from app.oracle.port import (
    PortDataClient,
    PortData,
    PortSnapshot,
    PortStatus,
    get_port_client,
)
from app.oracle.correlator import SignalCorrelator, get_correlator, create_correlator
from app.oracle.service import OracleService, get_oracle_service, create_oracle_service

__all__ = [
    # Schemas
    "CorrelationStatus",
    "ChokepointHealth",
    "VesselMovement",
    "RealitySnapshot",
    "CorrelatedIntelligence",
    # AIS
    "AISClient",
    "AISConfig",
    "AISProvider",
    "get_ais_client",
    # Freight
    "FreightRateClient",
    "FreightRateData",
    "FreightRateSnapshot",
    "FreightRoute",
    "get_freight_client",
    # Port
    "PortDataClient",
    "PortData",
    "PortSnapshot",
    "PortStatus",
    "get_port_client",
    # Correlator
    "SignalCorrelator",
    "get_correlator",
    "create_correlator",
    # Service
    "OracleService",
    "get_oracle_service",
    "create_oracle_service",
]
