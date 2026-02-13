# RISKCAST ULTIMATE BUILD SYSTEM
## From Prototype to Enterprise-Grade Decision Intelligence Platform

> **Mục tiêu**: Transform RISKCAST từ prototype (287/1000) thành production-ready system (750+/1000)
> 
> **Approach**: Phased prompts, mỗi phase có clear deliverables và acceptance criteria
> 
> **Standard**: Palantir/Everstream/project44 level

---

## MASTER CONTEXT (Copy vào đầu MỌI prompt)

```markdown
# RISKCAST PROJECT CONTEXT

## What RISKCAST Is
RISKCAST is a Decision Intelligence Platform for maritime supply chain. Unlike notification systems that say "event detected", RISKCAST outputs SPECIFIC DECISIONS with $ amounts, deadlines, and actionable steps.

## The 7 Questions Framework (CORE DIFFERENTIATOR)
Every decision MUST answer:
- Q1: What's happening? (personalized to customer's routes/shipments)
- Q2: When? (timeline + urgency level)
- Q3: How bad? ($ exposure + delay days)
- Q4: Why? (causal chain with evidence)
- Q5: What to do? (specific action + carrier + cost + deadline)
- Q6: Confidence? (calibrated score + factors)
- Q7: If nothing? (inaction cost escalation: 6h, 24h, 48h)

## Architecture
```
OMEN (Signals) → ORACLE (Reality) → RISKCAST (Decisions) → ALERTER (Delivery)
     ↓                ↓                    ↓                    ↓
 Polymarket      AIS Data           7 Questions          WhatsApp
 News API        Freight Rates      Personalized         Multi-lang
 Weather         Port Metrics       Actionable           Templates
```

## Current State
- OMEN: ✅ API exists at separate service (see OMEN API docs)
- ORACLE: ❌ Needs implementation
- RISKCAST: ✅ Core decision engine works
- ALERTER: ❌ Empty module
- API: ❌ No REST endpoints
- Database: ❌ In-memory only
- Security: ❌ None
- Observability: ❌ Basic logging only

## Tech Stack
- Python 3.11+
- FastAPI (async)
- Pydantic v2
- PostgreSQL + asyncpg
- Redis (caching)
- structlog (logging)
- Prometheus (metrics)
- OpenTelemetry (tracing)

## Code Standards
- Type hints on ALL code (100%)
- Docstrings on all public functions
- No magic numbers (use constants)
- Async by default for I/O
- Dependency injection via factories
- Repository pattern for data access
- Service layer for business logic

## File Structure
```
app/
├── core/           # Config, database, dependencies
├── omen/           # Signal integration (client to OMEN API)
├── oracle/         # Reality data services
├── riskcast/       # Decision engine (WORKING)
├── alerter/        # Delivery services
├── api/            # REST endpoints
└── common/         # Shared utilities
```
```

---

## EXECUTION TIMELINE

```
Week 1:
├── Phase 1: OMEN Client (2-3 days)
└── Phase 2: ORACLE Service (3-4 days)

Week 2:
├── Phase 3: PostgreSQL (3-4 days)
└── Phase 4: REST API (3-4 days)

Week 3:
├── Phase 5: Alerter (2-3 days)
└── Phase 6: Observability (2-3 days)

Week 4:
├── Phase 7: Security (3-4 days)
└── Phase 8: CI/CD (2-3 days)
```

After 4 weeks, RISKCAST should score **600-700/1000** on the audit.

---

## QUICK REFERENCE: Which Prompt to Use When

| Goal | Phase | Prompt |
|------|-------|--------|
| Connect to OMEN API | Phase 1 | 1.1 OMEN Client |
| Build reality data layer | Phase 2 | 2.1 Oracle Service |
| Add PostgreSQL | Phase 3 | 3.1 Database |
| Create REST API | Phase 4 | 4.1 API Routes |
| Send WhatsApp alerts | Phase 5 | 5.1 Alerter |
| Add metrics/tracing | Phase 6 | 6.1 Observability |
| Add authentication | Phase 7 | 7.1 Security |
| Containerize & CI/CD | Phase 8 | 8.1 Docker |

---

## PHASE 1: OMEN INTEGRATION CLIENT
**Duration**: 2-3 days | **Priority**: P0

### Prompt 1.1: OMEN Client Service

```markdown
# Task: Build OMEN API Client for RISKCAST

## Context
OMEN is a separate service that provides signals. RISKCAST needs a client to consume OMEN's API.

## OMEN API Reference (CRITICAL - READ CAREFULLY)

### Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/signals/` | GET | List signals |
| `/api/v1/signals/{id}` | GET | Get single signal |
| `/api/v1/signals/batch` | POST | Generate from Polymarket |
| `/api/v1/signals/refresh` | POST | Refresh from live sources |
| `/api/v1/multi-source/signals` | GET | All sources aggregated |

### WebSocket
- Endpoint: `/ws`
- Events: `signal_emitted`, `signal_ingested`, `stats_update`

### SSE
- Endpoint: `/api/v1/realtime/prices`

### OmenSignal Schema (what OMEN returns)
```json
{
  "signal_id": "OMEN-RS2024-001",
  "title": "Red Sea shipping disruption probability",
  "probability": 0.73,
  "probability_source": "polymarket",
  "confidence_score": 0.85,
  "confidence_level": "HIGH",
  "confidence_factors": {
    "liquidity": 0.9,
    "cross_source": 0.8,
    "freshness": 0.85
  },
  "category": "GEOPOLITICAL",
  "status": "ACTIVE",
  "signal_type": "DISRUPTION",
  "geographic": {
    "regions": ["Middle East", "Red Sea"],
    "chokepoints": ["Suez Canal", "Bab el-Mandeb"]
  },
  "temporal": {
    "event_horizon": "7d",
    "resolution_date": "2024-02-15"
  },
  "evidence": [
    {"source": "polymarket", "url": "...", "observed_at": "..."}
  ],
  "impact_hints": {
    "domains": ["shipping", "oil"],
    "direction": "negative",
    "affected_asset_types": ["freight", "crude"]
  },
  "trace_id": "abc123",
  "data_provenance": {
    "provider_type": "real",
    "freshness_seconds": 120
  }
}
```

### Response Wrapper
```json
{
  "data": { ... },
  "meta": {
    "mode": "LIVE",
    "real_source_coverage": 0.85,
    "live_gate_status": "ALLOWED",
    "real_sources": ["polymarket", "news_api"],
    "mock_sources": ["ais"],
    "timestamp": "2024-02-04T..."
  }
}
```

## Requirements

### 1. Create `app/omen/client.py`

