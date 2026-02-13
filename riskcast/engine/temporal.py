"""
Temporal Risk Decay Engine.

Signals lose relevance over time. A port closure from 3 months ago
is less relevant than one from yesterday.

Implements:
- Exponential decay: weight = e^(-λt)
- Configurable half-life per signal type
- Time-weighted signal aggregation
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────

# Half-life in hours: after this many hours, signal weight = 0.5
DEFAULT_HALF_LIVES: dict[str, float] = {
    "payment_risk": 720.0,           # 30 days (payment patterns are slow-moving)
    "route_disruption": 168.0,       # 7 days (routes change frequently)
    "order_risk_composite": 336.0,   # 14 days
    "market_volatility": 72.0,       # 3 days (markets move fast)
    "port_closure": 48.0,            # 2 days (very time-sensitive)
    "weather_alert": 24.0,           # 1 day
    "default": 168.0,                # 7 days fallback
}

MIN_WEIGHT: float = 0.01  # Below this, signal is considered expired


@dataclass(frozen=True)
class DecayedSignal:
    """A signal with its temporal decay weight applied."""
    signal_type: str
    original_score: float       # Raw severity (0-100)
    decayed_score: float        # After decay applied
    decay_weight: float         # 0-1 (1 = fresh, 0 = expired)
    age_hours: float            # How old the signal is
    half_life_hours: float      # Half-life used
    is_expired: bool            # decay_weight < MIN_WEIGHT


@dataclass(frozen=True)
class TemporalAggregation:
    """Result of time-weighted signal aggregation."""
    weighted_score: float       # Time-weighted average score
    n_active: int               # Non-expired signals
    n_expired: int              # Expired signals (excluded)
    avg_age_hours: float        # Average age of active signals
    freshness: str              # "fresh" | "aging" | "stale"
    signals: list[DecayedSignal]


class TemporalDecayEngine:
    """
    Apply exponential time decay to risk signals.

    weight(t) = e^(-λt) where λ = ln(2) / half_life
    """

    def __init__(self, half_lives: Optional[dict[str, float]] = None):
        self.half_lives = half_lives or DEFAULT_HALF_LIVES.copy()

    def compute_decay(
        self,
        signal_type: str,
        severity_score: float,
        signal_timestamp: datetime,
        now: Optional[datetime] = None,
    ) -> DecayedSignal:
        """Compute the decayed score for a single signal."""
        if now is None:
            now = datetime.utcnow()

        # Ensure timezone-aware comparison
        if signal_timestamp.tzinfo is None:
            signal_timestamp = signal_timestamp.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        age_hours = (now - signal_timestamp).total_seconds() / 3600.0
        half_life = self.half_lives.get(signal_type, self.half_lives.get("default", 168.0))

        # Exponential decay: w = e^(-λt) where λ = ln(2) / half_life
        decay_lambda = math.log(2) / half_life
        weight = math.exp(-decay_lambda * age_hours)
        is_expired = weight < MIN_WEIGHT

        return DecayedSignal(
            signal_type=signal_type,
            original_score=severity_score,
            decayed_score=round(severity_score * weight, 2),
            decay_weight=round(weight, 6),
            age_hours=round(age_hours, 1),
            half_life_hours=half_life,
            is_expired=is_expired,
        )

    def aggregate(
        self,
        signals: list[tuple[str, float, datetime]],  # (type, severity, timestamp)
        now: Optional[datetime] = None,
    ) -> TemporalAggregation:
        """
        Aggregate signals with temporal decay.

        Expired signals are excluded. Active signals are weighted by freshness.
        """
        if now is None:
            now = datetime.utcnow()

        decayed: list[DecayedSignal] = []
        for sig_type, severity, ts in signals:
            d = self.compute_decay(sig_type, severity, ts, now)
            decayed.append(d)

        active = [d for d in decayed if not d.is_expired]
        expired = [d for d in decayed if d.is_expired]

        if active:
            total_weight = sum(d.decay_weight for d in active)
            weighted_score = sum(d.decayed_score * d.decay_weight for d in active) / total_weight
            avg_age = sum(d.age_hours for d in active) / len(active)
        else:
            weighted_score = 0.0
            avg_age = 0.0

        # Freshness classification
        if not active:
            freshness = "stale"
        elif avg_age < 24:
            freshness = "fresh"
        elif avg_age < 168:
            freshness = "aging"
        else:
            freshness = "stale"

        return TemporalAggregation(
            weighted_score=round(weighted_score, 2),
            n_active=len(active),
            n_expired=len(expired),
            avg_age_hours=round(avg_age, 1),
            freshness=freshness,
            signals=decayed,
        )
