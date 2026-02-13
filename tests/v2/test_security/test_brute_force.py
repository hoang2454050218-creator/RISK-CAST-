"""
Brute Force Protection Tests.

Tests: lockout thresholds, progressive delay, unlock after timeout, email + IP tracking.
"""

import time

import pytest

from riskcast.middleware.brute_force import AttemptTracker, BruteForceProtection


class TestAttemptTracker:
    """Test the per-key attempt tracker."""

    def test_initial_state(self):
        """Fresh tracker has no attempts and is not locked."""
        tracker = AttemptTracker()
        assert tracker.failure_count == 0
        assert not tracker.is_locked(time.monotonic())

    def test_record_failure(self):
        """Recording a failure increments the count."""
        tracker = AttemptTracker()
        tracker.record_failure(time.monotonic())
        assert tracker.failure_count == 1

    def test_prune_old_attempts(self):
        """Old attempts are pruned outside the window."""
        tracker = AttemptTracker()
        old_time = time.monotonic() - 1000
        tracker.record_failure(old_time)
        assert tracker.failure_count == 1
        tracker.prune_old(time.monotonic(), window_seconds=500)
        assert tracker.failure_count == 0

    def test_lock_and_check(self):
        """Locked tracker reports locked until duration expires."""
        tracker = AttemptTracker()
        now = time.monotonic()
        tracker.lock(10.0, now)
        assert tracker.is_locked(now + 5)
        assert not tracker.is_locked(now + 11)


class TestBruteForceProtection:
    """Test the full brute force protection system."""

    def _make_bf(self, **kwargs):
        """Create a BruteForceProtection with custom thresholds for fast tests."""
        defaults = {
            "ip_max_attempts": 3,
            "ip_window_seconds": 60.0,
            "ip_lockout_seconds": 30.0,
            "email_max_attempts": 5,
            "email_window_seconds": 120.0,
            "email_lockout_seconds": 60.0,
        }
        defaults.update(kwargs)
        return BruteForceProtection(**defaults)

    def test_initial_allowed(self):
        """First attempt is always allowed."""
        bf = self._make_bf()
        allowed, reason, retry = bf.check_allowed("1.2.3.4", "user@test.com")
        assert allowed
        assert reason == ""
        assert retry == 0

    def test_ip_lockout_after_threshold(self):
        """IP is locked after max failures."""
        bf = self._make_bf(ip_max_attempts=3)
        for _ in range(3):
            bf.record_failure("1.2.3.4", "user@test.com")

        allowed, reason, retry = bf.check_allowed("1.2.3.4")
        assert not allowed
        assert "IP" in reason
        assert retry > 0

    def test_email_lockout_after_threshold(self):
        """Email is locked after max failures (from different IPs)."""
        bf = self._make_bf(email_max_attempts=3)
        for i in range(3):
            bf.record_failure(f"10.0.0.{i}", "target@test.com")

        allowed, reason, _ = bf.check_allowed("10.0.0.99", "target@test.com")
        assert not allowed
        assert "locked" in reason.lower()

    def test_different_ips_not_affected(self):
        """Failures from one IP don't lock another."""
        bf = self._make_bf(ip_max_attempts=3)
        for _ in range(3):
            bf.record_failure("1.1.1.1")

        allowed, _, _ = bf.check_allowed("2.2.2.2")
        assert allowed

    def test_success_clears_counters(self):
        """Successful login clears failure history."""
        bf = self._make_bf(ip_max_attempts=5)
        for _ in range(4):
            bf.record_failure("1.2.3.4", "user@test.com")

        bf.record_success("1.2.3.4", "user@test.com")

        # Should be allowed again (counters cleared)
        allowed, _, _ = bf.check_allowed("1.2.3.4", "user@test.com")
        assert allowed

    def test_progressive_delay_none_initially(self):
        """No delay for first few attempts."""
        bf = self._make_bf()
        assert bf.get_progressive_delay("1.2.3.4") == 0.0

    def test_progressive_delay_after_3_failures(self):
        """Delay kicks in after 3 failures: 1s, 2s, 4s, 8s."""
        bf = self._make_bf(ip_max_attempts=20)  # Don't lock
        for _ in range(3):
            bf.record_failure("1.2.3.4")
        assert bf.get_progressive_delay("1.2.3.4") == 1.0

        bf.record_failure("1.2.3.4")
        assert bf.get_progressive_delay("1.2.3.4") == 2.0

        bf.record_failure("1.2.3.4")
        assert bf.get_progressive_delay("1.2.3.4") == 4.0

        bf.record_failure("1.2.3.4")
        assert bf.get_progressive_delay("1.2.3.4") == 8.0

    def test_progressive_delay_capped(self):
        """Delay is capped at 8 seconds."""
        bf = self._make_bf(ip_max_attempts=100)
        for _ in range(20):
            bf.record_failure("1.2.3.4")
        assert bf.get_progressive_delay("1.2.3.4") == 8.0

    def test_email_case_insensitive(self):
        """Email tracking is case-insensitive."""
        bf = self._make_bf(email_max_attempts=2)
        bf.record_failure("1.1.1.1", "User@Test.COM")
        bf.record_failure("2.2.2.2", "user@test.com")

        allowed, _, _ = bf.check_allowed("3.3.3.3", "USER@TEST.COM")
        assert not allowed
