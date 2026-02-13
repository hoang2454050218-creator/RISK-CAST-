"""
Alert Deduplication & Cooldown — Prevent alert storms.

Strategies:
1. Cooldown: Don't fire the same rule again within N minutes
2. Daily limit: Max N alerts per rule per day
3. Content dedup: Don't re-alert for the same metric + entity + threshold

All state is tracked in-memory (for speed) and backed by DB (for persistence).
"""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog

from riskcast.alerting.schemas import AlertRecord, AlertStatus

logger = structlog.get_logger(__name__)


class DedupManager:
    """
    Manages alert deduplication and cooldown.

    In-memory state for fast lookups, persistent via DB for durability.
    """

    def __init__(self):
        # In-memory state: rule_id → last fire time
        self._last_fired: dict[str, datetime] = {}
        # In-memory state: rule_id → count today
        self._daily_counts: dict[str, int] = {}
        # In-memory state: content_hash → last fire time
        self._content_hashes: dict[str, datetime] = {}
        # Track the "today" for resetting daily counts
        self._count_date: Optional[datetime] = None

    def should_suppress(
        self,
        alert: AlertRecord,
        cooldown_minutes: int,
        max_per_day: int,
    ) -> tuple[bool, str]:
        """
        Check if an alert should be suppressed.

        Args:
            alert: The alert to check
            cooldown_minutes: Minimum minutes between alerts for same rule
            max_per_day: Maximum alerts for this rule per day

        Returns:
            (should_suppress: bool, reason: str)
        """
        now = datetime.utcnow()
        self._maybe_reset_daily(now)

        # ── 1. Cooldown check ─────────────────────────────────────────
        last_time = self._last_fired.get(alert.rule_id)
        if last_time:
            elapsed = (now - last_time).total_seconds() / 60.0
            if elapsed < cooldown_minutes:
                remaining = cooldown_minutes - elapsed
                reason = (
                    f"Cooldown active: {remaining:.0f}m remaining "
                    f"(rule '{alert.rule_name}' fired {elapsed:.0f}m ago)"
                )
                logger.debug(
                    "alert_suppressed_cooldown",
                    rule_id=alert.rule_id,
                    elapsed_minutes=round(elapsed, 1),
                    cooldown_minutes=cooldown_minutes,
                )
                return True, reason

        # ── 2. Daily limit check ──────────────────────────────────────
        daily_count = self._daily_counts.get(alert.rule_id, 0)
        if daily_count >= max_per_day:
            reason = (
                f"Daily limit reached: {daily_count}/{max_per_day} "
                f"alerts for rule '{alert.rule_name}'"
            )
            logger.debug(
                "alert_suppressed_daily_limit",
                rule_id=alert.rule_id,
                daily_count=daily_count,
                max_per_day=max_per_day,
            )
            return True, reason

        # ── 3. Content dedup check ────────────────────────────────────
        content_hash = self._compute_content_hash(alert)
        last_content_time = self._content_hashes.get(content_hash)
        if last_content_time:
            elapsed = (now - last_content_time).total_seconds() / 60.0
            # Content dedup uses max(2x cooldown, 60 minutes) to prevent duplicates
            content_cooldown = max(cooldown_minutes * 2, 60)
            if elapsed < content_cooldown:
                reason = (
                    f"Duplicate content: same alert for "
                    f"{alert.metric}={alert.metric_value:.2f} "
                    f"on {alert.entity_type}/{alert.entity_id} "
                    f"was sent {elapsed:.0f}m ago"
                )
                logger.debug(
                    "alert_suppressed_content_dedup",
                    rule_id=alert.rule_id,
                    content_hash=content_hash[:16],
                )
                return True, reason

        return False, ""

    def record_fired(self, alert: AlertRecord) -> None:
        """Record that an alert was fired (updates cooldown and counts)."""
        now = datetime.utcnow()
        self._maybe_reset_daily(now)
        self._last_fired[alert.rule_id] = now
        self._daily_counts[alert.rule_id] = (
            self._daily_counts.get(alert.rule_id, 0) + 1
        )
        content_hash = self._compute_content_hash(alert)
        self._content_hashes[content_hash] = now

    def get_daily_count(self, rule_id: str) -> int:
        """Get the current daily alert count for a rule."""
        self._maybe_reset_daily(datetime.utcnow())
        return self._daily_counts.get(rule_id, 0)

    def reset(self) -> None:
        """Reset all state (for testing)."""
        self._last_fired.clear()
        self._daily_counts.clear()
        self._content_hashes.clear()
        self._count_date = None

    def _maybe_reset_daily(self, now: datetime) -> None:
        """Reset daily counts if the date has changed."""
        today = now.date()
        if self._count_date is None or self._count_date != today:
            self._daily_counts.clear()
            self._count_date = today

    def _compute_content_hash(self, alert: AlertRecord) -> str:
        """Compute a content hash for dedup — same metric/entity/threshold → same hash."""
        content = (
            f"{alert.rule_id}|{alert.metric}|"
            f"{alert.metric_value:.2f}|{alert.threshold}|"
            f"{alert.entity_type}|{alert.entity_id}"
        )
        return hashlib.sha256(content.encode()).hexdigest()