```python
"""
OMEN API Client for RISKCAST

Responsibilities:
- Fetch signals from OMEN API
- Subscribe to real-time updates via WebSocket
- Convert OMEN responses to internal OmenSignal schema
- Handle connection failures with retry + circuit breaker
"""

from typing import AsyncGenerator, Optional
from datetime import datetime
import httpx
import websockets
from pydantic import BaseModel

from app.omen.schemas import OmenSignal
from app.core.config import settings
from app.common.resilience import retry_with_backoff, circuit_breaker

class OmenClientConfig(BaseModel):
    """Configuration for OMEN client."""
    base_url: str = "http://localhost:8001"  # OMEN service URL
    timeout_seconds: float = 30.0
    max_retries: int = 3
    ws_reconnect_delay: float = 5.0

class OmenAPIResponse(BaseModel):
    """Wrapper for OMEN API responses."""
    data: dict | list
    meta: dict

class OmenClient:
    """
    Client for OMEN Signal Intelligence API.
    
    Usage:
        async with OmenClient() as client:
            signals = await client.get_signals()
            async for signal in client.subscribe():
                process(signal)
    """
    
    def __init__(self, config: Optional[OmenClientConfig] = None):
        self.config = config or OmenClientConfig()
        self._http_client: Optional[httpx.AsyncClient] = None
        self._ws_connection = None
    
    async def __aenter__(self):
        self._http_client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=self.config.timeout_seconds,
        )
        return self
    
    async def __aexit__(self, *args):
        if self._http_client:
            await self._http_client.aclose()
        if self._ws_connection:
            await self._ws_connection.close()
    
    # === REST Methods ===
    
    @retry_with_backoff(max_retries=3)
    @circuit_breaker(failure_threshold=5, recovery_timeout=60)
    async def get_signals(
        self,
        category: Optional[str] = None,
        status: str = "ACTIVE",
        limit: int = 100,
    ) -> list[OmenSignal]:
        """Fetch signals from OMEN API."""
        # Implementation here
        pass
    
    @retry_with_backoff(max_retries=3)
    async def get_signal(self, signal_id: str) -> Optional[OmenSignal]:
        """Fetch single signal by ID."""
        pass
    
    async def refresh_signals(self) -> list[OmenSignal]:
        """Trigger OMEN to refresh from live sources."""
        pass
    
    # === WebSocket Methods ===
    
    async def subscribe(self) -> AsyncGenerator[OmenSignal, None]:
        """
        Subscribe to real-time signal updates.
        
        Yields OmenSignal objects as they arrive.
        Auto-reconnects on connection failure.
        """
        pass
    
    # === Helper Methods ===
    
    def _parse_signal(self, data: dict) -> OmenSignal:
        """Convert OMEN API response to internal schema."""
        # Map OMEN's geographic.chokepoints to our Chokepoint enum
        # Map OMEN's category to our SignalCategory enum
        pass
    
    def _check_data_quality(self, meta: dict) -> bool:
        """Check if data is from real sources."""
        return meta.get("mode") == "LIVE" and meta.get("real_source_coverage", 0) > 0.5
```

### 2. Create `app/common/resilience.py`

```python
"""
Resilience patterns for external service calls.

Implements:
- Retry with exponential backoff
- Circuit breaker pattern
- Timeout handling
- Fallback responses
"""

import asyncio
from functools import wraps
from typing import Callable, TypeVar, ParamSpec
from enum import Enum
import structlog

logger = structlog.get_logger()

P = ParamSpec("P")
T = TypeVar("T")

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple = (Exception,),
):
    """
    Decorator for retry with exponential backoff.
    
    Usage:
        @retry_with_backoff(max_retries=3)
        async def fetch_data():
            ...
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = min(base_delay * (exponential_base ** attempt), max_delay)
                        logger.warning(
                            "retry_attempt",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            delay=delay,
                            error=str(e),
                        )
                        await asyncio.sleep(delay)
            raise last_exception
        return wrapper
    return decorator

class CircuitBreaker:
    """
    Circuit breaker implementation.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests rejected immediately
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0
        self._half_open_calls = 0
    
    # Implementation details...

def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
):
    """Decorator version of circuit breaker."""
    # Implementation...
```

### 3. Create `app/omen/service.py`

```python
"""
OMEN Integration Service for RISKCAST.

This service:
- Manages OMEN client lifecycle
- Provides caching layer for signals
- Handles signal-to-intelligence conversion
- Maintains connection health metrics
"""

from typing import Optional
from datetime import datetime, timedelta
import structlog

from app.omen.client import OmenClient, OmenClientConfig
from app.omen.schemas import OmenSignal
from app.oracle.schemas import CorrelatedIntelligence
from app.core.cache import CacheService

logger = structlog.get_logger()

class OmenService:
    """
    High-level service for OMEN integration.
    
    Usage:
        service = OmenService()
        await service.start()
        
        # Get signals
        signals = await service.get_active_signals()
        
        # Subscribe to updates
        async for signal in service.stream_signals():
            await process_signal(signal)
    """
    
    def __init__(
        self,
        client: Optional[OmenClient] = None,
        cache: Optional[CacheService] = None,
    ):
        self._client = client or OmenClient()
        self._cache = cache
        self._running = False
    
    async def start(self):
        """Start the service and establish connections."""
        pass
    
    async def stop(self):
        """Gracefully stop the service."""
        pass
    
    async def get_active_signals(
        self,
        chokepoints: Optional[list[str]] = None,
        min_probability: float = 0.3,
        use_cache: bool = True,
    ) -> list[OmenSignal]:
        """
        Get active signals, optionally filtered.
        
        Args:
            chokepoints: Filter by specific chokepoints
            min_probability: Minimum probability threshold
            use_cache: Whether to use cached results
        """
        pass
    
    async def get_signal_for_route(
        self,
        origin: str,
        destination: str,
    ) -> list[OmenSignal]:
        """Get signals affecting a specific route."""
        pass
    
    async def stream_signals(self):
        """Stream real-time signal updates."""
        pass
    
    def signal_to_intelligence(
        self,
        signal: OmenSignal,
        reality_snapshot: "RealitySnapshot",
    ) -> CorrelatedIntelligence:
        """
        Combine signal with reality data to create intelligence.
        
        This is the bridge between OMEN and RISKCAST.
        """
        pass
```

### 4. Update `app/omen/__init__.py`

```python
"""
OMEN Integration Module

Provides client and service for consuming OMEN Signal Intelligence API.
"""

from app.omen.schemas import (
    OmenSignal,
    SignalCategory,
    Chokepoint,
    EvidenceItem,
    GeographicScope,
    TemporalScope,
)
from app.omen.client import OmenClient, OmenClientConfig
from app.omen.service import OmenService

__all__ = [
    # Schemas
    "OmenSignal",
    "SignalCategory", 
    "Chokepoint",
    "EvidenceItem",
    "GeographicScope",
    "TemporalScope",
    # Client
    "OmenClient",
    "OmenClientConfig",
    # Service
    "OmenService",
]
```

## Acceptance Criteria

- [ ] `OmenClient` can fetch signals from OMEN API
- [ ] `OmenClient` can subscribe to WebSocket for real-time updates
- [ ] Retry logic works (test with network failures)
- [ ] Circuit breaker opens after 5 consecutive failures
- [ ] Circuit breaker recovers after 60 seconds
- [ ] Signal schema mapping handles all OMEN fields
- [ ] `OmenService` provides high-level interface
- [ ] Logging includes trace_id for debugging
- [ ] All code has type hints and docstrings

## Tests Required

Create `tests/test_omen/test_client.py`:
- test_get_signals_success
- test_get_signals_with_filters
- test_get_signal_not_found
- test_retry_on_failure
- test_circuit_breaker_opens
- test_circuit_breaker_recovers
- test_websocket_reconnect

