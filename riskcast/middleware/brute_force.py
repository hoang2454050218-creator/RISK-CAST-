"""
Brute Force Protection — OWASP A07 Coverage.

Separate rate limiter for authentication endpoints.
- 5 failed attempts per IP per 15 minutes → 15 min lockout
- 10 failed attempts per email per hour → 1 hour lockout
- Progressive delay: 1s, 2s, 4s, 8s between attempts after 3 failures
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class AttemptTracker:
    """Track failed login attempts for a single key (IP or email)."""

    attempts: list[float] = field(default_factory=list)
    locked_until: float = 0.0

    def record_failure(self, now: float) -> None:
        """Record a failed attempt timestamp."""
        self.attempts.append(now)

    def prune_old(self, now: float, window_seconds: float) -> None:
        """Remove attempts outside the tracking window."""
        cutoff = now - window_seconds
        self.attempts = [t for t in self.attempts if t > cutoff]

    @property
    def failure_count(self) -> int:
        return len(self.attempts)

    def is_locked(self, now: float) -> bool:
        return now < self.locked_until

    def lock(self, duration_seconds: float, now: float) -> None:
        self.locked_until = now + duration_seconds


class BruteForceProtection:
    """
    In-memory brute force protection for login endpoints.

    Two tracking dimensions:
    1. Per IP: 5 failures in 15min → 15min lockout
    2. Per email: 10 failures in 60min → 60min lockout
    """

    def __init__(
        self,
        ip_max_attempts: int = 5,
        ip_window_seconds: float = 900.0,   # 15 minutes
        ip_lockout_seconds: float = 900.0,   # 15 minutes
        email_max_attempts: int = 10,
        email_window_seconds: float = 3600.0,  # 1 hour
        email_lockout_seconds: float = 3600.0,  # 1 hour
    ):
        self.ip_max = ip_max_attempts
        self.ip_window = ip_window_seconds
        self.ip_lockout = ip_lockout_seconds
        self.email_max = email_max_attempts
        self.email_window = email_window_seconds
        self.email_lockout = email_lockout_seconds
        self._ip_trackers: dict[str, AttemptTracker] = defaultdict(AttemptTracker)
        self._email_trackers: dict[str, AttemptTracker] = defaultdict(AttemptTracker)

    def check_allowed(self, ip: str, email: str | None = None) -> tuple[bool, str, int]:
        """
        Check if a login attempt is allowed.

        Returns:
            (allowed, reason, retry_after_seconds)
        """
        now = time.monotonic()

        # Check IP lockout
        ip_tracker = self._ip_trackers[ip]
        if ip_tracker.is_locked(now):
            remaining = int(ip_tracker.locked_until - now)
            return False, "Too many failed attempts from this IP", remaining

        # Check email lockout
        if email:
            email_lower = email.lower()
            email_tracker = self._email_trackers[email_lower]
            if email_tracker.is_locked(now):
                remaining = int(email_tracker.locked_until - now)
                return False, "Account temporarily locked", remaining

        return True, "", 0

    def record_failure(self, ip: str, email: str | None = None) -> None:
        """Record a failed login attempt."""
        now = time.monotonic()

        # IP tracking
        ip_tracker = self._ip_trackers[ip]
        ip_tracker.prune_old(now, self.ip_window)
        ip_tracker.record_failure(now)

        if ip_tracker.failure_count >= self.ip_max:
            ip_tracker.lock(self.ip_lockout, now)
            logger.warning("brute_force_ip_locked", ip=ip, failures=ip_tracker.failure_count)

        # Email tracking
        if email:
            email_lower = email.lower()
            email_tracker = self._email_trackers[email_lower]
            email_tracker.prune_old(now, self.email_window)
            email_tracker.record_failure(now)

            if email_tracker.failure_count >= self.email_max:
                email_tracker.lock(self.email_lockout, now)
                logger.warning(
                    "brute_force_email_locked",
                    email=email_lower,
                    failures=email_tracker.failure_count,
                )

    def record_success(self, ip: str, email: str | None = None) -> None:
        """Record a successful login — clears attempt history."""
        if ip in self._ip_trackers:
            self._ip_trackers[ip] = AttemptTracker()
        if email and email.lower() in self._email_trackers:
            self._email_trackers[email.lower()] = AttemptTracker()

    def get_progressive_delay(self, ip: str) -> float:
        """
        Calculate progressive delay based on recent failures.

        After 3 failures: 1s, then 2s, 4s, 8s (capped at 8s).
        """
        tracker = self._ip_trackers.get(ip)
        if not tracker or tracker.failure_count < 3:
            return 0.0
        exponent = min(tracker.failure_count - 3, 3)  # cap at 2^3 = 8
        return float(2 ** exponent)


# Module-level singleton
_brute_force = BruteForceProtection()


def get_brute_force_protection() -> BruteForceProtection:
    """Get the singleton brute force protection instance."""
    return _brute_force
