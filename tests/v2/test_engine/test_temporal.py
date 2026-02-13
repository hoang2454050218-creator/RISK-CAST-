"""
Temporal Decay Engine Tests.
"""

import math
from datetime import datetime, timedelta, timezone

import pytest

from riskcast.engine.temporal import (
    TemporalDecayEngine,
    MIN_WEIGHT,
)


class TestTemporalDecay:
    """Test exponential time decay."""

    def setup_method(self):
        self.engine = TemporalDecayEngine()
        self.now = datetime(2026, 2, 11, 12, 0, 0, tzinfo=timezone.utc)

    def test_fresh_signal_full_weight(self):
        """A signal from now has decay_weight ≈ 1.0."""
        result = self.engine.compute_decay(
            "payment_risk", 80.0, self.now, self.now
        )
        assert abs(result.decay_weight - 1.0) < 0.01
        assert abs(result.decayed_score - 80.0) < 1.0
        assert not result.is_expired

    def test_half_life_gives_half_weight(self):
        """At exactly one half-life, weight ≈ 0.5."""
        half_life_hours = 720  # payment_risk default
        half_life_ago = self.now - timedelta(hours=half_life_hours)
        result = self.engine.compute_decay(
            "payment_risk", 100.0, half_life_ago, self.now
        )
        assert abs(result.decay_weight - 0.5) < 0.05

    def test_old_signal_low_weight(self):
        """A very old signal has near-zero weight."""
        very_old = self.now - timedelta(days=365)
        result = self.engine.compute_decay(
            "weather_alert", 100.0, very_old, self.now
        )
        assert result.is_expired
        assert result.decay_weight < MIN_WEIGHT

    def test_different_half_lives(self):
        """Different signal types decay at different rates."""
        one_week_ago = self.now - timedelta(days=7)

        market = self.engine.compute_decay("market_volatility", 80.0, one_week_ago, self.now)
        payment = self.engine.compute_decay("payment_risk", 80.0, one_week_ago, self.now)

        # Market (72h half-life) decays faster than payment (720h)
        assert market.decay_weight < payment.decay_weight

    def test_decayed_score_equals_original_times_weight(self):
        """Decayed score = original × weight."""
        ts = self.now - timedelta(hours=100)
        result = self.engine.compute_decay("route_disruption", 60.0, ts, self.now)
        expected = 60.0 * result.decay_weight
        assert abs(result.decayed_score - expected) < 0.1


class TestTemporalAggregation:
    """Test time-weighted signal aggregation."""

    def setup_method(self):
        self.engine = TemporalDecayEngine()
        self.now = datetime(2026, 2, 11, 12, 0, 0, tzinfo=timezone.utc)

    def test_empty_signals(self):
        """Empty signals → zero score."""
        result = self.engine.aggregate([], self.now)
        assert result.weighted_score == 0.0
        assert result.n_active == 0
        assert result.freshness == "stale"

    def test_all_fresh(self):
        """All fresh signals → freshness is 'fresh'."""
        signals = [
            ("payment_risk", 80.0, self.now - timedelta(hours=1)),
            ("route_disruption", 60.0, self.now - timedelta(hours=2)),
        ]
        result = self.engine.aggregate(signals, self.now)
        assert result.freshness == "fresh"
        assert result.n_active == 2
        assert result.n_expired == 0

    def test_mixed_fresh_and_expired(self):
        """Some fresh, some expired → only active count."""
        signals = [
            ("payment_risk", 80.0, self.now - timedelta(hours=1)),
            ("weather_alert", 60.0, self.now - timedelta(days=365)),  # Very old
        ]
        result = self.engine.aggregate(signals, self.now)
        assert result.n_active == 1
        assert result.n_expired == 1

    def test_fresher_signals_weighted_more(self):
        """Fresher signals contribute more to the weighted score."""
        fresh = ("payment_risk", 30.0, self.now - timedelta(hours=1))
        old = ("payment_risk", 90.0, self.now - timedelta(days=30))
        result = self.engine.aggregate([fresh, old], self.now)
        # Should be closer to 30 (fresh) than 90 (old)
        assert result.weighted_score < 60