## Do NOT

- Do NOT modify existing `app/omen/schemas.py` (it's correct)
- Do NOT create mock OMEN service (use real OMEN API)
- Do NOT skip error handling
- Do NOT use synchronous HTTP calls
```

---

## PHASE 2: ORACLE SERVICE (Reality Data)
**Duration**: 1 week | **Priority**: P0

### Prompt 2.1: Oracle Core Service

```markdown
# Task: Build ORACLE Reality Data Service

## Context
ORACLE provides "ground truth" about what's actually happening:
- AIS vessel tracking (where ships actually are)
- Freight rate data (actual market prices)
- Port congestion metrics (real delays)

ORACLE's job is to VALIDATE or CONTRADICT signals from OMEN.

## Correlation Status Logic

```
OMEN says "Red Sea disruption 73% likely"
ORACLE checks:
- Are vessels actually rerouting? → YES, 23 ships diverted
- Are freight rates spiking? → YES, +35% premium
- Result: CONFIRMED (signal matches reality)

OMEN says "Panama drought 60% likely"
ORACLE checks:
- Are vessels delayed at Panama? → NO, normal flow
- Are rates changed? → NO, stable
- Result: PREDICTED_NOT_OBSERVED (signal exists but reality normal)
```

## Files to Create

### 1. `app/oracle/services/ais.py` - AIS Data Service

```python
"""
AIS (Automatic Identification System) Data Service.

Provides real-time vessel tracking data.
For MVP, we use mock data or free AIS APIs.
Production would use MarineTraffic, VesselFinder, or Spire.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()

class VesselPosition(BaseModel):
    """Current position of a vessel."""
    mmsi: str                    # Maritime Mobile Service Identity
    imo: Optional[str]           # IMO number
    vessel_name: str
    latitude: float
    longitude: float
    speed_knots: float
    heading: float
    destination: Optional[str]
    eta: Optional[datetime]
    timestamp: datetime

class VesselRoute(BaseModel):
    """Historical route of a vessel."""
    mmsi: str
    positions: list[VesselPosition]
    origin_port: Optional[str]
    destination_port: Optional[str]
    is_rerouting: bool = False   # Detected route change
    reroute_reason: Optional[str]

class AISService:
    """
    Service for AIS vessel tracking data.
    
    MVP Implementation:
    - Uses mock data for development
    - Can integrate with free AIS APIs
    
    Production:
    - MarineTraffic API
    - VesselFinder API
    - Spire Maritime
    """
    
    async def get_vessels_in_region(
        self,
        region: str,  # e.g., "red_sea", "suez"
        vessel_types: Optional[list[str]] = None,
    ) -> list[VesselPosition]:
        """Get all vessels in a geographic region."""
        pass
    
    async def get_vessels_rerouting(
        self,
        from_chokepoint: str,
        time_window_hours: int = 24,
    ) -> list[VesselRoute]:
        """
        Detect vessels that changed route away from a chokepoint.
        
        This is KEY for confirming disruptions.
        If many vessels suddenly avoid Red Sea → disruption confirmed.
        """
        pass
    
    async def get_vessel_by_shipment(
        self,
        origin_port: str,
        destination_port: str,
        etd: datetime,
    ) -> Optional[VesselPosition]:
        """Find vessel for a specific shipment."""
        pass
    
    async def count_vessels_waiting(
        self,
        port_or_chokepoint: str,
    ) -> int:
        """Count vessels waiting/anchored at a location."""
        pass
```

### 2. `app/oracle/services/freight.py` - Freight Rate Service

```python
"""
Freight Rate Data Service.

Provides market rate data for shipping lanes.
Rate spikes often indicate disruptions.
"""

from typing import Optional
from datetime import datetime, date
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()

class FreightRate(BaseModel):
    """Freight rate for a route."""
    route: str                   # e.g., "CNSHA-NLRTM"
    rate_usd_per_teu: float
    rate_date: date
    carrier: Optional[str]
    contract_type: str = "spot"  # spot | contract
    
class RateChange(BaseModel):
    """Rate change analysis."""
    route: str
    current_rate: float
    baseline_rate: float         # 30-day average
    change_pct: float
    change_direction: str        # up | down | stable
    is_anomaly: bool            # > 2 std dev from baseline

class FreightRateService:
    """
    Service for freight rate data.
    
    MVP: Mock data or Freightos API (free tier)
    Production: Xeneta, Freightos, Drewry
    """
    
    async def get_current_rate(
        self,
        origin: str,
        destination: str,
        container_type: str = "40GP",
    ) -> Optional[FreightRate]:
        """Get current spot rate for a route."""
        pass
    
    async def get_rate_history(
        self,
        origin: str,
        destination: str,
        days: int = 30,
    ) -> list[FreightRate]:
        """Get historical rates for trend analysis."""
        pass
    
    async def detect_rate_anomaly(
        self,
        origin: str,
        destination: str,
    ) -> Optional[RateChange]:
        """
        Detect if current rate is anomalous.
        
        Rate spike often indicates:
        - Capacity shortage
        - Disruption forcing reroutes
        - Seasonal demand
        """
        pass
    
    async def get_chokepoint_premium(
        self,
        chokepoint: str,
    ) -> float:
        """
        Calculate premium for routes through a chokepoint.
        
        Compare rates through chokepoint vs alternative routes.
        """
        pass
```

### 3. `app/oracle/services/port.py` - Port Metrics Service

```python
"""
Port Congestion and Metrics Service.

Tracks port-level operational data.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class PortMetrics(BaseModel):
    """Operational metrics for a port."""
    port_code: str               # UN/LOCODE
    port_name: str
    vessels_at_anchor: int
    vessels_at_berth: int
    avg_wait_time_hours: float
    avg_turnaround_hours: float
    congestion_level: str        # low | medium | high | critical
    timestamp: datetime

class PortService:
    """Service for port operational data."""
    
    async def get_port_metrics(self, port_code: str) -> Optional[PortMetrics]:
        """Get current metrics for a port."""
        pass
    
    async def get_congestion_trend(
        self,
        port_code: str,
        days: int = 7,
    ) -> list[PortMetrics]:
        """Get historical congestion data."""
        pass
```

### 4. `app/oracle/correlator.py` - Signal-Reality Correlator

```python
"""
Signal-Reality Correlator.

This is the BRAIN of ORACLE.
Takes an OMEN signal and determines if reality confirms it.
"""

from typing import Optional
from datetime import datetime
from enum import Enum
import structlog

from app.omen.schemas import OmenSignal, Chokepoint
from app.oracle.schemas import (
    CorrelationStatus,
    RealitySnapshot,
    ChokepointHealth,
    CorrelatedIntelligence,
)
from app.oracle.services.ais import AISService
from app.oracle.services.freight import FreightRateService
from app.oracle.services.port import PortService

logger = structlog.get_logger()

class CorrelationResult(Enum):
    """Detailed correlation result."""
    STRONG_CONFIRM = "strong_confirm"      # Multiple reality indicators match
    WEAK_CONFIRM = "weak_confirm"          # Some indicators match
    NEUTRAL = "neutral"                    # Inconclusive
    CONTRADICTS = "contradicts"            # Reality contradicts signal
    NO_DATA = "no_data"                    # Cannot assess

class Correlator:
    """
    Correlates OMEN signals with reality data.
    
    Logic:
    1. Get signal's affected chokepoint(s)
    2. Gather reality data for those chokepoints
    3. Compare signal prediction vs reality
    4. Output CorrelatedIntelligence
    """
    
    def __init__(
        self,
        ais_service: AISService,
        freight_service: FreightRateService,
        port_service: PortService,
    ):
        self._ais = ais_service
        self._freight = freight_service
        self._port = port_service
    
    async def correlate(
        self,
        signal: OmenSignal,
    ) -> CorrelatedIntelligence:
        """
        Main correlation method.
        
        Returns CorrelatedIntelligence ready for RISKCAST.
        """
        # Step 1: Build reality snapshot
        reality = await self._build_reality_snapshot(signal)
        
        # Step 2: Determine correlation status
        status = await self._determine_status(signal, reality)
        
        # Step 3: Calculate combined confidence
        combined_confidence = self._calculate_combined_confidence(
            signal_confidence=signal.confidence_score,
            reality_strength=reality.confidence,
            correlation_status=status,
        )
        
        return CorrelatedIntelligence(
            signal=signal,
            reality=reality,
            correlation_status=status,
            combined_confidence=combined_confidence,
            correlation_time=datetime.utcnow(),
        )
    
    async def _build_reality_snapshot(
        self,
        signal: OmenSignal,
    ) -> RealitySnapshot:
        """Gather reality data for signal's geographic scope."""
        chokepoint_health = {}
        
        for cp in signal.geographic.chokepoints:
            health = await self._assess_chokepoint_health(cp)
            chokepoint_health[cp] = health
        
        return RealitySnapshot(
            timestamp=datetime.utcnow(),
            chokepoint_health=chokepoint_health,
        )
    
    async def _assess_chokepoint_health(
        self,
        chokepoint: str,
    ) -> ChokepointHealth:
        """
        Assess health of a chokepoint.
        
        Checks:
        - Vessels waiting/rerouting
        - Rate premiums
        - Port congestion
        """
        # Get vessel data
        rerouting_vessels = await self._ais.get_vessels_rerouting(chokepoint)
        waiting_count = await self._ais.count_vessels_waiting(chokepoint)
        
        # Get rate data
        rate_premium = await self._freight.get_chokepoint_premium(chokepoint)
        
        return ChokepointHealth(
            chokepoint=chokepoint,
            vessels_waiting=waiting_count,
            vessels_rerouting=len(rerouting_vessels),
            rate_premium_pct=rate_premium,
            status=self._determine_health_status(
                waiting_count, len(rerouting_vessels), rate_premium
            ),
        )
    
    async def _determine_status(
        self,
        signal: OmenSignal,
        reality: RealitySnapshot,
    ) -> CorrelationStatus:
        """
        Determine correlation status.
        
        Rules:
        - CONFIRMED: High probability signal + reality shows disruption
        - MATERIALIZING: Medium probability + early signs in reality
        - PREDICTED_NOT_OBSERVED: Signal exists but reality normal
        - SURPRISE: No signal but reality shows disruption
        - NORMAL: No signal, reality normal
        """
        pass
    
    def _calculate_combined_confidence(
        self,
        signal_confidence: float,
        reality_strength: float,
        correlation_status: CorrelationStatus,
    ) -> float:
        """
        Calculate combined confidence score.
        
        Formula:
        - CONFIRMED: boost confidence (signal + reality agree)
        - CONTRADICTS: reduce confidence
        - NO_DATA: use signal confidence with penalty
        """
        pass
```

### 5. `app/oracle/service.py` - Main Oracle Service

```python
"""
Main ORACLE Service.

High-level interface for reality data and correlation.
"""

from typing import Optional
from datetime import datetime
import structlog

from app.omen.schemas import OmenSignal
from app.oracle.schemas import CorrelatedIntelligence, RealitySnapshot
from app.oracle.correlator import Correlator
from app.oracle.services.ais import AISService
from app.oracle.services.freight import FreightRateService
from app.oracle.services.port import PortService

logger = structlog.get_logger()

class OracleService:
    """
    Main service for ORACLE reality intelligence.
    
    Usage:
        oracle = OracleService()
        
        # Correlate a signal
        intelligence = await oracle.correlate_signal(signal)
        
        # Get reality snapshot
        snapshot = await oracle.get_reality_snapshot(chokepoints=["red_sea"])
    """
    
    def __init__(
        self,
        ais_service: Optional[AISService] = None,
        freight_service: Optional[FreightRateService] = None,
        port_service: Optional[PortService] = None,
    ):
        self._ais = ais_service or AISService()
        self._freight = freight_service or FreightRateService()
        self._port = port_service or PortService()
        self._correlator = Correlator(self._ais, self._freight, self._port)
    
    async def correlate_signal(
        self,
        signal: OmenSignal,
    ) -> CorrelatedIntelligence:
        """
        Correlate an OMEN signal with reality data.
        
        This is the main entry point for RISKCAST integration.
        """
        return await self._correlator.correlate(signal)
    
    async def get_reality_snapshot(
        self,
        chokepoints: Optional[list[str]] = None,
    ) -> RealitySnapshot:
        """Get current reality snapshot."""
        pass
    
    async def detect_surprise_events(self) -> list[CorrelatedIntelligence]:
        """
        Detect disruptions without corresponding OMEN signals.
        
        This catches "surprises" - reality disruptions that
        weren't predicted by signals.
        """
        pass
```

## Acceptance Criteria

- [ ] AISService can get vessels in region
- [ ] AISService can detect rerouting vessels
- [ ] FreightRateService can get current rates
- [ ] FreightRateService can detect rate anomalies
- [ ] Correlator correctly determines CONFIRMED status
- [ ] Correlator correctly determines PREDICTED_NOT_OBSERVED status
- [ ] Combined confidence calculation is sensible
- [ ] OracleService provides clean interface
- [ ] All services have mock data for testing
- [ ] Logging includes chokepoint and signal_id

## Tests Required

- test_correlation_confirmed (high signal + reality confirms)
- test_correlation_predicted_not_observed (signal but normal reality)
- test_correlation_surprise (no signal but disruption in reality)
- test_ais_rerouting_detection
- test_freight_rate_anomaly
- test_combined_confidence_calculation
```

---

## PHASE 3: DATABASE & PERSISTENCE
**Duration**: 3-4 days | **Priority**: P0

### Prompt 3.1: PostgreSQL Integration

```markdown
# Task: Replace In-Memory Storage with PostgreSQL

## Context
Current state: All data in memory, lost on restart.
Target state: PostgreSQL with async access, proper migrations.

## Requirements

### 1. `app/core/database.py` - Database Connection

```python
"""
PostgreSQL database connection management.

Uses asyncpg for async operations.
Provides connection pooling and health checks.
"""

from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
import asyncpg
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
import structlog

from app.core.config import settings

logger = structlog.get_logger()

class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass

class Database:
    """
    Database connection manager.
    
    Usage:
        db = Database()
        await db.connect()
        
        async with db.session() as session:
            # use session
            pass
        
        await db.disconnect()
    """
    
    def __init__(self, url: Optional[str] = None):
        self._url = url or settings.database_url
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None
    
    async def connect(self):
        """Initialize database connection pool."""
        self._engine = create_async_engine(
            self._url,
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True,
            echo=settings.debug,
        )
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        logger.info("database_connected", url=self._url.split("@")[-1])
    
    async def disconnect(self):
        """Close all connections."""
        if self._engine:
            await self._engine.dispose()
            logger.info("database_disconnected")
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session."""
        if not self._session_factory:
            raise RuntimeError("Database not connected")
        
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    async def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            async with self.session() as session:
                await session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error("database_health_check_failed", error=str(e))
            return False

# Global instance
database = Database()

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI."""
    async with database.session() as session:
        yield session
```

### 2. `app/core/models.py` - SQLAlchemy Models

```python
"""
SQLAlchemy models for RISKCAST.

Maps Pydantic schemas to database tables.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, JSON,
    ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base

class CustomerModel(Base):
    """Customer profile table."""
    __tablename__ = "customers"
    
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    company_name: Mapped[str] = mapped_column(String(200))
    primary_routes: Mapped[list] = mapped_column(JSONB, default=list)
    relevant_chokepoints: Mapped[list] = mapped_column(JSONB, default=list)
    risk_tolerance: Mapped[str] = mapped_column(String(20), default="balanced")
    primary_phone: Mapped[Optional[str]] = mapped_column(String(20))
    language: Mapped[str] = mapped_column(String(10), default="en")
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    
    # Audit fields
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    shipments: Mapped[list["ShipmentModel"]] = relationship(back_populates="customer")
    decisions: Mapped[list["DecisionModel"]] = relationship(back_populates="customer")
    
    __table_args__ = (
        Index("ix_customers_company_name", "company_name"),
    )

class ShipmentModel(Base):
    """Shipment table."""
    __tablename__ = "shipments"
    
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"))
    origin_port: Mapped[str] = mapped_column(String(10))
    destination_port: Mapped[str] = mapped_column(String(10))
    cargo_value_usd: Mapped[float] = mapped_column(Float)
    container_type: Mapped[str] = mapped_column(String(10), default="40GP")
    container_count: Mapped[int] = mapped_column(Integer, default=1)
    etd: Mapped[datetime] = mapped_column(DateTime)
    eta: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="booked")
    has_delay_penalty: Mapped[bool] = mapped_column(Boolean, default=False)
    delay_penalty_per_day_usd: Mapped[float] = mapped_column(Float, default=0)
    
    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer: Mapped["CustomerModel"] = relationship(back_populates="shipments")
    
    __table_args__ = (
        Index("ix_shipments_customer_status", "customer_id", "status"),
        Index("ix_shipments_route", "origin_port", "destination_port"),
        Index("ix_shipments_eta", "eta"),
    )

class DecisionModel(Base):
    """Decision table - stores generated decisions."""
    __tablename__ = "decisions"
    
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"))
    signal_id: Mapped[str] = mapped_column(String(100))
    
    # 7 Questions (stored as JSONB for flexibility)
    q1_what: Mapped[dict] = mapped_column(JSONB)
    q2_when: Mapped[dict] = mapped_column(JSONB)
    q3_severity: Mapped[dict] = mapped_column(JSONB)
    q4_why: Mapped[dict] = mapped_column(JSONB)
    q5_action: Mapped[dict] = mapped_column(JSONB)
    q6_confidence: Mapped[dict] = mapped_column(JSONB)
    q7_inaction: Mapped[dict] = mapped_column(JSONB)
    
    # Metadata
    alternative_actions: Mapped[list] = mapped_column(JSONB, default=list)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    was_acted_upon: Mapped[Optional[bool]] = mapped_column(Boolean)
    acted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    user_feedback: Mapped[Optional[str]] = mapped_column(String(1000))
    
    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    customer: Mapped["CustomerModel"] = relationship(back_populates="decisions")
    
    __table_args__ = (
        Index("ix_decisions_customer_signal", "customer_id", "signal_id"),
        Index("ix_decisions_expires", "expires_at"),
        Index("ix_decisions_created", "created_at"),
    )
```

### 3. Update Repository to use PostgreSQL

```python
# app/riskcast/repos/customer.py

"""
Customer repository with PostgreSQL implementation.
"""

from typing import Optional, Protocol
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.models import CustomerModel, ShipmentModel
from app.riskcast.schemas.customer import CustomerProfile, Shipment, CustomerContext

logger = structlog.get_logger()

class CustomerRepository(Protocol):
    """Repository interface for customer data."""
    
    async def get_profile(self, customer_id: str) -> Optional[CustomerProfile]:
        ...
    
    async def get_shipments(
        self,
        customer_id: str,
        status: Optional[str] = None,
    ) -> list[Shipment]:
        ...
    
    async def get_context(self, customer_id: str) -> Optional[CustomerContext]:
        ...
    
    async def get_all_contexts(self) -> list[CustomerContext]:
        ...
    
    async def save_profile(self, profile: CustomerProfile) -> None:
        ...
    
    async def save_shipment(self, shipment: Shipment) -> None:
        ...

class PostgresCustomerRepository:
    """PostgreSQL implementation of CustomerRepository."""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get_profile(self, customer_id: str) -> Optional[CustomerProfile]:
        """Get customer profile by ID."""
        result = await self._session.execute(
            select(CustomerModel).where(CustomerModel.id == customer_id)
        )
        model = result.scalar_one_or_none()
        
        if not model:
            return None
        
        return self._model_to_profile(model)
    
    async def get_shipments(
        self,
        customer_id: str,
        status: Optional[str] = None,
    ) -> list[Shipment]:
        """Get shipments for a customer."""
        query = select(ShipmentModel).where(
            ShipmentModel.customer_id == customer_id
        )
        
        if status:
            query = query.where(ShipmentModel.status == status)
        
        result = await self._session.execute(query)
        models = result.scalars().all()
        
        return [self._model_to_shipment(m) for m in models]
    
    async def get_context(self, customer_id: str) -> Optional[CustomerContext]:
        """Get full customer context."""
        profile = await self.get_profile(customer_id)
        if not profile:
            return None
        
        shipments = await self.get_shipments(
            customer_id,
            status="booked",  # Active shipments
        )
        
        return CustomerContext(
            profile=profile,
            active_shipments=shipments,
        )
    
    def _model_to_profile(self, model: CustomerModel) -> CustomerProfile:
        """Convert SQLAlchemy model to Pydantic schema."""
        return CustomerProfile(
            customer_id=model.id,
            company_name=model.company_name,
            primary_routes=model.primary_routes,
            relevant_chokepoints=model.relevant_chokepoints,
            risk_tolerance=model.risk_tolerance,
            primary_phone=model.primary_phone,
            language=model.language,
            timezone=model.timezone,
        )
    
    def _model_to_shipment(self, model: ShipmentModel) -> Shipment:
        """Convert SQLAlchemy model to Pydantic schema."""
        return Shipment(
            shipment_id=model.id,
            customer_id=model.customer_id,
            origin_port=model.origin_port,
            destination_port=model.destination_port,
            cargo_value_usd=model.cargo_value_usd,
            container_type=model.container_type,
            container_count=model.container_count,
            etd=model.etd,
            eta=model.eta,
            status=model.status,
            has_delay_penalty=model.has_delay_penalty,
            delay_penalty_per_day_usd=model.delay_penalty_per_day_usd,
        )
```

### 4. Database Migrations with Alembic

```bash
# Setup
pip install alembic

# Initialize
alembic init alembic

# Configure alembic.ini and env.py for async
```

## Acceptance Criteria

- [ ] Database connection pooling works
- [ ] Health check endpoint verifies DB connectivity
- [ ] All models have proper indexes
- [ ] Repository pattern abstracts database access
- [ ] Alembic migrations work
- [ ] Existing tests still pass
- [ ] Data survives application restart
```

---

## PHASE 4: REST API ENDPOINTS
**Duration**: 3-4 days | **Priority**: P0

### Prompt 4.1: API Routes

```markdown
# Task: Build REST API Endpoints

## Context
RISKCAST needs a full REST API for:
- Customer management
- Shipment management  
- Decision retrieval
- Signal processing triggers

## API Design Principles
- RESTful resource naming
- Consistent error responses
- Pagination for lists
- Versioned endpoints (v1)
- OpenAPI documentation

## Files to Create

### 1. `app/api/schemas.py` - API Request/Response Schemas

```python
"""
API-specific schemas.

These wrap internal schemas with API-specific fields
like pagination, error responses, etc.
"""

from typing import Generic, TypeVar, Optional
from datetime import datetime
from pydantic import BaseModel, Field

T = TypeVar("T")

class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    code: str
    message: str
    details: Optional[dict] = None
    request_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    database: bool
    omen: bool
    oracle: bool
    uptime_seconds: float
```

### 2. `app/api/routes/customers.py`

```python
"""
Customer API endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_session
from app.riskcast.repos.customer import PostgresCustomerRepository
from app.riskcast.schemas.customer import CustomerProfile, Shipment, CustomerContext
from app.api.schemas import PaginatedResponse, PaginationParams

logger = structlog.get_logger()
router = APIRouter(prefix="/customers", tags=["customers"])

@router.get("", response_model=PaginatedResponse[CustomerProfile])
async def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """List all customers with pagination."""
    repo = PostgresCustomerRepository(session)
    # Implementation
    pass

@router.get("/{customer_id}", response_model=CustomerProfile)
async def get_customer(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get customer by ID."""
    repo = PostgresCustomerRepository(session)
    profile = await repo.get_profile(customer_id)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found",
        )
    
    return profile

@router.post("", response_model=CustomerProfile, status_code=status.HTTP_201_CREATED)
async def create_customer(
    profile: CustomerProfile,
    session: AsyncSession = Depends(get_session),
):
    """Create a new customer."""
    pass

@router.put("/{customer_id}", response_model=CustomerProfile)
async def update_customer(
    customer_id: str,
    profile: CustomerProfile,
    session: AsyncSession = Depends(get_session),
):
    """Update customer profile."""
    pass

@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Delete a customer."""
    pass

# === Shipments ===

@router.get("/{customer_id}/shipments", response_model=list[Shipment])
async def list_shipments(
    customer_id: str,
    status: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """List shipments for a customer."""
    pass

@router.post("/{customer_id}/shipments", response_model=Shipment)
async def create_shipment(
    customer_id: str,
    shipment: Shipment,
    session: AsyncSession = Depends(get_session),
):
    """Create a shipment for a customer."""
    pass

# === Context ===

@router.get("/{customer_id}/context", response_model=CustomerContext)
async def get_customer_context(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get full customer context (profile + active shipments)."""
    pass
```

### 3. `app/api/routes/decisions.py`

```python
"""
Decision API endpoints.
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_session
from app.riskcast.schemas.decision import DecisionObject
from app.riskcast.service import RiskCastService, get_riskcast_service
from app.api.schemas import PaginatedResponse

logger = structlog.get_logger()
router = APIRouter(prefix="/decisions", tags=["decisions"])

@router.get("", response_model=PaginatedResponse[DecisionObject])
async def list_decisions(
    customer_id: Optional[str] = Query(None),
    signal_id: Optional[str] = Query(None),
    include_expired: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """
    List decisions with filters.
    
    Filters:
    - customer_id: Filter by customer
    - signal_id: Filter by signal
    - include_expired: Include expired decisions
    """
    pass

@router.get("/{decision_id}", response_model=DecisionObject)
async def get_decision(
    decision_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get decision by ID."""
    pass

@router.post("/{decision_id}/action", status_code=status.HTTP_200_OK)
async def record_action(
    decision_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Record that user acted on a decision."""
    service = get_riskcast_service()
    service.record_action_taken(decision_id)
    return {"status": "recorded"}

@router.post("/{decision_id}/feedback")
async def record_feedback(
    decision_id: str,
    feedback: str,
    session: AsyncSession = Depends(get_session),
):
    """Record user feedback on a decision."""
    service = get_riskcast_service()
    service.record_feedback(decision_id, feedback)
    return {"status": "recorded"}

# === Signal Processing ===

@router.post("/process-signal")
async def process_signal(
    signal_id: str,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """
    Trigger decision generation for a signal.
    
    This is called when OMEN emits a new signal.
    Processing happens in background.
    """
    background_tasks.add_task(_process_signal_background, signal_id)
    return {"status": "processing", "signal_id": signal_id}

async def _process_signal_background(signal_id: str):
    """Background task for signal processing."""
    # Fetch signal from OMEN
    # Correlate with ORACLE
    # Generate decisions via RISKCAST
    # Send alerts via ALERTER
    pass
```

### 4. `app/api/__init__.py` - Router Registration

```python
"""
API router registration.
"""

from fastapi import APIRouter

from app.api.routes import customers, decisions, signals, health

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router)
api_router.include_router(customers.router)
api_router.include_router(decisions.router)
api_router.include_router(signals.router)
```

## Acceptance Criteria

- [ ] All CRUD endpoints work for customers
- [ ] All CRUD endpoints work for shipments
- [ ] Decision listing with filters works
- [ ] Signal processing trigger works
- [ ] Health check reports all components
- [ ] OpenAPI docs auto-generated at /docs
- [ ] Error responses follow ErrorResponse schema
- [ ] Pagination works correctly
```

---

## PHASE 5: ALERTER SERVICE (WhatsApp Delivery)
**Duration**: 2-3 days | **Priority**: P0

### Prompt 5.1: WhatsApp Alerter

```markdown
# Task: Build Alerter Service for WhatsApp Delivery

## Context
ALERTER delivers decisions to users via WhatsApp.
Uses Twilio WhatsApp Business API.

## Requirements

### 1. `app/alerter/templates.py` - Message Templates

```python
"""
WhatsApp message templates.

Templates must be pre-approved by WhatsApp.
Use template variables for personalization.
"""

from typing import Optional
from pydantic import BaseModel
from enum import Enum

class TemplateLanguage(str, Enum):
    EN = "en"
    VI = "vi"

class AlertTemplate(BaseModel):
    """WhatsApp template definition."""
    name: str
    language: TemplateLanguage
    body: str
    variables: list[str]  # Placeholder names

# Define templates
TEMPLATES = {
    "decision_alert_en": AlertTemplate(
        name="riskcast_decision_alert",
        language=TemplateLanguage.EN,
        body="""🚨 *RISKCAST ALERT*

*{{1}}*  ← Q1: What's happening

⏰ *When:* {{2}}
💰 *Exposure:* {{3}}
📊 *Confidence:* {{4}}

*Recommended Action:*
{{5}}

⚠️ *If no action:* {{6}}

Reply DETAILS for full analysis.
Reply ACT to confirm action taken.""",
        variables=["event", "when", "exposure", "confidence", "action", "inaction"],
    ),
    
    "decision_alert_vi": AlertTemplate(
        name="riskcast_decision_alert_vi",
        language=TemplateLanguage.VI,
        body="""🚨 *CẢNH BÁO RISKCAST*

*{{1}}*

⏰ *Khi nào:* {{2}}
💰 *Rủi ro:* {{3}}
📊 *Độ tin cậy:* {{4}}

*Hành động đề xuất:*
{{5}}

⚠️ *Nếu không hành động:* {{6}}

Trả lời CHITIET để xem phân tích đầy đủ.
Trả lời XACNHAN khi đã thực hiện.""",
        variables=["event", "when", "exposure", "confidence", "action", "inaction"],
    ),
}

def render_decision_alert(
    decision: "DecisionObject",
    language: TemplateLanguage = TemplateLanguage.EN,
) -> dict:
    """
    Render decision to WhatsApp template variables.
    
    Returns dict ready for Twilio API.
    """
    template = TEMPLATES[f"decision_alert_{language.value}"]
    
    return {
        "template_name": template.name,
        "language": language.value,
        "variables": {
            "1": decision.q1_what.event_summary[:100],
            "2": f"{decision.q2_when.urgency.value.upper()} - {decision.q2_when.impact_timeline}",
            "3": f"${decision.q3_severity.total_exposure_usd:,.0f}",
            "4": f"{decision.q6_confidence.score_pct}% ({decision.q6_confidence.level.value})",
            "5": decision.q5_action.action_summary[:200],
            "6": f"${decision.q7_inaction.expected_loss_if_nothing:,.0f} loss expected",
        },
    }
```

### 2. `app/alerter/twilio_client.py` - Twilio Integration

```python
"""
Twilio WhatsApp client.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import structlog

from app.core.config import settings
from app.common.resilience import retry_with_backoff, circuit_breaker

logger = structlog.get_logger()

class MessageStatus(BaseModel):
    """WhatsApp message status."""
    message_sid: str
    status: str  # queued, sent, delivered, read, failed
    error_code: Optional[str]
    error_message: Optional[str]
    sent_at: datetime

class TwilioWhatsAppClient:
    """
    Twilio WhatsApp Business API client.
    
    Usage:
        client = TwilioWhatsAppClient()
        status = await client.send_template(
            to="+84901234567",
            template_name="riskcast_decision_alert",
            variables={"1": "...", "2": "..."},
        )
    """
    
    def __init__(self):
        self._client = Client(
            settings.twilio_account_sid,
            settings.twilio_auth_token,
        )
        self._from_number = f"whatsapp:{settings.twilio_whatsapp_number}"
    
    @retry_with_backoff(max_retries=3)
    @circuit_breaker(failure_threshold=5, recovery_timeout=60)
    async def send_template(
        self,
        to: str,
        template_name: str,
        language: str,
        variables: dict[str, str],
    ) -> MessageStatus:
        """
        Send a template message via WhatsApp.
        
        Args:
            to: E.164 phone number (+84901234567)
            template_name: Pre-approved template name
            language: Template language code
            variables: Template variable values
        """
        try:
            to_whatsapp = f"whatsapp:{to}"
            
            content_variables = {
                str(i): v for i, v in enumerate(variables.values(), 1)
            }
            
            message = self._client.messages.create(
                from_=self._from_number,
                to=to_whatsapp,
                content_sid=template_name,
                content_variables=content_variables,
            )
            
            logger.info(
                "whatsapp_message_sent",
                message_sid=message.sid,
                to=to,
                template=template_name,
            )
            
            return MessageStatus(
                message_sid=message.sid,
                status=message.status,
                error_code=None,
                error_message=None,
                sent_at=datetime.utcnow(),
            )
            
        except TwilioRestException as e:
            logger.error(
                "whatsapp_send_failed",
                to=to,
                error_code=e.code,
                error_message=e.msg,
            )
            
            return MessageStatus(
                message_sid="",
                status="failed",
                error_code=str(e.code),
                error_message=e.msg,
                sent_at=datetime.utcnow(),
            )
```

### 3. `app/alerter/service.py` - Alerter Service

```python
"""
Alerter service for decision delivery.
"""

from typing import Optional
from datetime import datetime
import structlog

from app.alerter.twilio_client import TwilioWhatsAppClient, MessageStatus
from app.alerter.templates import render_decision_alert, TemplateLanguage
from app.riskcast.schemas.decision import DecisionObject
from app.riskcast.schemas.customer import CustomerProfile

logger = structlog.get_logger()

class AlerterService:
    """
    Service for delivering decisions to users.
    
    Responsibilities:
    - Render decisions to message templates
    - Send via WhatsApp
    - Track delivery status
    - Handle failures and retries
    """
    
    def __init__(
        self,
        whatsapp_client: Optional[TwilioWhatsAppClient] = None,
    ):
        self._whatsapp = whatsapp_client or TwilioWhatsAppClient()
    
    async def send_decision(
        self,
        decision: DecisionObject,
        profile: CustomerProfile,
    ) -> MessageStatus:
        """
        Send a decision alert to a customer.
        
        Uses customer's language preference.
        """
        language = TemplateLanguage(profile.language) if profile.language in ["en", "vi"] else TemplateLanguage.EN
        
        template_data = render_decision_alert(decision, language)
        
        status = await self._whatsapp.send_template(
            to=profile.primary_phone,
            template_name=template_data["template_name"],
            language=template_data["language"],
            variables=template_data["variables"],
        )
        
        logger.info(
            "decision_alert_sent",
            decision_id=decision.decision_id,
            customer_id=profile.customer_id,
            message_sid=status.message_sid,
            status=status.status,
        )
        
        return status
    
    async def send_batch(
        self,
        decisions: list[tuple[DecisionObject, CustomerProfile]],
    ) -> list[MessageStatus]:
        """Send multiple decision alerts."""
        results = []
        
        for decision, profile in decisions:
            status = await self.send_decision(decision, profile)
            results.append(status)
        
        return results
```

## Acceptance Criteria

- [ ] Templates render correctly for both EN and VI
- [ ] Twilio client sends messages successfully
- [ ] Retry logic works on transient failures
- [ ] Circuit breaker prevents hammering failed service
- [ ] Message status tracking works
- [ ] Logging includes all relevant IDs
```

---

## PHASE 6: OBSERVABILITY
**Duration**: 2-3 days | **Priority**: P1

### Prompt 6.1: Metrics & Tracing

```markdown
# Task: Add Prometheus Metrics and OpenTelemetry Tracing

## Requirements

### 1. `app/common/metrics.py` - Prometheus Metrics

```python
"""
Prometheus metrics for RISKCAST.
"""

from prometheus_client import Counter, Histogram, Gauge, Info

# === Business Metrics ===

DECISIONS_GENERATED = Counter(
    "riskcast_decisions_generated_total",
    "Total decisions generated",
    ["customer_id", "signal_category", "severity"],
)

DECISIONS_ACTED_UPON = Counter(
    "riskcast_decisions_acted_upon_total",
    "Decisions where user took action",
    ["action_type"],
)

ALERTS_SENT = Counter(
    "riskcast_alerts_sent_total",
    "WhatsApp alerts sent",
    ["status", "language"],
)

# === Performance Metrics ===

DECISION_LATENCY = Histogram(
    "riskcast_decision_generation_seconds",
    "Time to generate a decision",
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

OMEN_REQUEST_LATENCY = Histogram(
    "riskcast_omen_request_seconds",
    "OMEN API request latency",
    ["endpoint"],
)

ORACLE_CORRELATION_LATENCY = Histogram(
    "riskcast_oracle_correlation_seconds",
    "ORACLE correlation time",
)

# === Health Metrics ===

ACTIVE_SIGNALS = Gauge(
    "riskcast_active_signals",
    "Number of active signals being monitored",
)

ACTIVE_CUSTOMERS = Gauge(
    "riskcast_active_customers",
    "Number of customers with active shipments",
)

CIRCUIT_BREAKER_STATE = Gauge(
    "riskcast_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["service"],
)

# === Info ===

BUILD_INFO = Info(
    "riskcast_build",
    "Build information",
)
```

### 2. `app/common/tracing.py` - OpenTelemetry Setup

```python
"""
OpenTelemetry tracing configuration.
"""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from app.core.config import settings

def setup_tracing(app):
    """Configure OpenTelemetry tracing."""
    
    provider = TracerProvider()
    
    if settings.otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=settings.otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    
    trace.set_tracer_provider(provider)
    
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()

def get_tracer(name: str):
    """Get a tracer for a module."""
    return trace.get_tracer(name)
```

## Acceptance Criteria

- [ ] Prometheus metrics endpoint at /metrics
- [ ] All business metrics tracked
- [ ] All latency metrics tracked
- [ ] OpenTelemetry traces exported
- [ ] Traces include custom spans for key operations
```

---

## PHASE 7: SECURITY & AUTH
**Duration**: 3-4 days | **Priority**: P1

### Prompt 7.1: API Authentication

```markdown
# Task: Add API Key Authentication

## Context
For MVP, use API key authentication.
Later can add OAuth2/JWT.

## Requirements

### 1. `app/core/auth.py`

```python
"""
API authentication.
"""

from typing import Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
import secrets
import hashlib
import structlog

from app.core.database import get_session

logger = structlog.get_logger()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

class APIKey:
    """API key with metadata."""
    key_id: str
    customer_id: str
    scopes: list[str]
    is_active: bool

async def verify_api_key(
    api_key: str = Security(api_key_header),
    session: AsyncSession = Depends(get_session),
) -> APIKey:
    """
    Verify API key and return associated metadata.
    
    Raises HTTPException if invalid.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    # Lookup in database
    # ... implementation ...
    
    logger.info("api_key_verified", key_id=api_key_obj.key_id)
    return api_key_obj

def require_scope(required_scope: str):
    """Dependency to require a specific scope."""
    async def check_scope(api_key: APIKey = Depends(verify_api_key)):
        if required_scope not in api_key.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Scope '{required_scope}' required",
            )
        return api_key
    return check_scope
```

## Acceptance Criteria

- [ ] API key authentication works
- [ ] Invalid keys return 401
- [ ] Scope checking works
- [ ] Rate limiting prevents abuse
- [ ] Keys are hashed in database
```

---

## PHASE 8: CI/CD & DEPLOYMENT
**Duration**: 2-3 days | **Priority**: P1

### Prompt 8.1: Docker & GitHub Actions

```markdown
# Task: Containerization and CI/CD Pipeline

## Requirements

### 1. `Dockerfile`

```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

RUN addgroup --system app && adduser --system --group app

RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*

COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

RUN chown -R app:app /app

USER app

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. `docker-compose.yml`

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://riskcast:riskcast@db:5432/riskcast
      - REDIS_URL=redis://redis:6379/0
      - OMEN_API_URL=http://omen:8001
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=riskcast
      - POSTGRES_PASSWORD=riskcast
      - POSTGRES_DB=riskcast
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U riskcast"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### 3. `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run linting
        run: |
          ruff check app/
          mypy app/
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/test
        run: |
          pytest --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: coverage.xml

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Build Docker image
        run: docker build -t riskcast:${{ github.sha }} .
      
      - name: Push to registry
        run: |
          echo "Push to registry here"
```

## Acceptance Criteria

- [ ] Docker build succeeds
- [ ] docker-compose up starts all services
- [ ] Health checks pass
- [ ] CI pipeline runs on push
- [ ] Tests run in CI
- [ ] Coverage reported
- [ ] Linting enforced
```

---

## FILES THIS SYSTEM WILL CREATE

```
app/
├── core/
│   ├── auth.py           [Phase 7]
│   ├── database.py       [Phase 3]
│   └── models.py         [Phase 3]
├── omen/
│   ├── client.py         [Phase 1]
│   └── service.py        [Phase 1]
├── oracle/
│   ├── correlator.py     [Phase 2]
│   ├── service.py        [Phase 2]
│   └── services/
│       ├── ais.py        [Phase 2]
│       ├── freight.py    [Phase 2]
│       └── port.py       [Phase 2]
├── alerter/
│   ├── service.py        [Phase 5]
│   ├── templates.py      [Phase 5]
│   └── twilio_client.py  [Phase 5]
├── api/
│   ├── __init__.py       [Phase 4]
│   ├── schemas.py        [Phase 4]
│   └── routes/
│       ├── customers.py  [Phase 4]
│       ├── decisions.py  [Phase 4]
│       ├── signals.py    [Phase 4]
│       └── health.py     [Phase 4]
├── common/
│   ├── metrics.py        [Phase 6]
│   ├── resilience.py     [Phase 1]
│   └── tracing.py        [Phase 6]
├── Dockerfile            [Phase 8]
├── docker-compose.yml    [Phase 8]
└── .github/workflows/    [Phase 8]
```

---

## IMPORTANT NOTES FOR CURSOR

1. **Always start with MASTER CONTEXT** - Copy it into every prompt
2. **One phase at a time** - Don't try to do multiple phases
3. **Run tests after each phase** - Ensure nothing breaks
4. **Commit frequently** - Small, atomic commits
5. **Ask for clarification** - If requirements unclear, ask

---

*Build System Version: 1.0*
*Created: 2026-02-05*
*Target: Enterprise-Grade Decision Intelligence*
