"""
Pipeline Health Monitor — Signal freshness, lag detection, gap detection.

Monitors:
1. Signal freshness: how recently signals were received
2. Ingest lag: delay between OMEN emitting and RiskCast ingesting
3. Gap detection: periods with no signals (unexpected silence)
4. Volume anomalies: unusual spikes or drops in signal volume
5. Error rates: ingest failure rate trends

All metrics are derived from real DB data — no mocking.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import OmenIngestSignal, SignalLedger

logger = structlog.get_logger(__name__)

# Configuration
FRESHNESS_STALE_MINUTES: int = 60       # >1 hour = stale
FRESHNESS_OUTDATED_MINUTES: int = 360   # >6 hours = outdated
GAP_THRESHOLD_MINUTES: int = 120        # >2 hours silence = gap
VOLUME_ANOMALY_FACTOR: float = 3.0      # 3x normal = anomaly


class PipelineHealth:
    """Snapshot of pipeline health metrics."""

    def __init__(
        self,
        last_signal_at: Optional[str],
        freshness_status: str,
        minutes_since_last: float,
        avg_ingest_lag_seconds: float,
        max_ingest_lag_seconds: float,
        signals_last_hour: int,
        signals_last_24h: int,
        avg_hourly_volume: float,
        volume_status: str,
        gaps_detected: list[dict],
        error_rate_24h: float,
        total_ingested_24h: int,
        total_errors_24h: int,
        overall_status: str,
        recommendations: list[str],
    ):
        self.last_signal_at = last_signal_at
        self.freshness_status = freshness_status
        self.minutes_since_last = minutes_since_last
        self.avg_ingest_lag_seconds = avg_ingest_lag_seconds
        self.max_ingest_lag_seconds = max_ingest_lag_seconds
        self.signals_last_hour = signals_last_hour
        self.signals_last_24h = signals_last_24h
        self.avg_hourly_volume = avg_hourly_volume
        self.volume_status = volume_status
        self.gaps_detected = gaps_detected
        self.error_rate_24h = error_rate_24h
        self.total_ingested_24h = total_ingested_24h
        self.total_errors_24h = total_errors_24h
        self.overall_status = overall_status
        self.recommendations = recommendations

    def to_dict(self) -> dict:
        mins = self.minutes_since_last
        if mins == float("inf"):
            mins = -1  # -1 indicates no data
        return {
            "last_signal_at": self.last_signal_at,
            "freshness_status": self.freshness_status,
            "minutes_since_last": round(mins, 1),
            "ingest_lag": {
                "avg_seconds": round(self.avg_ingest_lag_seconds, 2),
                "max_seconds": round(self.max_ingest_lag_seconds, 2),
            },
            "volume": {
                "last_hour": self.signals_last_hour,
                "last_24h": self.signals_last_24h,
                "avg_hourly": round(self.avg_hourly_volume, 1),
                "status": self.volume_status,
            },
            "gaps_detected": self.gaps_detected,
            "errors": {
                "rate_24h": round(self.error_rate_24h, 4),
                "total_ingested_24h": self.total_ingested_24h,
                "total_errors_24h": self.total_errors_24h,
            },
            "overall_status": self.overall_status,
            "recommendations": self.recommendations,
        }


class PipelineHealthMonitor:
    """
    Monitors the OMEN → RiskCast signal pipeline health.

    Queries real DB data to detect freshness issues, gaps, and anomalies.
    """

    async def check_health(self, session: AsyncSession) -> PipelineHealth:
        """Run all health checks and return a PipelineHealth snapshot."""
        now = datetime.utcnow()
        recommendations: list[str] = []

        # ── 1. Signal freshness ───────────────────────────────────────
        last_signal_at, minutes_since = await self._check_freshness(session, now)
        freshness_status = self._classify_freshness(minutes_since)

        if freshness_status == "no_data":
            recommendations.append(
                "No signals ever received. Verify OMEN integration is configured."
            )
        elif freshness_status == "outdated":
            recommendations.append(
                f"No signals for {minutes_since:.0f}m. Check OMEN connectivity."
            )
        elif freshness_status == "stale":
            recommendations.append(
                f"Last signal was {minutes_since:.0f}m ago. Monitor OMEN pipeline."
            )

        # ── 2. Ingest lag ─────────────────────────────────────────────
        avg_lag, max_lag = await self._check_ingest_lag(session, now)

        if max_lag > 300:  # >5 minutes
            recommendations.append(
                f"High ingest lag detected (max {max_lag:.0f}s). "
                "Check network or processing bottlenecks."
            )

        # ── 3. Volume ─────────────────────────────────────────────────
        last_hour, last_24h, avg_hourly = await self._check_volume(session, now)
        volume_status = self._classify_volume(last_hour, avg_hourly)

        if volume_status == "spike":
            recommendations.append(
                f"Signal volume spike: {last_hour} in last hour "
                f"(avg {avg_hourly:.0f}/h). Investigate source."
            )
        elif volume_status == "drought":
            recommendations.append(
                "Signal volume is unusually low. Check data sources."
            )

        # ── 4. Gap detection ──────────────────────────────────────────
        gaps = await self._detect_gaps(session, now)
        if gaps:
            recommendations.append(
                f"Detected {len(gaps)} signal gap(s) in the last 24h. "
                "Run reconciliation to replay missed signals."
            )

        # ── 5. Error rate ─────────────────────────────────────────────
        total_ingested, total_errors = await self._check_errors(session, now)
        total = total_ingested + total_errors
        error_rate = total_errors / max(total, 1)

        if error_rate > 0.05:
            recommendations.append(
                f"Error rate is {error_rate:.1%}. Review ingest errors."
            )

        # ── Overall status ────────────────────────────────────────────
        overall = self._overall_status(
            freshness_status, error_rate, len(gaps), volume_status
        )

        return PipelineHealth(
            last_signal_at=last_signal_at,
            freshness_status=freshness_status,
            minutes_since_last=minutes_since,
            avg_ingest_lag_seconds=avg_lag,
            max_ingest_lag_seconds=max_lag,
            signals_last_hour=last_hour,
            signals_last_24h=last_24h,
            avg_hourly_volume=avg_hourly,
            volume_status=volume_status,
            gaps_detected=gaps,
            error_rate_24h=error_rate,
            total_ingested_24h=total_ingested,
            total_errors_24h=total_errors,
            overall_status=overall,
            recommendations=recommendations,
        )

    async def _check_freshness(
        self, session: AsyncSession, now: datetime
    ) -> tuple[Optional[str], float]:
        """Check when the last signal was ingested."""
        result = await session.execute(
            select(func.max(OmenIngestSignal.ingested_at))
        )
        last_at = result.scalar_one_or_none()

        if last_at is None:
            return None, float("inf")

        if last_at.tzinfo is None:
            last_at = last_at.replace(tzinfo=timezone.utc)

        minutes_since = (now - last_at).total_seconds() / 60.0
        return last_at.isoformat(), minutes_since

    def _classify_freshness(self, minutes_since: float) -> str:
        if minutes_since == float("inf"):
            return "no_data"
        if minutes_since < FRESHNESS_STALE_MINUTES:
            return "fresh"
        if minutes_since < FRESHNESS_OUTDATED_MINUTES:
            return "stale"
        return "outdated"

    async def _check_ingest_lag(
        self, session: AsyncSession, now: datetime
    ) -> tuple[float, float]:
        """Compute average and max lag between emitted_at and ingested_at."""
        cutoff = now - timedelta(hours=24)
        result = await session.execute(
            select(
                OmenIngestSignal.emitted_at,
                OmenIngestSignal.ingested_at,
            )
            .where(
                OmenIngestSignal.ingested_at >= cutoff,
                OmenIngestSignal.emitted_at.isnot(None),
            )
        )
        rows = result.all()

        if not rows:
            return 0.0, 0.0

        lags: list[float] = []
        for emitted_at, ingested_at in rows:
            if emitted_at and ingested_at:
                e = emitted_at.replace(tzinfo=timezone.utc) if emitted_at.tzinfo is None else emitted_at
                i = ingested_at.replace(tzinfo=timezone.utc) if ingested_at.tzinfo is None else ingested_at
                lag = (i - e).total_seconds()
                if lag >= 0:
                    lags.append(lag)

        if not lags:
            return 0.0, 0.0

        return sum(lags) / len(lags), max(lags)

    async def _check_volume(
        self, session: AsyncSession, now: datetime
    ) -> tuple[int, int, float]:
        """Check signal volume: last hour, last 24h, average hourly."""
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(hours=24)

        result_hour = await session.execute(
            select(func.count(OmenIngestSignal.id)).where(
                OmenIngestSignal.ingested_at >= hour_ago,
            )
        )
        last_hour = result_hour.scalar_one() or 0

        result_day = await session.execute(
            select(func.count(OmenIngestSignal.id)).where(
                OmenIngestSignal.ingested_at >= day_ago,
            )
        )
        last_24h = result_day.scalar_one() or 0

        avg_hourly = last_24h / 24.0
        return last_hour, last_24h, avg_hourly

    def _classify_volume(self, last_hour: int, avg_hourly: float) -> str:
        if avg_hourly < 0.5:
            return "no_baseline"
        if last_hour > avg_hourly * VOLUME_ANOMALY_FACTOR:
            return "spike"
        if avg_hourly > 1 and last_hour < avg_hourly * 0.1:
            return "drought"
        return "normal"

    async def _detect_gaps(
        self, session: AsyncSession, now: datetime
    ) -> list[dict]:
        """Detect gaps >2 hours in the last 24h."""
        cutoff = now - timedelta(hours=24)
        result = await session.execute(
            select(OmenIngestSignal.ingested_at)
            .where(OmenIngestSignal.ingested_at >= cutoff)
            .order_by(OmenIngestSignal.ingested_at)
        )
        times = [row[0] for row in result.all()]

        gaps: list[dict] = []
        for i in range(1, len(times)):
            prev = times[i - 1]
            curr = times[i]
            if prev.tzinfo is None:
                prev = prev.replace(tzinfo=timezone.utc)
            if curr.tzinfo is None:
                curr = curr.replace(tzinfo=timezone.utc)
            gap_minutes = (curr - prev).total_seconds() / 60.0
            if gap_minutes > GAP_THRESHOLD_MINUTES:
                gaps.append({
                    "start": prev.isoformat(),
                    "end": curr.isoformat(),
                    "duration_minutes": round(gap_minutes, 1),
                })

        return gaps

    async def _check_errors(
        self, session: AsyncSession, now: datetime
    ) -> tuple[int, int]:
        """Count ingested and errored signals in last 24h."""
        cutoff = now - timedelta(hours=24)

        ingested = await session.execute(
            select(func.count(OmenIngestSignal.id)).where(
                OmenIngestSignal.ingested_at >= cutoff,
            )
        )
        total_ingested = ingested.scalar_one() or 0

        errored = await session.execute(
            select(func.count(SignalLedger.id)).where(
                SignalLedger.recorded_at >= cutoff,
                SignalLedger.status == "failed",
            )
        )
        total_errors = errored.scalar_one() or 0

        return total_ingested, total_errors

    def _overall_status(
        self,
        freshness: str,
        error_rate: float,
        gap_count: int,
        volume: str,
    ) -> str:
        if freshness in ("outdated", "no_data") or error_rate > 0.1:
            return "critical"
        if freshness == "stale" or error_rate > 0.05 or gap_count > 2:
            return "degraded"
        if gap_count > 0 or volume == "spike":
            return "warning"
        return "healthy"
