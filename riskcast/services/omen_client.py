"""
OMEN Client — HTTP client for the external OMEN Signal Engine.

OMEN is an external service (separate repo). RiskCast only consumes signals.
If OMEN is down, RiskCast continues with internal signals (graceful degradation).

NOTE: The real OMEN API wraps responses in {"data": {"signals": [...]}, "meta": {...}}
and uses different field names (signal_id, confidence_score, etc.).
This client maps OMEN's format to RiskCast's internal representation.
"""

import httpx
import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class OmenSignal(BaseModel):
    """
    Signal from OMEN external service — RiskCast's internal representation.

    Fields are mapped from OMEN's native format:
      OMEN signal_id       → id
      OMEN signal_type     → signal_type
      OMEN confidence_score → confidence
      OMEN confidence_score * 100 → severity_score (derived)
      OMEN evidence[]      → evidence (collapsed to dict)
      OMEN geographic+temporal → context
      OMEN generated_at    → created_at
    """

    id: str
    signal_type: str
    confidence: float
    severity_score: float
    evidence: dict
    context: dict = {}
    created_at: str
    title: str = ""
    description: str = ""
    probability: float = 0.0
    category: str = ""


def _parse_omen_signal(raw: dict) -> OmenSignal:
    """Map a raw OMEN signal dict to our OmenSignal model."""
    # Evidence: OMEN sends a list of evidence items → collapse to dict
    evidence_raw = raw.get("evidence", [])
    if isinstance(evidence_raw, list):
        evidence = {
            "sources": [
                {
                    "source": e.get("source", ""),
                    "source_type": e.get("source_type", ""),
                    "url": e.get("url"),
                }
                for e in evidence_raw
            ],
            "count": len(evidence_raw),
        }
    elif isinstance(evidence_raw, dict):
        evidence = evidence_raw
    else:
        evidence = {}

    # Context: build from geographic + temporal + category info
    context: dict = {}
    geo = raw.get("geographic") or {}
    if geo:
        context["regions"] = geo.get("regions", [])
        context["chokepoints"] = geo.get("chokepoints", [])
    temporal = raw.get("temporal") or {}
    if temporal:
        context["event_horizon"] = temporal.get("event_horizon")
        context["resolution_date"] = temporal.get("resolution_date")
    if raw.get("tags"):
        context["tags"] = raw["tags"]

    confidence = float(raw.get("confidence_score", 0.0))

    return OmenSignal(
        id=raw.get("signal_id", raw.get("id", "")),
        signal_type=raw.get("signal_type", "unknown"),
        confidence=confidence,
        severity_score=confidence * 100,  # Derive: 0-1 → 0-100
        evidence=evidence,
        context=context,
        created_at=raw.get("generated_at", raw.get("observed_at", "")),
        title=raw.get("title", ""),
        description=raw.get("description", ""),
        probability=float(raw.get("probability", 0.0)),
        category=raw.get("category", ""),
    )


def _extract_signals(body: dict | list) -> list[dict]:
    """
    Extract signal list from OMEN response (handles both formats).

    Real OMEN:  {"data": {"signals": [...]}, "meta": {...}}
    Mock OMEN:  [...]  (flat list)
    """
    if isinstance(body, list):
        return body

    if isinstance(body, dict):
        # Standard OMEN envelope: data.signals
        data = body.get("data")
        if isinstance(data, dict):
            signals = data.get("signals")
            if isinstance(signals, list):
                return signals
        # Maybe signals directly in data
        if isinstance(data, list):
            return data
        # Maybe flat dict with signals key
        signals = body.get("signals")
        if isinstance(signals, list):
            return signals

    return []


class OmenClient:
    """
    HTTP client for OMEN API.

    OMEN is external — RiskCast does NOT depend on OMEN availability.
    All methods return empty lists on failure (graceful degradation).
    """

    def __init__(self, base_url: str, api_key: str = "", timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _client(self, timeout: float | None = None) -> httpx.AsyncClient:
        """Create an httpx client that follows redirects (OMEN uses trailing-slash redirects)."""
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return httpx.AsyncClient(
            timeout=timeout or self.timeout,
            follow_redirects=True,
            headers=headers,
        )

    async def get_signals(
        self,
        signal_type: str | None = None,
        min_confidence: float = 0.0,
        limit: int = 50,
    ) -> list[OmenSignal]:
        """Fetch signals from OMEN. Returns empty list if unavailable."""
        params: dict = {"limit": limit, "min_confidence": min_confidence}
        if signal_type:
            params["signal_type"] = signal_type

        try:
            async with self._client() as client:
                resp = await client.get(
                    f"{self.base_url}/api/v1/signals", params=params
                )
                resp.raise_for_status()
                raw_signals = _extract_signals(resp.json())
                signals = []
                for s in raw_signals:
                    try:
                        signals.append(_parse_omen_signal(s))
                    except Exception as parse_err:
                        logger.debug(
                            "omen_signal_parse_skip",
                            signal_id=s.get("signal_id", "?"),
                            error=str(parse_err),
                        )
                logger.info(
                    "omen_signals_fetched",
                    total=len(signals),
                    requested_limit=limit,
                )
                return signals
        except Exception as e:
            logger.warning("omen_unavailable", error=str(e), endpoint="signals")
            return []

    async def get_market_signals(
        self, location: str | None = None
    ) -> list[OmenSignal]:
        """Fetch market-specific signals. Returns empty list if unavailable."""
        params: dict = {}
        if location:
            params["location"] = location

        try:
            async with self._client() as client:
                resp = await client.get(
                    f"{self.base_url}/api/v1/signals/market", params=params
                )
                resp.raise_for_status()
                raw_signals = _extract_signals(resp.json())
                return [_parse_omen_signal(s) for s in raw_signals]
        except Exception as e:
            logger.warning(
                "omen_market_signals_unavailable",
                error=str(e),
                location=location,
            )
            return []

    async def health_check(self) -> bool:
        """Check if OMEN is reachable."""
        try:
            async with self._client(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False
